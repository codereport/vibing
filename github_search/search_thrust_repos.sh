#!/bin/bash
# Wrapper script to run thrust repository search using uv

echo "🚀 GitHub Thrust Repository Search"
echo "Searching for 'thrust' keyword in .cu/.h/.cpp/.hpp/.cuh files"
echo "=================================================="

# Run using uv to ensure proper dependencies
uv run python thrust_repository_search.py
