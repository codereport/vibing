import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DATA_FILE = "leaderboard_data.json"
HTML_FILE = "index.html"
PAGES_TO_FETCH = 5 # 12 per page * 5 = 60 runners, enough for top 50

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
            name = name_tag.get_text(strip=True) if name_tag else "Unknown"
            
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
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CityStrides Top 50 Leaderboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f4f5; color: #18181b; margin: 0; padding: 20px; }}
            .container {{ max_width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #4c1d95; }}
            .updated {{ text-align: center; color: #71717a; font-size: 0.9em; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e4e4e7; }}
            th {{ background: #f8fafc; font-weight: 600; }}
            .rank-up {{ color: #16a34a; }}
            .rank-down {{ color: #dc2626; }}
            .streets-up {{ color: #16a34a; font-size: 0.9em; }}
            .profile-link {{ color: #4c1d95; text-decoration: none; font-weight: 500; }}
            .profile-link:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>CityStrides Top 50</h1>
            <p class="updated">Last updated: {last_updated}</p>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Runner</th>
                        <th>Streets</th>
                        <th>Change (Streets)</th>
                        <th>Change (Rank)</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, runner in enumerate(runners):
        rank = i + 1
        rank_delta = runner.get("rank_delta", 0)
        streets_delta = runner.get("streets_delta", 0)
        
        rank_display = f"{rank}"
        if rank_delta > 0:
            rank_display += f" <span class='rank-up'>(▲{rank_delta})</span>"
        elif rank_delta < 0:
            rank_display += f" <span class='rank-down'>(▼{abs(rank_delta)})</span>"
            
        streets_delta_display = f"+{streets_delta}" if streets_delta > 0 else "-"
        
        html += f"""
                    <tr>
                        <td>{rank_display}</td>
                        <td><a href="https://citystrides.com{runner['profile_url']}" class="profile-link" target="_blank">{runner['name']}</a></td>
                        <td>{runner['streets']:,}</td>
                        <td class="streets-up">{streets_delta_display}</td>
                        <td>{rank_delta if rank_delta != 0 else '-'}</td>
                    </tr>
        """
        
    html += """
                </tbody>
            </table>
        </div>
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
