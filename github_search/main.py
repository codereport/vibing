#!/usr/bin/env python3
"""
GitHub Thrust Library Search Tool
A web application to search and rank GitHub repositories by Nvidia Thrust library usage.
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from github_analyzer import GitHubAnalyzer
from ranking_engine import RankingEngine

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="GitHub Thrust Search",
    description="Search and rank GitHub repositories by Nvidia Thrust library usage",
    version="1.0.0",
)

# Initialize components
github_analyzer = GitHubAnalyzer()
ranking_engine = RankingEngine()

# Global progress tracking
current_search_progress: Optional[Dict[str, Any]] = None
search_in_progress = False
background_search_task: Optional[asyncio.Task] = None


def progress_callback(progress_data: Dict[str, Any]):
    """Callback function for progress updates"""
    global current_search_progress
    current_search_progress = progress_data
    current_search_progress["timestamp"] = datetime.now().isoformat()


async def background_repository_search(
    query: Optional[str] = None,
    language: Optional[str] = None,
    min_stars: int = 0,
    max_results: int = 50,
    sort_by: str = "combined_score",
):
    """Background task for repository search and analysis"""
    global search_in_progress, current_search_progress

    try:
        search_in_progress = True

        # Set up progress callback
        github_analyzer.set_progress_callback(progress_callback)
        github_analyzer.reset_progress()

        # Search repositories using GitHub API
        repositories = await github_analyzer.search_repositories(
            query=query, language=language, min_stars=min_stars, max_results=max_results
        )

        # Analyze each repository for Thrust usage
        analyzed_repos = []
        for repo in repositories:
            analysis_result = await github_analyzer.analyze_thrust_usage(repo)

            # Only include repositories that have NVIDIA Thrust API usage
            if analysis_result["nvidia_apis"] == 0:
                print(
                    f"⏭️  Skipping {repo['full_name']} - no NVIDIA Thrust API usage found"
                )
                continue

            # Calculate scores
            scores = ranking_engine.calculate_scores(
                thrust_usage=analysis_result["total_thrust"],
                stars=repo.get("stargazers_count", 0),
                forks=repo.get("forks_count", 0),
                last_updated=repo.get("updated_at", ""),
            )

            repo_result = RepositoryResult(
                name=repo["name"],
                full_name=repo["full_name"],
                description=repo.get("description"),
                url=repo["html_url"],
                stars=repo.get("stargazers_count", 0),
                forks=repo.get("forks_count", 0),
                language=repo.get("language") or "Unknown",
                thrust_usage_count=analysis_result["total_thrust"],
                nvidia_api_count=analysis_result["nvidia_apis"],
                thrust_score=scores["thrust_score"],
                popularity_score=scores["popularity_score"],
                combined_score=scores["combined_score"],
                last_updated=repo.get("updated_at", ""),
            )

            analyzed_repos.append(repo_result)

            # Update progress with current results
            github_analyzer.progress.results = [repo.dict() for repo in analyzed_repos]
            progress_callback(github_analyzer.get_progress())

        # Sort results
        if sort_by == "thrust_usage":
            analyzed_repos.sort(key=lambda x: x.thrust_usage_count, reverse=True)
        elif sort_by == "popularity":
            analyzed_repos.sort(key=lambda x: x.popularity_score, reverse=True)
        else:  # combined_score
            analyzed_repos.sort(key=lambda x: x.combined_score, reverse=True)

        # Final update
        github_analyzer.progress.results = [repo.dict() for repo in analyzed_repos]
        github_analyzer.progress.status = "completed"
        progress_callback(github_analyzer.get_progress())

    except Exception as e:
        print(f"Error in background search: {e}")
        if current_search_progress:
            current_search_progress["status"] = "error"
            current_search_progress["error"] = str(e)
    finally:
        search_in_progress = False


class RepositoryResult(BaseModel):
    """Model for repository search results"""

    name: str
    full_name: str
    description: Optional[str]
    url: str
    stars: int
    forks: int
    language: str
    thrust_usage_count: int
    nvidia_api_count: int
    thrust_score: float
    popularity_score: float
    combined_score: float
    last_updated: str


class SearchRequest(BaseModel):
    """Model for search requests"""

    query: Optional[str] = None
    language: Optional[str] = None
    min_stars: Optional[int] = 0
    max_results: Optional[int] = 50
    sort_by: Optional[str] = (
        "combined_score"  # Options: thrust_usage, popularity, combined_score
    )


@app.get("/")
async def read_root():
    """Serve the main page"""
    return HTMLResponse(
        content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GitHub Thrust Library Search</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }
            .header p {
                margin: 10px 0 0 0;
                opacity: 0.9;
                font-size: 1.1em;
            }
            .search-form {
                padding: 40px;
                background: #f8f9fa;
            }
            .form-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }
            .form-group {
                display: flex;
                flex-direction: column;
            }
            .form-group.full-width {
                grid-column: 1 / -1;
            }
            label {
                margin-bottom: 5px;
                font-weight: 600;
                color: #333;
            }
            input, select {
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #4CAF50;
            }
            .search-btn {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 18px;
                border-radius: 8px;
                cursor: pointer;
                transition: transform 0.2s;
                width: 100%;
            }
            .search-btn:hover {
                transform: translateY(-2px);
            }
            .results {
                padding: 40px;
                min-height: 200px;
            }
            .loading {
                text-align: center;
                padding: 40px;
                font-size: 18px;
                color: #666;
            }
            .repo-card {
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                background: white;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .repo-card:hover {
                transform: translateY(-3px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .repo-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 10px;
            }
            .repo-name {
                font-size: 1.3em;
                font-weight: 600;
                color: #0366d6;
                text-decoration: none;
            }
            .repo-stats {
                display: flex;
                gap: 15px;
                font-size: 0.9em;
                color: #586069;
            }
            .stat {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            .thrust-score {
                background: #ff6b6b;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: 600;
            }
            .nvidia-api-score {
                background: #28a745;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: 600;
            }
            .description {
                color: #586069;
                margin: 10px 0;
                line-height: 1.5;
            }
            .scores {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin-top: 15px;
            }
            .score-item {
                background: #f6f8fa;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 0.9em;
            }
            .score-label {
                font-weight: 600;
                color: #24292e;
            }
            .statistics-section {
                padding: 20px 40px;
                background: #f8f9fa;
                border-top: 1px solid #e1e5e9;
                display: none; /* Hidden by default */
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .stat-card {
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stat-title {
                font-weight: 600;
                color: #333;
                margin-bottom: 10px;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .stat-values {
                display: flex;
                justify-content: space-between;
                font-size: 0.85em;
            }
            .stat-label {
                color: #666;
            }
            .stat-value {
                font-weight: 600;
                color: #333;
            }
            .chart-container {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                height: 400px;
            }
            .chart-title {
                font-weight: 600;
                color: #333;
                margin-bottom: 15px;
                text-align: center;
            }
            @media (max-width: 768px) {
                .form-grid {
                    grid-template-columns: 1fr;
                }
                .repo-header {
                    flex-direction: column;
                    gap: 10px;
                }
                .statistics-section {
                    padding: 15px 20px;
                }
                .stats-grid {
                    grid-template-columns: 1fr;
                }
                .chart-container {
                    height: 300px;
                    padding: 15px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 GitHub Thrust Search</h1>
                <p>Find and rank repositories by NVIDIA Thrust library API usage</p>
                <p style="font-size: 0.9em; opacity: 0.8;">Searches for repositories containing: thrust::transform, thrust::reduce, thrust::inclusive_scan, thrust::sort, thrust::make_*</p>
            </div>
            
            <div class="search-form">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="language">Language Filter</label>
                        <select id="language">
                            <option value="">Any Language</option>
                            <option value="C++">C++</option>
                            <option value="C">C</option>
                            <option value="CUDA">CUDA</option>
                            <option value="Python">Python</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="min_stars">Minimum Stars</label>
                        <input type="number" id="min_stars" placeholder="5" min="0" value="5" />
                    </div>
                    <div class="form-group">
                        <label for="sort_by">Sort By</label>
                        <select id="sort_by">
                            <option value="combined_score">Combined Score</option>
                            <option value="thrust_usage">Thrust Usage</option>
                            <option value="popularity">Popularity</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="max_results">Max Results</label>
                        <input type="number" id="max_results" placeholder="20" min="1" max="100" value="20" />
                    </div>
                </div>
                <button class="search-btn" onclick="searchRepositories()">Search Repositories</button>
                <div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 6px; font-size: 0.9em;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div id="cache-info">Loading cache info...</div>
                        <div style="display: flex; gap: 8px;">
                            <button onclick="loadCachedResults()" style="background: #28a745; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8em;">Load Cached Results</button>
                            <button onclick="clearCache()" style="background: #dc3545; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.8em;">Clear Cache</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="statistics-section" id="statistics-section">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-title">Repository Count</div>
                        <div class="stat-values">
                            <div class="stat-value" id="total-repos">0</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">GitHub Stars</div>
                        <div class="stat-values">
                            <div><span class="stat-label">Min:</span> <span class="stat-value" id="stars-min">0</span></div>
                            <div><span class="stat-label">Avg:</span> <span class="stat-value" id="stars-avg">0</span></div>
                            <div><span class="stat-label">Max:</span> <span class="stat-value" id="stars-max">0</span></div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">Forks</div>
                        <div class="stat-values">
                            <div><span class="stat-label">Min:</span> <span class="stat-value" id="forks-min">0</span></div>
                            <div><span class="stat-label">Avg:</span> <span class="stat-value" id="forks-avg">0</span></div>
                            <div><span class="stat-label">Max:</span> <span class="stat-value" id="forks-max">0</span></div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">Thrust Usage</div>
                        <div class="stat-values">
                            <div><span class="stat-label">Min:</span> <span class="stat-value" id="thrust-min">0</span></div>
                            <div><span class="stat-label">Avg:</span> <span class="stat-value" id="thrust-avg">0</span></div>
                            <div><span class="stat-label">Max:</span> <span class="stat-value" id="thrust-max">0</span></div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-title">API Calls</div>
                        <div class="stat-values">
                            <div><span class="stat-label">Min:</span> <span class="stat-value" id="api-min">0</span></div>
                            <div><span class="stat-label">Avg:</span> <span class="stat-value" id="api-avg">0</span></div>
                            <div><span class="stat-label">Max:</span> <span class="stat-value" id="api-max">0</span></div>
                        </div>
                    </div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">📊 Stars vs Thrust Usage & API Calls</div>
                    <canvas id="scatter-chart"></canvas>
                </div>
            </div>
            
            <div class="results" id="results">
                <p style="text-align: center; color: #666; font-size: 18px;">
                    Click "Search Repositories" to find repositories using NVIDIA Thrust APIs<br>
                    <small style="opacity: 0.7;">Only repositories with actual API usage (thrust::transform, thrust::reduce, etc.) will be shown</small>
                </p>
            </div>
        </div>

        <script>
            let scatterChart = null; // Global chart instance
            
            // Load cache info when page loads
            document.addEventListener('DOMContentLoaded', function() {
                loadCacheInfo();
            });
            
            function calculateStatistics(results) {
                if (results.length === 0) return null;
                
                const stats = {
                    total: results.length,
                    stars: {
                        values: results.map(r => r.stars),
                        min: Math.min(...results.map(r => r.stars)),
                        max: Math.max(...results.map(r => r.stars)),
                        avg: Math.round(results.reduce((sum, r) => sum + r.stars, 0) / results.length)
                    },
                    forks: {
                        values: results.map(r => r.forks),
                        min: Math.min(...results.map(r => r.forks)),
                        max: Math.max(...results.map(r => r.forks)),
                        avg: Math.round(results.reduce((sum, r) => sum + r.forks, 0) / results.length)
                    },
                    thrust: {
                        values: results.map(r => r.thrust_usage_count),
                        min: Math.min(...results.map(r => r.thrust_usage_count)),
                        max: Math.max(...results.map(r => r.thrust_usage_count)),
                        avg: Math.round(results.reduce((sum, r) => sum + r.thrust_usage_count, 0) / results.length * 10) / 10
                    },
                    api: {
                        values: results.map(r => r.nvidia_api_count),
                        min: Math.min(...results.map(r => r.nvidia_api_count)),
                        max: Math.max(...results.map(r => r.nvidia_api_count)),
                        avg: Math.round(results.reduce((sum, r) => sum + r.nvidia_api_count, 0) / results.length * 10) / 10
                    }
                };
                
                return stats;
            }
            
            function updateStatisticsDisplay(stats) {
                if (!stats) return;
                
                // Update statistics
                document.getElementById('total-repos').textContent = stats.total;
                
                document.getElementById('stars-min').textContent = stats.stars.min.toLocaleString();
                document.getElementById('stars-avg').textContent = stats.stars.avg.toLocaleString();
                document.getElementById('stars-max').textContent = stats.stars.max.toLocaleString();
                
                document.getElementById('forks-min').textContent = stats.forks.min.toLocaleString();
                document.getElementById('forks-avg').textContent = stats.forks.avg.toLocaleString();
                document.getElementById('forks-max').textContent = stats.forks.max.toLocaleString();
                
                document.getElementById('thrust-min').textContent = stats.thrust.min;
                document.getElementById('thrust-avg').textContent = stats.thrust.avg;
                document.getElementById('thrust-max').textContent = stats.thrust.max;
                
                document.getElementById('api-min').textContent = stats.api.min;
                document.getElementById('api-avg').textContent = stats.api.avg;
                document.getElementById('api-max').textContent = stats.api.max;
            }
            
            function createScatterPlot(results) {
                const ctx = document.getElementById('scatter-chart').getContext('2d');
                
                // Destroy existing chart
                if (scatterChart) {
                    scatterChart.destroy();
                }
                
                // Prepare data for scatter plot
                const thrustData = results.map(repo => ({
                    x: repo.stars,
                    y: repo.thrust_usage_count,
                    label: repo.full_name
                }));
                
                const apiData = results.map(repo => ({
                    x: repo.stars,
                    y: repo.nvidia_api_count,
                    label: repo.full_name
                }));
                
                scatterChart = new Chart(ctx, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Thrust Usage',
                            data: thrustData,
                            backgroundColor: 'rgba(255, 99, 132, 0.6)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }, {
                            label: 'API Calls',
                            data: apiData,
                            backgroundColor: 'rgba(75, 192, 192, 0.6)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                type: 'logarithmic',
                                display: true,
                                title: {
                                    display: true,
                                    text: 'GitHub Stars (log scale)'
                                }
                            },
                            y: {
                                display: true,
                                title: {
                                    display: true,
                                    text: 'Count'
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.parsed.y} (${context.raw.label})`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            async function loadCacheInfo() {
                try {
                    const response = await fetch('/cache/info');
                    const cacheInfo = await response.json();
                    
                    const cacheInfoDiv = document.getElementById('cache-info');
                    if (cacheInfo.total_entries === 0) {
                        cacheInfoDiv.innerHTML = '💾 Cache: Empty';
                    } else {
                        cacheInfoDiv.innerHTML = `💾 Cache: ${cacheInfo.total_entries} entries (${cacheInfo.fresh_entries} fresh, ${cacheInfo.old_entries} old)`;
                    }
                } catch (error) {
                    document.getElementById('cache-info').innerHTML = '💾 Cache: Error loading info';
                }
            }

            async function clearCache() {
                if (confirm('Are you sure you want to clear the analysis cache? This will make future searches slower until the cache rebuilds.')) {
                    try {
                        const response = await fetch('/cache/clear', { method: 'POST' });
                        const result = await response.json();
                        alert('Cache cleared successfully!');
                        loadCacheInfo(); // Refresh cache info
                    } catch (error) {
                        alert('Error clearing cache: ' + error.message);
                    }
                }
            }

            async function loadCachedResults() {
                const resultsDiv = document.getElementById('results');
                const statisticsSection = document.getElementById('statistics-section');
                
                resultsDiv.innerHTML = '<div class="loading">💾 Loading cached results...</div>';
                statisticsSection.style.display = 'none'; // Hide stats during loading
                
                // Get current sort setting
                const sortBy = document.getElementById('sort_by').value;
                console.log('🔍 Loading cached results with sort_by:', sortBy);
                
                try {
                    const response = await fetch(`/cache/results?sort_by=${sortBy}`);
                    const data = await response.json();
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<div style="color: #d73a49; text-align: center;">Error: ${data.error}</div>`;
                        return;
                    }
                    
                    if (data.repositories.length === 0) {
                        resultsDiv.innerHTML = '<div style="text-align: center; color: #666;">No cached results with Thrust usage found. Run a search first to populate the cache.</div>';
                        statisticsSection.style.display = 'none';
                        return;
                    }
                    
                    renderResults(data.repositories);
                    
                } catch (error) {
                    resultsDiv.innerHTML = `<div style="color: #d73a49; text-align: center;">Error loading cached results: ${error.message}</div>`;
                }
            }

            function renderResults(results) {
                const resultsDiv = document.getElementById('results');
                const statisticsSection = document.getElementById('statistics-section');
                
                if (results.length === 0) {
                    statisticsSection.style.display = 'none';
                    return; // Keep showing progress, don't show "no results" yet
                }
                
                // Calculate and display statistics
                const stats = calculateStatistics(results);
                updateStatisticsDisplay(stats);
                createScatterPlot(results);
                statisticsSection.style.display = 'block';
                
                resultsDiv.innerHTML = results.map(repo => `
                    <div class="repo-card">
                        <div class="repo-header">
                            <a href="${repo.url}" target="_blank" class="repo-name">${repo.full_name}</a>
                            <div class="repo-stats">
                                <div class="stat">⭐ ${repo.stars}</div>
                                <div class="stat">🍴 ${repo.forks}</div>
                                <div class="stat">${repo.language || 'Unknown'}</div>
                                <div class="thrust-score">Thrust: ${repo.thrust_usage_count}</div>
                                <div class="nvidia-api-score">API: ${repo.nvidia_api_count}</div>
                            </div>
                        </div>
                        <div class="description">${repo.description || 'No description available'}</div>
                        <div class="scores">
                            <div class="score-item">
                                <div class="score-label">Thrust Score</div>
                                <div>${repo.thrust_score.toFixed(2)}</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">Popularity Score</div>
                                <div>${repo.popularity_score.toFixed(2)}</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">Combined Score</div>
                                <div>${repo.combined_score.toFixed(2)}</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">Last Updated</div>
                                <div>${new Date(repo.last_updated).toLocaleDateString()}</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }



            async function searchRepositories() {
                const resultsDiv = document.getElementById('results');
                const statisticsSection = document.getElementById('statistics-section');
                
                resultsDiv.innerHTML = '<div class="loading">🚀 Searching repositories and analyzing NVIDIA Thrust API usage...</div>';
                statisticsSection.style.display = 'none'; // Hide stats during search
                
                const language = document.getElementById('language').value;
                const minStars = document.getElementById('min_stars').value;
                const sortBy = document.getElementById('sort_by').value;
                const maxResults = document.getElementById('max_results').value;
                
                const params = new URLSearchParams();
                if (language) params.append('language', language);
                if (minStars) params.append('min_stars', minStars);
                if (maxResults) params.append('max_results', maxResults);
                params.append('sort_by', sortBy);
                
                try {
                    const response = await fetch(`/search?${params.toString()}`);
                    const data = await response.json();
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<div style="color: #d73a49; text-align: center;">Error: ${data.error}</div>`;
                        return;
                    }
                    
                    if (data.repositories.length === 0) {
                        resultsDiv.innerHTML = '<div style="text-align: center; color: #666;">No repositories found matching your criteria.</div>';
                        statisticsSection.style.display = 'none';
                        return;
                    }
                    
                    renderResults(data.repositories);
                    loadCacheInfo();
                    
                } catch (error) {
                    resultsDiv.innerHTML = `<div style="color: #d73a49; text-align: center;">Error: ${error.message}</div>`;
                }
            }


        </script>
    </body>
    </html>
    """
    )


@app.get("/progress")
async def get_progress():
    """Get current search progress"""
    if current_search_progress:
        return current_search_progress
    return {"status": "idle", "progress_percentage": 0}


@app.get("/progress/stream")
async def progress_stream():
    """Server-sent events for real-time progress updates"""

    async def event_generator():
        last_progress = None
        while True:
            if current_search_progress != last_progress:
                if current_search_progress:
                    yield f"data: {json.dumps(current_search_progress)}\n\n"
                    last_progress = current_search_progress.copy()
            await asyncio.sleep(1)  # Update every second

    return StreamingResponse(event_generator(), media_type="text/plain")


@app.post("/search/start")
async def start_search(
    background_tasks: BackgroundTasks,
    query: Optional[str] = None,
    language: Optional[str] = None,
    min_stars: Optional[int] = 0,
    max_results: Optional[int] = 50,
    sort_by: Optional[str] = "combined_score",
):
    """Start a background search task"""
    global background_search_task

    if search_in_progress:
        return {"message": "Search already in progress", "status": "in_progress"}

    # Start background task
    background_search_task = asyncio.create_task(
        background_repository_search(query, language, min_stars, max_results, sort_by)
    )

    return {"message": "Search started", "status": "started"}


@app.post("/search/stop")
async def stop_search():
    """Stop the current search"""
    global background_search_task, search_in_progress, current_search_progress

    if background_search_task and not background_search_task.done():
        background_search_task.cancel()

    search_in_progress = False
    if current_search_progress:
        current_search_progress["status"] = "cancelled"

    return {"message": "Search stopped"}


@app.get("/cache/info")
async def get_cache_info():
    """Get cache statistics"""
    return github_analyzer.get_cache_info()


@app.post("/cache/clear")
async def clear_cache():
    """Clear the analysis cache"""
    github_analyzer.clear_cache()
    return {"message": "Cache cleared successfully"}


@app.get("/cache/results")
async def get_cached_results(
    sort_by: Optional[str] = Query("combined_score", description="Sort criteria")
):
    """Get all cached analysis results"""
    try:
        cached_results = []
        print(
            f"🔍 Loading cached results from {len(github_analyzer.cache)} cache entries"
        )

        for cache_key, cache_data in github_analyzer.cache.items():
            # Parse cache key: "repo_name:updated_at"
            if ":" in cache_key:
                full_name = cache_key.split(":")[0]
                updated_at = ":".join(cache_key.split(":")[1:])

                nvidia_apis = cache_data.get("nvidia_apis", 0)
                total_thrust = cache_data.get("total_thrust", 0)
                print(
                    f"📊 {full_name}: nvidia_apis={nvidia_apis}, total_thrust={total_thrust}"
                )

                # Only include repos with thrust usage
                if nvidia_apis > 0 or total_thrust > 0:
                    # Use cached repository metadata if available, fallback to parsed values
                    name = cache_data.get("repo_name", full_name.split("/")[-1])
                    description = (
                        cache_data.get("description")
                        or "[Cached Result - Description not available]"
                    )
                    url = cache_data.get("html_url", f"https://github.com/{full_name}")
                    stars = cache_data.get("stars", 0)
                    forks = cache_data.get("forks", 0)
                    language = cache_data.get("language", "Unknown")

                    # Calculate scores for cached results
                    thrust_usage_count = cache_data.get("total_thrust", 0)
                    nvidia_api_count = cache_data.get("nvidia_apis", 0)

                    # Calculate scores using the correct method signature
                    scores = ranking_engine.calculate_scores(
                        thrust_usage=thrust_usage_count,
                        stars=stars,
                        forks=forks,
                        last_updated=updated_at,
                    )

                    repo_result = RepositoryResult(
                        name=name,
                        full_name=full_name,
                        description=description,
                        url=url,
                        stars=stars,
                        forks=forks,
                        language=language,
                        thrust_usage_count=thrust_usage_count,
                        nvidia_api_count=nvidia_api_count,
                        thrust_score=scores["thrust_score"],
                        popularity_score=scores["popularity_score"],
                        combined_score=scores["combined_score"],
                        last_updated=updated_at,
                    )
                    cached_results.append(repo_result)

        # Sort results based on sort_by parameter
        if sort_by == "thrust_usage":
            cached_results.sort(key=lambda x: x.thrust_usage_count, reverse=True)
            print(
                f"🔢 Sorted by thrust_usage: top 3 counts = {[x.thrust_usage_count for x in cached_results[:3]]}"
            )
        elif sort_by == "popularity":
            cached_results.sort(key=lambda x: x.popularity_score, reverse=True)
            print(
                f"🔢 Sorted by popularity: top 3 scores = {[x.popularity_score for x in cached_results[:3]]}"
            )
        else:  # combined_score
            cached_results.sort(key=lambda x: x.combined_score, reverse=True)
            print(
                f"🔢 Sorted by combined_score: top 3 scores = {[x.combined_score for x in cached_results[:3]]}"
            )

        print(f"✅ Returning {len(cached_results)} cached results with Thrust usage")
        return {"repositories": cached_results}

    except Exception as e:
        print(f"❌ Error in get_cached_results: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error retrieving cached results: {str(e)}"
        )


@app.get("/search")
async def search_repositories(
    query: Optional[str] = Query(None, description="Search query"),
    language: Optional[str] = Query(None, description="Programming language filter"),
    min_stars: Optional[int] = Query(0, description="Minimum number of stars"),
    max_results: Optional[int] = Query(50, description="Maximum number of results"),
    sort_by: Optional[str] = Query("combined_score", description="Sort criteria"),
):
    """Search and analyze repositories for Thrust usage"""
    try:
        # Search repositories using GitHub API
        repositories = await github_analyzer.search_repositories(
            query=query, language=language, min_stars=min_stars, max_results=max_results
        )

        # Analyze each repository for Thrust usage
        analyzed_repos = []
        for repo in repositories:
            analysis_result = await github_analyzer.analyze_thrust_usage(repo)

            # Only include repositories that have NVIDIA Thrust API usage
            if analysis_result["nvidia_apis"] == 0:
                print(
                    f"⏭️  Skipping {repo['full_name']} - no NVIDIA Thrust API usage found"
                )
                continue

            # Calculate scores
            scores = ranking_engine.calculate_scores(
                thrust_usage=analysis_result["total_thrust"],
                stars=repo.get("stargazers_count", 0),
                forks=repo.get("forks_count", 0),
                last_updated=repo.get("updated_at", ""),
            )

            analyzed_repos.append(
                RepositoryResult(
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    url=repo["html_url"],
                    stars=repo.get("stargazers_count", 0),
                    forks=repo.get("forks_count", 0),
                    language=repo.get("language") or "Unknown",
                    thrust_usage_count=analysis_result["total_thrust"],
                    nvidia_api_count=analysis_result["nvidia_apis"],
                    thrust_score=scores["thrust_score"],
                    popularity_score=scores["popularity_score"],
                    combined_score=scores["combined_score"],
                    last_updated=repo.get("updated_at", ""),
                )
            )

        # Sort results
        if sort_by == "thrust_usage":
            analyzed_repos.sort(key=lambda x: x.thrust_usage_count, reverse=True)
        elif sort_by == "popularity":
            analyzed_repos.sort(key=lambda x: x.popularity_score, reverse=True)
        else:  # combined_score
            analyzed_repos.sort(key=lambda x: x.combined_score, reverse=True)

        return {"repositories": analyzed_repos}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
