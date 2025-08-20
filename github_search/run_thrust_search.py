#!/usr/bin/env python3
"""
Simple runner script for thrust repository search
"""

import asyncio
import os
from thrust_repository_search import ThrustRepositorySearcher

def main():
    """Simple main function to run the thrust search"""
    print("🚀 GitHub Thrust Repository Search")
    print("=" * 50)
    
    # Check for GitHub token
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠️  Warning: GITHUB_TOKEN not found in environment")
        print("   Create a .env file with your GitHub token for better rate limits")
        print("   Example: echo 'GITHUB_TOKEN=your_token_here' > .env")
        print()
        
        choice = input("Continue anyway? (y/N): ").strip().lower()
        if choice != 'y':
            print("Exiting. Set up your GitHub token and try again.")
            return
    
    print("Starting search for 'thrust' keyword in .cu/.h/.cpp/.hpp/.cuh files...\n")
    
    # Run the async search
    asyncio.run(run_search())

async def run_search():
    """Run the actual search"""
    searcher = ThrustRepositorySearcher()
    
    try:
        # Search all file extensions  
        results = await searcher.search_all_extensions()
        
        # Get unique repositories
        unique_repos = searcher.get_unique_repositories(results)
        
        # Print summary
        searcher.print_summary(results, unique_repos)
        
        # Save results
        searcher.save_results(results, unique_repos)
        
        print(f"\n✅ Search completed successfully!")
        print(f"🎯 Found {len(unique_repos)} unique GitHub repositories containing 'thrust'")
        
    except KeyboardInterrupt:
        print("\n⏹️  Search interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if searcher.session:
            await searcher.session.aclose()

if __name__ == "__main__":
    main()
