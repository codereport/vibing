# GitHub Thrust Library Search Tool

A web application that searches and ranks GitHub repositories based on their usage of the Nvidia Thrust library. The tool combines Thrust usage analysis with repository popularity metrics to provide comprehensive rankings.

## Features

🔍 **Smart Repository Search**
- Search GitHub repositories with custom queries
- Filter by programming language (C++, CUDA, Python, etc.)
- Set minimum star thresholds
- Intelligent default search for GPU/CUDA-related repositories

⚡ **Thrust Usage Analysis**
- Analyzes repository code for Thrust library usage patterns
- Detects namespace usage, header includes, and function calls
- Counts occurrences across relevant source files
- Supports multiple file formats (.cu, .cpp, .h, etc.)

📊 **Advanced Ranking System**
- **Thrust Score**: Based on frequency of Thrust library usage
- **Popularity Score**: Combines stars, forks, and recency
- **Combined Score**: Weighted combination of both metrics
- Logarithmic scaling to handle outliers

🎨 **Modern Web Interface**
- Clean, responsive design
- Real-time search results
- Sortable by different metrics
- Repository cards with detailed information

## Setup

### Prerequisites
- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- GitHub Personal Access Token (recommended for higher rate limits)

### Quick Start

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
make install

# 3. Create .env file with your GitHub token
echo "GITHUB_TOKEN=your_token_here" > .env

# 4. Start the application
make run

# 5. Open http://localhost:8000 in your browser
```

### Manual Installation

1. **Navigate to the project directory:**
   ```bash
   cd /home/cph/vibing/github_search
   ```

2. **Install Python dependencies:**
   
   With uv (recommended):
   ```bash
   uv sync
   ```
   
   Or with pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file:
   ```bash
   echo "GITHUB_TOKEN=your_github_personal_access_token_here" > .env
   ```

4. **Run the application:**
   ```bash
   python run.py
   # or
   python main.py
   ```

5. **Access the web interface:**
   Open `http://localhost:8000` in your browser

### Docker Deployment

```bash
# Build and run with Docker Compose
make docker

# Or manually:
docker-compose up --build
```

### Testing

```bash
# Run the test suite
make test

# Or manually:
python test_search.py
```

## Advanced Analysis

### Secondary Analysis (GitHub API)
Performs deep analysis of top repositories using the GitHub API:

```bash
# Analyze top 20 repositories with thrust usage
uv run secondary_analysis.py --top 20
```

### Local Clone Analysis (No API Limits)
Alternative analysis that clones repositories locally for comprehensive analysis without API rate limits:

```bash
# Analyze top 20 repositories by cloning locally
uv run local_clone_analysis.py --top 20

# Use custom clone directory
uv run local_clone_analysis.py --top 10 --clone-dir /tmp/analysis_repos
```

**Benefits of Local Clone Analysis:**
- ✅ No GitHub API rate limits
- ✅ Faster analysis of repository contents
- ✅ More comprehensive file analysis
- ✅ Better performance metrics (clone size, analysis time)
- ✅ Automatic cleanup of cloned repositories

**Performance:** Typically analyzes 30+ repos/minute depending on repository size.

## API Endpoints

### `GET /`
Serves the main web interface

### `GET /search`
Search and analyze repositories

**Parameters:**
- `query` (optional): Search query string
- `language` (optional): Programming language filter
- `min_stars` (optional): Minimum number of stars (default: 0)
- `max_results` (optional): Maximum results to return (default: 50)
- `sort_by` (optional): Sort criteria - "combined_score", "thrust_usage", or "popularity"

**Example:**
```
GET /search?query=CUDA&language=C++&min_stars=10&sort_by=thrust_usage
```

## Scoring Algorithm

### Thrust Score (0-100)
- Based on the number of Thrust library usage occurrences
- Uses logarithmic scaling: `100 * log(usage + 1) / log(base + 1)`
- Patterns detected:
  - `thrust::` namespace usage
  - `#include <thrust/...>` header includes
  - `thrust_` prefixed functions
  - `using namespace thrust`

### Popularity Score (0-100)
- Combines stars and forks: `stars + (forks * 0.3)`
- Applies recency factor based on last update
- Uses logarithmic scaling to handle viral repositories
- Recent updates boost the score

### Combined Score
- Weighted average: `(thrust_score * 0.6) + (popularity_score * 0.4)`
- Balances technical relevance with community adoption

## Architecture

```
main.py                    # FastAPI web server and routes
github_analyzer.py         # GitHub API integration and code analysis  
ranking_engine.py          # Scoring and ranking algorithms
secondary_analysis.py      # Deep analysis using GitHub API
local_clone_analysis.py    # Local repository clone analysis (no API limits)
requirements.txt           # Python dependencies
```

## Rate Limiting

- The tool respects GitHub API rate limits
- With authentication: 5,000 requests/hour
- Without authentication: 60 requests/hour
- Automatic retry with exponential backoff

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use this tool for your own projects!

## Troubleshooting

**Rate Limit Errors:**
- Add a GitHub personal access token to increase limits
- Reduce `max_results` parameter
- Wait for rate limit reset

**No Results Found:**
- Try broader search terms
- Lower `min_stars` threshold
- Check repository language filters

**Analysis Timeouts:**
- Large repositories may take longer to analyze
- The tool automatically skips very large files (>1MB)
- Results are cached for efficiency
