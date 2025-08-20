#!/usr/bin/env python3
"""
Local Clone Analysis Script for GitHub Thrust Usage

Clones the top 20 repositories by combined score from the cache locally using
shallow git clones and performs local grep-based analysis instead of using
the GitHub API. This approach provides faster and more comprehensive analysis
without API rate limits.

Features:
- Shallow git clones for efficiency (depth=1)
- Local file system analysis using grep and file operations
- Comprehensive thrust pattern detection
- Detailed reporting with extension-based analysis
- Automatic cleanup of cloned repositories
"""

import json
import os
import re
import asyncio
import subprocess
import shutil
import tempfile
from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path
import argparse


@dataclass
class FileAnalysis:
    """Results of analyzing a single file"""

    file_path: str
    extension: str
    size_bytes: int
    thrust_patterns: Dict[str, int]
    total_thrust: int
    nvidia_apis: int


@dataclass
class RepoAnalysis:
    """Results of analyzing a complete repository"""

    repo_name: str
    stars: int
    forks: int
    language: str
    combined_score: float
    files_analyzed: int
    files_by_extension: Dict[str, int]
    thrust_by_extension: Dict[str, int]
    api_by_extension: Dict[str, int]
    top_files: List[FileAnalysis]
    clone_size_mb: float
    analysis_time_seconds: float


class LocalCloneAnalyzer:
    """Performs local analysis of top repositories by cloning them"""

    def __init__(self, clone_dir: Optional[str] = None):
        # Clone directory setup
        if clone_dir:
            self.clone_base_dir = Path(clone_dir)
        else:
            self.clone_base_dir = Path("./cloned_repos")

        self.clone_base_dir.mkdir(exist_ok=True)
        print(f"📁 Using clone directory: {self.clone_base_dir.absolute()}")

        # Thrust patterns from the main analyzer (same as secondary_analysis.py)
        self.nvidia_thrust_apis = [
            r"thrust::transform",
            r"thrust::reduce",
            r"thrust::inclusive_scan",
            r"thrust::sort",
            r"thrust::make_",
        ]

        self.thrust_patterns = [
            r"thrust::",  # Any thrust namespace usage
            r"#include\s*<thrust/",  # Thrust header includes
            r"thrust\s*::\s*\w+",  # Thrust API calls
            r"device_vector\s*<",  # Thrust containers
            r"host_vector\s*<",
            r"thrust\.h",  # Legacy thrust headers
        ]

        # File extensions to analyze (expanded beyond just CUDA)
        self.relevant_extensions = [
            ".cu",
            ".cuh",
            ".cpp",
            ".cc",
            ".cxx",
            ".c++",
            ".hpp",
            ".hh",
            ".hxx",
            ".h++",
            ".h",
            ".py",
            ".pyx",
            ".pxd",  # Python/Cython
            ".rs",  # Rust
            ".go",  # Go
            ".jl",  # Julia
            ".f90",
            ".f95",
            ".f03",
            ".f08",
            ".f",
            ".for",  # Fortran
            ".m",
            ".mm",  # Objective-C
            ".swift",  # Swift
            ".kt",  # Kotlin
            ".java",  # Java
            ".cs",  # C#
            ".js",
            ".ts",  # JavaScript/TypeScript
            ".cmake",
            ".txt",
            ".md",  # Build files and docs
        ]

        # Skip binary and large files
        self.skip_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".ico",
            ".svg",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".so",
            ".dll",
            ".dylib",
            ".exe",
            ".bin",
            ".obj",
            ".o",
            ".a",
            ".lib",
            ".wav",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
        }

        self.max_file_size_mb = 5  # Allow larger files for thorough analysis
        self.git_timeout = 300  # 5 minutes timeout for git operations

    async def load_cached_repositories(self) -> List[Dict]:
        """Load and parse cached repository data"""
        cache_file = "thrust_analysis_cache.json"

        if not os.path.exists(cache_file):
            raise FileNotFoundError(
                f"Cache file {cache_file} not found. Run searches first to populate cache."
            )

        with open(cache_file, "r") as f:
            cache = json.load(f)

        # Parse cache entries and calculate combined scores
        repos = []
        for cache_key, cache_data in cache.items():
            if ":" not in cache_key:
                continue

            full_name = cache_key.split(":")[0]

            # Only include repos with some thrust usage
            if (
                cache_data.get("nvidia_apis", 0) == 0
                and cache_data.get("total_thrust", 0) == 0
            ):
                continue

            # Calculate combined score (same logic as ranking_engine.py)
            thrust_usage = cache_data.get("total_thrust", 0)
            nvidia_apis = cache_data.get("nvidia_apis", 0)
            stars = cache_data.get("stars", 0)
            forks = cache_data.get("forks", 0)

            # Simple scoring (simplified version since we don't have the full ranking engine)
            thrust_score = min(100, thrust_usage * 10)  # Basic thrust scoring
            popularity_score = min(
                100, (stars + forks * 0.3) / 100
            )  # Basic popularity scoring
            combined_score = (thrust_score * 0.6) + (popularity_score * 0.4)

            repos.append(
                {
                    "full_name": full_name,
                    "repo_name": cache_data.get("repo_name", full_name.split("/")[-1]),
                    "stars": stars,
                    "forks": forks,
                    "language": cache_data.get("language", "Unknown"),
                    "thrust_usage": thrust_usage,
                    "nvidia_apis": nvidia_apis,
                    "combined_score": combined_score,
                    "cached_data": cache_data,
                }
            )

        # Sort by combined score and return top repositories
        repos.sort(key=lambda x: x["combined_score"], reverse=True)
        return repos

    async def clone_repository(self, repo_info: Dict) -> Optional[Path]:
        """Clone a repository using shallow git clone"""
        repo_name = repo_info["full_name"]
        safe_name = repo_name.replace("/", "_")
        clone_dir = self.clone_base_dir / safe_name

        # Remove existing clone if it exists
        if clone_dir.exists():
            print(f"   🗑️  Removing existing clone at {clone_dir}")
            shutil.rmtree(clone_dir)

        clone_url = f"https://github.com/{repo_name}.git"

        print(f"   📥 Cloning {repo_name} (shallow)...")

        try:
            # Use shallow clone with depth=1 for efficiency
            result = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth",
                "1",
                clone_url,
                str(clone_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(), timeout=self.git_timeout
                )
            except asyncio.TimeoutError:
                result.terminate()
                await result.wait()
                raise asyncio.TimeoutError("Git clone timeout")

            if result.returncode != 0:
                print(f"   ❌ Failed to clone {repo_name}: {stderr.decode()}")
                return None

            print(f"   ✅ Successfully cloned {repo_name}")
            return clone_dir

        except asyncio.TimeoutError:
            print(f"   ⏱️  Timeout cloning {repo_name}")
            return None
        except Exception as e:
            print(f"   ❌ Error cloning {repo_name}: {e}")
            return None

    def get_clone_size(self, clone_dir: Path) -> float:
        """Get the size of the cloned repository in MB"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(clone_dir):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0

    def find_relevant_files(self, clone_dir: Path) -> List[Path]:
        """Find all relevant files for analysis"""
        relevant_files = []

        for file_path in clone_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip hidden files and directories
            if any(part.startswith(".") for part in file_path.parts):
                continue

            extension = file_path.suffix.lower()

            # Skip unwanted file types
            if extension in self.skip_extensions:
                continue

            # Skip files that are too large
            try:
                if file_path.stat().st_size > self.max_file_size_mb * 1024 * 1024:
                    continue
            except (OSError, PermissionError):
                continue

            # Include files with relevant extensions or no extension
            if extension in self.relevant_extensions or not extension:
                relevant_files.append(file_path)

        return relevant_files

    def analyze_file_content(
        self, file_path: Path, clone_dir: Path
    ) -> Optional[FileAnalysis]:
        """Analyze a single file for thrust usage"""
        try:
            # Try to read file content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError, OSError):
            # Skip files that can't be read as text
            return None

        # Get relative path from clone directory
        try:
            relative_path = file_path.relative_to(clone_dir)
        except ValueError:
            relative_path = file_path

        extension = file_path.suffix.lower() or "no_extension"

        # Count thrust usage patterns
        thrust_counts = {}
        total_thrust = 0
        nvidia_apis = 0

        # Count general thrust patterns
        for pattern in self.thrust_patterns:
            try:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                if matches > 0:
                    thrust_counts[pattern] = matches
                    total_thrust += matches
            except re.error:
                # Skip invalid regex patterns
                continue

        # Count specific NVIDIA API patterns
        for api_pattern in self.nvidia_thrust_apis:
            try:
                matches = len(re.findall(api_pattern, content, re.IGNORECASE))
                if matches > 0:
                    nvidia_apis += matches
            except re.error:
                continue

        # Only return analysis if we found thrust usage
        if total_thrust > 0 or nvidia_apis > 0:
            return FileAnalysis(
                file_path=str(relative_path),
                extension=extension,
                size_bytes=file_path.stat().st_size,
                thrust_patterns=thrust_counts,
                total_thrust=total_thrust,
                nvidia_apis=nvidia_apis,
            )

        return None

    async def analyze_repository(self, repo_info: Dict) -> Optional[RepoAnalysis]:
        """Perform complete analysis of a single repository"""
        repo_name = repo_info["full_name"]
        start_time = datetime.now()

        print(f"🔬 Analyzing {repo_name} (score: {repo_info['combined_score']:.1f})...")

        # Clone the repository
        clone_dir = await self.clone_repository(repo_info)
        if not clone_dir:
            print(f"   ⏭️  Could not clone repository")
            return None

        try:
            # Get clone size
            clone_size_mb = self.get_clone_size(clone_dir)
            print(f"   📊 Repository size: {clone_size_mb:.1f} MB")

            # Find all relevant files
            relevant_files = self.find_relevant_files(clone_dir)
            print(f"   📁 Found {len(relevant_files)} relevant files to analyze")

            if not relevant_files:
                print(f"   ⏭️  No relevant files found")
                return None

            # Analyze files
            file_analyses = []
            files_by_extension = Counter()
            thrust_by_extension = Counter()
            api_by_extension = Counter()

            # Count all files by extension first
            for file_path in relevant_files:
                extension = file_path.suffix.lower() or "no_extension"
                files_by_extension[extension] += 1

            print(f"   🔍 Analyzing files for thrust usage...")

            # Analyze each file
            for file_path in relevant_files:
                analysis = self.analyze_file_content(file_path, clone_dir)
                if analysis:
                    file_analyses.append(analysis)
                    thrust_by_extension[analysis.extension] += analysis.total_thrust
                    api_by_extension[analysis.extension] += analysis.nvidia_apis

            if not file_analyses:
                print(f"   ⏭️  No thrust usage found in analyzed files")
                return None

            # Sort files by total thrust usage
            file_analyses.sort(
                key=lambda x: x.total_thrust + x.nvidia_apis, reverse=True
            )

            analysis_time = (datetime.now() - start_time).total_seconds()
            print(
                f"   ✅ Found thrust usage in {len(file_analyses)} files ({analysis_time:.1f}s)"
            )

            return RepoAnalysis(
                repo_name=repo_name,
                stars=repo_info["stars"],
                forks=repo_info["forks"],
                language=repo_info["language"],
                combined_score=repo_info["combined_score"],
                files_analyzed=len(relevant_files),
                files_by_extension=dict(files_by_extension),
                thrust_by_extension=dict(thrust_by_extension),
                api_by_extension=dict(api_by_extension),
                top_files=file_analyses[:10],  # Top 10 files with most usage
                clone_size_mb=clone_size_mb,
                analysis_time_seconds=analysis_time,
            )

        finally:
            # Clean up: remove the cloned repository
            if clone_dir.exists():
                print(f"   🗑️  Cleaning up clone directory")
                shutil.rmtree(clone_dir)

    async def run_analysis(self, top_n: int = 20) -> None:
        """Run the complete local clone analysis"""
        print(f"🚀 Starting local clone analysis of top {top_n} repositories...")

        # Load cached repositories
        print("📊 Loading cached repository data...")
        repos = await self.load_cached_repositories()

        if len(repos) == 0:
            print("❌ No repositories with thrust usage found in cache!")
            return

        print(f"✅ Found {len(repos)} repositories with thrust usage in cache")

        # Analyze top N repositories
        top_repos = repos[:top_n]
        print(f"\n🔍 Analyzing top {len(top_repos)} repositories by combined score...")

        analyses = []
        for i, repo in enumerate(top_repos, 1):
            print(f"\n[{i}/{len(top_repos)}]", end=" ")
            analysis = await self.analyze_repository(repo)
            if analysis:
                analyses.append(analysis)

        await self.generate_report(analyses)

    async def generate_report(self, analyses: List[RepoAnalysis]) -> None:
        """Generate comprehensive analysis report"""
        if not analyses:
            print("❌ No successful analyses to report!")
            return

        print(f"\n" + "=" * 80)
        print(f"📋 LOCAL CLONE ANALYSIS REPORT")
        print(f"=" * 80)
        print(f"Analyzed {len(analyses)} repositories successfully")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Performance metrics
        total_clone_size = sum(a.clone_size_mb for a in analyses)
        total_analysis_time = sum(a.analysis_time_seconds for a in analyses)
        avg_analysis_time = total_analysis_time / len(analyses) if analyses else 0

        print(f"\n⚡ PERFORMANCE METRICS")
        print(f"-" * 50)
        print(f"Total data cloned: {total_clone_size:.1f} MB")
        print(f"Total analysis time: {total_analysis_time:.1f} seconds")
        print(f"Average time per repo: {avg_analysis_time:.1f} seconds")
        print(
            f"Analysis throughput: {len(analyses) / (total_analysis_time / 60):.1f} repos/minute"
        )

        # Overall statistics by file extension
        print(f"\n📊 THRUST USAGE BY FILE EXTENSION")
        print(f"-" * 50)

        all_thrust_by_ext = Counter()
        all_api_by_ext = Counter()
        all_files_by_ext = Counter()

        for analysis in analyses:
            for ext, count in analysis.thrust_by_extension.items():
                all_thrust_by_ext[ext] += count
            for ext, count in analysis.api_by_extension.items():
                all_api_by_ext[ext] += count
            for ext, count in analysis.files_by_extension.items():
                all_files_by_ext[ext] += count

        # Report by extension
        print(
            f"{'Extension':<15} {'Files':<8} {'Thrust':<8} {'APIs':<8} {'Avg/File':<10}"
        )
        print(f"-" * 55)

        for ext in sorted(
            all_thrust_by_ext.keys(), key=lambda x: all_thrust_by_ext[x], reverse=True
        ):
            thrust_count = all_thrust_by_ext[ext]
            api_count = all_api_by_ext[ext]
            file_count = all_files_by_ext[ext]
            avg_per_file = (
                (thrust_count + api_count) / file_count if file_count > 0 else 0
            )

            print(
                f"{ext:<15} {file_count:<8} {thrust_count:<8} {api_count:<8} {avg_per_file:<10.1f}"
            )

        # Top repositories
        print(f"\n🏆 TOP REPOSITORIES BY THRUST USAGE")
        print(f"-" * 50)

        analyses.sort(
            key=lambda x: sum(x.thrust_by_extension.values())
            + sum(x.api_by_extension.values()),
            reverse=True,
        )

        for i, analysis in enumerate(analyses[:10], 1):
            total_thrust = sum(analysis.thrust_by_extension.values())
            total_apis = sum(analysis.api_by_extension.values())
            print(f"{i:2d}. {analysis.repo_name}")
            print(
                f"    ⭐ Stars: {analysis.stars:,} | 🍴 Forks: {analysis.forks:,} | 📊 Score: {analysis.combined_score:.1f}"
            )
            print(
                f"    🔥 Thrust: {total_thrust} | 🎯 APIs: {total_apis} | 📁 Files: {analysis.files_analyzed}"
            )
            print(
                f"    💾 Size: {analysis.clone_size_mb:.1f} MB | ⏱️  Time: {analysis.analysis_time_seconds:.1f}s"
            )

            # Top extensions for this repo
            top_exts = sorted(
                analysis.thrust_by_extension.items(), key=lambda x: x[1], reverse=True
            )[:3]
            if top_exts:
                ext_summary = ", ".join(
                    [f"{ext}({count})" for ext, count in top_exts if count > 0]
                )
                print(f"    📄 Top extensions: {ext_summary}")
            print()

        # Most active files across all repos
        print(f"\n📄 MOST ACTIVE FILES ACROSS ALL REPOSITORIES")
        print(f"-" * 50)

        all_files = []
        for analysis in analyses:
            for file_analysis in analysis.top_files:
                all_files.append((analysis.repo_name, file_analysis))

        all_files.sort(key=lambda x: x[1].total_thrust + x[1].nvidia_apis, reverse=True)

        for i, (repo_name, file_analysis) in enumerate(all_files[:15], 1):
            print(f"{i:2d}. {repo_name}/{file_analysis.file_path}")
            print(
                f"    🔥 Thrust: {file_analysis.total_thrust} | 🎯 APIs: {file_analysis.nvidia_apis} | 📄 {file_analysis.extension}"
            )
            print(f"    📏 Size: {file_analysis.size_bytes:,} bytes")

        print(f"\n" + "=" * 80)
        print(f"✅ Local clone analysis complete!")

        # Save raw data to files
        await self.save_raw_data(analyses)

    async def save_raw_data(self, analyses: List[RepoAnalysis]) -> None:
        """Save raw analysis data to various formats for further processing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Save complete analysis data as JSON
        total_files = sum(analysis.files_analyzed for analysis in analyses)
        json_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_repositories": len(analyses),
                "total_files_analyzed": total_files,
                "analysis_version": "1.0_local_clone",
                "analysis_method": "local_git_clone",
            },
            "repositories": [],
        }

        for analysis in analyses:
            repo_data = {
                "repo_name": analysis.repo_name,
                "stars": analysis.stars,
                "forks": analysis.forks,
                "language": analysis.language,
                "combined_score": analysis.combined_score,
                "files_analyzed": analysis.files_analyzed,
                "files_by_extension": analysis.files_by_extension,
                "thrust_by_extension": analysis.thrust_by_extension,
                "api_by_extension": analysis.api_by_extension,
                "clone_size_mb": analysis.clone_size_mb,
                "analysis_time_seconds": analysis.analysis_time_seconds,
                "top_files": [
                    {
                        "file_path": f.file_path,
                        "extension": f.extension,
                        "size_bytes": f.size_bytes,
                        "thrust_patterns": f.thrust_patterns,
                        "total_thrust": f.total_thrust,
                        "nvidia_apis": f.nvidia_apis,
                    }
                    for f in analysis.top_files
                ],
            }
            json_data["repositories"].append(repo_data)

        json_filename = f"thrust_analysis_local_clone_{timestamp}.json"
        with open(json_filename, "w") as f:
            json.dump(json_data, f, indent=2)
        print(f"💾 Saved detailed analysis to: {json_filename}")

        # 2. Save file-level data as CSV
        import csv

        csv_filename = f"thrust_analysis_local_files_{timestamp}.csv"
        with open(csv_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "repository",
                    "file_path",
                    "extension",
                    "size_bytes",
                    "total_thrust",
                    "nvidia_apis",
                    "thrust_patterns",
                ]
            )

            for analysis in analyses:
                for file_analysis in analysis.top_files:
                    writer.writerow(
                        [
                            analysis.repo_name,
                            file_analysis.file_path,
                            file_analysis.extension,
                            file_analysis.size_bytes,
                            file_analysis.total_thrust,
                            file_analysis.nvidia_apis,
                            str(file_analysis.thrust_patterns),
                        ]
                    )
        print(f"📊 Saved file-level data to: {csv_filename}")

        # 3. Save repository summary as CSV
        repo_csv_filename = f"thrust_analysis_local_repos_{timestamp}.csv"
        with open(repo_csv_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "repository",
                    "stars",
                    "forks",
                    "language",
                    "combined_score",
                    "files_analyzed",
                    "total_thrust_usage",
                    "total_api_calls",
                    "clone_size_mb",
                    "analysis_time_seconds",
                    "top_extension_by_thrust",
                    "thrust_files_count",
                ]
            )

            for analysis in analyses:
                total_thrust = sum(analysis.thrust_by_extension.values())
                total_apis = sum(analysis.api_by_extension.values())
                top_ext = (
                    max(analysis.thrust_by_extension.items(), key=lambda x: x[1])[0]
                    if analysis.thrust_by_extension
                    else "none"
                )
                thrust_files = len(
                    [f for f in analysis.top_files if f.total_thrust > 0]
                )

                writer.writerow(
                    [
                        analysis.repo_name,
                        analysis.stars,
                        analysis.forks,
                        analysis.language,
                        analysis.combined_score,
                        analysis.files_analyzed,
                        total_thrust,
                        total_apis,
                        analysis.clone_size_mb,
                        analysis.analysis_time_seconds,
                        top_ext,
                        thrust_files,
                    ]
                )
        print(f"📈 Saved repository summary to: {repo_csv_filename}")

        print(f"🎯 All analysis files saved with timestamp: {timestamp}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Local clone analysis of GitHub Thrust usage"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top repositories to analyze (default: 20)",
    )
    parser.add_argument(
        "--clone-dir",
        type=str,
        help="Directory to use for cloning repositories (default: ./cloned_repos)",
    )

    args = parser.parse_args()

    analyzer = LocalCloneAnalyzer(clone_dir=args.clone_dir)

    try:
        await analyzer.run_analysis(args.top)
    except KeyboardInterrupt:
        print("\n🛑 Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
