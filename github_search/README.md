# GitHub Search - Thrust Analysis

A comprehensive analysis and exploration platform for NVIDIA Thrust usage across GitHub repositories.

## 🌐 Live Demo

- **Main Hub:** `index.html` - Landing page with links to both dashboards
- **Repository Browser:** `thrust_repos.html` - Browse 3,142+ repositories using Thrust
- **Usage Analysis:** `thrust_usage.html` - Interactive dashboard analyzing thrust usage patterns

## 🚀 Quick Start

### Local Development
```bash
python serve.py
```
Opens `http://localhost:8080` with the full application.

### GitHub Pages
Just push to your repository and enable GitHub Pages - all files are static and will work immediately.

## 📁 Project Structure

```
github_search/
├── index.html              # 🔍 Main landing page
├── thrust_repos.html       # 🚀 Repository browser (3,142+ repos)
├── thrust_usage.html       # 📊 Analysis dashboard
├── serve.py                # 🌐 Local development server
├── scripts/                # 📝 Data generation scripts
│   ├── thrust_repository_search.py    # GitHub API search
│   ├── fetch_stars_latest.py         # Fetch star counts
│   ├── generate_repo_data.py         # Generate repository data
│   └── local_clone_analysis.py       # Clone and analyze top repos
├── data/                   # 📊 Generated data files
│   ├── thrust_repos_with_stars_*.json        # Repository browser data
│   └── thrust_analysis_local_clone_*.json    # Analysis dashboard data
└── requirements.txt        # Python dependencies
```

## 🔄 Data Generation

To generate fresh data:

1. **Search for repositories:**
   ```bash
   cd scripts
   python thrust_repository_search.py
   ```

2. **Fetch star counts:**
   ```bash
   python fetch_stars_latest.py
   ```

3. **Generate repository viewer data:**
   ```bash
   python generate_repo_data.py
   ```

4. **Analyze top repositories:**
   ```bash
   python local_clone_analysis.py
   ```

## 📊 Features

### Repository Browser (`thrust_repos.html`)
- 3,142+ repositories discovered
- Star-based ranking system
- Advanced search and filtering
- Repository metadata and links
- Language and topic categorization

### Analysis Dashboard (`thrust_usage.html`)
- Extension-based usage analysis
- Interactive charts and visualizations
- Repository filtering and sorting
- Statistical summaries and metrics
- Local clone vs API analysis comparison

## 🛠 Requirements

- Python 3.8+ (for data generation scripts)
- GitHub API token (set in `.env` file for data generation)
- Modern web browser (for viewing dashboards)

## ✨ GitHub Pages Ready

All HTML files are fully static and work perfectly on GitHub Pages without any server-side requirements.