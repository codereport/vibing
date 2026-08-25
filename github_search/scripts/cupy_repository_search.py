#!/usr/bin/env python3
"""Build the static CuPy repository dataset from GitHub's dependency graph.

The CuPy project publishes several distribution packages (``cupy``,
``cupy-cuda11x``, and so on). GitHub's dependency graph exposes repositories
that declare those packages as dependencies and includes the star/fork counts
needed by the static viewer. This source does not require a GitHub API token.

The crawl is resumable. A checkpoint is written after every page and removed
only after all requested packages have completed successfully.

Usage:
    python scripts/cupy_repository_search.py
    python scripts/cupy_repository_search.py --packages cupy cupy-cuda12x
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPENDENTS_URL = "https://github.com/cupy/cupy/network/dependents"
DEFAULT_PACKAGES = ("cupy", "cupy-cuda11x", "cupy-cuda12x", "cupy-cuda13x")
USER_AGENT = "CuPyRepositoryStats/1.0 (+https://github.com/codereport/vibing)"
COUNT_RE = re.compile(r"([0-9][0-9,]*)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")
    temporary.replace(path)


def parse_count(value: str) -> int:
    match = COUNT_RE.search(value)
    return int(match.group(1).replace(",", "")) if match else 0


def package_id_from_url(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("package_id")
    return values[0] if values else None


def discover_packages(html: str) -> dict[str, str]:
    """Return the dependency package name -> package id mapping."""
    soup = BeautifulSoup(html, "html.parser")
    packages: dict[str, str] = {}
    for link in soup.select('a.select-menu-item[role="menuitemradio"]'):
        label = link.select_one(".select-menu-item-text")
        href = link.get("href")
        if not label or not href:
            continue
        package_name = " ".join(label.stripped_strings)
        package_id = package_id_from_url(str(href))
        if package_name and package_id:
            packages[package_name] = package_id
    return packages


def parse_reported_count(soup: BeautifulSoup) -> int | None:
    for link in soup.select(".table-list-header-toggle a.btn-link.selected"):
        text = " ".join(link.stripped_strings)
        if "Repositories" in text:
            return parse_count(text)
    return None


def parse_repository_rows(soup: BeautifulSoup, package_name: str) -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    for row in soup.select('[data-test-id="dg-repo-pkg-dependent"]'):
        repo_link = row.select_one('a[data-hovercard-type="repository"]')
        if not repo_link:
            continue

        href = str(repo_link.get("href", ""))
        full_name = href.strip("/")
        if full_name.count("/") != 1:
            continue

        stars = 0
        forks = 0
        for stat in row.select("div.flex-justify-end > span"):
            if stat.select_one("svg.octicon-star"):
                stars = parse_count(stat.get_text(" ", strip=True))
            elif stat.select_one("svg.octicon-repo-forked"):
                forks = parse_count(stat.get_text(" ", strip=True))

        repositories.append(
            {
                "name": full_name.split("/", 1)[1],
                "full_name": full_name,
                "html_url": urljoin("https://github.com", href),
                "stars": stars,
                "forks": forks,
                "cupy_packages": [package_name],
            }
        )
    return repositories


def find_next_url(soup: BeautifulSoup) -> str | None:
    for link in soup.select('[data-test-selector="pagination"] a'):
        if link.get_text(" ", strip=True).lower() == "next":
            href = link.get("href")
            return urljoin("https://github.com", str(href)) if href else None
    return None


def merge_repository(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    target["stars"] = max(target.get("stars", 0), incoming.get("stars", 0))
    target["forks"] = max(target.get("forks", 0), incoming.get("forks", 0))
    packages = set(target.get("cupy_packages", []))
    packages.update(incoming.get("cupy_packages", []))
    target["cupy_packages"] = sorted(packages)


class CuPyDependencyCrawler:
    def __init__(self, checkpoint_path: Path, delay: float, retries: int = 5):
        self.checkpoint_path = checkpoint_path
        self.delay = delay
        self.retries = retries
        self.client = httpx.Client(
            follow_redirects=True,
            headers={"Accept": "text/html", "User-Agent": USER_AGENT},
            timeout=30.0,
        )

    def close(self) -> None:
        self.client.close()

    def fetch(self, url: str) -> str:
        for attempt in range(1, self.retries + 1):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                if "Too many requests" in response.text:
                    raise httpx.HTTPStatusError(
                        "GitHub returned a rate-limit page",
                        request=response.request,
                        response=response,
                    )
                if self.delay:
                    time.sleep(self.delay)
                return response.text
            except (httpx.HTTPError, httpx.TimeoutException) as error:
                if attempt == self.retries:
                    raise RuntimeError(f"Could not fetch {url}: {error}") from error
                wait_seconds = min(60.0, 2.0**attempt)
                print(
                    f"  Request failed ({error}); retrying in {wait_seconds:.0f}s "
                    f"[{attempt}/{self.retries}]",
                    flush=True,
                )
                time.sleep(wait_seconds)
        raise AssertionError("unreachable")

    def load_or_create_state(self, package_names: list[str]) -> dict[str, Any]:
        if self.checkpoint_path.exists():
            with self.checkpoint_path.open(encoding="utf-8") as handle:
                state = json.load(handle)
            checkpoint_packages = list(state.get("requested_packages", []))
            if checkpoint_packages != package_names:
                raise RuntimeError(
                    "The checkpoint was created for different packages. "
                    f"Remove {self.checkpoint_path} or reuse: "
                    + " ".join(checkpoint_packages)
                )
            print(f"Resuming from {self.checkpoint_path}", flush=True)
            return state

        landing_html = self.fetch(DEPENDENTS_URL)
        available_packages = discover_packages(landing_html)
        missing = [name for name in package_names if name not in available_packages]
        if missing:
            available = ", ".join(sorted(available_packages))
            raise RuntimeError(
                f"Unknown CuPy dependency package(s): {', '.join(missing)}. "
                f"Available packages: {available}"
            )

        state: dict[str, Any] = {
            "started_at": utc_now(),
            "requested_packages": package_names,
            "repositories": {},
            "packages": {},
        }
        for package_name in package_names:
            package_id = available_packages[package_name]
            state["packages"][package_name] = {
                "package_id": package_id,
                "next_url": (
                    f"{DEPENDENTS_URL}?dependent_type=REPOSITORY"
                    f"&package_id={package_id}"
                ),
                "pages_fetched": 0,
                "rows_seen": 0,
                "reported_repositories": None,
                "complete": False,
            }
        atomic_write_json(self.checkpoint_path, state)
        return state

    def crawl(self, package_names: list[str], max_pages: int | None = None) -> dict[str, Any]:
        state = self.load_or_create_state(package_names)
        repositories: dict[str, dict[str, Any]] = state["repositories"]

        for package_name in package_names:
            package_state = state["packages"][package_name]
            if package_state.get("complete"):
                print(f"{package_name}: already complete", flush=True)
                continue

            print(f"{package_name}: starting dependency crawl", flush=True)
            pages_this_run = 0
            while package_state.get("next_url"):
                if max_pages is not None and pages_this_run >= max_pages:
                    print(f"{package_name}: stopped at --max-pages={max_pages}", flush=True)
                    break

                html = self.fetch(package_state["next_url"])
                soup = BeautifulSoup(html, "html.parser")
                rows = parse_repository_rows(soup, package_name)
                if not rows:
                    raise RuntimeError(
                        f"GitHub returned no repository rows for {package_name}; "
                        "the dependency page format may have changed."
                    )

                if package_state["reported_repositories"] is None:
                    package_state["reported_repositories"] = parse_reported_count(soup)

                for repo in rows:
                    full_name = repo["full_name"]
                    if full_name in repositories:
                        merge_repository(repositories[full_name], repo)
                    else:
                        repositories[full_name] = repo

                package_state["pages_fetched"] += 1
                package_state["rows_seen"] += len(rows)
                package_state["next_url"] = find_next_url(soup)
                package_state["complete"] = package_state["next_url"] is None
                pages_this_run += 1
                atomic_write_json(self.checkpoint_path, state)

                pages = package_state["pages_fetched"]
                if pages == 1 or pages % 10 == 0 or package_state["complete"]:
                    print(
                        f"  {package_name}: {package_state['rows_seen']:,} rows, "
                        f"{len(repositories):,} unique repos ({pages} pages)",
                        flush=True,
                    )

            if package_state.get("complete"):
                print(f"{package_name}: complete", flush=True)

        return state


def build_output(state: dict[str, Any]) -> dict[str, Any]:
    repositories = list(state["repositories"].values())
    repositories.sort(key=lambda repo: (-repo.get("stars", 0), repo["full_name"].lower()))
    package_stats = {
        name: {
            "reported_repositories": values.get("reported_repositories"),
            "rows_seen": values.get("rows_seen", 0),
            "pages_fetched": values.get("pages_fetched", 0),
            "complete": bool(values.get("complete")),
        }
        for name, values in state["packages"].items()
    }
    complete = all(package["complete"] for package in package_stats.values())
    return {
        "generated_at": utc_now(),
        "source": {
            "type": "github_dependency_graph",
            "repository": "cupy/cupy",
            "url": DEPENDENTS_URL,
            "packages": list(state["requested_packages"]),
            "package_stats": package_stats,
            "complete": complete,
            "note": "Counts on GitHub's dependency graph are approximate.",
        },
        "total_repositories": len(repositories),
        "total_stars": sum(repo.get("stars", 0) for repo in repositories),
        "repositories": repositories,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packages",
        nargs="+",
        default=list(DEFAULT_PACKAGES),
        help="CuPy distribution package names to crawl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "cupy_repos.json",
        help="final static viewer JSON path",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=PROJECT_ROOT / "data" / ".cupy_repos_checkpoint.json",
        help="resumable crawl checkpoint path",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="delay between GitHub page requests in seconds (default: 0.25)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="testing aid: fetch at most this many pages per package in this run",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.delay < 0:
        print("--delay must not be negative", file=sys.stderr)
        return 2
    if args.max_pages is not None and args.max_pages < 1:
        print("--max-pages must be positive", file=sys.stderr)
        return 2

    crawler = CuPyDependencyCrawler(args.checkpoint, args.delay)
    try:
        state = crawler.crawl(args.packages, args.max_pages)
        output = build_output(state)
        atomic_write_json(args.output, output)
    except (OSError, RuntimeError, httpx.HTTPError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        crawler.close()

    if output["source"]["complete"]:
        args.checkpoint.unlink(missing_ok=True)
        print(
            f"Wrote {output['total_repositories']:,} repositories to {args.output}",
            flush=True,
        )
        return 0

    print(
        f"Wrote partial data ({output['total_repositories']:,} repositories) to "
        f"{args.output}; rerun the same command to resume.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
