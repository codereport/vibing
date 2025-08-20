#!/usr/bin/env python3
"""
Secondary Analysis Script for GitHub Thrust Usage

Analyzes the top 20 repositories by combined score from the cache and examines
which file extensions contain the most Thrust library and API usage patterns.

This provides deeper insights into where Thrust is actually being used across
different file types in the most popular repositories.
"""

import json
import os
import re
import asyncio
import aiohttp
from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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


class SecondaryAnalyzer:
    """Performs deep analysis of top repositories"""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None

        # Debug token loading
        if self.github_token:
            print(f"✅ GitHub token loaded (length: {len(self.github_token)})")
        else:
            print(
                "⚠️  No GitHub token found - API rate limits will be very restrictive!"
            )
            print("   Set GITHUB_TOKEN in .env file or use --token argument")

        # Thrust patterns from the main analyzer
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
        self.file_extensions = {
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
        }

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
        self.max_files_per_repo = None  # Analyze ALL files for complete results
        self.max_concurrent_files = 20  # Process 20 files concurrently

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

            # Simple scoring (we'll use a simplified version since we don't have the full ranking engine)
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

    async def get_session(self):
        """Get or create aiohttp session with GitHub auth"""
        if self.session is None:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def get_all_files(self, repo_full_name: str) -> List[Dict]:
        """Get all files from a repository using GitHub API"""
        session = await self.get_session()

        # Use the git trees API to get all files
        url = f"{self.base_url}/repos/{repo_full_name}/git/trees/main?recursive=1"

        try:
            async with session.get(url) as response:
                if response.status == 404:
                    # Try 'master' branch if 'main' doesn't exist
                    url = f"{self.base_url}/repos/{repo_full_name}/git/trees/master?recursive=1"
                    async with session.get(url) as response2:
                        if response2.status == 403:
                            rate_limit_remaining = response2.headers.get(
                                "X-RateLimit-Remaining", "unknown"
                            )
                            rate_limit_reset = response2.headers.get(
                                "X-RateLimit-Reset", "unknown"
                            )
                            print(
                                f"   ❌ Rate limited for {repo_full_name}! Remaining: {rate_limit_remaining}, Reset: {rate_limit_reset}"
                            )
                            return []
                        elif response2.status != 200:
                            print(
                                f"   ❌ Could not access repository tree for {repo_full_name}: HTTP {response2.status}"
                            )
                            return []
                        data = await response2.json()
                elif response.status == 403:
                    rate_limit_remaining = response.headers.get(
                        "X-RateLimit-Remaining", "unknown"
                    )
                    rate_limit_reset = response.headers.get(
                        "X-RateLimit-Reset", "unknown"
                    )
                    print(
                        f"   ❌ Rate limited for {repo_full_name}! Remaining: {rate_limit_remaining}, Reset: {rate_limit_reset}"
                    )
                    return []
                elif response.status != 200:
                    print(
                        f"   ❌ Error accessing {repo_full_name}: HTTP {response.status}"
                    )
                    return []
                else:
                    data = await response.json()

        except Exception as e:
            print(f"   ❌ Error fetching files for {repo_full_name}: {e}")
            return []

        # Filter for relevant files
        relevant_files = []
        for item in data.get("tree", []):
            if item["type"] != "blob":  # Skip directories
                continue

            file_path = item["path"]
            extension = os.path.splitext(file_path)[1].lower()

            # Skip unwanted file types
            if extension in self.skip_extensions:
                continue

            # Only include files with relevant extensions or if they might contain code
            if extension in self.file_extensions or not extension:
                relevant_files.append(
                    {
                        "path": file_path,
                        "url": item["url"],
                        "size": item.get("size", 0),
                        "extension": extension,
                    }
                )

                # Sort by size (analyze smaller files first) and return ALL relevant files
        relevant_files.sort(key=lambda x: x["size"])

        print(f"   📊 Repository has {len(data.get('tree', []))} total files")
        print(
            f"   🎯 Found {len(relevant_files)} relevant files to analyze (after filtering)"
        )

        return relevant_files

    async def analyze_file_content(
        self, repo_full_name: str, file_info: Dict
    ) -> Optional[FileAnalysis]:
        """Download and analyze a single file for thrust usage"""
        session = await self.get_session()

        # Skip large files
        if file_info["size"] > self.max_file_size_mb * 1024 * 1024:
            return None

        try:
            # Get file content from GitHub API
            url = f"{self.base_url}/repos/{repo_full_name}/contents/{file_info['path']}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                file_data = await response.json()

                # Handle base64 encoded content
                import base64

                if file_data.get("encoding") == "base64":
                    try:
                        content = base64.b64decode(file_data["content"]).decode(
                            "utf-8", errors="ignore"
                        )
                    except:
                        return None  # Skip files that can't be decoded as text
                else:
                    content = file_data.get("content", "")

        except Exception as e:
            return None

        # Analyze content for thrust patterns
        thrust_counts = {}
        total_thrust = 0
        nvidia_apis = 0

        # Count general thrust patterns
        for pattern in self.thrust_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            if matches > 0:
                thrust_counts[pattern] = matches
                total_thrust += matches

        # Count specific NVIDIA API patterns
        for api_pattern in self.nvidia_thrust_apis:
            matches = len(re.findall(api_pattern, content, re.IGNORECASE))
            if matches > 0:
                nvidia_apis += matches

        # Only return analysis if we found thrust usage
        if total_thrust > 0 or nvidia_apis > 0:
            return FileAnalysis(
                file_path=file_info["path"],
                extension=file_info["extension"] or "no_extension",
                size_bytes=file_info["size"],
                thrust_patterns=thrust_counts,
                total_thrust=total_thrust,
                nvidia_apis=nvidia_apis,
            )

        return None

    async def analyze_repository(self, repo_info: Dict) -> Optional[RepoAnalysis]:
        """Perform complete analysis of a single repository"""
        repo_name = repo_info["full_name"]
        print(f"🔬 Analyzing {repo_name} (score: {repo_info['combined_score']:.1f})...")

        # Get all files
        files = await self.get_all_files(repo_name)
        if not files:
            print(f"   ⏭️  No files found or accessible")
            return None

        print(f"   🔍 Analyzing {len(files)} relevant files...")

        # Analyze files concurrently in batches
        file_analyses = []
        files_by_extension = Counter()
        thrust_by_extension = Counter()
        api_by_extension = Counter()

        # Count all files by extension first
        for file_info in files:
            files_by_extension[file_info["extension"] or "no_extension"] += 1

        # Process files in concurrent batches
        batch_size = self.max_concurrent_files
        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]
            print(
                f"      ⚡ Analyzing batch {i//batch_size + 1}/{(len(files) + batch_size - 1)//batch_size} ({len(batch)} files)..."
            )

            # Create concurrent tasks for this batch
            tasks = [
                self.analyze_file_content(repo_name, file_info) for file_info in batch
            ]

            # Wait for all tasks in this batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for analysis in batch_results:
                if isinstance(analysis, Exception):
                    continue  # Skip failed analyses
                if analysis:
                    file_analyses.append(analysis)
                    thrust_by_extension[analysis.extension] += analysis.total_thrust
                    api_by_extension[analysis.extension] += analysis.nvidia_apis

        if not file_analyses:
            print(f"   ⏭️  No thrust usage found in analyzed files")
            return None

        # Sort files by total thrust usage
        file_analyses.sort(key=lambda x: x.total_thrust + x.nvidia_apis, reverse=True)

        print(f"   ✅ Found thrust usage in {len(file_analyses)} files")

        return RepoAnalysis(
            repo_name=repo_name,
            stars=repo_info["stars"],
            forks=repo_info["forks"],
            language=repo_info["language"],
            combined_score=repo_info["combined_score"],
            files_analyzed=len(files),
            files_by_extension=dict(files_by_extension),
            thrust_by_extension=dict(thrust_by_extension),
            api_by_extension=dict(api_by_extension),
            top_files=file_analyses[:10],  # Top 10 files with most usage
        )

    async def run_analysis(self, top_n: int = 20) -> None:
        """Run the complete secondary analysis"""
        print(f"🚀 Starting secondary analysis of top {top_n} repositories...")

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
        print(f"📋 SECONDARY ANALYSIS REPORT")
        print(f"=" * 80)
        print(f"Analyzed {len(analyses)} repositories successfully")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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
        print(f"✅ Analysis complete!")

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
                "analysis_version": "1.0",
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

        json_filename = f"thrust_analysis_detailed_{timestamp}.json"
        with open(json_filename, "w") as f:
            json.dump(json_data, f, indent=2)
        print(f"💾 Saved detailed analysis to: {json_filename}")

        # 2. Save file-level data as CSV
        import csv

        csv_filename = f"thrust_analysis_files_{timestamp}.csv"
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
        repo_csv_filename = f"thrust_analysis_repositories_{timestamp}.csv"
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
                        top_ext,
                        thrust_files,
                    ]
                )
        print(f"📈 Saved repository summary to: {repo_csv_filename}")

        # 4. Save extension aggregated data as CSV
        from collections import Counter

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

        ext_csv_filename = f"thrust_analysis_extensions_{timestamp}.csv"
        with open(ext_csv_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "extension",
                    "total_files",
                    "thrust_usage",
                    "api_calls",
                    "avg_thrust_per_file",
                    "avg_apis_per_file",
                    "thrust_density",
                ]
            )

            for ext in sorted(
                all_thrust_by_ext.keys(),
                key=lambda x: all_thrust_by_ext[x],
                reverse=True,
            ):
                thrust_count = all_thrust_by_ext[ext]
                api_count = all_api_by_ext[ext]
                file_count = all_files_by_ext[ext]
                avg_thrust = thrust_count / file_count if file_count > 0 else 0
                avg_apis = api_count / file_count if file_count > 0 else 0
                density = (
                    (thrust_count + api_count) / file_count if file_count > 0 else 0
                )

                writer.writerow(
                    [
                        ext,
                        file_count,
                        thrust_count,
                        api_count,
                        round(avg_thrust, 2),
                        round(avg_apis, 2),
                        round(density, 2),
                    ]
                )
        print(f"📋 Saved extension analysis to: {ext_csv_filename}")

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Secondary analysis of GitHub Thrust usage"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top repositories to analyze (default: 20)",
    )
    parser.add_argument(
        "--token", type=str, help="GitHub token (or set GITHUB_TOKEN env var)"
    )

    args = parser.parse_args()

    if args.token:
        os.environ["GITHUB_TOKEN"] = args.token

    analyzer = SecondaryAnalyzer()

    try:
        await analyzer.run_analysis(args.top)
    finally:
        await analyzer.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
