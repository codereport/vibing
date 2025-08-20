# GitHub Thrust Repository Search

This script searches GitHub for repositories containing the keyword "thrust" in specific file extensions and returns a unique list of repositories.

## What it does

The script searches for the keyword **"thrust"** in files with these extensions:
- `.cu` - CUDA source files
- `.h` - C/C++ header files  
- `.cpp` - C++ source files
- `.hpp` - C++ header files
- `.cuh` - CUDA header files

It returns a **unique list of GitHub repositories** that contain files with the "thrust" keyword.

## Usage

### Option 1: Using the wrapper script (recommended)
```bash
./search_thrust_repos.sh
```

### Option 2: Using uv directly
```bash
uv run python thrust_repository_search.py
```

### Option 3: Using the simple runner
```bash
uv run python run_thrust_search.py
```

## GitHub Authentication

For better rate limits (5000 requests/hour vs 60 requests/hour), set up a GitHub token:

1. Create a GitHub Personal Access Token at: https://github.com/settings/tokens
2. Create a `.env` file in this directory:
   ```
   GITHUB_TOKEN=your_token_here
   ```

## Output Files

The script creates three output files with timestamps:

1. **`thrust_unique_repositories_YYYYMMDD_HHMMSS.txt`** - Plain text list of unique repositories (what you requested)
2. **`thrust_search_detailed_YYYYMMDD_HHMMSS.json`** - Detailed results by file extension
3. **`thrust_repositories_YYYYMMDD_HHMMSS.csv`** - CSV format with repository names and URLs

## Rate Limiting

- **Without GitHub token**: 60 requests/hour
- **With GitHub token**: 5000 requests/hour

The script automatically:
- Monitors rate limits
- Stops when approaching limits
- Searches up to 10 pages per file extension (1000 results max per extension)

## Expected Results

Based on your mention of 51,000 files for `.cu` extension alone, you should expect to find thousands of unique repositories. The script will show progress for each file extension and provide a summary at the end.

## Example Output

```
🔍 Searching for 'thrust' in .cu files...
   📄 Fetching page 1...
   📊 Page 1: Found 100 files, 95 unique repos this page
   📈 Total unique repos so far for .cu: 95
   ...

✅ Found 1,234 unique repositories with 'thrust' in .cu files

🏆 TOTAL UNIQUE REPOSITORIES: 3,456
```
