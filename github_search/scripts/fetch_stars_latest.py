#!/usr/bin/env python3
"""
Fetch GitHub Stars for Latest Thrust Repository Search Results
Reads the CSV file from the latest search and fetches star counts for all repositories.
"""

import os
import asyncio
import httpx
import json
import csv
import time
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GitHubStarFetcher:
    """Fetches GitHub star counts for repositories from the latest search"""

    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None

        # Rate limiting (authenticated: 5000/hour, unauthenticated: 60/hour)
        self.rate_limit_remaining = 5000 if self.github_token else 60
        self.repositories = []
        self.results = []

    async def _get_session(self):
        """Get or create HTTP session with GitHub authentication"""
        if self.session is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "ThrustRepositoryStarFetcher/1.0",
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
                print("✅ Using authenticated GitHub API (5000 requests/hour)")
            else:
                print(
                    "⚠️  Warning: No GITHUB_TOKEN found. Using unauthenticated API (60 requests/hour)"
                )
                print(
                    "   This will take much longer. Set GITHUB_TOKEN for better performance"
                )

            self.session = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self.session

    def load_repositories(self):
        """Load repository list from CSV file"""
        print(f"📁 Loading repositories from {self.csv_file}")

        with open(self.csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                repo_name = row["repository_name"]
                self.repositories.append(repo_name)

        print(f"📊 Loaded {len(self.repositories)} repositories")
        return len(self.repositories)

    def _check_rate_limit(self, response):
        """Check and update rate limit from response headers"""
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        reset_time = response.headers.get("X-RateLimit-Reset")

        if remaining:
            self.rate_limit_remaining = int(remaining)
            if limit:
                print(f"   API requests remaining: {self.rate_limit_remaining}/{limit}")

            # If we're low on requests, show when it resets
            if self.rate_limit_remaining < 10 and reset_time:
                reset_dt = datetime.fromtimestamp(int(reset_time))
                print(f"   Rate limit resets at: {reset_dt.strftime('%H:%M:%S')}")

    async def fetch_repository_info(self, repo_name: str) -> Dict[str, Any]:
        """Fetch detailed information for a single repository"""
        session = await self._get_session()

        try:
            url = f"{self.base_url}/repos/{repo_name}"
            response = await session.get(url)

            # Check rate limit
            self._check_rate_limit(response)

            if response.status_code == 404:
                return {
                    "name": repo_name,
                    "full_name": repo_name,
                    "stars": -1,
                    "error": "not_found",
                    "html_url": f"https://github.com/{repo_name}",
                    "description": "Repository not found",
                    "language": "Unknown",
                    "forks": 0,
                    "updated_at": None,
                    "license": "Unknown",
                    "topics": [],
                }

            if response.status_code == 403:
                return {
                    "name": repo_name,
                    "full_name": repo_name,
                    "stars": -2,
                    "error": "rate_limited",
                    "html_url": f"https://github.com/{repo_name}",
                    "description": "Rate limited",
                    "language": "Unknown",
                    "forks": 0,
                    "updated_at": None,
                    "license": "Unknown",
                    "topics": [],
                }

            if response.status_code != 200:
                return {
                    "name": repo_name,
                    "full_name": repo_name,
                    "stars": -3,
                    "error": f"api_error_{response.status_code}",
                    "html_url": f"https://github.com/{repo_name}",
                    "description": f"API Error {response.status_code}",
                    "language": "Unknown",
                    "forks": 0,
                    "updated_at": None,
                    "license": "Unknown",
                    "topics": [],
                }

            data = response.json()

            # Extract license info
            license_info = "Unknown"
            if data.get("license") and data["license"].get("name"):
                license_info = data["license"]["name"]

            return {
                "name": data.get("name", repo_name.split("/")[-1]),
                "full_name": data.get("full_name", repo_name),
                "stars": data.get("stargazers_count", 0),
                "error": None,
                "html_url": data.get("html_url", f"https://github.com/{repo_name}"),
                "description": data.get("description", "No description available"),
                "language": data.get("language", "Unknown"),
                "forks": data.get("forks_count", 0),
                "updated_at": data.get("updated_at"),
                "license": license_info,
                "topics": data.get("topics", []),
            }

        except Exception as e:
            return {
                "name": repo_name,
                "full_name": repo_name,
                "stars": -4,
                "error": f"exception_{str(e)}",
                "html_url": f"https://github.com/{repo_name}",
                "description": f"Error: {str(e)}",
                "language": "Unknown",
                "forks": 0,
                "updated_at": None,
                "license": "Unknown",
                "topics": [],
            }

    async def fetch_all_stars(self):
        """Fetch star counts for all repositories with progress tracking"""
        total_repos = len(self.repositories)
        print(f"🚀 Starting to fetch star data for {total_repos} repositories")
        print(f"⏱️  Estimated time: {total_repos * 0.6:.1f} seconds (0.6s per repo)")

        start_time = time.time()
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

        async def fetch_with_semaphore(repo_name: str, index: int):
            async with semaphore:
                result = await self.fetch_repository_info(repo_name)

                # Progress update every 50 repos
                if (index + 1) % 50 == 0 or index + 1 == total_repos:
                    elapsed = time.time() - start_time
                    rate = (index + 1) / elapsed
                    eta = (total_repos - index - 1) / rate if rate > 0 else 0

                    stars = result.get("stars", 0)
                    star_status = "⭐" if stars > 0 else "❌" if stars < 0 else "⚪"

                    print(
                        f"{star_status} Progress: {index + 1:>4}/{total_repos} ({((index + 1)/total_repos)*100:.1f}%) | "
                        f"Rate: {rate:.1f} repos/s | ETA: {eta/60:.1f}m | "
                        f"Latest: {repo_name} ({stars} stars)"
                    )

                return result

        # Create tasks for all repositories
        tasks = [
            fetch_with_semaphore(repo_name, i)
            for i, repo_name in enumerate(self.repositories)
        ]

        # Execute all tasks
        self.results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        successful = len([r for r in self.results if r.get("stars", -1) >= 0])

        print(f"\n✅ Completed in {total_time:.1f} seconds")
        print(f"📊 Successfully fetched: {successful}/{total_repos} repositories")
        print(f"⚡ Average rate: {total_repos/total_time:.1f} repositories/second")

    def analyze_results(self):
        """Analyze and display results statistics"""
        successful = [r for r in self.results if r.get("stars", -1) >= 0]
        total_stars = sum(r.get("stars", 0) for r in successful)

        # Sort by stars for top repositories
        sorted_repos = sorted(successful, key=lambda x: x.get("stars", 0), reverse=True)

        print(f"\n📈 ANALYSIS RESULTS")
        print(f"=" * 60)
        print(f"Total repositories: {len(self.results)}")
        print(f"Successfully fetched: {len(successful)}")
        print(f"Total stars: {total_stars:,}")
        print(
            f"Average stars: {total_stars/len(successful):.1f}" if successful else "N/A"
        )
        print(
            f"Median stars: {sorted_repos[len(sorted_repos)//2].get('stars', 0)}"
            if successful
            else "N/A"
        )

        # Show top 15 repositories
        print(f"\n🏆 TOP 15 REPOSITORIES BY STARS:")
        for i, repo in enumerate(sorted_repos[:15], 1):
            stars = repo.get("stars", 0)
            name = repo.get("full_name", repo.get("name", "Unknown"))
            print(f"   {i:>2}. {name:<40} {stars:>6,} ⭐")

        # Show distribution
        star_ranges = [
            (10000, "10K+"),
            (1000, "1K-10K"),
            (100, "100-1K"),
            (10, "10-100"),
            (1, "1-10"),
            (0, "0"),
        ]

        print(f"\n📊 STAR DISTRIBUTION:")
        for min_stars, label in star_ranges:
            if min_stars == 10000:
                count = len([r for r in successful if r.get("stars", 0) >= min_stars])
            elif min_stars == 0:
                count = len([r for r in successful if r.get("stars", 0) == 0])
            else:
                next_min = star_ranges[star_ranges.index((min_stars, label)) - 1][0]
                count = len(
                    [r for r in successful if min_stars <= r.get("stars", 0) < next_min]
                )

            percentage = (count / len(successful)) * 100 if successful else 0
            print(f"   {label:>8}: {count:>4} repos ({percentage:>5.1f}%)")

    def save_results(self):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"../data/thrust_repos_with_stars_{timestamp}.json"

        # Sort by stars (descending)
        sorted_results = sorted(
            self.results, key=lambda x: x.get("stars", -1), reverse=True
        )

        output_data = {
            "generated_at": datetime.now().isoformat(),
            "source_file": self.csv_file,
            "total_repositories": len(self.results),
            "successful_fetches": len(
                [r for r in self.results if r.get("stars", -1) >= 0]
            ),
            "total_stars": sum(
                r.get("stars", 0) for r in self.results if r.get("stars", -1) >= 0
            ),
            "repositories": sorted_results,
        }

        with open(filename, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n💾 Results saved to: {filename}")
        return filename


async def main():
    """Main function"""
    csv_file = "../data/thrust_repositories_20250819_155819.csv"

    if not os.path.exists(csv_file):
        print(f"❌ Error: CSV file {csv_file} not found")
        return

    fetcher = GitHubStarFetcher(csv_file)

    try:
        # Load repositories
        fetcher.load_repositories()

        # Fetch star data
        await fetcher.fetch_all_stars()

        # Analyze results
        fetcher.analyze_results()

        # Save results
        output_file = fetcher.save_results()

        print(f"\n✅ Star fetching completed!")
        print(f"📁 Output saved to: {output_file}")

    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if fetcher.session:
            await fetcher.session.aclose()


if __name__ == "__main__":
    asyncio.run(main())
