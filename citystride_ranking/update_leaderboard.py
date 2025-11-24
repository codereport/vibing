import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DATA_FILE = "leaderboard_data.json"
HTML_FILE = "index.html"
PAGES_TO_FETCH = 5 # 12 per page * 5 = 60 runners, enough for top 50
HISTORY_DIR = "history"

def clean_name(name):
    # Specific fix for James Salmon
    if "James Salmon" in name and "Purple Runner" in name:
        return "James Salmon"
    return name

import time

def get_runner_location(profile_url):
    if not profile_url:
        return None
        
    # Construct full URL (profile_url is like /users/123/map, we want /users/123)
    # Actually, the profile_url we saved is /users/123/map. 
    # The profile page is /users/123.
    base_url = "https://citystrides.com" + profile_url.replace("/map", "")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        time.sleep(0.5) # Be nice to the server
        response = requests.get(base_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Look for the location div we found
            # <div class="text-xs text-right truncate text-zinc-600 dark:text-zinc-200">Canada</div>
            location_div = soup.find("div", class_="text-xs text-right truncate text-zinc-600 dark:text-zinc-200")
            if location_div:
                return location_div.get_text(strip=True)
    except Exception as e:
        print(f"Error fetching location for {base_url}: {e}")
        
    return None

def has_flag(name):
    # Check if name contains any emoji flag
    # This is a simple check, might need refinement
    # Flags are usually 2 regional indicator symbols, but let's just check for non-ascii or specific ranges if needed.
    # Actually, let's just check if there's an emoji.
    # Or simpler: check if the user asked for it. 
    # "for the user without flag emojis suffixes"
    # Let's assume if we find a location, we add it.
    # But we should only do it if they don't have one.
    # Let's check if the name ends with a flag-like character?
    # Easier: just fetch for everyone who doesn't have a flag.
    # How to detect flag?
    # Flags are unicode range 1F1E6-1F1FF.
    for char in name:
        if 0x1F1E6 <= ord(char) <= 0x1F1FF:
            return True
    return False

LOCATION_CACHE_FILE = "runner_locations.json"

def load_location_cache():
    if os.path.exists(LOCATION_CACHE_FILE):
        with open(LOCATION_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_location_cache(cache):
    with open(LOCATION_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def country_to_flag(country):
    if not country:
        return ""
    
    mapping = {
        "United States": "🇺🇸",
        "United Kingdom": "🇬🇧",
        "Canada": "🇨🇦",
        "Deutschland": "🇩🇪",
        "Germany": "🇩🇪",
        "Nederland": "🇳🇱",
        "Netherlands": "🇳🇱",
        "Portugal": "🇵🇹",
        "Australia": "🇦🇺",
        "España": "🇪🇸",
        "Spain": "🇪🇸",
        "België / Belgique / Belgien": "🇧🇪",
        "Belgium": "🇧🇪",
        "France": "🇫🇷",
        "Italy": "🇮🇹",
        "Italia": "🇮🇹",
        "Sweden": "🇸🇪",
        "Sverige": "🇸🇪",
        "Norway": "🇳🇴",
        "Norge": "🇳🇴",
        "Denmark": "🇩🇰",
        "Danmark": "🇩🇰",
        "Finland": "🇫🇮",
        "Suomi": "🇫🇮",
        "Ireland": "🇮🇪",
        "New Zealand": "🇳🇿",
        "Switzerland": "🇨🇭",
        "Schweiz": "🇨🇭",
        "Austria": "🇦🇹",
        "Österreich": "🇦🇹",
        "Poland": "🇵🇱",
        "Polska": "🇵🇱"
    }
    
    return mapping.get(country, country) # Return mapped flag or original text if not found

def fetch_leaderboard():
    runners = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    location_cache = load_location_cache()
    cache_updated = False
    
    for page in range(1, PAGES_TO_FETCH + 1):
        print(f"Fetching page {page}...")
        url = f"https://citystrides.com/users/search?context=leaderboard&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: {response.status_code}")
            continue
            
        soup = BeautifulSoup(response.content, "html.parser")
        cards = soup.find_all("div", class_=lambda c: c and "col-span-1" in c and "bg-white" in c)
        
        for card in cards:
            name_tag = card.find("h3")
            raw_name = name_tag.get_text(strip=True) if name_tag else "Unknown"
            name = clean_name(raw_name)
            
            profile_url = card.find("a", href=lambda h: h and "/users/" in h)['href'] if card.find("a", href=lambda h: h and "/users/" in h) else ""
            
            # Check if we need to fetch location
            # Use profile_url as cache key
            user_id = profile_url.split("/")[2] if len(profile_url.split("/")) > 2 else name
            
            if not has_flag(name):
                if user_id in location_cache:
                    location_flag = location_cache[user_id]
                    if location_flag:
                        name = f"{name} {location_flag}"
                else:
                    print(f"Fetching location for {name}...")
                    location = get_runner_location(profile_url)
                    if location:
                        flag = country_to_flag(location)
                        location_cache[user_id] = flag
                        cache_updated = True
                        name = f"{name} {flag}"
                    else:
                        # Cache empty result to avoid re-fetching failed/empty locations
                        location_cache[user_id] = ""
                        cache_updated = True
            
            # Extract streets count
            # Text is like "36656 total streets"
            text = card.get_text(separator=" ")
            streets = 0
            try:
                # Find the number before "total streets"
                import re
                match = re.search(r'([\d,]+)\s+total streets', text)
                if match:
                    streets = int(match.group(1).replace(",", ""))
            except Exception as e:
                print(f"Error parsing streets for {name}: {e}")
                
            runners.append({
                "name": name,
                "streets": streets,
                "profile_url": profile_url
            })
            
    if cache_updated:
        save_location_cache(location_cache)
        
    return runners[:50] # Return top 50

def load_previous_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return None

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    # Also save timestamped version for history
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = os.path.join(HISTORY_DIR, f"leaderboard_{timestamp}.json")
    with open(history_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved historical snapshot: {history_file}")

def calculate_deltas(current_runners, previous_data):
    if not previous_data:
        return current_runners
        
    prev_map = {r["name"]: r for r in previous_data["runners"]}
    prev_ranks = {r["name"]: i + 1 for i, r in enumerate(previous_data["runners"])}
    
    for i, runner in enumerate(current_runners):
        name = runner["name"]
        current_rank = i + 1
        
        if name in prev_map:
            prev_runner = prev_map[name]
            prev_rank = prev_ranks.get(name, 999)
            
            runner["streets_delta"] = runner["streets"] - prev_runner["streets"]
            runner["rank_delta"] = prev_rank - current_rank # Positive means gained rank (e.g. 5 -> 3 is +2)
        else:
            runner["streets_delta"] = 0
            runner["rank_delta"] = 0 # New entrant
            
    return current_runners

def load_historical_data():
    """Load all historical data files for time series chart"""
    if not os.path.exists(HISTORY_DIR):
        return []
    
    history_files = sorted([f for f in os.listdir(HISTORY_DIR) if f.startswith("leaderboard_") and f.endswith(".json")])
    historical_data = []
    
    for filename in history_files:
        filepath = os.path.join(HISTORY_DIR, filename)
        with open(filepath, "r") as f:
            data = json.load(f)
            historical_data.append(data)
    
    return historical_data

def generate_html(runners, last_updated):
    # Prepare data for chart (All 50)
    chart_labels = [r['name'].replace("'", "\\'") for r in runners]
    chart_data = [r['streets'] for r in runners]
    
    # Load historical data for time series
    historical_data = load_historical_data()
    
    # Prepare time series data (track all 50 runners over time)
    time_series_data = {}
    time_labels = []
    
    if historical_data:
        # Get all 50 current runners
        all_runner_names = [r['name'] for r in runners[:50]]
        
        # Initialize data structure
        for name in all_runner_names:
            time_series_data[name] = []
        
        # Collect data points
        for snapshot in historical_data:
            timestamp = snapshot.get('last_updated', '')
            time_labels.append(timestamp)
            
            # Create a map of runner data in this snapshot
            snapshot_map = {r['name']: r['streets'] for r in snapshot.get('runners', [])}
            
            # Add data point for each runner
            for name in all_runner_names:
                time_series_data[name].append(snapshot_map.get(name, None))
    
    # Convert to Chart.js format
    time_series_datasets = []
    # Generate 50 distinct colors
    colors = [
        'rgb(76, 29, 149)', 'rgb(220, 38, 38)', 'rgb(22, 163, 74)', 
        'rgb(37, 99, 235)', 'rgb(234, 88, 12)', 'rgb(168, 85, 247)',
        'rgb(236, 72, 153)', 'rgb(14, 165, 233)', 'rgb(132, 204, 22)',
        'rgb(251, 146, 60)', 'rgb(59, 130, 246)', 'rgb(239, 68, 68)',
        'rgb(16, 185, 129)', 'rgb(245, 158, 11)', 'rgb(139, 92, 246)',
        'rgb(244, 114, 182)', 'rgb(6, 182, 212)', 'rgb(163, 230, 53)',
        'rgb(251, 191, 36)', 'rgb(99, 102, 241)', 'rgb(248, 113, 113)',
        'rgb(52, 211, 153)', 'rgb(251, 146, 60)', 'rgb(167, 139, 250)',
        'rgb(251, 113, 133)', 'rgb(34, 211, 238)', 'rgb(190, 242, 100)',
        'rgb(252, 211, 77)', 'rgb(129, 140, 248)', 'rgb(252, 165, 165)',
        'rgb(110, 231, 183)', 'rgb(253, 186, 116)', 'rgb(196, 181, 253)',
        'rgb(253, 164, 175)', 'rgb(103, 232, 249)', 'rgb(217, 249, 157)',
        'rgb(254, 240, 138)', 'rgb(165, 180, 252)', 'rgb(254, 202, 202)',
        'rgb(167, 243, 208)', 'rgb(254, 215, 170)', 'rgb(221, 214, 254)',
        'rgb(254, 205, 211)', 'rgb(165, 243, 252)', 'rgb(233, 250, 203)',
        'rgb(254, 249, 195)', 'rgb(199, 210, 254)', 'rgb(254, 226, 226)',
        'rgb(209, 250, 229)', 'rgb(254, 235, 200)', 'rgb(237, 233, 254)'
    ]
    
    for i, name in enumerate(list(time_series_data.keys())[:50]):
        time_series_datasets.append({
            'label': name,
            'data': time_series_data[name],
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)].replace('rgb', 'rgba').replace(')', ', 0.1)'),
            'tension': 0.1,
            'fill': False
        })
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CityStrides Top 50 Leaderboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f4f5; color: #18181b; margin: 0; padding: 30px; font-size: 24px; }}
            .main-container {{ max_width: 95%; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #4c1d95; margin-bottom: 30px; }}
            .updated {{ text-align: center; color: #71717a; font-size: 0.8em; margin-bottom: 40px; }}
            
            .content-wrapper {{ display: flex; gap: 30px; }}
            .chart-section {{ flex: 1; min-width: 0; }}
            .table-section {{ flex: 1; min-width: 0; }}
            
            /* 60px per row * 50 rows = 3000px */
            .chart-container {{ position: relative; height: 3000px; width: 100%; }}
            
            table {{ width: 100%; border-collapse: collapse; font-size: 1em; height: 100%; }}
            th, td {{ padding: 12px 18px; text-align: left; border-bottom: 1px solid #e4e4e7; height: 60px; box-sizing: border-box; }}
            th {{ background: #f8fafc; font-weight: 600; position: sticky; top: 0; z-index: 10; }}
            
            .rank-up {{ color: #16a34a; }}
            .rank-down {{ color: #dc2626; }}
            .streets-up {{ color: #16a34a; font-size: 0.9em; }}
            .gap {{ color: #71717a; font-size: 0.9em; }}
            .profile-link {{ color: #4c1d95; text-decoration: none; font-weight: 500; }}
            .profile-link:hover {{ text-decoration: underline; }}
            
            .toggle-button {{ 
                display: inline-block; 
                margin: 0 0 30px 0; 
                padding: 12px 24px; 
                background: #4c1d95; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                font-size: 0.9em; 
                cursor: pointer; 
                transition: background 0.3s; 
            }}
            .toggle-button:hover {{ background: #5b21b6; }}
            
            /* Modal styles */
            .modal {{ 
                display: none; 
                position: fixed; 
                z-index: 1000; 
                left: 0; 
                top: 0; 
                width: 100%; 
                height: 100%; 
                background-color: rgba(0, 0, 0, 0.5); 
                backdrop-filter: blur(4px);
            }}
            .modal.visible {{ display: flex; align-items: center; justify-content: center; }}
            
            .modal-content {{ 
                background: white; 
                padding: 40px; 
                border-radius: 16px; 
                width: 90%; 
                max-width: 1400px; 
                max-height: 90vh; 
                overflow-y: auto; 
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); 
                position: relative;
            }}
            
            .modal-close {{ 
                position: absolute; 
                top: 20px; 
                right: 20px; 
                font-size: 32px; 
                font-weight: bold; 
                color: #71717a; 
                cursor: pointer; 
                background: none; 
                border: none; 
                padding: 0; 
                width: 40px; 
                height: 40px; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                border-radius: 50%; 
                transition: all 0.2s;
            }}
            .modal-close:hover {{ background: #f4f4f5; color: #18181b; }}
            
            .time-series-container {{ position: relative; height: 600px; width: 100%; margin-top: 20px; }}
            
            @media (max-width: 1400px) {{
                .content-wrapper {{ flex-direction: column; }}
                .chart-container {{ height: 1200px; }}
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <h1>CityStrides Top 50</h1>
            <div style="text-align: center;">
                <button class="toggle-button" onclick="openModal()">📈 View Historical Progress (All 50)</button>
            </div>
            <p class="updated">Last updated: {last_updated}</p>
            
            <div class="content-wrapper">
                <div class="table-section">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Runner</th>
                                <th>Streets</th>
                                <th>Gap</th>
                                <th>Streets Δ</th>
                                <th>Rank Δ</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    for i, runner in enumerate(runners):
        rank = i + 1
        rank_delta = runner.get("rank_delta", 0)
        streets_delta = runner.get("streets_delta", 0)
        
        # Calculate gap to runner ahead
        gap = 0
        if i > 0:
            gap = runners[i-1]['streets'] - runner['streets']
        
        rank_display = f"{rank}"
        if rank_delta > 0:
            rank_display += f" <span class='rank-up'>(▲{rank_delta})</span>"
        elif rank_delta < 0:
            rank_display += f" <span class='rank-down'>(▼{abs(rank_delta)})</span>"
            
        streets_delta_display = f"+{streets_delta}" if streets_delta > 0 else "-"
        gap_display = f"-{gap:,}" if i > 0 else "-"
        
        # Format rank delta display
        rank_delta_display = "-"
        rank_delta_class = ""
        if rank_delta > 0:
            rank_delta_display = f"▲{rank_delta}"
            rank_delta_class = "rank-up"
        elif rank_delta < 0:
            rank_delta_display = f"▼{abs(rank_delta)}"
            rank_delta_class = "rank-down"
        
        html += f"""
                            <tr>
                                <td>{rank}</td>
                                <td><a href="https://citystrides.com{runner['profile_url']}" class="profile-link" target="_blank">{runner['name']}</a></td>
                                <td>{runner['streets']:,}</td>
                                <td class="gap">{gap_display}</td>
                                <td class="streets-up">{streets_delta_display}</td>
                                <td class="{rank_delta_class}">{rank_delta_display}</td>
                            </tr>
        """
        
    html += f"""
                        </tbody>
                    </table>
                </div>
                
                <div class="chart-section">
                    <div class="chart-container">
                        <canvas id="rankingChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Modal for time series chart -->
        <div id="chartModal" class="modal">
            <div class="modal-content">
                <button class="modal-close" onclick="closeModal()">×</button>
                <h2 style="text-align: center; color: #4c1d95; margin-bottom: 20px;">Street Count Progress Over Time</h2>
                <div class="time-series-container">
                    <canvas id="timeSeriesChart"></canvas>
                </div>
            </div>
        </div>
        
        <script>
            function openModal() {{
                document.getElementById('chartModal').classList.add('visible');
            }}
            
            function closeModal() {{
                document.getElementById('chartModal').classList.remove('visible');
            }}
            
            // Close modal when clicking outside the content
            window.onclick = function(event) {{
                const modal = document.getElementById('chartModal');
                if (event.target === modal) {{
                    closeModal();
                }}
            }}
            
            // Close modal with Escape key
            document.addEventListener('keydown', function(event) {{
                if (event.key === 'Escape') {{
                    closeModal();
                }}
            }})
            
            const ctx = document.getElementById('rankingChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {chart_labels},
                    datasets: [{{
                        label: 'Total Streets',
                        data: {chart_data},
                        backgroundColor: 'rgba(76, 29, 149, 0.6)',
                        borderColor: 'rgba(76, 29, 149, 1)',
                        borderWidth: 1,
                        barPercentage: 0.8,
                        categoryPercentage: 0.9
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        title: {{
                            display: true,
                            text: 'Street Count Distribution',
                            font: {{
                                size: 24
                            }}
                        }},
                        tooltip: {{
                            enabled: true,
                            bodyFont: {{
                                size: 18
                            }},
                            titleFont: {{
                                size: 18
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            beginAtZero: true,
                            grid: {{
                                display: true
                            }},
                            ticks: {{
                                font: {{
                                    size: 16
                                }}
                            }}
                        }},
                        y: {{
                            ticks: {{
                                display: true,
                                font: {{
                                    size: 16
                                }}
                            }},
                            grid: {{
                                display: false
                            }}
                        }}
                    }}
                }}
            }});
            
            // Time series chart
            const timeCtx = document.getElementById('timeSeriesChart').getContext('2d');
            new Chart(timeCtx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(time_labels)},
                    datasets: {json.dumps(time_series_datasets)}
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        title: {{
                            display: false
                        }},
                        tooltip: {{
                            enabled: true,
                            bodyFont: {{
                                size: 14
                            }},
                            titleFont: {{
                                size: 14
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{
                                display: true
                            }},
                            ticks: {{
                                font: {{
                                    size: 12
                                }},
                                maxRotation: 45,
                                minRotation: 45
                            }}
                        }},
                        y: {{
                            beginAtZero: false,
                            grid: {{
                                display: true
                            }},
                            ticks: {{
                                font: {{
                                    size: 12
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    with open(HTML_FILE, "w") as f:
        f.write(html)
    print(f"Generated {HTML_FILE}")

def main():
    print("Starting leaderboard update...")
    
    # Load previous data
    previous_data = load_previous_data()
    
    # Fetch current data
    current_runners = fetch_leaderboard()
    print(f"Fetched {len(current_runners)} runners")
    
    # Calculate deltas
    processed_runners = calculate_deltas(current_runners, previous_data)
    
    # Save new data
    new_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runners": processed_runners
    }
    save_data(new_data)
    
    # Generate HTML
    generate_html(processed_runners, new_data["last_updated"])
    print("Done!")

if __name__ == "__main__":
    main()
