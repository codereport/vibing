#!/usr/bin/env python3
"""
Generate repository data with star counts for SPA display
Reads thrust search results and fetches star counts from GitHub API
"""

import json
import asyncio
import httpx
import os
from typing import List, Dict, Set
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RepoDataGenerator:
    """Generates repository data with star counts for SPA display"""
    
    def __init__(self, search_results_file: str):
        self.search_results_file = search_results_file
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.session = None
        self.rate_limit_remaining = 5000
        
    async def _get_session(self):
        """Get or create HTTP session with GitHub authentication"""
        if self.session is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "ThrustRepoViewer/1.0",
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
                print("✅ Using authenticated GitHub API for repo data fetching")
            else:
                print("⚠️  Warning: No GITHUB_TOKEN found. Using unauthenticated API (lower rate limits)")
                
            self.session = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self.session
        
    def load_search_results(self) -> Set[str]:
        """Load and parse search results to get unique repositories"""
        print(f"📖 Loading search results from {self.search_results_file}")
        
        with open(self.search_results_file, 'r') as f:
            data = json.load(f)
            
        unique_repos = set()
        results_by_extension = data.get("results_by_extension", {})
        
        for extension, repos in results_by_extension.items():
            unique_repos.update(repos)
            print(f"   {extension}: {len(repos)} repositories")
            
        print(f"🎯 Total unique repositories: {len(unique_repos)}")
        return unique_repos
        
    async def fetch_repo_details(self, repo_name: str) -> Dict:
        """Fetch repository details from GitHub API"""
        session = await self._get_session()
        
        try:
            url = f"{self.base_url}/repos/{repo_name}"
            response = await session.get(url)
            
            # Update rate limit tracking
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining:
                self.rate_limit_remaining = int(remaining)
                
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": repo_name,
                    "stars": data.get("stargazers_count", 0),
                    "description": data.get("description", ""),
                    "language": data.get("language", "Unknown"),
                    "updated_at": data.get("updated_at", ""),
                    "html_url": data.get("html_url", f"https://github.com/{repo_name}"),
                    "topics": data.get("topics", []),
                    "forks": data.get("forks_count", 0),
                    "open_issues": data.get("open_issues_count", 0),
                    "created_at": data.get("created_at", ""),
                    "license": data.get("license", {}).get("name", "Unknown") if data.get("license") else "Unknown",
                    "homepage": data.get("homepage", ""),
                    "size": data.get("size", 0)
                }
            elif response.status_code == 404:
                return {
                    "name": repo_name,
                    "stars": -1,  # Mark as not found
                    "description": "Repository not found",
                    "language": "Unknown",
                    "updated_at": "",
                    "html_url": f"https://github.com/{repo_name}",
                    "topics": [],
                    "forks": 0,
                    "open_issues": 0,
                    "created_at": "",
                    "license": "Unknown",
                    "homepage": "",
                    "size": 0
                }
            else:
                print(f"❌ Error fetching {repo_name}: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Exception fetching {repo_name}: {e}")
            return None
            
    async def generate_repo_data(self) -> List[Dict]:
        """Generate complete repository data with star counts"""
        # Load unique repositories
        unique_repos = self.load_search_results()
        repo_list = sorted(unique_repos)
        
        print(f"\n🚀 Fetching details for {len(repo_list)} repositories...")
        print("⚠️  This may take a while due to API rate limits...")
        
        repo_data = []
        processed = 0
        
        # Process repositories in batches to manage rate limits
        batch_size = 100
        for i in range(0, len(repo_list), batch_size):
            batch = repo_list[i:i + batch_size]
            
            print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(repo_list) + batch_size - 1)//batch_size}")
            print(f"   Repositories {i+1}-{min(i+batch_size, len(repo_list))} of {len(repo_list)}")
            
            # Fetch data for batch
            tasks = [self.fetch_repo_details(repo) for repo in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for repo, result in zip(batch, batch_results):
                processed += 1
                
                if isinstance(result, Exception):
                    print(f"   ❌ {repo}: {result}")
                    continue
                    
                if result is not None:
                    repo_data.append(result)
                    stars = result['stars']
                    star_display = f"{stars:,}" if stars >= 0 else "N/A"
                    print(f"   ✅ {repo}: {star_display} stars")
                else:
                    print(f"   ⚠️  {repo}: Failed to fetch")
                    
                # Show progress
                if processed % 50 == 0:
                    print(f"   📊 Progress: {processed}/{len(repo_list)} ({processed/len(repo_list)*100:.1f}%)")
                    print(f"   🔄 Rate limit remaining: {self.rate_limit_remaining}")
                    
            # Small delay between batches
            if i + batch_size < len(repo_list):
                print(f"   ⏱️  Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
                
        # Sort by star count (descending)
        repo_data.sort(key=lambda x: x['stars'], reverse=True)
        
        print(f"\n✅ Successfully processed {len(repo_data)} repositories")
        return repo_data
        
    def save_repo_data(self, repo_data: List[Dict]):
        """Save repository data to JSON file for SPA"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"thrust_repos_with_stars_{timestamp}.json"
        
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "total_repositories": len(repo_data),
            "source_file": self.search_results_file,
            "repositories": repo_data
        }
        
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        print(f"💾 Repository data saved to: {filename}")
        
        # Also save a summary
        summary_filename = f"thrust_repos_summary_{timestamp}.txt"
        with open(summary_filename, 'w') as f:
            f.write(f"Thrust Repository Summary - Generated {datetime.now().isoformat()}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Total repositories: {len(repo_data)}\n")
            f.write(f"Source: {self.search_results_file}\n\n")
            
            f.write("Top 20 repositories by stars:\n")
            f.write("-" * 50 + "\n")
            
            for i, repo in enumerate(repo_data[:20], 1):
                stars = f"{repo['stars']:,}" if repo['stars'] >= 0 else "N/A"
                f.write(f"{i:2}. {repo['name']} - {stars} stars\n")
                
        print(f"📄 Summary saved to: {summary_filename}")
        return filename

async def main():
    """Main function"""
    search_file = "thrust_search_detailed_20250819_142934.json"
    
    # Check if search results file exists
    if not os.path.exists(search_file):
        print(f"❌ Search results file not found: {search_file}")
        return
        
    generator = RepoDataGenerator(search_file)
    
    try:
        # Generate repository data
        repo_data = await generator.generate_repo_data()
        
        # Save data for SPA
        output_file = generator.save_repo_data(repo_data)
        
        print(f"\n🎉 Repository data generation completed!")
        print(f"📊 Found {len(repo_data)} valid repositories")
        print(f"💾 Data saved to: {output_file}")
        print(f"🌟 Ready to create SPA!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if generator.session:
            await generator.session.aclose()

if __name__ == "__main__":
    asyncio.run(main())
