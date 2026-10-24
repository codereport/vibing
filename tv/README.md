# The watchlist

A compact, dark-mode static TV tracker at `/tv/`. Plain HTML, CSS, and JavaScript; no build, production backend, API keys, or runtime API requests. `releases.json` is a checked-in snapshot from the [TVmaze API](https://www.tvmaze.com/api). Like AI-FI, the published watchlist is read-only; editing and saving are available on localhost.

Run from this `tv` directory:

```sh
node scripts/dev-server.mjs
```

Open <http://localhost:8766/> (or <http://localhost:8766/tv/>). The server binds to loopback and serves only this site's assets plus its local save endpoint. Use an HTTP server; browsers block JSON fetches when opening the HTML directly from disk.

## Save and publish progress

1. Start the local server above and click season boxes to edit progress. The title opens the full progress editor.
2. Click **Save to repository** in the footer. This writes your current progress directly to `tv/shows.json`, preserving show identities, TVmaze IDs, titles, and notes.
3. Review `git diff -- tv/shows.json` from the repository root, then commit and push normally.

Progress edits are also kept in browser `localStorage` until you save them to the repository. Browser storage belongs to the exact host and port. To keep progress previously entered at `http://localhost:8000/tv/`, stop the old server and run `node scripts/dev-server.mjs 8000`, then open that same URL. You can also set `TV_PORT`.

**Export** downloads a `shows.json` backup. **Import** restores progress for matching shows locally; click **Save to repository** afterward to persist it to disk. Imports cannot add shows or replace catalog metadata.

If you use a different static preview server, **Save to repository** downloads JSON instead. Apply the downloaded file from this `tv` directory:

```sh
node scripts/import-progress.mjs --check ~/Downloads/shows.json
node scripts/import-progress.mjs ~/Downloads/shows.json
```

The importer also accepts JSON on stdin with `-`. It validates the entire export before writing, merges only progress for known shows, and replaces the file atomically. `--check` validates without writing.

On a published hostname, season boxes and titles are read-only and the import and repository-save controls are unavailable. The page always uses repository progress, ignores old browser overrides, and never writes progress to browser storage. Search, filters, tabs, the calendar, and JSON export still work. Publishing requires only the static files; the local server is never used in production.

## Progress and colors

- **Green — Watching:** actively watching the first season after `watchedThrough`.
- **Yellow — Ready:** the next unwatched season has premiered.
- **No highlight — Waiting:** caught up, a future premiere, or no date announced yet.
- **Done:** TVmaze says the series has ended and every listed season is finished. An ended series with unwatched seasons stays Active.

Active shows are grouped Watching, Ready, then Waiting. Waiting shows are sorted by premiere date, nearest first, with unannounced dates at the bottom.

The list has Series, Date, and Seasons columns. Premiere dates sit beside the season boxes so rows stay compact; on narrow screens dates sit beneath the series details. Row colors and season icons show progress without a separate status column.

Each row has up to five season boxes, aligned to the right: **✓ green = done**, **▶ gold = watching**, **○ outlined = not watched**. Until a season is finished, the boxes start at S1–S5; afterward they show the latest five known seasons. Shows with fewer than five seasons display only those seasons. If season metadata is missing, the row falls back to S1–S5 and preserves any recorded progress.

Locally, clicking a box cycles **not watched → watching → done → not watched**. Starting a later season marks all earlier seasons done. Clearing a completed season also clears later progress, so progress always follows watch order. Changes are saved in the browser immediately; use **Save to repository** to write them to disk. Use the title to adjust seasons outside the five visible boxes.

Locally, click a show title to set the last season finished and whether you’re watching the next one. Changing the finished season clears the watching checkbox; check it again if you’ve already started the following season. State updates immediately and is saved in local storage. A season becomes Ready on its premiere date using the viewer’s local calendar, including between weekly updates. Release dates describe the original premiere, not availability on a particular Canadian streaming service.

`watchedThrough` means full seasons finished, not the season currently being watched. The Wire starts at season 1 because its current season wasn’t supplied; adjust it in the editor. All three emoji-marked shows start Watching, including VisionQuest. The four shows described as waiting start caught up to their latest aired season at setup (Black Mirror 7, 3 Body Problem 1, Silo 3, Severance 2). Doctor Who uses the 2005 series containing **Blink, S3 E10**. The US Traitors listing numbers New Blood as season 5; Love Is Blind starts at season 11.

The Bear starts Ready at season 3, with seasons 1–2 marked finished and a note to watch seasons 3–4. Finishing season 3 queues season 4 automatically.

Million Dollar Secret, The Traitors UK, and Ted Lasso start Waiting, caught up through seasons 2, 4, and 4 respectively. The UK Traitors uses its own BBC listing, separate from New Blood. Mad Men starts Ready at season 1 with nothing watched.

Reacher starts Waiting for season 5, with seasons 1–4 marked finished. Reacher and The Traitors: New Blood have `seasonLimit: 5` to keep undated S6 placeholders out of their season lists, including after release refreshes. Adjust or remove this optional per-show limit to include later seasons.

Extrapolations starts Ready with season 1 unwatched. Finishing its only season moves it to Done.

The Capture and The Day of the Jackal start Waiting, caught up through seasons 3 and 1 respectively. The Agency uses the 2024 Paramount+ series and starts Ready at season 1 with nothing watched.

Ahsoka starts Waiting for season 2, with season 1 marked finished. Westworld starts Ready for season 4, with seasons 1–3 marked finished.

On localhost, existing browser progress takes priority over repository defaults. Save it to the repository to share updated progress across devices; published pages always show that committed snapshot.

## Weekly release updates

`.github/workflows/tv-releases.yml` runs every Monday at **12:17 UTC**, on manual dispatch, and when its config/updater changes on `main`. It fetches show status and all season premiere dates using fixed TVmaze IDs, then commits only `tv/releases.json`. No fuzzy title matching is performed by the scheduled job.

The workflow uses the built-in `GITHUB_TOKEN` with `contents: write` and `pages: write`; it needs no personal token or secrets. The repository currently publishes GitHub Pages from `main` at `/`. Since bot commits [do not trigger a branch-based Pages build](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), the workflow explicitly [requests a Pages build](https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build) after pushing the snapshot. The existing Pages publishing configuration is preserved.

After the files are committed and pushed to the default branch, the schedule becomes eligible to run. GitHub can delay scheduled runs; in public repositories it disables schedules after 60 days without repository activity. Use **Actions → Update TV premieres → Run workflow** for a manual refresh. This implementation does not change repository settings or enable workflows remotely.

The updater retries rate limits and temporary network/server errors. On partial failure it retains that show’s previous snapshot, publishes successful updates, displays a notice on the site, and reports a failed workflow run. Each show keeps its own successful check timestamp. Missing dates stay unknown; no premiere dates are guessed. The site also warns if its snapshot is over two weeks old.

To refresh locally:

```sh
python tv/scripts/update_releases.py
```

To add a show, add a unique `id`, `title`, verified `tvmazeId`, `watching`, and `watchedThrough` to `tv/shows.json`, then refresh. `note` is optional and appears in the progress editor. To verify an ID, search `https://api.tvmaze.com/search/shows?q=TITLE` and check the network and original premiere. This avoids confusing remakes and international editions.

## Checks

Requires Python 3.10+ and Node.js 22+. Production hosting requires neither.

```sh
python -m unittest discover -s tv/tests -p 'test_*.py'
node --test tv/tests/*.test.mjs
node --check tv/app.mjs
```

The checks cover status transitions, season-box ranges and click cycles, revival of ended shows, local-date boundaries, progress validation, atomic repository imports, local server saves and request restrictions, response normalization, rate-limit retries, partial failure recovery, and the initial snapshot. `.github/workflows/tv-checks.yml` runs them on tracker pull requests and pushes.

TVmaze-derived metadata in `releases.json` is attributed to [TVmaze](https://www.tvmaze.com/) and available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The site links to the source and license in its footer.
