#!/usr/bin/env python3
"""
Fast GitHub Thrust Repository Search (Alternative approach)
Uses repository search instead of code search to avoid the 10/minute rate limit.

This approach searches for repositories that mention "thrust" and then filters by language.
"""

import os
import asyncio
import httpx
import json
from typing import Set, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class FastThrustRepositorySearcher:
    """Fast searcher using repository search API (5000/hour limit instead of 10/minute)"""

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None

        # Rate limiting - Repository search has much higher limits
        self.rate_limit_remaining = 5000
        self.results_per_page = 100
        self.max_pages = 50  # Can search more pages with repo search

    async def _get_session(self):
        """Get or create HTTP session with GitHub authentication"""
        if self.session is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "ThrustRepositorySearcher/1.0",
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
                print(
                    "✅ Using authenticated GitHub API (5000 requests/hour for repo search)"
                )
            else:
                print(
                    "⚠️  Warning: No GITHUB_TOKEN found. Using unauthenticated API (60 requests/hour)"
                )

            self.session = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self.session

    def _check_rate_limit(self, response):
        """Check and update rate limit from response headers"""
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        resource = response.headers.get("X-RateLimit-Resource", "core")

        if remaining:
            self.rate_limit_remaining = int(remaining)
            if limit:
                print(
                    f"   API requests remaining: {self.rate_limit_remaining}/{limit} per hour ({resource})"
                )
            else:
                print(
                    f"   API requests remaining: {self.rate_limit_remaining} ({resource})"
                )

    async def search_thrust_repositories(self) -> Set[str]:
        """Search for repositories containing 'thrust' using repository search"""
        session = await self._get_session()
        unique_repos = set()

        print("\n🔍 Searching for repositories containing 'thrust'...")
        print("   Using repository search API (much faster than code search)")

        # Search strategies for thrust-related repositories
        search_queries = [
            "thrust",  # Basic thrust search
            "thrust CUDA",  # Thrust + CUDA
            "thrust GPU",  # Thrust + GPU
            "nvidia thrust",  # NVIDIA Thrust
            "thrust parallel",  # Thrust parallel
            "thrust algorithm",  # Thrust algorithms
            # Language-specific searches
            "thrust language:C++",
            "thrust language:C",
            "thrust language:CUDA",
            # Topic-based searches
            "topic:thrust",
            "topic:cuda topic:thrust",
            "topic:gpu topic:thrust",
        ]

        for query in search_queries:
            print(f"\n   🎯 Query: '{query}'")
            query_repos = await self._search_single_query(query)

            before_count = len(unique_repos)
            unique_repos.update(query_repos)
            new_repos = len(unique_repos) - before_count

            print(f"      Found {len(query_repos)} repos, {new_repos} new unique repos")
            print(f"      Total unique repos: {len(unique_repos)}")

            # Small delay between queries
            await asyncio.sleep(1)

            # Check rate limit
            if self.rate_limit_remaining < 50:
                print(
                    f"   ⚠️  Low on API requests ({self.rate_limit_remaining}). Stopping search."
                )
                break

        return unique_repos

    async def _search_single_query(self, query: str) -> Set[str]:
        """Execute a single repository search query"""
        session = await self._get_session()
        repos = set()

        page = 1
        while page <= self.max_pages:
            try:
                url = f"{self.base_url}/search/repositories"
                params = {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "page": page,
                    "per_page": self.results_per_page,
                }

                response = await session.get(url, params=params)

                # Check rate limit
                self._check_rate_limit(response)

                if response.status_code == 403:
                    print(f"      Rate limited. Stopping this query.")
                    break

                if response.status_code != 200:
                    print(f"      GitHub API error: {response.status_code}")
                    break

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                # Extract repository names
                for item in items:
                    repos.add(item["full_name"])

                # If we got fewer results than requested, we've reached the end
                if len(items) < self.results_per_page:
                    break

                page += 1

                # Check rate limit
                if self.rate_limit_remaining < 10:
                    print(
                        f"      Low on API requests ({self.rate_limit_remaining}). Stopping."
                    )
                    break

                # Small delay
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"      Error: {e}")
                break

        return repos

    def save_results(self, repos: Set[str]):
        """Save search results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save unique repository list
        repos_filename = f"thrust_repos_fast_search_{timestamp}.txt"
        sorted_repos = sorted(repos)

        with open(repos_filename, "w") as f:
            f.write(
                f"# GitHub Repositories containing 'thrust' (Fast Repository Search)\n"
            )
            f.write(f"# Search performed: {datetime.now().isoformat()}\n")
            f.write(f"# Method: Repository search API (5000/hour limit)\n")
            f.write(f"# Total unique repositories: {len(sorted_repos)}\n\n")

            for repo in sorted_repos:
                f.write(f"{repo}\n")

        print(f"📝 Repository list saved to: {repos_filename}")

        # Save CSV format
        csv_filename = f"thrust_repos_fast_{timestamp}.csv"
        with open(csv_filename, "w") as f:
            f.write("repository_name,github_url\n")
            for repo in sorted_repos:
                f.write(f"{repo},https://github.com/{repo}\n")

        print(f"📊 CSV format saved to: {csv_filename}")

    def print_summary(self, repos: Set[str]):
        """Print summary of search results"""
        print("\n" + "=" * 60)
        print("📊 FAST SEARCH RESULTS SUMMARY")
        print("=" * 60)

        print(f"🎯 Search method: Repository search API")
        print(f"⚡ Rate limit: 5000 requests/hour (vs 10/minute for code search)")
        print(f"🕒 Search completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"\n🏆 TOTAL UNIQUE REPOSITORIES: {len(repos)}")

        if repos:
            print("\n🔝 Top 15 repositories (alphabetical):")
            for i, repo in enumerate(sorted(repos)[:15], 1):
                print(f"   {i:>2}. {repo}")

            if len(repos) > 15:
                print(f"   ... and {len(repos) - 15} more repositories")


async def main():
    """Main function to run the fast search"""
    searcher = FastThrustRepositorySearcher()

    try:
        print("🚀 Fast GitHub Thrust Repository Search")
        print("Using repository search API instead of code search for speed")
        print("=" * 60)

        # Search for repositories
        repos = await searcher.search_thrust_repositories()

        # Print summary
        searcher.print_summary(repos)

        # Save results
        searcher.save_results(repos)

        print(f"\n✅ Fast search completed!")
        print(f"🎯 Found {len(repos)} unique repositories")
        print(f"💡 This approach is much faster but may miss some repositories")
        print(f"   that only mention 'thrust' in code files, not in repo metadata.")

    except KeyboardInterrupt:
        print("\n⏹️  Search interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
    finally:
        if searcher.session:
            await searcher.session.aclose()


if __name__ == "__main__":
    asyncio.run(main())
