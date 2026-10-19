# The watchlist

A compact, dark-mode static TV tracker at `/tv/`. Plain HTML, CSS, and JavaScript; no build, backend, API keys, or runtime API requests. `releases.json` is a checked-in snapshot from the [TVmaze API](https://www.tvmaze.com/api).

Run from the repository root:

```sh
python -m http.server 8000
```

Open <http://localhost:8000/tv/>. Use an HTTP server; browsers block JSON fetches when opening the HTML directly from disk.

## Progress and colors

- **Green — Watching:** actively watching the first season after `watchedThrough`.
- **Yellow — Ready:** the next unwatched season has premiered.
- **No highlight — Waiting:** caught up, a future premiere, or no date announced yet.
- **Done:** TVmaze says the series has ended and every listed season is finished. An ended series with unwatched seasons stays Active.

Active shows are grouped Watching, Ready, then Waiting. Waiting shows are sorted by premiere date, nearest first, with unannounced dates at the bottom.

Click a show title or pencil to set the last season finished and whether you’re watching the next one. Changing the finished season clears the watching checkbox; check it again if you’ve already started the following season. State updates immediately and is saved in local storage. A season becomes Ready on its premiere date using the viewer’s local calendar, including between weekly updates. Release dates describe the original premiere, not availability on a particular Canadian streaming service.

`watchedThrough` means full seasons finished, not the season currently being watched. The Wire starts at season 1 because its current season wasn’t supplied; adjust it in the editor. All three emoji-marked shows start Watching, including VisionQuest. The four shows described as waiting start caught up to their latest aired season at setup (Black Mirror 7, 3 Body Problem 1, Silo 3, Severance 2). Doctor Who uses the 2005 series containing **Blink, S3 E10**. The US Traitors listing numbers New Blood as season 5; Love Is Blind starts at season 11.

The Bear starts Ready at season 3, with seasons 1–2 marked finished and a note to watch seasons 3–4. Finishing season 3 queues season 4 automatically.

Million Dollar Secret, The Traitors UK, and Ted Lasso start Waiting, caught up through seasons 2, 4, and 4 respectively. The UK Traitors uses its own BBC listing, separate from New Blood. Mad Men starts Ready at season 1 with nothing watched.

Reacher starts Waiting for season 5, with seasons 1–4 marked finished.

The footer’s **Export** downloads a full `shows.json` backup. **Import** restores progress for matching shows on another browser; it does not alter show identities or add shows. Progress in a browser is private to that browser and does not automatically sync to the repository. To share updated defaults across devices, replace `tv/shows.json` with the export and commit it. A browser’s existing saved progress takes priority over repository defaults.

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
node --test tv/tests/model.test.mjs
node --check tv/app.mjs
```

The checks cover status transitions, revival of ended shows, local-date boundaries, progress validation, response normalization, rate-limit retries, partial failure recovery, and the initial snapshot. `.github/workflows/tv-checks.yml` runs them on tracker pull requests and pushes.

TVmaze-derived metadata in `releases.json` is attributed to [TVmaze](https://www.tvmaze.com/) and available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The site links to the source and license in its footer.
