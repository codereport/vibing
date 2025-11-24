# CityStrides Leaderboard Tracker

This project tracks the top 50 runners on CityStrides and generates a static HTML leaderboard with weekly changes.

## Setup

1.  Ensure you have `uv` installed.
2.  Install dependencies:
    ```bash
    uv sync
    ```

## Usage

Run the update script to fetch the latest data and generate the website:

```bash
uv run update_leaderboard.py
```

This will:
1.  Read `leaderboard_data.json` (if it exists) to get the previous week's stats.
2.  Fetch the current top 50 runners from CityStrides.
3.  Calculate the change in rank and streets run.
4.  Save the new data to `leaderboard_data.json`.
5.  Generate `index.html`.

## Automation

To run this weekly (e.g., every Sunday at 8 PM), add a cron job:

```bash
0 20 * * 0 cd /path/to/citystride_ranking && uv run update_leaderboard.py
```
