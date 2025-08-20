#!/usr/bin/env python3
"""
Advanced Thrust Analysis Dashboard
Provides comprehensive visualization and tabular analysis of thrust usage across repositories.
"""

import os
import json
import csv
from flask import Flask, render_template_string, jsonify
from collections import defaultdict

app = Flask(__name__)


class ThrustAnalyzer:
    def __init__(self):
        self.data = {}
        self.load_data()

    def load_data(self):
        """Load data from all available analysis files"""
        # Load detailed JSON data - support both API-based and local clone analysis
        json_files = [
            f
            for f in os.listdir("data")
            if (
                f.startswith("thrust_analysis_detailed_")
                or f.startswith("thrust_analysis_local_clone_")
            )
            and f.endswith(".json")
        ]
        if json_files:
            # Use the most recent file (by timestamp in filename)
            json_files.sort(reverse=True)
            with open(os.path.join("data", json_files[0]), "r") as f:
                self.detailed_data = json.load(f)
                print(f"📊 Loaded analysis data from: {json_files[0]}")

        # Load aggregated extensions data - support both analysis types
        ext_files = [
            f
            for f in os.listdir("data")
            if f.startswith("thrust_analysis_extensions_") and f.endswith(".csv")
        ]
        if ext_files:
            ext_files.sort(reverse=True)
            self.extensions_data = self._read_csv_to_dict(
                os.path.join("data", ext_files[0])
            )
            print(f"📊 Loaded extensions data from: {ext_files[0]}")

        # Load repositories data - support both analysis types
        repo_files = [
            f
            for f in os.listdir("data")
            if (
                f.startswith("thrust_analysis_repositories_")
                or f.startswith("thrust_analysis_local_repos_")
            )
            and f.endswith(".csv")
        ]
        if repo_files:
            repo_files.sort(reverse=True)
            self.repositories_data = self._read_csv_to_dict(
                os.path.join("data", repo_files[0])
            )
            print(f"📊 Loaded repository data from: {repo_files[0]}")

        # Generate extensions data from detailed data if we don't have the CSV
        if not hasattr(self, "extensions_data") and hasattr(self, "detailed_data"):
            print("📊 Generating extensions data from detailed analysis...")
            self.extensions_data = self._generate_extensions_from_detailed()

    def _read_csv_to_dict(self, filename):
        """Read CSV file and return list of dictionaries"""
        data = []
        try:
            with open(filename, "r") as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, 1):
                    # Convert numeric fields
                    for key, value in row.items():
                        if value is None or value == "":
                            continue
                        try:
                            if "." in str(value):
                                row[key] = float(value)
                            else:
                                row[key] = int(value)
                        except (ValueError, TypeError):
                            pass  # Keep as string
                    data.append(row)
                    if row_num <= 5:  # Debug first few rows
                        print(f"📊 CSV row {row_num}: {row.get('repository', 'N/A')}")
            print(f"📊 Successfully loaded {len(data)} rows from {filename}")
        except Exception as e:
            print(f"❌ Error reading CSV {filename}: {e}")
        return data

    def _generate_extensions_from_detailed(self):
        """Generate extension summary from detailed analysis data"""
        if not hasattr(self, "detailed_data") or not self.detailed_data:
            return []

        extensions_summary = defaultdict(
            lambda: {"total_files": 0, "thrust_usage": 0, "api_calls": 0}
        )

        for repo in self.detailed_data.get("repositories", []):
            for ext, count in repo.get("files_by_extension", {}).items():
                extensions_summary[ext]["total_files"] += count
            for ext, count in repo.get("thrust_by_extension", {}).items():
                extensions_summary[ext]["thrust_usage"] += count
            for ext, count in repo.get("api_by_extension", {}).items():
                extensions_summary[ext]["api_calls"] += count

        # Convert to list format expected by dashboard
        result = []
        for ext, data in extensions_summary.items():
            files = data["total_files"]
            thrust = data["thrust_usage"]
            apis = data["api_calls"]

            # Only include extensions that have thrust usage > 0
            if thrust > 0:
                result.append(
                    {
                        "extension": ext,
                        "total_files": files,
                        "thrust_usage": thrust,
                        "api_calls": apis,
                        "avg_thrust_per_file": (
                            round(thrust / files, 2) if files > 0 else 0
                        ),
                        "avg_apis_per_file": round(apis / files, 2) if files > 0 else 0,
                        "thrust_density": (
                            round((thrust + apis) / files, 2) if files > 0 else 0
                        ),
                    }
                )

        # Sort by thrust usage
        result.sort(key=lambda x: x["thrust_usage"], reverse=True)
        return result

    def get_extension_summary(self, repo_filter=None):
        """Get extension summary for all repos or specific repo"""
        print(f"DEBUG: repo_filter = '{repo_filter}'")  # Debug line

        if repo_filter == "all" or repo_filter is None:
            # Use the pre-computed aggregated data
            return self.extensions_data
        else:
            # Calculate for specific repository from detailed data
            if not hasattr(self, "detailed_data") or not self.detailed_data:
                print("DEBUG: No detailed data available")  # Debug line
                return []

            repo_data = None
            available_repos = []
            for repo in self.detailed_data.get("repositories", []):
                available_repos.append(repo["repo_name"])
                if repo["repo_name"] == repo_filter:
                    repo_data = repo
                    break

            print(f"DEBUG: Available repos: {available_repos}")  # Debug line
            print(f"DEBUG: Looking for: '{repo_filter}'")  # Debug line

            if not repo_data:
                print(f"DEBUG: Repository '{repo_filter}' not found")  # Debug line
                return []

            print(f"DEBUG: Found repo data for {repo_data['repo_name']}")  # Debug line

            extensions = []
            for ext, files in repo_data["files_by_extension"].items():
                thrust_usage = repo_data["thrust_by_extension"].get(ext, 0)
                api_calls = repo_data["api_by_extension"].get(ext, 0)
                avg_thrust = round(thrust_usage / files, 2) if files > 0 else 0
                avg_apis = round(api_calls / files, 2) if files > 0 else 0
                thrust_density = round(thrust_usage / files, 2) if files > 0 else 0

                # Only include extensions that have thrust usage > 0
                if thrust_usage > 0:
                    extensions.append(
                        {
                            "extension": ext,
                            "total_files": files,
                            "thrust_usage": thrust_usage,
                            "api_calls": api_calls,
                            "avg_thrust_per_file": avg_thrust,
                            "avg_apis_per_file": avg_apis,
                            "thrust_density": thrust_density,
                        }
                    )

            # Sort by thrust usage descending
            extensions.sort(key=lambda x: x["thrust_usage"], reverse=True)
            print(f"DEBUG: Returning {len(extensions)} extensions")  # Debug line
            return extensions

    def get_repositories(self):
        """Get list of available repositories"""
        repos = [{"name": "all", "display": "All Repositories"}]
        if hasattr(self, "detailed_data"):
            for repo in self.detailed_data.get("repositories", []):
                repos.append(
                    {
                        "name": repo["repo_name"],
                        "display": f"{repo['repo_name']} ({repo['stars']} ⭐)",
                    }
                )
        return repos

    def get_repository_stats(self):
        """Get overall repository statistics"""
        # Force use of detailed JSON data for local clone analysis
        if (
            hasattr(self, "detailed_data")
            and self.detailed_data.get("metadata", {}).get("analysis_method")
            == "local_git_clone"
        ):
            print(f"📊 Using detailed JSON data for local clone analysis")
            return self._generate_stats_from_detailed()
        elif hasattr(self, "repositories_data"):
            print(f"📊 Returning {len(self.repositories_data)} repos from CSV data")
            return self.repositories_data
        elif hasattr(self, "detailed_data"):
            return self._generate_stats_from_detailed()
        print("📊 No data available")
        return []

    def _generate_stats_from_detailed(self):
        """Generate repository stats from detailed JSON data"""
        print(
            f"📊 Generating stats from detailed data with {len(self.detailed_data.get('repositories', []))} repos"
        )
        stats = []
        for repo in self.detailed_data.get("repositories", []):
            total_thrust = sum(repo.get("thrust_by_extension", {}).values())
            total_apis = sum(repo.get("api_by_extension", {}).values())
            top_ext = (
                max(repo.get("thrust_by_extension", {}).items(), key=lambda x: x[1])[0]
                if repo.get("thrust_by_extension")
                else "none"
            )

            stats.append(
                {
                    "repository": repo.get("repo_name", ""),
                    "stars": repo.get("stars", 0),
                    "forks": repo.get("forks", 0),
                    "language": repo.get("language", "Unknown"),
                    "combined_score": repo.get("combined_score", 0),
                    "files_analyzed": repo.get("files_analyzed", 0),
                    "total_thrust_usage": total_thrust,
                    "total_api_calls": total_apis,
                    "top_extension_by_thrust": top_ext,
                    "thrust_files_count": len(
                        [
                            f
                            for f in repo.get("top_files", [])
                            if f.get("total_thrust", 0) > 0
                        ]
                    ),
                    # Local clone specific fields (if available)
                    "clone_size_mb": repo.get("clone_size_mb", 0),
                    "analysis_time_seconds": repo.get("analysis_time_seconds", 0),
                }
            )
        print(f"📊 Generated {len(stats)} repository stats")
        return stats


analyzer = ThrustAnalyzer()


@app.route("/")
def dashboard():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_TEMPLATE)


@app.route("/api/extensions/<path:repo_filter>")
def get_extensions(repo_filter):
    """API endpoint for extension data"""
    # URL decode the repository name
    from urllib.parse import unquote

    repo_filter = unquote(repo_filter)
    data = analyzer.get_extension_summary(repo_filter)
    return jsonify(data)


@app.route("/api/repositories")
def get_repositories():
    """API endpoint for repository list"""
    return jsonify(analyzer.get_repositories())


@app.route("/api/repository-stats")
def get_repository_stats():
    """API endpoint for repository statistics"""
    return jsonify(analyzer.get_repository_stats())


DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thrust Usage Analysis Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .controls {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 15px;
            justify-content: center;
        }
        
        .control-group label {
            font-weight: 600;
            color: #495057;
        }
        
        select {
            padding: 12px 20px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            background: white;
            min-width: 250px;
            transition: all 0.3s ease;
        }
        
        select:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
        }
        
        .content {
            padding: 30px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .section {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border: 1px solid #e9ecef;
        }
        
        .section h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.4em;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .icon {
            font-size: 1.2em;
        }
        
        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        
        .sortable {
            cursor: pointer;
            user-select: none;
            transition: background-color 0.2s ease;
        }
        
        .sortable:hover {
            background: linear-gradient(135deg, #5a6fd8 0%, #6b4190 100%);
        }
        
        .sort-indicator {
            font-size: 0.8em;
            opacity: 0.6;
            margin-left: 5px;
        }
        
        .sorted-asc .sort-indicator::after {
            content: " ▲";
            opacity: 1;
        }
        
        .sorted-desc .sort-indicator::after {
            content: " ▼";
            opacity: 1;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
            transition: background 0.2s ease;
        }
        
        tr:hover td {
            background: #f8f9fa;
        }
        
        .number {
            text-align: right;
            font-family: 'Monaco', 'Menlo', monospace;
            font-weight: 500;
        }
        
        .extension {
            font-family: 'Monaco', 'Menlo', monospace;
            font-weight: 600;
            color: #e83e8c;
        }
        
        .chart-container {
            position: relative;
            height: 400px;
            margin-top: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-card h3 {
            font-size: 2em;
            margin-bottom: 5px;
        }
        
        .stat-card p {
            opacity: 0.9;
            font-size: 0.9em;
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
            color: #6c757d;
            font-style: italic;
        }
        
        .repo-badge {
            display: inline-block;
            background: #e3f2fd;
            color: #1565c0;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 10px;
        }
        
        @media (max-width: 768px) {
            .content {
                grid-template-columns: 1fr;
            }
            
            .control-group {
                flex-direction: column;
                align-items: stretch;
            }
            
            select {
                min-width: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Thrust Usage Analysis Dashboard</h1>
            <p>Comprehensive analysis of NVIDIA Thrust library usage across CUDA repositories</p>
            <p id="analysisInfo" style="font-size: 0.9em; opacity: 0.8; margin-top: 10px;"></p>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label for="repoSelect">📁 Repository:</label>
                <select id="repoSelect">
                    <option value="all">Loading repositories...</option>
                </select>
            </div>
        </div>
        
        <div class="content">
            <div class="section full-width">
                <h2><span class="icon">📈</span>Thrust Usage by File Extension</h2>
                <div class="table-container">
                    <table id="extensionsTable">
                        <thead>
                            <tr>
                                <th data-sort="extension" class="sortable">Extension <span class="sort-indicator">↕</span></th>
                                <th data-sort="files" class="sortable">Files <span class="sort-indicator">↕</span></th>
                                <th data-sort="thrust" class="sortable">Thrust <span class="sort-indicator">↕</span></th>
                                <th data-sort="apis" class="sortable">APIs <span class="sort-indicator">↕</span></th>
                                <th data-sort="avg" class="sortable">Avg/File <span class="sort-indicator">↕</span></th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="5" class="loading">Loading data...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="section">
                <h2><span class="icon">📊</span>Thrust Usage Distribution</h2>
                <div class="chart-container">
                    <canvas id="thrustChart"></canvas>
                </div>
            </div>
            
            <div class="section">
                <h2><span class="icon">🎯</span>Files vs API Calls</h2>
                <div class="chart-container">
                    <canvas id="apiChart"></canvas>
                </div>
            </div>
            
            <div class="section full-width">
                <h2><span class="icon">📊</span>Summary Statistics</h2>
                <div class="stats-grid" id="statsGrid">
                    <div class="stat-card">
                        <h3 id="totalFiles">-</h3>
                        <p>Total Files</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="totalThrust">-</h3>
                        <p>Total Thrust Usage</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="totalApis">-</h3>
                        <p>Total API Calls</p>
                    </div>
                    <div class="stat-card">
                        <h3 id="avgPerFile">-</h3>
                        <p>Avg Thrust/File</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let thrustChart = null;
        let apiChart = null;
        
        // Sorting state
        let currentExtensionData = [];
        let currentSortColumn = 'thrust';
        let currentSortDirection = 'desc';
        
        // Load repositories on page load
        async function loadRepositories() {
            try {
                const response = await fetch('/api/repositories');
                const repos = await response.json();
                const select = document.getElementById('repoSelect');
                select.innerHTML = '';
                
                repos.forEach(repo => {
                    const option = document.createElement('option');
                    option.value = repo.name;
                    option.textContent = repo.display;
                    select.appendChild(option);
                });
                
                // Load repository stats to show analysis info
                const statsResponse = await fetch('/api/repository-stats');
                const stats = await statsResponse.json();
                
                // Check if any repository has local clone fields (clone_size_mb or analysis_time_seconds)
                const isLocalClone = stats.some(repo => 
                    (repo.clone_size_mb !== undefined && repo.clone_size_mb > 0) || 
                    (repo.analysis_time_seconds !== undefined && repo.analysis_time_seconds > 0)
                );
                
                if (isLocalClone) {
                    const totalSize = stats.reduce((sum, repo) => sum + (repo.clone_size_mb || 0), 0);
                    const totalTime = stats.reduce((sum, repo) => sum + (repo.analysis_time_seconds || 0), 0);
                    document.getElementById('analysisInfo').textContent = 
                        `Local Clone Analysis • ${stats.length} repos • ${totalSize.toFixed(1)} MB • ${totalTime.toFixed(1)}s`;
                } else {
                    document.getElementById('analysisInfo').textContent = 
                        `GitHub API Analysis • ${stats.length} repositories analyzed`;
                }
                
                // Load initial data
                loadExtensionData('all');
            } catch (error) {
                console.error('Error loading repositories:', error);
            }
        }
        
        // Load extension data
        async function loadExtensionData(repoFilter) {
            try {
                const encodedRepo = encodeURIComponent(repoFilter);
                const response = await fetch(`/api/extensions/${encodedRepo}`);
                const extensions = await response.json();
                
                // Store data for sorting
                currentExtensionData = extensions;
                
                // Apply current sort
                sortExtensionData();
                
                updateTable(currentExtensionData);
                updateCharts(currentExtensionData);
                updateStats(currentExtensionData);
                updateSortIndicators();
            } catch (error) {
                console.error('Error loading extension data:', error);
            }
        }
        
        // Sort extension data
        function sortExtensionData() {
            currentExtensionData.sort((a, b) => {
                let aValue, bValue;
                
                switch(currentSortColumn) {
                    case 'extension':
                        aValue = a.extension.toLowerCase();
                        bValue = b.extension.toLowerCase();
                        break;
                    case 'files':
                        aValue = a.total_files;
                        bValue = b.total_files;
                        break;
                    case 'thrust':
                        aValue = a.thrust_usage;
                        bValue = b.thrust_usage;
                        break;
                    case 'apis':
                        aValue = a.api_calls;
                        bValue = b.api_calls;
                        break;
                    case 'avg':
                        aValue = a.avg_thrust_per_file;
                        bValue = b.avg_thrust_per_file;
                        break;
                    default:
                        return 0;
                }
                
                if (currentSortDirection === 'asc') {
                    return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
                } else {
                    return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
                }
            });
        }
        
        // Handle column sorting
        function sortByColumn(column) {
            if (currentSortColumn === column) {
                // Toggle direction if same column
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                // New column, default to descending (except for extension which should be ascending)
                currentSortColumn = column;
                currentSortDirection = column === 'extension' ? 'asc' : 'desc';
            }
            
            sortExtensionData();
            updateTable(currentExtensionData);
            updateSortIndicators();
        }
        
        // Update sort indicators in table headers
        function updateSortIndicators() {
            // Clear all sort indicators
            document.querySelectorAll('.sortable').forEach(th => {
                th.classList.remove('sorted-asc', 'sorted-desc');
            });
            
            // Add indicator to current sort column
            const currentHeader = document.querySelector(`[data-sort="${currentSortColumn}"]`);
            if (currentHeader) {
                currentHeader.classList.add(`sorted-${currentSortDirection}`);
            }
        }
        
        // Update the extensions table
        function updateTable(extensions) {
            const tbody = document.querySelector('#extensionsTable tbody');
            tbody.innerHTML = '';
            
            // Calculate totals
            let totalFiles = 0;
            let totalThrust = 0;
            let totalApis = 0;
            
            extensions.forEach((ext, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="extension">${ext.extension}</td>
                    <td class="number">${ext.total_files.toLocaleString()}</td>
                    <td class="number">${ext.thrust_usage.toLocaleString()}</td>
                    <td class="number">${ext.api_calls.toLocaleString()}</td>
                    <td class="number">${ext.avg_thrust_per_file.toFixed(1)}</td>
                `;
                tbody.appendChild(row);
                
                // Add to totals
                totalFiles += ext.total_files;
                totalThrust += ext.thrust_usage;
                totalApis += ext.api_calls;
            });
            
            // Add total row
            if (extensions.length > 0) {
                const totalRow = document.createElement('tr');
                totalRow.style.borderTop = '2px solid #667eea';
                totalRow.style.fontWeight = 'bold';
                totalRow.style.backgroundColor = '#f8f9fa';
                
                const overallAvg = totalFiles > 0 ? (totalThrust / totalFiles).toFixed(1) : '0.0';
                
                totalRow.innerHTML = `
                    <td class="extension" style="font-weight: bold;">TOTAL</td>
                    <td class="number" style="font-weight: bold;">${totalFiles.toLocaleString()}</td>
                    <td class="number" style="font-weight: bold;">${totalThrust.toLocaleString()}</td>
                    <td class="number" style="font-weight: bold;">${totalApis.toLocaleString()}</td>
                    <td class="number" style="font-weight: bold;">${overallAvg}</td>
                `;
                tbody.appendChild(totalRow);
            }
        }
        
        // Update charts
        function updateCharts(extensions) {
            const labels = extensions.map(ext => ext.extension);
            const thrustData = extensions.map(ext => ext.thrust_usage);
            const apiData = extensions.map(ext => ext.api_calls);
            const filesData = extensions.map(ext => ext.total_files);
            
            // Thrust usage chart
            const thrustCtx = document.getElementById('thrustChart').getContext('2d');
            if (thrustChart) thrustChart.destroy();
            
            thrustChart = new Chart(thrustCtx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: thrustData,
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
                            '#4BC0C0', '#FF6384', '#36A2EB'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const total = thrustData.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return `${context.label}: ${context.parsed.toLocaleString()} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
            
            // API calls vs Files chart
            const apiCtx = document.getElementById('apiChart').getContext('2d');
            if (apiChart) apiChart.destroy();
            
            apiChart = new Chart(apiCtx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Extensions',
                        data: extensions.map((ext, i) => ({
                            x: ext.total_files,
                            y: ext.api_calls,
                            label: ext.extension
                        })),
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Total Files'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'API Calls'
                            }
                        }
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const point = context.raw;
                                    return `${point.label}: ${point.x} files, ${point.y} API calls`;
                                }
                            }
                        },
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
        
        // Update summary statistics
        function updateStats(extensions) {
            const totalFiles = extensions.reduce((sum, ext) => sum + ext.total_files, 0);
            const totalThrust = extensions.reduce((sum, ext) => sum + ext.thrust_usage, 0);
            const totalApis = extensions.reduce((sum, ext) => sum + ext.api_calls, 0);
            const avgPerFile = totalFiles > 0 ? (totalThrust / totalFiles).toFixed(1) : 0;
            
            document.getElementById('totalFiles').textContent = totalFiles.toLocaleString();
            document.getElementById('totalThrust').textContent = totalThrust.toLocaleString();
            document.getElementById('totalApis').textContent = totalApis.toLocaleString();
            document.getElementById('avgPerFile').textContent = avgPerFile;
        }
        
        // Event listeners
        document.getElementById('repoSelect').addEventListener('change', (e) => {
            loadExtensionData(e.target.value);
        });
        
        // Add sorting event listeners
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.sortable').forEach(header => {
                header.addEventListener('click', () => {
                    const sortColumn = header.getAttribute('data-sort');
                    sortByColumn(sortColumn);
                });
            });
        });
        
        // Initialize dashboard
        loadRepositories();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
