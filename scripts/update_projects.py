#!/usr/bin/env python3
"""Sort the homepage by project commit dates, preserving the static HTML."""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
TABLE = re.compile(r'(<table class="projects-table">)(.*?)(</table>)', re.DOTALL)
ROWS = re.compile(r'<tr\b[^>]*>.*?</tr>', re.DOTALL)


class RowAttributes(HTMLParser):
    def __init__(self, row):
        super().__init__()
        self.attrs = {}
        self.feed(row)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.attrs = dict(attrs)


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()


def latest_github_commit(repo, path=None):
    query = urlencode({"per_page": 1, **({"path": path} if path else {})})
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "vibing-project-order",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/repos/{repo}/commits?{query}", headers=headers)
    with urlopen(request, timeout=20) as response:
        commits = json.load(response)
    if not commits:
        raise ValueError(f"No commits found for {repo}/{path or ''}")
    return commits[0]["commit"]["committer"]["date"]


def timestamp(date):
    return datetime.fromisoformat(date.replace("Z", "+00:00")).timestamp()


def sort_projects(html, root=ROOT, fetch_commit=latest_github_commit):
    if git(root, "rev-parse", "--is-shallow-repository") == "true":
        raise ValueError("Full Git history is required; use fetch-depth: 0 or git fetch --unshallow.")
    table = TABLE.search(html)
    if table is None:
        raise ValueError("Homepage projects table was not found.")
    rows = ROWS.findall(table[2])
    if not rows:
        raise ValueError("Homepage projects table has no rows.")

    projects = []
    for row in rows:
        attrs = RowAttributes(row).attrs
        date = attrs.get("data-updated")
        path = attrs.get("data-project-path")
        repo = attrs.get("data-project-repo")
        if repo:
            if fetch_commit is not None:
                try:
                    fetched_date = fetch_commit(repo, path)
                    timestamp(fetched_date)
                    date = fetched_date
                except (URLError, TimeoutError, ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
                    print(f"Warning: keeping cached date for {repo}: {error}", file=sys.stderr)
        elif path:
            date = git(root, "log", "-1", "--format=%cI", "--", path)
            if not date:
                raise ValueError(f"No Git history found for local project: {path}")

        updated = timestamp(date) if date else 0
        if date:
            canonical = datetime.fromtimestamp(updated, timezone.utc).isoformat().replace("+00:00", "Z")
            row = re.sub(r'\sdata-updated="[^"]*"', '', row, count=1)
            row = row.replace("<tr", f'<tr data-updated="{canonical}"', 1)
        projects.append((updated, row))

    # Python's stable sort preserves the order of ties and undated external links.
    projects.sort(key=lambda project: project[0], reverse=True)
    body = "\n            " + "\n            ".join(row for _, row in projects) + "\n        "
    return html[:table.start(2)] + body + html[table.end(2):]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Keep cached dates for external GitHub projects.")
    args = parser.parse_args()
    homepage = ROOT / "index.html"
    original = homepage.read_text()
    updated = sort_projects(original, fetch_commit=None if args.offline else latest_github_commit)
    if updated != original:
        homepage.write_text(updated)
        print("Updated homepage project order.")
    else:
        print("Homepage project order is current.")


if __name__ == "__main__":
    main()
