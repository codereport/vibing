#!/usr/bin/env python3
"""
GitHub Repository Analyzer for Thrust Library Usage
Searches GitHub for repositories using NVIDIA Thrust library and analyzes their usage patterns.
"""

import os
import re
import json
import httpx
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class AnalysisProgress:
    """Progress tracking for repository analysis"""

    total_repos: int = 0
    processed_repos: int = 0
    current_repo: str = ""
    current_repo_index: int = 0
    found_thrust_repos: int = 0
    rate_limited: bool = False
    rate_limit_remaining: int = 5000
    rate_limit_reset_time: Optional[datetime] = None
    current_strategy: str = ""
    status: str = "idle"  # idle, searching, analyzing, rate_limited, completed
    results: List[Dict] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    def to_dict(self):
        result = asdict(self)
        if self.rate_limit_reset_time:
            result["rate_limit_reset_time"] = self.rate_limit_reset_time.isoformat()
        return result

    @property
    def progress_percentage(self) -> float:
        if self.total_repos == 0:
            return 0.0
        return (self.processed_repos / self.total_repos) * 100


class GitHubAnalyzer:
    """Analyzes GitHub repositories for Thrust library usage"""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None

        # Cache settings
        self.cache_file = "thrust_analysis_cache.json"
        self.cache_max_age_days = 7  # Cache results for 7 days
        self.cache = self._load_cache()

        # Analysis settings - SIMPLIFIED!
        self.max_cuda_files_per_repo = 50  # Only check first 50 CUDA files per repo
        self.max_file_size_mb = 2  # Increased from 1MB to 2MB for larger files

        # Progress tracking and rate limiting
        self.progress = AnalysisProgress()
        self.rate_limit_remaining = 5000  # Will be updated from API headers
        self.rate_limit_reset_time = None
        self.progress_callback: Optional[Callable] = None
        self.min_remaining_requests = (
            2  # Use almost all requests (keep 2 as safety buffer)
        )

        # NVIDIA Thrust API patterns - these are the core APIs that identify real Thrust usage
        self.nvidia_thrust_apis = [
            r"thrust::transform",
            r"thrust::reduce",
            r"thrust::inclusive_scan",
            r"thrust::sort",
            r"thrust::make_",
        ]

        # General thrust patterns (broader detection)
        self.thrust_patterns = [
            r"thrust::",  # Any thrust namespace usage
            r"#include\s*<thrust/",  # Thrust header includes
            r"thrust\s*::\s*\w+",  # Thrust API calls
            r"device_vector\s*<",  # Thrust containers
            r"host_vector\s*<",
            r"thrust\.h",  # Legacy thrust headers
        ]

        # File extensions to search in (prioritized for CUDA)
        self.relevant_extensions = [
            ".cu",  # CUDA source files (highest priority)
            ".cuh",  # CUDA header files
            ".inl",  # CUDA inline files
            ".cuf",  # CUDA Fortran files
            ".cpp",  # C++ source files
            ".cxx",
            ".cc",
            ".h",  # C/C++ header files
            ".hpp",
            ".hxx",
            ".c",  # C source files (lowest priority)
        ]

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                    # Clean up expired entries
                    return self._clean_expired_cache(cache)
            return {}
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")
            return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def _clean_expired_cache(self, cache: Dict[str, Any]) -> Dict[str, Any]:
        """Remove expired entries from cache"""
        cleaned = {}
        cutoff = datetime.now() - timedelta(days=self.cache_max_age_days)

        for key, value in cache.items():
            if isinstance(value, dict) and "timestamp" in value:
                try:
                    entry_time = datetime.fromisoformat(value["timestamp"])
                    if entry_time > cutoff:
                        cleaned[key] = value
                except:
                    pass  # Skip invalid entries

        return cleaned

    def _generate_cache_key(self, repo: Dict[str, Any]) -> str:
        """Generate a cache key for a repository"""
        return f"{repo['full_name']}:{repo.get('updated_at', '')}"

    def _get_from_cache(self, repo: Dict[str, Any]) -> Optional[Dict[str, int]]:
        """Get analysis results from cache if available"""
        cache_key = self._generate_cache_key(repo)
        print(f"🔑 Cache key for {repo['full_name']}: {cache_key}")
        print(f"📊 Cache has {len(self.cache)} entries")
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return {
                "total_thrust": cached.get("total_thrust", 0),
                "nvidia_apis": cached.get("nvidia_apis", 0),
            }
        else:
            print(f"❌ Cache key not found in cache")
        return None

    def _save_to_cache(self, repo: Dict[str, Any], result: Dict[str, int]):
        """Save analysis results to cache"""
        cache_key = self._generate_cache_key(repo)
        self.cache[cache_key] = {
            "total_thrust": result["total_thrust"],
            "nvidia_apis": result["nvidia_apis"],
            "timestamp": datetime.now().isoformat(),
            # Store repository metadata for cached results display
            "repo_name": repo.get("name", ""),
            "full_name": repo.get("full_name", ""),
            "description": repo.get("description", ""),
            "html_url": repo.get("html_url", ""),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language", "Unknown"),
        }
        self._save_cache()

    def get_cache_info(self) -> Dict[str, int]:
        """Get cache statistics"""
        total = len(self.cache)
        cutoff = datetime.now() - timedelta(days=1)  # Fresh = last 24 hours
        fresh = 0

        for value in self.cache.values():
            if isinstance(value, dict) and "timestamp" in value:
                try:
                    entry_time = datetime.fromisoformat(value["timestamp"])
                    if entry_time > cutoff:
                        fresh += 1
                except:
                    pass

        return {
            "total_entries": total,
            "fresh_entries": fresh,
            "old_entries": total - fresh,
        }

    def clear_cache(self):
        """Clear the analysis cache"""
        self.cache = {}
        self._save_cache()

    def set_progress_callback(self, callback: Callable):
        """Set callback function for progress updates"""
        self.progress_callback = callback

    def _update_progress(self, **kwargs):
        """Update progress and call callback if set"""
        for key, value in kwargs.items():
            if hasattr(self.progress, key):
                setattr(self.progress, key, value)

        if self.progress_callback:
            self.progress_callback(self.progress.to_dict())

    def _check_rate_limit_headers(self, response):
        """Check and update rate limit information from response headers - FIXED VERSION"""
        # GitHub uses different headers for different endpoints
        # Core API uses: X-RateLimit-Remaining, X-RateLimit-Reset
        # Search API uses: X-RateLimit-Remaining, X-RateLimit-Reset

        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_time = response.headers.get("X-RateLimit-Reset")

        if remaining:
            try:
                self.rate_limit_remaining = int(remaining)
                print(f"   📊 API requests remaining: {self.rate_limit_remaining}")
            except ValueError:
                print(f"   ⚠️ Invalid rate limit header: {remaining}")

        if reset_time:
            try:
                self.rate_limit_reset_time = datetime.fromtimestamp(int(reset_time))
            except ValueError:
                print(f"   ⚠️ Invalid reset time header: {reset_time}")

        # Update progress with rate limit info
        self._update_progress(
            rate_limited=(self.rate_limit_remaining < self.min_remaining_requests),
            rate_limit_reset_time=self.rate_limit_reset_time,
            rate_limit_remaining=self.rate_limit_remaining,
        )

    async def _wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset with progress updates"""
        if not self.rate_limit_reset_time:
            print("⏳ Rate limited, waiting 1 hour...")
            await asyncio.sleep(3600)
            return

        now = datetime.now()
        wait_time = (self.rate_limit_reset_time - now).total_seconds()

        if wait_time <= 0:
            return

        print(f"⏳ Rate limited! Waiting {wait_time/60:.0f} minutes until reset...")
        self._update_progress(status="rate_limited", rate_limited=True)

        # Update every 10 minutes
        update_interval = 600  # 10 minutes

        while wait_time > 0:
            wait_minutes = wait_time / 60
            print(f"⌛ {wait_minutes:.0f} minutes remaining until rate limit reset...")

            sleep_time = min(update_interval, wait_time)
            await asyncio.sleep(sleep_time)
            wait_time -= sleep_time

        print("✅ Rate limit reset! Resuming analysis...")
        self._update_progress(status="analyzing", rate_limited=False)

    async def _get_session(self):
        """Get or create HTTP session"""
        if self.session is None:
            headers = {"Accept": "application/vnd.github+json"}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            else:
                print("⚠️  Warning: No GITHUB_TOKEN found in environment variables")
                print("   You'll have lower rate limits without authentication")
                print("   Create a .env file with GITHUB_TOKEN=your_token")

            self.session = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self.session

    async def search_repositories(
        self,
        query: Optional[str] = None,
        language: Optional[str] = None,
        min_stars: int = 0,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for repositories using both code search and repository search"""

        # Initialize progress
        self._update_progress(
            status="searching",
            total_repos=0,
            processed_repos=0,
            current_repo="",
            found_thrust_repos=0,
            results=[],
        )

        session = await self._get_session()

        # SIMPLE 8-STRATEGY SEARCH - NO MORE CODE SEARCH BULLSHIT
        repo_search_strategies = [
            "thrust",  # Direct thrust mentions
            "CUDA parallel",  # CUDA parallel computing
            "GPU computing",  # GPU computing libraries
            "org:NVIDIA",  # All NVIDIA repositories
            "org:cupy",  # cupy organization
            "CUDA GPU parallel",  # Broader CUDA terms
            "cuBLAS cuDNN",  # CUDA math libraries
            "parallel algorithms",  # Parallel computing
        ]

        all_repositories = []
        seen_repos = set()  # Track repos we've already found to avoid duplicates

        print(f"🔍 Running 8-strategy repository search...")

        # Do the 8 repository searches to get candidates
        for strategy in repo_search_strategies:
            print(f"   🎯 Repository strategy: '{strategy}'")

            # Build search query for this strategy
            strategy_terms = [strategy]

            # Add language filter
            if language:
                strategy_terms.append(f"language:{language}")

            # Add minimum stars filter (be more lenient for org searches)
            if strategy.startswith("org:"):
                # For organization searches, use lower threshold to catch all repos
                if min_stars > 0:
                    strategy_terms.append(f"stars:>={max(1, min_stars // 10)}")
                else:
                    strategy_terms.append("stars:>=1")
            else:
                # For general searches, use normal thresholds
                if min_stars > 0:
                    strategy_terms.append(f"stars:>={min_stars}")
                else:
                    strategy_terms.append("stars:>=5")

            search_query = " ".join(strategy_terms)

            try:
                # Search for this strategy
                strategy_repos = await self._search_single_strategy(
                    search_query, max_results // len(repo_search_strategies)
                )

                # Add new repositories to our collection
                new_repos = 0
                for repo in strategy_repos:
                    repo_id = repo["full_name"]
                    if repo_id not in seen_repos:
                        seen_repos.add(repo_id)
                        all_repositories.append(repo)
                        new_repos += 1

                print(f"      Found {len(strategy_repos)} repos, {new_repos} new")

                # If we have enough repos, break early
                if len(all_repositories) >= max_results:
                    break

            except Exception as e:
                print(f"      Error with strategy '{strategy}': {e}")
                continue

        # Sort by stars and take the top results
        all_repositories.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
        final_repos = all_repositories[:max_results]

        print(f"📊 Combined search returned {len(final_repos)} unique repositories")
        if final_repos:
            print("📋 Top repositories found:")
            for i, repo in enumerate(final_repos[:5], 1):
                print(
                    f"   {i}. {repo['full_name']} ({repo.get('stargazers_count', 0)} stars)"
                )

        # Update progress with total repositories found
        self._update_progress(status="analyzing", total_repos=len(final_repos))

        return final_repos

    async def _search_single_strategy(
        self, search_query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Execute a single repository search strategy"""
        session = await self._get_session()
        repositories = []
        page = 1
        per_page = min(100, max_results)

        try:
            while len(repositories) < max_results:
                url = f"{self.base_url}/search/repositories"
                params = {
                    "q": search_query,
                    "sort": "stars",
                    "order": "desc",
                    "page": page,
                    "per_page": per_page,
                }

                response = await session.get(url, params=params)

                # Check rate limit headers - FIXED!
                self._check_rate_limit_headers(response)

                if response.status_code == 403:
                    print("      Rate limited! Waiting for reset...")
                    await self._wait_for_rate_limit_reset()
                    continue

                if response.status_code != 200:
                    print(f"      GitHub API error: {response.status_code}")
                    break

                # Check if we're getting low on requests
                if self.rate_limit_remaining < self.min_remaining_requests:
                    print(
                        f"      ⚠️ Low on API requests ({self.rate_limit_remaining} remaining), waiting for reset..."
                    )
                    await self._wait_for_rate_limit_reset()

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                repositories.extend(items)

                if len(items) < per_page:
                    break

                page += 1

                # Add small delay to be nice to GitHub API
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"      Error in search: {e}")

        return repositories[:max_results]

    async def analyze_thrust_usage(self, repo: Dict[str, Any]) -> Dict[str, int]:
        """Analyze a repository for Thrust library usage"""

        # Update progress
        self._update_progress(
            current_repo=repo["full_name"],
            processed_repos=self.progress.processed_repos + 1,
        )

        # Check cache first
        cached_result = self._get_from_cache(repo)
        if cached_result:
            print(f"💾 Using cached analysis for {repo['full_name']}")
            # Still update found count if this repo has thrust usage
            if cached_result["nvidia_apis"] > 0:
                self._update_progress(
                    found_thrust_repos=self.progress.found_thrust_repos + 1
                )
            return cached_result
        else:
            print(f"🔍 Cache miss for {repo['full_name']} - analyzing fresh")

        # Initialize counters
        total_thrust_count = 0
        nvidia_api_count = 0

        try:
            print(
                f"🔬 Analyzing {repo['full_name']} for thrust usage... ({self.progress.processed_repos}/{self.progress.total_repos})"
            )

            # Get ONLY CUDA files (max 50)
            cuda_files = await self._get_relevant_files(repo)

            if not cuda_files:
                print(f"   ⏭️  No CUDA files - skipping {repo['full_name']}")
                total_thrust_count = 0
                nvidia_api_count = 0
            else:
                print(f"   📁 Analyzing {len(cuda_files)} CUDA files")

                # Analyze each CUDA file - STOP if no thrust found
                for i, file_info in enumerate(cuda_files):
                    file_thrust_count, file_nvidia_count = (
                        await self._analyze_file_for_thrust(repo, file_info)
                    )
                    total_thrust_count += file_thrust_count
                    nvidia_api_count += file_nvidia_count

                    # Report findings
                    if file_thrust_count > 0 or file_nvidia_count > 0:
                        print(
                            f"   📄 {file_info['path']}: {file_thrust_count} thrust, {file_nvidia_count} API calls"
                        )

                    # EARLY EXIT: If we've checked 2+ files and found nothing, give up
                    if i >= 1 and total_thrust_count == 0 and nvidia_api_count == 0:
                        print(
                            f"   ⚡ No thrust found in first {i+1} CUDA files - moving on"
                        )
                        break

            print(
                f"   ✅ Total: {total_thrust_count} thrust usage, {nvidia_api_count} NVIDIA API calls"
            )

        except Exception as e:
            print(f"   ❌ Error analyzing {repo['full_name']}: {e}")
            total_thrust_count = 0
            nvidia_api_count = 0

        # Cache and return results
        result = {"total_thrust": total_thrust_count, "nvidia_apis": nvidia_api_count}
        self._save_to_cache(repo, result)
        print(f"💾 Cached analysis results for {repo['full_name']}")

        # Update found count if this repo has thrust usage
        if nvidia_api_count > 0:
            self._update_progress(
                found_thrust_repos=self.progress.found_thrust_repos + 1
            )

        return result

    async def _get_relevant_files(self, repo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get ONLY CUDA files (.cu, .cuh, .inl) - max 5 files per repo"""
        session = await self._get_session()

        try:
            # Get the default branch
            default_branch = repo.get("default_branch", "main")

            # Get repository tree (1 API call)
            url = f"{self.base_url}/repos/{repo['full_name']}/git/trees/{default_branch}?recursive=1"
            print(f"   🌐 Getting file tree from branch: {default_branch}")
            response = await session.get(url)

            # Check rate limit headers
            self._check_rate_limit_headers(response)

            if response.status_code != 200:
                print(f"   ⚠️  Could not get file tree: HTTP {response.status_code}")
                return []

            tree_data = response.json()
            tree = tree_data.get("tree", [])

            # Find ONLY CUDA files
            cuda_files = []
            cuda_extensions = [".cu", ".cuh", ".inl"]

            for item in tree:
                if item["type"] == "blob":  # Only files, not directories
                    path = item["path"]
                    if any(path.lower().endswith(ext) for ext in cuda_extensions):
                        cuda_files.append(item)
                        # Stop at max files to save API requests
                        if len(cuda_files) >= self.max_cuda_files_per_repo:
                            break

            print(
                f"   📊 Found {len(cuda_files)} CUDA files (analyzing max {self.max_cuda_files_per_repo})"
            )

            if len(cuda_files) == 0:
                print(f"   ⏭️  No CUDA files found - skipping {repo['full_name']}")
                return []

            return cuda_files[: self.max_cuda_files_per_repo]

        except Exception as e:
            print(f"   ❌ Error getting files for {repo['full_name']}: {e}")
            return []

    def _prioritize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize files by likelihood of containing thrust usage"""

        def priority_score(file_info):
            path = file_info["path"].lower()

            # ULTRA HIGH: CUDA source files - most likely to have thrust APIs
            if path.endswith(".cu"):
                return 10000

            # VERY HIGH: CUDA headers and inline files
            if path.endswith((".cuh", ".inl", ".cuf")):
                return 5000

            # HIGH: Files with "thrust" in name/path
            if "thrust" in path:
                return 2000

            # MEDIUM-HIGH: CUDA-related keywords in path
            if any(
                term in path
                for term in ["cuda", "gpu", "device", "kernel", "parallel", "algorithm"]
            ):
                return 1000

            # MEDIUM: C++ implementation files (might use thrust)
            if path.endswith((".cpp", ".cxx", ".cc")):
                return 500

            # LOW-MEDIUM: Header files (API declarations)
            if path.endswith((".h", ".hpp", ".hxx")):
                return 300

            # LOW: C files (unlikely to have thrust)
            if path.endswith(".c"):
                return 100

            # LOWEST: Other files
            return 50

        # Sort by priority score (highest first)
        return sorted(files, key=priority_score, reverse=True)

    async def _analyze_file_for_thrust(
        self, repo: Dict[str, Any], file_info: Dict[str, Any]
    ) -> tuple[int, int]:
        """Analyze a single file for thrust usage"""
        session = await self._get_session()

        try:
            # Get file contents
            url = f"{self.base_url}/repos/{repo['full_name']}/contents/{file_info['path']}"
            response = await session.get(url)

            # Check rate limit headers
            self._check_rate_limit_headers(response)

            # Check if we're getting low on requests and wait
            if self.rate_limit_remaining < self.min_remaining_requests:
                print(
                    f"      ⚠️ Low on API requests ({self.rate_limit_remaining} remaining), waiting for reset..."
                )
                await self._wait_for_rate_limit_reset()

            if response.status_code != 200:
                return 0, 0

            file_data = response.json()

            # Skip if file is too large
            size = file_data.get("size", 0)
            if size > self.max_file_size_mb * 1024 * 1024:
                return 0, 0

            # Get file content (it's base64 encoded)
            import base64

            content = base64.b64decode(file_data["content"]).decode(
                "utf-8", errors="ignore"
            )

        except Exception as e:
            return 0, 0

        # Count thrust usage patterns
        total_thrust = 0
        nvidia_apis = 0

        # Count general thrust patterns
        for pattern in self.thrust_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_thrust += len(matches)

        # Count specific NVIDIA thrust API usage
        for api_pattern in self.nvidia_thrust_apis:
            matches = re.findall(api_pattern, content, re.IGNORECASE)
            nvidia_apis += len(matches)

        return total_thrust, nvidia_apis

    def get_progress(self) -> Dict[str, Any]:
        """Get current analysis progress"""
        return self.progress.to_dict()

    def reset_progress(self):
        """Reset progress tracking"""
        self.progress = AnalysisProgress()
