# GitHub Search - GPU Repository Analysis

A static analysis and exploration site for NVIDIA Thrust and CuPy usage across GitHub repositories.

## 🌐 Live Demo

- **Main Hub:** `index.html` - Landing page with links to all viewers
- **Repository Browser:** `thrust_repos.html` - Browse 3,142+ repositories using Thrust
- **Usage Analysis:** `thrust_usage.html` - Interactive dashboard analyzing thrust usage patterns
- **CuPy Repository Browser:** `cupy_repos.html` - Browse repositories that declare CuPy dependencies

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
├── cupy_repos.html         # ⚡ CuPy repository browser
├── serve.py                # 🌐 Local development server
├── scripts/                # 📝 Data generation scripts
│   ├── thrust_repository_search.py    # GitHub API search
│   ├── fetch_stars_latest.py         # Fetch star counts
│   ├── generate_repo_data.py         # Generate repository data
│   ├── cupy_repository_search.py      # Crawl CuPy dependency data
│   ├── cupy_local_analysis.py         # Analyze CuPy patterns in Python files
│   └── local_clone_analysis.py       # Clone and analyze top repos
├── data/                   # 📊 Generated data files
│   ├── thrust_repos_with_stars_*.json        # Repository browser data
│   ├── thrust_analysis_local_clone_*.json    # Analysis dashboard data
│   ├── cupy_repos.json                       # CuPy repository browser data
│   └── cupy_analysis.json                    # Local CuPy usage analysis
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

### Generate the CuPy repository dataset

From the project root, run:

```bash
python scripts/cupy_repository_search.py
```

The CuPy crawler reads GitHub's public dependency graph for the `cupy`,
`cupy-cuda11x`, `cupy-cuda12x`, and `cupy-cuda13x` packages. It does not need a
GitHub API token, writes `data/cupy_repos.json`, and checkpoints after every
page so an interrupted crawl can be resumed with the same command.

To generate the import-aware source analysis for the top 100 repositories:

```bash
python scripts/cupy_local_analysis.py --top 100 --concurrent 2
```

This second stage uses anonymous shallow Git clones and checks out only Python
files. It counts `cupy.` patterns, counts `cp.` only in files that bind it with
`import cupy as cp`, and reports files with CuPy plus CuPy coverage across the
repository's analyzed Python files. It
also checkpoints completed repositories and can be resumed with the same
command.

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

### CuPy Repository Browser (`cupy_repos.html`)

- CuPy dependency discovery across current distribution packages
- Star and fork rankings
- Repository and package search
- Star-based filtering
- Import-aware `cupy.` and `cp.` pattern counts for top repositories
- Files-with-CuPy and CuPy coverage rankings
- Incremental rendering for large datasets

## 🛠 Requirements

- Python 3.10+ (for data generation scripts)
- Git (for local source analysis)
- GitHub API token (set in `.env` for the Thrust API scripts; not required for CuPy)
- Modern web browser (for viewing dashboards)

## ✨ GitHub Pages Ready

All HTML files are fully static and work perfectly on GitHub Pages without any server-side requirements.
