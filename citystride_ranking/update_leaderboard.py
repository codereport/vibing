import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DATA_FILE = "leaderboard_data.json"
HTML_FILE = "index.html"
PAGES_TO_FETCH = 5 # 12 per page * 5 = 60 runners, enough for top 50

def clean_name(name):
    # Specific fix for James Salmon
    if "James Salmon" in name and "Purple Runner" in name:
        return "James Salmon"
    return name

def fetch_leaderboard():
    runners = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
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
                "profile_url": card.find("a", href=lambda h: h and "/users/" in h)['href'] if card.find("a", href=lambda h: h and "/users/" in h) else ""
            })
            
    return runners[:50] # Return top 50

def load_previous_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return None

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

def generate_html(runners, last_updated):
    # Prepare data for chart (All 50)
    chart_labels = [r['name'].replace("'", "\\'") for r in runners]
    chart_data = [r['streets'] for r in runners]
    
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
            
            @media (max-width: 1400px) {{
                .content-wrapper {{ flex-direction: column; }}
                .chart-container {{ height: 1200px; }}
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <h1>CityStrides Top 50</h1>
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
                                <th>Change</th>
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
        
        html += f"""
                            <tr>
                                <td>{rank_display}</td>
                                <td><a href="https://citystrides.com{runner['profile_url']}" class="profile-link" target="_blank">{runner['name']}</a></td>
                                <td>{runner['streets']:,}</td>
                                <td class="gap">{gap_display}</td>
                                <td class="streets-up">{streets_delta_display}</td>
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
        
        <script>
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
