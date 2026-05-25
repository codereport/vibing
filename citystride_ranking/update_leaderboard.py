#! /usr/bin/env python3

import re
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DATA_FILE = "leaderboard_data.json"
HTML_FILE = "index.html"
PAGES_TO_FETCH = 5 # 12 per page * 5 = 60 runners, enough for top 50
HISTORY_DIR = "history"

GTA_DATA_FILE = "gta_cities_data.json"
CONOR_USER_ID = "55228"

GTA_CITIES = {
    "131268": "Toronto",
    "38108": "North York",
    "38102": "York",
    "38114": "East York",
    "38121": "Old Toronto",
    "38014": "Etobicoke",
    "37668": "Vaughan",
    "37680": "Markham",
    "38007": "Scarborough",
    "37878": "Richmond Hill",
}

EXTENDED_CITIES = {
    "38936": "Tiny",
    "38950": "Midland",
    "38946": "Penetanguishene",
}

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

def get_history_files_for_js():
    if not os.path.exists(HISTORY_DIR):
        return "[]"
    
    files = []
    for f in sorted(os.listdir(HISTORY_DIR)):
        if f.startswith("leaderboard_") and f.endswith(".json"):
            # Parse timestamp from filename: leaderboard_YYYYMMDD_HHMMSS.json
            try:
                timestamp_str = f.replace("leaderboard_", "").replace(".json", "")
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                files.append({
                    "file": f"{HISTORY_DIR}/{f}",
                    "date": formatted_date
                })
            except ValueError:
                continue
                
    return json.dumps(files, indent=4)


def fetch_total_runners(city_id, known_rank, headers):
    """Get total runners for a city by scanning leaderboard pages past the known rank."""
    max_rank = known_rank
    page = (known_rank - 1) // 12 + 2
    while page <= 200:
        time.sleep(0.3)
        url = f"https://citystrides.com/users/search?context=city_users-{city_id}&page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.content, "html.parser")
        entries = parse_leaderboard_entries(soup)
        if not entries:
            break
        max_rank = max(e["rank"] for e in entries)
        page += 1
    return max_rank


def parse_leaderboard_entries(soup):
    """Parse all leaderboard entries from a page, including private striders."""
    entries = []

    cards = soup.find_all("div", class_=lambda c: c and "col-span-1" in c)
    for card in cards:
        name_tag = card.find("h3")
        name = name_tag.get_text(strip=True) if name_tag else "?"
        text = card.get_text(separator=" ", strip=True)
        pct_match = re.search(r'([\d.]+)%', text)
        rank_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Place', text)
        if pct_match and rank_match:
            entries.append({
                "name": name,
                "pct": float(pct_match.group(1)),
                "rank": int(rank_match.group(1)),
            })

    page_text = soup.get_text()
    for m in re.finditer(
        r'private\s+[Ss]trider\s+is\s+in\s+(\d+)(?:st|nd|rd|th)\s+Place\s+at\s+([\d.]+)%',
        page_text,
    ):
        entries.append({
            "name": "A private Strider",
            "pct": float(m.group(2)),
            "rank": int(m.group(1)),
        })

    entries.sort(key=lambda e: e["rank"])
    return entries


def fetch_runner_above(city_id, rank, conor_pct, headers):
    """Fetch the runner ranked one above Conor from the city leaderboard"""
    if rank <= 1:
        return None

    page = max(1, (rank - 1) // 12 + 1)

    lb_url = f"https://citystrides.com/users/search?context=city_users-{city_id}&page={page}"
    resp = requests.get(lb_url, headers=headers)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.content, "html.parser")
    entries = parse_leaderboard_entries(soup)

    conor_idx = None
    for i, entry in enumerate(entries):
        if "Conor" in entry["name"]:
            conor_idx = i
            break

    if conor_idx is None:
        return None
    if conor_idx > 0:
        above = entries[conor_idx - 1]
        if above["pct"] == conor_pct:
            return None
        return {"name": above["name"], "pct": above["pct"]}
    if page > 1:
        prev_url = f"https://citystrides.com/users/search?context=city_users-{city_id}&page={page - 1}"
        prev_resp = requests.get(prev_url, headers=headers)
        if prev_resp.status_code == 200:
            prev_entries = parse_leaderboard_entries(
                BeautifulSoup(prev_resp.content, "html.parser")
            )
            if prev_entries:
                above = prev_entries[-1]
                if above["pct"] == conor_pct:
                    return None
                return {"name": above["name"], "pct": above["pct"]}
    return None


def fetch_gta_cities():
    """Fetch GTA city data from Conor's CityStrides profile page"""
    url = f"https://citystrides.com/users/{CONOR_USER_ID}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Fetching GTA cities data...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch profile: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    cities = []

    for city_id, city_name in GTA_CITIES.items():
        city_path = f"/users/{CONOR_USER_ID}/cities/{city_id}"
        city_full_url = f"https://citystrides.com{city_path}"
        link = soup.find("a", href=lambda h: h and city_path in h)
        city_page_soup = None

        if link:
            text = link.get_text(separator=" ")

            streets_match = re.search(r'(\d[\d,]*)\s+of\s+(\d[\d,]*)\s+streets', text)
            rank_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+of\s+([\d,]+)', text)
            pct_match = re.search(r'([\d.]+)%', text)

            completed = int(streets_match.group(1).replace(",", "")) if streets_match else 0
            total = int(streets_match.group(2).replace(",", "")) if streets_match else 0
            rank = int(rank_match.group(1).replace(",", "")) if rank_match else 0
            total_runners = int(rank_match.group(2).replace(",", "")) if rank_match else 0
            percentage = float(pct_match.group(1)) if pct_match else 0.0
        else:
            print(f"  {city_name} not on profile page, fetching directly...")
            time.sleep(0.5)
            direct_resp = requests.get(city_full_url, headers=headers)
            if direct_resp.status_code != 200:
                print(f"  Could not fetch {city_name} (id={city_id})")
                continue

            city_page_soup = BeautifulSoup(direct_resp.content, "html.parser")
            direct_text = city_page_soup.get_text(separator=" ")

            pct_match = re.search(r'([\d.]+)%', direct_text)
            percentage = float(pct_match.group(1)) if pct_match else 0.0

            rank_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Place', direct_text)
            rank = int(rank_match.group(1)) if rank_match else 0

            total_match = re.search(r'([\d,]+)\s+streets\s+[\d,.]+\s+miles', direct_text)
            total = int(total_match.group(1).replace(",", "")) if total_match else 0

            completed_match = re.search(r'Place\s+(\d[\d,]*)\s+street', direct_text)
            completed = int(completed_match.group(1).replace(",", "")) if completed_match else 0

            total_runners = fetch_total_runners(city_id, rank, headers) if rank > 0 else 0

        if city_page_soup is None:
            time.sleep(0.5)
            city_resp = requests.get(city_full_url, headers=headers)
            if city_resp.status_code == 200:
                city_page_soup = BeautifulSoup(city_resp.content, "html.parser")

        was_100 = False
        if city_page_soup:
            badge = city_page_soup.find("span", title="Completed this city")
            was_100 = badge is not None

        # Fetch the runner ranked directly above Conor
        time.sleep(0.3)
        above = fetch_runner_above(city_id, rank, percentage, headers)

        cities.append({
            "city_id": city_id,
            "name": city_name,
            "completed": completed,
            "total": total,
            "percentage": percentage,
            "rank": rank,
            "total_runners": total_runners,
            "city_url": city_full_url,
            "was_100": was_100,
            "runner_above": above,
        })
        above_str = f" | above: {above['name']} ({above['pct']}%)" if above else ""
        status = "💯" if was_100 else ""
        print(f"  {city_name}: {percentage}% ({completed}/{total}), rank {rank} of {total_runners} {status}{above_str}")

    cities.sort(key=lambda x: x["percentage"], reverse=True)
    print(f"Fetched {len(cities)} GTA cities")
    return cities


def fetch_extended_cities():
    """Fetch extended city data directly from each city page"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("Fetching extended cities data...")
    cities = []

    for city_id, city_name in EXTENDED_CITIES.items():
        city_path = f"/users/{CONOR_USER_ID}/cities/{city_id}"
        city_full_url = f"https://citystrides.com{city_path}"

        time.sleep(0.5)
        resp = requests.get(city_full_url, headers=headers)
        if resp.status_code != 200:
            print(f"  Could not fetch {city_name} (id={city_id})")
            continue

        soup = BeautifulSoup(resp.content, "html.parser")
        text = soup.get_text(separator=" ")

        pct_match = re.search(r'([\d.]+)%', text)
        percentage = float(pct_match.group(1)) if pct_match else 0.0

        rank_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Place', text)
        rank = int(rank_match.group(1)) if rank_match else 0

        total_match = re.search(r'([\d,]+)\s+streets\s+[\d,.]+\s+miles', text)
        total = int(total_match.group(1).replace(",", "")) if total_match else 0

        completed_match = re.search(r'Place\s+(\d[\d,]*)\s+street', text)
        completed = int(completed_match.group(1).replace(",", "")) if completed_match else 0

        total_runners = fetch_total_runners(city_id, rank, headers) if rank > 0 else 0

        was_100 = False
        badge = soup.find("span", title="Completed this city")
        was_100 = badge is not None

        time.sleep(0.3)
        above = fetch_runner_above(city_id, rank, percentage, headers)

        cities.append({
            "city_id": city_id,
            "name": city_name,
            "completed": completed,
            "total": total,
            "percentage": percentage,
            "rank": rank,
            "total_runners": total_runners,
            "city_url": city_full_url,
            "was_100": was_100,
            "runner_above": above,
        })
        above_str = f" | above: {above['name']} ({above['pct']}%)" if above else ""
        status = "💯" if was_100 else ""
        print(f"  {city_name}: {percentage}% ({completed}/{total}), rank {rank} of {total_runners} {status}{above_str}")

    cities.sort(key=lambda x: x["percentage"], reverse=True)
    print(f"Fetched {len(cities)} extended cities")
    return cities


def load_gta_data():
    if os.path.exists(GTA_DATA_FILE):
        with open(GTA_DATA_FILE, "r") as f:
            return json.load(f)
    return {"cities": {}, "last_updated": None}


def save_gta_data(gta_data):
    with open(GTA_DATA_FILE, "w") as f:
        json.dump(gta_data, f, indent=2)


def update_gta_tracking(cities):
    """Save GTA data snapshot"""
    gta_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cities": {city["city_id"]: city for city in cities},
    }
    save_gta_data(gta_data)
    return cities


def ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def generate_html(runners, last_updated, gta_cities=None, extended_cities=None):
    # Generate history files JSON for the frontend
    history_files_json = get_history_files_for_js()

    # Build GTA cities table rows
    gta_rows_html = ""
    if gta_cities:
        for city in gta_cities:
            is_100 = city["percentage"] >= 100.0
            was_100 = city.get("was_100", False)

            row_class = ""
            if is_100:
                row_class = ' class="city-100"'
            elif was_100:
                row_class = ' class="city-was-100"'

            hundred_emoji = "💯" if is_100 or was_100 else ""
            rank_str = f"{ordinal(city['rank'])} of {city['total_runners']:,}" if city['total_runners'] > 0 else ordinal(city['rank'])

            above = city.get("runner_above")
            above_name = above["name"] if above else "-"
            above_pct = f"{above['pct']:.2f}%" if above else ""

            gta_rows_html += f"""
                <tr{row_class}>
                    <td><a href="{city['city_url']}" class="profile-link" target="_blank">{city['name']}</a></td>
                    <td>{city['completed']:,} / {city['total']:,}</td>
                    <td><strong>{city['percentage']:.2f}%</strong></td>
                    <td>{rank_str}</td>
                    <td>{above_name}</td>
                    <td>{above_pct}</td>
                    <td style="text-align:center; font-size:1.2em;">{hundred_emoji}</td>
                </tr>"""

    # Build extended cities table rows
    extended_rows_html = ""
    if extended_cities:
        for city in extended_cities:
            is_100 = city["percentage"] >= 100.0
            was_100 = city.get("was_100", False)

            row_class = ""
            if is_100:
                row_class = ' class="city-100"'
            elif was_100:
                row_class = ' class="city-was-100"'

            hundred_emoji = "💯" if is_100 or was_100 else ""
            rank_str = f"{ordinal(city['rank'])} of {city['total_runners']:,}" if city['total_runners'] > 0 else ordinal(city['rank'])

            above = city.get("runner_above")
            above_name = above["name"] if above else "-"
            above_pct = f"{above['pct']:.2f}%" if above else ""

            extended_rows_html += f"""
                <tr{row_class}>
                    <td><a href="{city['city_url']}" class="profile-link" target="_blank">{city['name']}</a></td>
                    <td>{city['completed']:,} / {city['total']:,}</td>
                    <td><strong>{city['percentage']:.2f}%</strong></td>
                    <td>{rank_str}</td>
                    <td>{above_name}</td>
                    <td>{above_pct}</td>
                    <td style="text-align:center; font-size:1.2em;">{hundred_emoji}</td>
                </tr>"""

    html = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CityStrides Rankings</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f4f4f5;
            color: #18181b;
            margin: 0;
            padding: 30px;
            font-size: 24px;
        }}

        .main-container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        }}

        h1 {{
            text-align: center;
            color: #4c1d95;
            margin-bottom: 10px;
        }}

        .tab-bar {{
            display: flex;
            gap: 0;
            border-bottom: 2px solid #e4e4e7;
            margin-bottom: 0;
        }}

        .tab-btn {{
            padding: 14px 28px;
            background: none;
            border: none;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            font-size: 0.9em;
            font-weight: 500;
            color: #71717a;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .tab-btn:hover {{
            color: #4c1d95;
            background: #faf5ff;
        }}

        .tab-btn.active {{
            color: #4c1d95;
            border-bottom-color: #4c1d95;
            font-weight: 600;
        }}

        .tab-content {{
            display: none;
            padding-top: 20px;
        }}

        .tab-content.active {{
            display: block;
        }}

        .updated {{
            text-align: center;
            color: #71717a;
            font-size: 0.8em;
            margin-bottom: 20px;
        }}

        .delta-controls {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
        }}

        .delta-controls label {{
            font-size: 0.85em;
            font-weight: 500;
            color: #4c1d95;
        }}

        .delta-controls select {{
            padding: 10px 15px;
            font-size: 0.85em;
            border: 2px solid #e4e4e7;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            min-width: 180px;
        }}

        .delta-controls select:focus {{
            outline: none;
            border-color: #4c1d95;
        }}

        .delta-arrow {{
            font-size: 1.5em;
            color: #4c1d95;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 1em;
        }}

        th,
        td {{
            padding: 12px 18px;
            text-align: left;
            border-bottom: 1px solid #e4e4e7;
        }}

        th {{
            background: #f8fafc;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}

        th.custom-col {{
            background: #ede9fe;
        }}

        .rank-up {{
            color: #16a34a;
        }}

        .rank-down {{
            color: #dc2626;
        }}

        .streets-up {{
            color: #16a34a;
            font-size: 0.9em;
        }}

        .streets-down {{
            color: #dc2626;
            font-size: 0.9em;
        }}

        .gap {{
            color: #71717a;
            font-size: 0.9em;
        }}

        .profile-link {{
            color: #4c1d95;
            text-decoration: none;
            font-weight: 500;
        }}

        .profile-link:hover {{
            text-decoration: underline;
        }}

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

        .toggle-button:hover {{
            background: #5b21b6;
        }}

        .city-100 {{
            background-color: #dcfce7;
        }}

        .city-was-100 {{
            background-color: #fef9c3;
        }}

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

        .modal.visible {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}

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

        .modal-close:hover {{
            background: #f4f4f5;
            color: #18181b;
        }}

        .time-series-container {{
            position: relative;
            height: 600px;
            width: 100%;
            margin-top: 20px;
        }}
    </style>
</head>

<body>
    <div class="main-container">
        <h1>CityStrides Rankings</h1>

        <div class="tab-bar">
            <button class="tab-btn active" data-tab="leaderboard" onclick="switchTab('leaderboard')">Top 50 Leaderboard</button>
            <button class="tab-btn" data-tab="gta" onclick="switchTab('gta')">Top GTA Cities</button>
        </div>

        <div id="tab-leaderboard" class="tab-content active">
            <div style="text-align: center; margin-top: 20px;">
                <button class="toggle-button" onclick="openModal()">📈 View Rank History (Top 30)</button>
            </div>
            <p class="updated">Last updated: {last_updated}</p>

            <div class="delta-controls">
                <label for="fromDate">Custom compare from:</label>
                <select id="fromDate" onchange="updateCustomDeltas()"></select>
                <span class="delta-arrow">→</span>
                <label for="toDate">to:</label>
                <select id="toDate" onchange="updateCustomDeltas()"></select>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Runner</th>
                        <th>Streets</th>
                        <th>Gap</th>
                        <th>Streets Δ</th>
                        <th>Rank Δ</th>
                        <th class="custom-col">Custom Streets Δ</th>
                        <th class="custom-col">Custom Rank Δ</th>
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
        
        # Gap display
        gap_display = f"-{gap:,}" if i > 0 else "-"
        
        # Streets delta display
        streets_delta_display = "-"
        streets_delta_class = "streets-up" # Default green, change if negative
        if streets_delta > 0:
            streets_delta_display = f"+{streets_delta}"
        elif streets_delta < 0:
            streets_delta_display = f"{streets_delta}"
            streets_delta_class = "streets-down"
            
        # Rank delta display
        rank_delta_display = "-"
        rank_delta_class = ""
        if rank_delta > 0:
            rank_delta_display = f"▲{rank_delta}"
            rank_delta_class = "rank-up"
        elif rank_delta < 0:
            rank_delta_display = f"▼{abs(rank_delta)}"
            rank_delta_class = "rank-down"
        
        html += f"""
                <tr data-url="{runner['profile_url']}">
                    <td>{rank}</td>
                    <td><a href="https://citystrides.com{runner['profile_url']}" class="profile-link" target="_blank">{runner['name']}</a></td>
                    <td>{runner['streets']:,}</td>
                    <td class="gap">{gap_display}</td>
                    <td class="{streets_delta_class}">{streets_delta_display}</td>
                    <td class="{rank_delta_class}">{rank_delta_display}</td>
                    <td class="custom-streets">-</td>
                    <td class="custom-rank">-</td>
                </tr>
        """
        
    html += f"""
                </tbody>
            </table>
        </div>

        <div id="tab-gta" class="tab-content">
            <p class="updated" style="margin-top: 20px;">Data for <a href="https://citystrides.com/users/{CONOR_USER_ID}" class="profile-link" target="_blank">Conor Hoekstra</a> &middot; Last updated: {last_updated}</p>
            <table>
                <thead>
                    <tr>
                        <th>City</th>
                        <th>Progress</th>
                        <th>% Complete</th>
                        <th>Rank</th>
                        <th>Next Target</th>
                        <th>Their %</th>
                        <th style="text-align:center;">💯</th>
                    </tr>
                </thead>
                <tbody>
                    {gta_rows_html}
                </tbody>
            </table>

            <h3 style="color: #4c1d95; margin-top: 40px;">Extended</h3>
            <table>
                <thead>
                    <tr>
                        <th>City</th>
                        <th>Progress</th>
                        <th>% Complete</th>
                        <th>Rank</th>
                        <th>Next Target</th>
                        <th>Their %</th>
                        <th style="text-align:center;">💯</th>
                    </tr>
                </thead>
                <tbody>
                    {extended_rows_html}
                </tbody>
            </table>
        </div>
    </div>

    <div id="chartModal" class="modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
            <h2 style="text-align: center; color: #4c1d95; margin-bottom: 20px;">Rank Progress Over Time</h2>
            <div class="time-series-container">
                <canvas id="timeSeriesChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
        }}

        const historyFiles = {history_files_json};

        let historyCache = {{}};

        async function init() {{
            const fromSelect = document.getElementById('fromDate');
            const toSelect = document.getElementById('toDate');

            historyFiles.forEach((item, index) => {{
                fromSelect.add(new Option(item.date, item.file));
                toSelect.add(new Option(item.date, item.file));
            }});

            if (historyFiles.length > 0) {{
                fromSelect.selectedIndex = 0;
                toSelect.selectedIndex = historyFiles.length - 1;
            }}

            await updateCustomDeltas();
        }}

        async function loadHistoryData(file) {{
            if (historyCache[file]) return historyCache[file];
            try {{
                const response = await fetch(file);
                if (!response.ok) throw new Error('HTTP ' + response.status);
                const data = await response.json();
                historyCache[file] = data;
                return data;
            }} catch (e) {{
                console.error('Failed to load', file, e);
                return null;
            }}
        }}

        async function updateCustomDeltas() {{
            const fromFile = document.getElementById('fromDate').value;
            const toFile = document.getElementById('toDate').value;

            if (!fromFile || !toFile) return;

            const fromData = await loadHistoryData(fromFile);
            const toData = await loadHistoryData(toFile);

            if (!fromData || !toData) return;

            const fromByUrl = {{}};
            fromData.runners.forEach((runner, idx) => {{
                fromByUrl[runner.profile_url] = {{ ...runner, rank: idx + 1 }};
            }});

            const toByUrl = {{}};
            toData.runners.forEach((runner, idx) => {{
                toByUrl[runner.profile_url] = {{ ...runner, rank: idx + 1 }};
            }});

            document.querySelectorAll('#tab-leaderboard tbody tr').forEach(row => {{
                const url = row.dataset.url;
                const fromRunner = fromByUrl[url];
                const toRunner = toByUrl[url];

                const streetsCell = row.querySelector('.custom-streets');
                const rankCell = row.querySelector('.custom-rank');

                if (fromRunner && toRunner) {{
                    const streetsDelta = toRunner.streets - fromRunner.streets;
                    const rankDelta = fromRunner.rank - toRunner.rank;

                    streetsCell.textContent = streetsDelta === 0 ? '-' : (streetsDelta > 0 ? '+' + streetsDelta.toLocaleString() : streetsDelta.toLocaleString());
                    streetsCell.className = 'custom-streets ' + (streetsDelta > 0 ? 'streets-up' : streetsDelta < 0 ? 'streets-down' : '');

                    rankCell.textContent = rankDelta === 0 ? '-' : (rankDelta > 0 ? '▲' + rankDelta : '▼' + Math.abs(rankDelta));
                    rankCell.className = 'custom-rank ' + (rankDelta > 0 ? 'rank-up' : rankDelta < 0 ? 'rank-down' : '');
                }} else {{
                    streetsCell.textContent = '-';
                    streetsCell.className = 'custom-streets';
                    rankCell.textContent = '-';
                    rankCell.className = 'custom-rank';
                }}
            }});
        }}

        function openModal() {{
            document.getElementById('chartModal').classList.add('visible');
            initTimeSeriesChart();
        }}

        function closeModal() {{
            document.getElementById('chartModal').classList.remove('visible');
        }}

        window.onclick = function (event) {{
            if (event.target === document.getElementById('chartModal')) closeModal();
        }}

        document.addEventListener('keydown', function (event) {{
            if (event.key === 'Escape') closeModal();
        }});

        let timeSeriesChart = null;
        async function initTimeSeriesChart() {{
            if (timeSeriesChart) return;

            const allData = await Promise.all(
                historyFiles.map(async (item) => {{
                    const data = await loadHistoryData(item.file);
                    return {{ date: item.date, data }};
                }})
            );

            if (allData.some(d => !d.data)) return;

            const colors = [
                'rgb(76, 29, 149)', 'rgb(220, 38, 38)', 'rgb(22, 163, 74)', 'rgb(37, 99, 235)',
                'rgb(234, 88, 12)', 'rgb(168, 85, 247)', 'rgb(236, 72, 153)', 'rgb(14, 165, 233)',
                'rgb(132, 204, 22)', 'rgb(251, 146, 60)', 'rgb(59, 130, 246)', 'rgb(239, 68, 68)',
                'rgb(16, 185, 129)', 'rgb(245, 158, 11)', 'rgb(139, 92, 246)', 'rgb(244, 114, 182)',
                'rgb(6, 182, 212)', 'rgb(163, 230, 53)', 'rgb(251, 191, 36)', 'rgb(99, 102, 241)',
                'rgb(248, 113, 113)', 'rgb(52, 211, 153)', 'rgb(167, 139, 250)', 'rgb(251, 113, 133)',
                'rgb(34, 211, 238)', 'rgb(190, 242, 100)', 'rgb(252, 211, 77)', 'rgb(129, 140, 248)',
                'rgb(252, 165, 165)', 'rgb(110, 231, 183)', 'rgb(253, 186, 116)', 'rgb(196, 181, 253)',
                'rgb(253, 164, 175)', 'rgb(103, 232, 249)', 'rgb(217, 249, 157)', 'rgb(254, 240, 138)',
                'rgb(165, 180, 252)', 'rgb(254, 202, 202)', 'rgb(167, 243, 208)', 'rgb(254, 215, 170)',
                'rgb(221, 214, 254)', 'rgb(254, 205, 211)', 'rgb(165, 243, 252)', 'rgb(233, 250, 203)',
                'rgb(254, 249, 195)', 'rgb(199, 210, 254)', 'rgb(254, 226, 226)', 'rgb(209, 250, 229)',
                'rgb(254, 235, 200)', 'rgb(238, 242, 255)'
            ];

            const latestRunners = allData[allData.length - 1].data.runners.slice(0, 30);
            const datasets = latestRunners.map((runner, idx) => {{
                const isConor = runner.name.includes('Conor Hoekstra');
                return {{
                    label: runner.name,
                    data: allData.map(({{ data }}) => {{
                        const rankIndex = data.runners.findIndex(r => r.profile_url === runner.profile_url);
                        return rankIndex >= 0 ? rankIndex + 1 : null;
                    }}),
                    borderColor: isConor ? 'rgb(220, 38, 38)' : colors[idx % colors.length],
                    borderWidth: isConor ? 4 : 1.5,
                    tension: 0.1,
                    fill: false,
                    order: isConor ? 0 : 1
                }};
            }});

            const ctx = document.getElementById('timeSeriesChart').getContext('2d');
            timeSeriesChart = new Chart(ctx, {{
                type: 'line',
                data: {{ labels: allData.map(d => d.date), datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ ticks: {{ maxRotation: 45, minRotation: 45 }} }},
                        y: {{
                            reverse: true,
                            min: 1,
                            max: 30,
                            ticks: {{ stepSize: 5 }}
                        }}
                    }}
                }}
            }});
        }}

        init();
    </script>
</body>
</html>
"""
    
    with open(HTML_FILE, "w") as f:
        f.write(html)
    print(f"Generated {HTML_FILE}")

def main():
    print("Starting leaderboard update...")
    
    previous_data = load_previous_data()
    
    current_runners = fetch_leaderboard()
    print(f"Fetched {len(current_runners)} runners")
    
    processed_runners = calculate_deltas(current_runners, previous_data)
    
    new_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runners": processed_runners
    }
    save_data(new_data)
    
    gta_cities = fetch_gta_cities()
    if gta_cities:
        gta_cities = update_gta_tracking(gta_cities)

    extended_cities = fetch_extended_cities()

    generate_html(processed_runners, new_data["last_updated"], gta_cities, extended_cities)
    print("Done!")

if __name__ == "__main__":
    main()
