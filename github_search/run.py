#!/usr/bin/env python3
"""
Startup script for GitHub Thrust Search Tool
"""

import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv


def main():
    """Start the web application"""
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Load environment variables from .env file
    load_dotenv()

    print("🚀 Starting GitHub Thrust Search Tool...")
    print("📍 Server will be available at: http://localhost:8000")
    print("⚡ Use Ctrl+C to stop the server")
    print()

    # Check for GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("⚠️  Warning: No GITHUB_TOKEN found in environment variables")
        print("   You'll have lower rate limits without authentication")
        print("   Create a .env file with GITHUB_TOKEN=your_token")
        print()

    # Start the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["./"])


if __name__ == "__main__":
    main()
