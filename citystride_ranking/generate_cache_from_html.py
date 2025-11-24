#!/usr/bin/env python3
"""
Generate runner_locations.json cache from existing index.html
This extracts the location data from names and creates the cache file.
"""

from bs4 import BeautifulSoup
import json
import re

def country_to_flag(country):
    """Convert country name to flag emoji"""
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
    
    return mapping.get(country, country)

def has_flag(text):
    """Check if text contains a flag emoji"""
    for char in text:
        if 0x1F1E6 <= ord(char) <= 0x1F1FF:
            return True
    return False

def extract_location_from_name(name):
    """
    Extract location from runner name.
    Returns (clean_name, flag_emoji)
    """
    # If already has a flag, return empty (we don't need to cache it)
    if has_flag(name):
        return name, ""
    
    # Try to match known country names at the end
    countries = [
        "United States", "United Kingdom", "Canada", "Deutschland", "Germany",
        "Nederland", "Netherlands", "Portugal", "Australia", "España", "Spain",
        "België / Belgique / Belgien", "Belgium", "France", "Italy", "Italia",
        "Sweden", "Sverige", "Norway", "Norge", "Denmark", "Danmark",
        "Finland", "Suomi", "Ireland", "New Zealand", "Switzerland", "Schweiz",
        "Austria", "Österreich", "Poland", "Polska"
    ]
    
    for country in countries:
        if name.endswith(" " + country):
            clean_name = name[:-len(country)-1].strip()
            flag = country_to_flag(country)
            return clean_name, flag
    
    # No location found
    return name, ""

def main():
    # Read the HTML file
    with open("index.html", "r") as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find all profile links
    cache = {}
    
    # Find all table rows with runner data
    rows = soup.find_all("tr")
    
    for row in rows:
        # Find the profile link
        link = row.find("a", class_="profile-link")
        if link:
            href = link.get("href")
            name = link.get_text(strip=True)
            
            # Extract user ID from href
            # href is like "https://citystrides.com/users/8376/map"
            match = re.search(r'/users/(\d+)/', href)
            if match:
                user_id = match.group(1)
                
                # Extract location from name
                clean_name, flag = extract_location_from_name(name)
                
                # Only cache if we found a location
                if flag:
                    cache[user_id] = flag
                    print(f"Cached: {user_id} -> {clean_name} -> {flag}")
    
    # Save the cache
    with open("runner_locations.json", "w") as f:
        json.dump(cache, f, indent=2)
    
    print(f"\nGenerated cache with {len(cache)} entries")
    print("Saved to runner_locations.json")

if __name__ == "__main__":
    main()
