#!/usr/bin/env python3
"""Analyze CuPy usage in top repositories using anonymous shallow git clones.

This stage does not use the GitHub API. It reads ``data/cupy_repos.json``,
clones the highest-star public repositories, checks out Python files only, and
counts import-aware ``cupy.`` and ``cp.`` attribute patterns. A ``cp.`` pattern
is counted only when that same file contains ``import cupy as cp``.

The analysis is resumable: completed repositories are saved to a checkpoint
after each batch. The final static output is ``data/cupy_analysis.json``.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "data" / "cupy_repos.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "cupy_analysis.json"
DEFAULT_CHECKPOINT = PROJECT_ROOT / "data" / ".cupy_analysis_checkpoint.json"
ANALYSIS_VERSION = "1.0_import_aware"

FALLBACK_CUPY_ATTRIBUTE_RE = re.compile(r"\bcupy\s*\.")
FALLBACK_CP_ATTRIBUTE_RE = re.compile(r"\bcp\s*\.")
FALLBACK_CP_IMPORT_RE = re.compile(
    r"^\s*import\s+[^#\n]*\bcupy\s+as\s+cp\b", re.MULTILINE
)
FALLBACK_CUPY_IMPORT_RE = re.compile(
    r"^\s*import\s+[^#\n]*\bcupy(?:\s+as\s+\w+)?\b", re.MULTILINE
)
FALLBACK_FROM_CUPY_RE = re.compile(
    r"^\s*from\s+cupy(?:\.[A-Za-z_]\w*)*\s+import\b", re.MULTILINE
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    temporary.replace(path)


@dataclass
class FileMetrics:
    file_path: str
    size_bytes: int
    cupy_patterns: int
    cp_patterns: int
    cupy_imports: int
    from_cupy_imports: int
    parsed_with_ast: bool

    @property
    def total_patterns(self) -> int:
        return self.cupy_patterns + self.cp_patterns


@dataclass
class RepositoryMetrics:
    repo_name: str
    stars: int
    forks: int
    python_files_analyzed: int
    files_with_cupy: int
    cupy_patterns: int
    cp_patterns: int
    cupy_imports: int
    from_cupy_imports: int
    coverage_percentage: float
    top_files: list[dict[str, Any]]
    clone_size_mb: float
    analysis_time_seconds: float


class CuPyAstVisitor(ast.NodeVisitor):
    """Collect imports and root-level CuPy attribute accesses."""

    def __init__(self) -> None:
        self.cupy_imports = 0
        self.from_cupy_imports = 0
        self.cupy_patterns = 0
        self.cp_attribute_candidates = 0
        self.cp_is_cupy_alias = False

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            if alias.name == "cupy":
                self.cupy_imports += 1
                if alias.asname == "cp":
                    self.cp_is_cupy_alias = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module == "cupy" or (node.module or "").startswith("cupy."):
            self.from_cupy_imports += 1
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        # Only count the first dot in an attribute chain. For cp.cuda.Device,
        # the cp.cuda node counts once and the outer .Device node does not.
        if isinstance(node.value, ast.Name):
            if node.value.id == "cupy":
                self.cupy_patterns += 1
            elif node.value.id == "cp":
                self.cp_attribute_candidates += 1
        self.generic_visit(node)

    @property
    def cp_patterns(self) -> int:
        return self.cp_attribute_candidates if self.cp_is_cupy_alias else 0


def analyze_python_source(path: Path, clone_dir: Path) -> FileMetrics | None:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        size_bytes = path.stat().st_size
    except OSError:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(content, filename=str(path))
        visitor = CuPyAstVisitor()
        visitor.visit(tree)
        cupy_patterns = visitor.cupy_patterns
        cp_patterns = visitor.cp_patterns
        cupy_imports = visitor.cupy_imports
        from_cupy_imports = visitor.from_cupy_imports
        parsed_with_ast = True
    except (SyntaxError, ValueError, RecursionError):
        cp_is_cupy_alias = bool(FALLBACK_CP_IMPORT_RE.search(content))
        cupy_patterns = len(FALLBACK_CUPY_ATTRIBUTE_RE.findall(content))
        cp_patterns = (
            len(FALLBACK_CP_ATTRIBUTE_RE.findall(content)) if cp_is_cupy_alias else 0
        )
        cupy_imports = len(FALLBACK_CUPY_IMPORT_RE.findall(content))
        from_cupy_imports = len(FALLBACK_FROM_CUPY_RE.findall(content))
        parsed_with_ast = False

    if not (cupy_patterns or cp_patterns or cupy_imports or from_cupy_imports):
        return None

    try:
        relative_path = path.relative_to(clone_dir).as_posix()
    except ValueError:
        relative_path = path.as_posix()

    return FileMetrics(
        file_path=relative_path,
        size_bytes=size_bytes,
        cupy_patterns=cupy_patterns,
        cp_patterns=cp_patterns,
        cupy_imports=cupy_imports,
        from_cupy_imports=from_cupy_imports,
        parsed_with_ast=parsed_with_ast,
    )


def directory_size_mb(path: Path) -> float:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


async def run_command(*args: str, timeout: int) -> tuple[int, str]:
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=environment,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 124, f"command timed out after {timeout}s"
    output = (stderr or stdout).decode("utf-8", errors="replace").strip()
    return process.returncode or 0, output


class CuPyLocalAnalyzer:
    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        checkpoint_path: Path,
        top_n: int,
        concurrency: int,
        max_file_size_mb: float,
        clone_timeout: int,
    ) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.checkpoint_path = checkpoint_path
        self.top_n = top_n
        self.concurrency = concurrency
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
        self.clone_timeout = clone_timeout

    def load_candidates(self) -> list[dict[str, Any]]:
        with self.input_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        repositories = data.get("repositories")
        if not isinstance(repositories, list):
            raise RuntimeError(f"Invalid repository data in {self.input_path}")
        repositories.sort(key=lambda repo: repo.get("stars", 0), reverse=True)
        return repositories[: self.top_n]

    def load_or_create_state(
        self, candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        repo_names = [repo["full_name"] for repo in candidates]
        if self.checkpoint_path.exists():
            with self.checkpoint_path.open(encoding="utf-8") as handle:
                state = json.load(handle)
            if state.get("analysis_version") != ANALYSIS_VERSION:
                raise RuntimeError(
                    f"Checkpoint version mismatch. Remove {self.checkpoint_path} to restart."
                )
            if state.get("requested_repositories") != repo_names:
                raise RuntimeError(
                    "Checkpoint repository selection differs from this run. "
                    f"Remove {self.checkpoint_path} or rerun with --top "
                    f"{len(state.get('requested_repositories', []))}."
                )
            print(f"Resuming from {self.checkpoint_path}", flush=True)
            return state

        state = {
            "analysis_version": ANALYSIS_VERSION,
            "started_at": utc_now(),
            "requested_repositories": repo_names,
            "results": {},
            "failures": {},
        }
        atomic_write_json(self.checkpoint_path, state)
        return state

    async def clone_repository(self, repo_name: str, clone_dir: Path) -> str | None:
        clone_url = f"https://github.com/{repo_name}.git"
        return_code, output = await run_command(
            "git",
            "clone",
            "--quiet",
            "--depth=1",
            "--filter=blob:none",
            "--no-checkout",
            clone_url,
            str(clone_dir),
            timeout=self.clone_timeout,
        )
        if return_code:
            return f"clone failed: {output}"

        return_code, output = await run_command(
            "git",
            "-C",
            str(clone_dir),
            "sparse-checkout",
            "set",
            "--no-cone",
            "*.py",
            timeout=60,
        )
        if return_code:
            return f"sparse-checkout setup failed: {output}"

        return_code, output = await run_command(
            "git",
            "-C",
            str(clone_dir),
            "checkout",
            "--quiet",
            "HEAD",
            timeout=self.clone_timeout,
        )
        if return_code:
            return f"checkout failed: {output}"
        return None

    def find_python_files(self, clone_dir: Path) -> list[Path]:
        files: list[Path] = []
        for path in clone_dir.rglob("*.py"):
            if ".git" in path.parts:
                continue
            try:
                if path.is_file() and path.stat().st_size <= self.max_file_size_bytes:
                    files.append(path)
            except OSError:
                continue
        return files

    async def analyze_repository(
        self,
        repo: dict[str, Any],
        clone_root: Path,
        index: int,
        total: int,
    ) -> tuple[str, dict[str, Any] | None, str | None]:
        repo_name = repo["full_name"]
        safe_name = repo_name.replace("/", "__")
        clone_dir = clone_root / safe_name
        started = time.monotonic()
        print(
            f"[{index}/{total}] {repo_name} ({repo.get('stars', 0):,} stars)",
            flush=True,
        )

        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        try:
            clone_error = await self.clone_repository(repo_name, clone_dir)
            if clone_error:
                return repo_name, None, clone_error

            python_files = self.find_python_files(clone_dir)
            file_metrics: list[FileMetrics] = []
            for path in python_files:
                metrics = analyze_python_source(path, clone_dir)
                if metrics:
                    file_metrics.append(metrics)

            file_metrics.sort(
                key=lambda item: (
                    item.total_patterns,
                    item.cupy_imports + item.from_cupy_imports,
                ),
                reverse=True,
            )
            files_with_cupy = len(file_metrics)
            python_files_analyzed = len(python_files)
            coverage = (
                files_with_cupy / python_files_analyzed * 100
                if python_files_analyzed
                else 0.0
            )
            top_files = []
            for metrics in file_metrics[:10]:
                serialized = asdict(metrics)
                serialized["total_patterns"] = metrics.total_patterns
                top_files.append(serialized)

            result = RepositoryMetrics(
                repo_name=repo_name,
                stars=int(repo.get("stars", 0)),
                forks=int(repo.get("forks", 0)),
                python_files_analyzed=python_files_analyzed,
                files_with_cupy=files_with_cupy,
                cupy_patterns=sum(item.cupy_patterns for item in file_metrics),
                cp_patterns=sum(item.cp_patterns for item in file_metrics),
                cupy_imports=sum(item.cupy_imports for item in file_metrics),
                from_cupy_imports=sum(
                    item.from_cupy_imports for item in file_metrics
                ),
                coverage_percentage=round(coverage, 4),
                top_files=top_files,
                clone_size_mb=round(directory_size_mb(clone_dir), 3),
                analysis_time_seconds=round(time.monotonic() - started, 3),
            )
            print(
                f"  {repo_name}: {files_with_cupy:,}/{python_files_analyzed:,} files, "
                f"{result.cupy_patterns:,} cupy. + {result.cp_patterns:,} cp. patterns",
                flush=True,
            )
            return repo_name, asdict(result), None
        except Exception as error:  # Keep a long batch running if one repo is unusual.
            return repo_name, None, f"analysis failed: {error}"
        finally:
            if clone_dir.exists():
                shutil.rmtree(clone_dir, ignore_errors=True)

    def build_output(
        self,
        state: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candidate_order = {repo["full_name"]: index for index, repo in enumerate(candidates)}
        repositories = list(state["results"].values())
        repositories.sort(key=lambda repo: candidate_order.get(repo["repo_name"], sys.maxsize))
        return {
            "metadata": {
                "generated_at": utc_now(),
                "analysis_version": ANALYSIS_VERSION,
                "analysis_method": "anonymous_shallow_git_clone",
                "selection": f"top {len(candidates)} repositories by stars",
                "repositories_requested": len(candidates),
                "repositories_analyzed": len(repositories),
                "repositories_failed": len(state["failures"]),
                "total_python_files_analyzed": sum(
                    repo["python_files_analyzed"] for repo in repositories
                ),
                "total_files_with_cupy": sum(
                    repo["files_with_cupy"] for repo in repositories
                ),
                "total_cupy_patterns": sum(repo["cupy_patterns"] for repo in repositories),
                "total_cp_patterns": sum(repo["cp_patterns"] for repo in repositories),
                "cp_pattern_rule": (
                    "cp. is counted only in files containing import cupy as cp"
                ),
                "failures": state["failures"],
            },
            "repositories": repositories,
        }

    async def run(self) -> dict[str, Any]:
        candidates = self.load_candidates()
        if not candidates:
            raise RuntimeError("No repositories available for analysis")
        state = self.load_or_create_state(candidates)
        completed = set(state["results"])
        pending = [repo for repo in candidates if repo["full_name"] not in completed]
        total = len(candidates)

        print(
            f"Analyzing {len(pending):,} pending repositories "
            f"({len(completed):,}/{total:,} already complete), concurrency={self.concurrency}",
            flush=True,
        )

        with tempfile.TemporaryDirectory(prefix="cupy-local-analysis-") as temporary:
            clone_root = Path(temporary)
            for batch_start in range(0, len(pending), self.concurrency):
                batch = pending[batch_start : batch_start + self.concurrency]
                tasks = []
                for offset, repo in enumerate(batch):
                    original_index = next(
                        index
                        for index, candidate in enumerate(candidates, 1)
                        if candidate["full_name"] == repo["full_name"]
                    )
                    tasks.append(
                        self.analyze_repository(
                            repo, clone_root, original_index, total
                        )
                    )
                batch_results = await asyncio.gather(*tasks)
                for repo_name, result, error in batch_results:
                    if result is not None:
                        state["results"][repo_name] = result
                        state["failures"].pop(repo_name, None)
                    else:
                        state["failures"][repo_name] = error or "unknown error"
                        print(f"  {repo_name}: FAILED — {error}", flush=True)
                atomic_write_json(self.checkpoint_path, state)

        output = self.build_output(state, candidates)
        atomic_write_json(self.output_path, output)
        self.checkpoint_path.unlink(missing_ok=True)
        print(
            f"Wrote analysis for {output['metadata']['repositories_analyzed']:,} "
            f"repositories to {self.output_path}",
            flush=True,
        )
        return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument(
        "--top",
        type=int,
        default=100,
        help="number of highest-star repositories to analyze (default: 100)",
    )
    parser.add_argument(
        "--concurrent",
        "-c",
        type=int,
        default=2,
        help="repositories to clone/analyze concurrently (default: 2)",
    )
    parser.add_argument(
        "--max-file-size-mb",
        type=float,
        default=2.0,
        help="skip Python files larger than this many MiB (default: 2)",
    )
    parser.add_argument(
        "--clone-timeout",
        type=int,
        default=300,
        help="timeout for clone and checkout operations in seconds (default: 300)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="discard an existing analysis checkpoint before starting",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.top < 1 or args.concurrent < 1 or args.max_file_size_mb <= 0:
        print("--top, --concurrent, and --max-file-size-mb must be positive", file=sys.stderr)
        return 2
    if args.clone_timeout < 1:
        print("--clone-timeout must be positive", file=sys.stderr)
        return 2
    if args.reset:
        args.checkpoint.unlink(missing_ok=True)

    analyzer = CuPyLocalAnalyzer(
        input_path=args.input,
        output_path=args.output,
        checkpoint_path=args.checkpoint,
        top_n=args.top,
        concurrency=args.concurrent,
        max_file_size_mb=args.max_file_size_mb,
        clone_timeout=args.clone_timeout,
    )
    try:
        asyncio.run(analyzer.run())
    except KeyboardInterrupt:
        print("Analysis interrupted; rerun the same command to resume.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
