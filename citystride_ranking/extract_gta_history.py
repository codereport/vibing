#!/usr/bin/env python3
"""Reconstruct Toronto (and other GTA city) completion history from git commits
of gta_cities_data.json, and write it to gta_history.json.

Each git commit that touched gta_cities_data.json becomes one history record:
    {"date": "YYYY-MM-DD HH:MM:SS", "cities": {city_id: {"completed": int, "total": int}}}

This is a one-time backfill. Going forward, update_leaderboard.py appends new
records to the same file.
"""

import json
import subprocess

GTA_DATA_FILE = "gta_cities_data.json"
HISTORY_FILE = "gta_history.json"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main():
    # Oldest -> newest commit hashes + author date that touched the GTA file
    log = git("log", "--reverse", "--format=%H|%cd", "--date=format:%Y-%m-%d %H:%M:%S",
              "--", GTA_DATA_FILE)

    records = []
    seen_toronto = None  # dedupe consecutive identical Toronto completed counts

    for line in log.strip().splitlines():
        if "|" not in line:
            continue
        commit, date = line.split("|", 1)
        try:
            content = git("show", f"{commit}:./{GTA_DATA_FILE}")
        except subprocess.CalledProcessError:
            continue
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue

        cities = data.get("cities", {})
        if not cities:
            continue

        # Prefer the timestamp stored inside the file, fall back to commit date
        rec_date = data.get("last_updated") or date

        city_map = {}
        for cid, c in cities.items():
            completed = c.get("completed")
            total = c.get("total")
            if completed is None or total is None:
                continue
            city_map[cid] = {"completed": completed, "total": total}

        if not city_map:
            continue

        toronto = city_map.get("131268", {}).get("completed")
        # Skip records that don't change Toronto's completed count (flat duplicates),
        # but always keep the first record.
        if toronto is not None and toronto == seen_toronto:
            continue
        seen_toronto = toronto

        records.append({"date": rec_date, "cities": city_map})

    with open(HISTORY_FILE, "w") as f:
        json.dump({"records": records}, f, indent=2)

    print(f"Wrote {len(records)} records to {HISTORY_FILE}")
    if records:
        first_t = records[0]["cities"].get("131268", {})
        last_t = records[-1]["cities"].get("131268", {})
        print(f"Toronto: {first_t} ({records[0]['date']}) -> {last_t} ({records[-1]['date']})")


if __name__ == "__main__":
    main()
