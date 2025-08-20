#!/usr/bin/env python3
"""
Enhanced GitHub Thrust Repository Search
Efficiently uses the 10 requests/minute Code Search API limit by doing 2 searches per extension per minute.
Runs for 10 minutes total (100 total requests) with real-time progress updates.

Usage:
    python thrust_repository_search.py

This script searches for the keyword "thrust::" in the following file extensions:
- .cu (CUDA source files)
- .h (C/C++ header files)
- .cpp (C++ source files)
- .hpp (C++ header files)
- .cuh (CUDA header files)

Strategy: 2 searches per extension per minute × 5 extensions = 10 requests/minute × 10 minutes = 100 total requests
"""

import os
import asyncio
import httpx
import json
import time
from typing import Set, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug: Check if token is loaded
if not os.getenv("GITHUB_TOKEN"):
    print("⚠️  Warning: GITHUB_TOKEN not found in environment")
    print("   Trying to load from .env file...")
    load_dotenv(override=True)
    if os.getenv("GITHUB_TOKEN"):
        print("✅ GitHub token loaded from .env file")
    else:
        print("❌ No GitHub token found in .env file")


class EnhancedThrustRepositorySearcher:
    """Enhanced searcher that efficiently uses the 10 requests/minute Code Search API limit"""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None

        # File extensions to search
        self.target_extensions = [".cu", ".h", ".cpp", ".hpp", ".cuh"]

        # Enhanced batching strategy
        self.requests_per_minute = 10
        self.minutes_to_run = 10
        self.requests_per_extension_per_minute = 2  # 10 total / 5 extensions = 2 each
        self.results_per_page = 100

        # Progress tracking
        self.extension_pages = {
            ext: 1 for ext in self.target_extensions
        }  # Track current page per extension
        self.extension_repos = {
            ext: set() for ext in self.target_extensions
        }  # Track repos per extension
        self.all_unique_repos = set()  # Track all unique repos
        self.total_requests_made = 0
        self.rate_limit_remaining = 10

    async def _get_session(self):
        """Get or create HTTP session with GitHub authentication"""
        if self.session is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "ThrustRepositorySearcher/1.0",
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
                print("✅ Using authenticated GitHub API (higher rate limits)")
            else:
                print(
                    "⚠️  Warning: No GITHUB_TOKEN found. Using unauthenticated API (lower rate limits)"
                )
                print("   Set GITHUB_TOKEN environment variable for better performance")

            self.session = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self.session

    def _check_rate_limit(self, response):
        """Check and update rate limit from response headers"""
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        resource = response.headers.get("X-RateLimit-Resource", "unknown")

        if remaining:
            self.rate_limit_remaining = int(remaining)
            if limit:
                print(
                    f"   API requests remaining: {self.rate_limit_remaining}/{limit} per minute ({resource})"
                )
            else:
                print(
                    f"   API requests remaining: {self.rate_limit_remaining} ({resource})"
                )

    async def search_single_request(self, extension: str) -> Dict[str, Any]:
        """Execute a single search request for a specific extension and page"""
        session = await self._get_session()

        current_page = self.extension_pages[extension]
        query = f"thrust:: extension:{extension[1:]}"  # Remove the dot from extension

        try:
            url = f"{self.base_url}/search/code"
            params = {
                "q": query,
                "sort": "indexed",
                "order": "desc",
                "page": current_page,
                "per_page": self.results_per_page,
            }

            response = await session.get(url, params=params)
            self.total_requests_made += 1

            # Check rate limit
            self._check_rate_limit(response)

            if response.status_code == 403:
                return {"success": False, "error": "rate_limited", "repos": set()}

            if response.status_code == 422:
                return {"success": False, "error": "query_too_broad", "repos": set()}

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"api_error_{response.status_code}",
                    "repos": set(),
                }

            data = response.json()
            items = data.get("items", [])

            if not items:
                return {"success": True, "error": "no_more_results", "repos": set()}

            # Extract unique repository names
            new_repos = set()
            for item in items:
                repo_full_name = item["repository"]["full_name"]
                new_repos.add(repo_full_name)

            # Update tracking
            self.extension_repos[extension].update(new_repos)
            before_total = len(self.all_unique_repos)
            self.all_unique_repos.update(new_repos)
            new_unique_count = len(self.all_unique_repos) - before_total

            # Advance to next page for this extension
            if len(items) == self.results_per_page:  # More results likely available
                self.extension_pages[extension] += 1

            return {
                "success": True,
                "error": None,
                "repos": new_repos,
                "new_unique_count": new_unique_count,
                "files_found": len(items),
                "page": current_page,
            }

        except Exception as e:
            return {"success": False, "error": f"exception_{str(e)}", "repos": set()}

    def display_progress(
        self, minute: int, request_num: int, extension: str, result: Dict[str, Any]
    ):
        """Display real-time progress update"""
        # Clear line and move cursor up for live updates
        print(f"\r\033[K", end="")  # Clear current line

        status_emoji = "✅" if result["success"] else "❌"
        error_msg = (
            f" ({result['error']})"
            if result.get("error") and result["error"] != "no_more_results"
            else ""
        )

        print(
            f"{status_emoji} Minute {minute}/2, Request {request_num}/10: {extension} page {result.get('page', '?')}"
        )

        if result["success"] and result.get("files_found", 0) > 0:
            print(
                f"   Found {result['files_found']} files, {len(result['repos'])} repos, {result['new_unique_count']} new unique"
            )
        elif result.get("error") == "no_more_results":
            print(f"   No more results available for {extension}")
        elif error_msg:
            print(f"   Error{error_msg}")

        # Show current totals by extension
        print(f"\n📊 Current totals by extension:")
        for ext in self.target_extensions:
            count = len(self.extension_repos[ext])
            page = self.extension_pages[ext]
            print(f"   {ext:>5}: {count:>4} repos (next: page {page})")

        print(f"\n🎯 TOTAL UNIQUE REPOSITORIES: {len(self.all_unique_repos)}")
        print(f"🔢 Total requests made: {self.total_requests_made}")

        if len(self.all_unique_repos) > 0:
            print(f"\n🔝 Latest unique repositories:")
            latest_repos = sorted(self.all_unique_repos)[-5:]  # Show last 5 found
            for repo in latest_repos:
                print(f"   • {repo}")

        print("-" * 60)

    async def run_batched_search(self) -> Dict[str, Set[str]]:
        """Run the enhanced batched search strategy"""
        print("🚀 Enhanced GitHub Thrust Repository Search")
        print("=" * 60)
        print(f"📋 Target extensions: {', '.join(self.target_extensions)}")
        print(
            f"⏱️  Strategy: {self.requests_per_extension_per_minute} requests per extension per minute"
        )
        print(
            f"🎯 Total: {self.requests_per_minute} requests/minute × {self.minutes_to_run} minutes = {self.requests_per_minute * self.minutes_to_run} requests"
        )
        print("⚠️  Using GitHub Code Search API (10 requests/minute limit)")
        print("\n" + "=" * 60)

        start_time = time.time()

        for minute in range(1, self.minutes_to_run + 1):
            minute_start_time = time.time()
            print(
                f"\n🕐 MINUTE {minute}/{self.minutes_to_run} - Starting batch of {self.requests_per_minute} requests"
            )

            request_count = 0

            # Do 2 requests per extension in this minute
            for round_num in range(self.requests_per_extension_per_minute):
                for extension in self.target_extensions:
                    if request_count >= self.requests_per_minute:
                        break

                    request_count += 1

                    # Execute search request
                    result = await self.search_single_request(extension)

                    # Display progress
                    self.display_progress(minute, request_count, extension, result)

                    # Wait 6 seconds between requests (10 requests/minute = 6 seconds between)
                    if (
                        request_count < self.requests_per_minute
                    ):  # Don't wait after last request of minute
                        await asyncio.sleep(6)

                if request_count >= self.requests_per_minute:
                    break

            # Wait for minute to complete if we finished early
            minute_elapsed = time.time() - minute_start_time
            if minute_elapsed < 60 and minute < self.minutes_to_run:
                remaining_time = 60 - minute_elapsed
                print(
                    f"\n⏳ Minute {minute} completed in {minute_elapsed:.1f}s. Waiting {remaining_time:.1f}s for next minute..."
                )
                await asyncio.sleep(remaining_time)

        total_time = time.time() - start_time
        print(f"\n🏁 Search completed in {total_time:.1f} seconds")

        return self.extension_repos

    def get_unique_repositories(self, results: Dict[str, Set[str]]) -> Set[str]:
        """Get unique repositories across all file extensions"""
        return self.all_unique_repos  # We've been tracking this throughout the search

    def save_results(self, results: Dict[str, Set[str]], unique_repos: Set[str]):
        """Save search results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get the directory where this script is located and find the data directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # Go up one level from scripts/
        data_dir = os.path.join(project_root, "data")

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Save detailed results by extension
        detailed_filename = os.path.join(
            data_dir, f"thrust_search_detailed_{timestamp}.json"
        )
        detailed_data = {
            "search_timestamp": datetime.now().isoformat(),
            "keyword": "thrust::",
            "extensions": self.target_extensions,
            "results_by_extension": {
                ext: list(repos) for ext, repos in results.items()
            },
            "summary": {ext: len(repos) for ext, repos in results.items()},
        }

        with open(detailed_filename, "w") as f:
            json.dump(detailed_data, f, indent=2)
        print(f"💾 Detailed results saved to: {detailed_filename}")

        # Save unique repository list (what the user specifically requested)
        repos_filename = os.path.join(
            data_dir, f"thrust_unique_repositories_{timestamp}.txt"
        )
        sorted_repos = sorted(unique_repos)

        with open(repos_filename, "w") as f:
            f.write(f"# Unique GitHub Repositories containing 'thrust::' keyword\n")
            f.write(f"# Search performed: {datetime.now().isoformat()}\n")
            f.write(
                f"# File extensions searched: {', '.join(self.target_extensions)}\n"
            )
            f.write(f"# Total unique repositories: {len(sorted_repos)}\n\n")

            for repo in sorted_repos:
                f.write(f"{repo}\n")

        print(f"📝 Unique repository list saved to: {repos_filename}")

        # Save CSV format for easy analysis
        csv_filename = os.path.join(data_dir, f"thrust_repositories_{timestamp}.csv")
        with open(csv_filename, "w") as f:
            f.write("repository_name,github_url\n")
            for repo in sorted_repos:
                f.write(f"{repo},https://github.com/{repo}\n")

        print(f"📊 CSV format saved to: {csv_filename}")

    def print_summary(self, results: Dict[str, Set[str]], unique_repos: Set[str]):
        """Print final summary of search results"""
        print("\n" + "=" * 80)
        print("📊 ENHANCED SEARCH RESULTS SUMMARY")
        print("=" * 80)

        print(f"🎯 Keyword searched: 'thrust::'")
        print(f"📁 File extensions: {', '.join(self.target_extensions)}")
        print(f"🕒 Search completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(
            f"⚡ Strategy: {self.requests_per_extension_per_minute} requests per extension per minute for {self.minutes_to_run} minutes"
        )
        print(f"🔢 Total API requests made: {self.total_requests_made}")

        print("\n📋 Final results by file extension:")
        total_extension_repos = 0
        for extension in self.target_extensions:
            count = len(results.get(extension, set()))
            pages_searched = (
                self.extension_pages[extension] - 1
            )  # Pages actually searched
            total_extension_repos += count
            print(
                f"   {extension:>5}: {count:>6} repositories ({pages_searched} pages searched)"
            )

        print(f"\n🏆 TOTAL UNIQUE REPOSITORIES: {len(unique_repos)}")
        print(
            f"📁 Total repository instances across extensions: {total_extension_repos}"
        )
        print(
            f"📈 Efficiency: {len(unique_repos) / self.total_requests_made:.1f} unique repos per API request"
        )

        if unique_repos:
            print("\n🔝 Top 15 repositories (alphabetical):")
            for i, repo in enumerate(sorted(unique_repos)[:15], 1):
                print(f"   {i:>2}. {repo}")

            if len(unique_repos) > 15:
                print(f"   ... and {len(unique_repos) - 15} more repositories")

        print(
            f"\n💡 Search covered pages 1-{max(self.extension_pages[ext] - 1 for ext in self.target_extensions)} for extensions that had results"
        )
        print(
            f"🚀 This enhanced approach searched {self.total_requests_made} pages in {self.minutes_to_run} minutes vs. traditional sequential approach that would take much longer"
        )


async def main():
    """Main function to run the enhanced search"""
    searcher = EnhancedThrustRepositorySearcher()

    try:
        # Run the enhanced batched search
        results = await searcher.run_batched_search()

        # Get unique repositories
        unique_repos = searcher.get_unique_repositories(results)

        # Print final summary
        searcher.print_summary(results, unique_repos)

        # Save results
        searcher.save_results(results, unique_repos)

        print(f"\n✅ Enhanced search completed successfully!")
        print(
            f"🎯 Found {len(unique_repos)} unique GitHub repositories containing 'thrust::'"
        )
        print(
            f"⚡ Efficiency: {len(unique_repos) / searcher.total_requests_made:.1f} unique repos per API request"
        )
        print(f"🕒 Total time: ~{searcher.minutes_to_run} minutes (as planned)")

    except KeyboardInterrupt:
        print("\n⏹️  Search interrupted by user")
        print(
            f"📊 Partial results: {len(searcher.all_unique_repos)} unique repositories found so far"
        )
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        print(
            f"📊 Partial results: {len(searcher.all_unique_repos)} unique repositories found so far"
        )
    finally:
        if searcher.session:
            await searcher.session.aclose()


if __name__ == "__main__":
    asyncio.run(main())
