#!/usr/bin/env python3
"""Refresh the static TVmaze snapshot. No API key or third-party packages needed."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TV_DIR = Path(__file__).resolve().parents[1]
API = "https://api.tvmaze.com"


def fetch_json(path, attempts=4):
    for attempt in range(attempts):
        try:
            request = Request(API + path, headers={"User-Agent": "Vibing-TV-Tracker/1.0"})
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            if isinstance(error, HTTPError) and error.code != 429 and error.code < 500:
                raise
            if attempt == attempts - 1:
                raise
            retry_after = error.headers.get("Retry-After", "") if isinstance(error, HTTPError) else ""
            delay = min(60, int(retry_after)) if retry_after.isdigit() else 2 ** (attempt + 1)
            time.sleep(delay)
        finally:
            # TVmaze guarantees at least 20 requests per 10 seconds.
            time.sleep(0.6)


def valid_date(value):
    if not value:
        return None
    return date.fromisoformat(value).isoformat()


def make_snapshot(show, seasons, checked_at):
    if not isinstance(show, dict) or not isinstance(seasons, list):
        raise ValueError("Unexpected TVmaze response")
    normalized = []
    for season in seasons:
        number = season.get("number")
        if not isinstance(number, int) or number <= 0:
            continue
        normalized.append({
            "number": number,
            "premiereDate": valid_date(season.get("premiereDate")),
            "endDate": valid_date(season.get("endDate")),
            "episodeCount": season.get("episodeOrder"),
        })
    # Upcoming shows sometimes have a series premiere before any season records.
    premiered = valid_date(show.get("premiered"))
    first = next((season for season in normalized if season["number"] == 1), None)
    if first and not first["premiereDate"]:
        first["premiereDate"] = premiered
    elif not first and premiered:
        normalized.append({"number": 1, "premiereDate": premiered, "endDate": None, "episodeCount": None})
    channel = show.get("webChannel") or show.get("network") or {}
    return {
        "tvmazeId": show["id"],
        "status": show["status"],
        "network": channel.get("name"),
        "url": show["url"],
        "checkedAt": checked_at,
        "seasons": sorted(normalized, key=lambda season: season["number"]),
    }


def refresh(config, previous, fetch=fetch_json, checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshots = {}
    errors = []
    for item in config["shows"]:
        show_id = item["id"]
        try:
            tvmaze_id = item["tvmazeId"]
            show = fetch(f"/shows/{tvmaze_id}")
            seasons = fetch(f"/shows/{tvmaze_id}/seasons")
            snapshot = make_snapshot(show, seasons, checked_at)
            if snapshot["tvmazeId"] != tvmaze_id:
                raise ValueError("TVmaze returned a different show ID")
            snapshots[show_id] = snapshot
            print(f"Updated {item['title']}", flush=True)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError, OSError) as error:
            message = f"{item['title']}: {error}"
            print(f"Warning: {message}", file=sys.stderr)
            errors.append({"id": show_id, "message": message})
            # A failed request must never erase a previously known premiere.
            old = previous.get("shows", {}).get(show_id)
            if old and old.get("tvmazeId") == item.get("tvmazeId"):
                snapshots[show_id] = old
    return {
        "source": "TVmaze",
        "sourceUrl": "https://www.tvmaze.com/api",
        "checkedAt": checked_at,
        "errors": errors,
        "shows": snapshots,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=TV_DIR / "shows.json")
    parser.add_argument("--output", type=Path, default=TV_DIR / "releases.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    previous = json.loads(args.output.read_text()) if args.output.exists() else {}
    result = refresh(config, previous)
    temporary = args.output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, args.output)
    if result["errors"]:
        print(f"{len(result['errors'])} show(s) could not be refreshed; previous data retained.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
