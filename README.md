# Vibing projects

The root `index.html` is a static project directory. On screens up to 768px wide it shows titles only; desktop also shows descriptions. Icons occupy a fixed-width column, titles align to the left, and titles and descriptions stay on one line. On narrow desktop/tablet screens, the table can scroll horizontally to keep the full text available.

## Automatic project order

Projects are sorted newest first by their latest commit, using each row's source:

- `data-project-path="ai-fi"` tracks commits to that folder in this repository. Separate paths such as `survivor/50` and `survivor/51` are tracked independently.
- `data-project-repo="codereport/cuda-x-docs"` tracks commits on an external GitHub repository's default branch. Add `data-project-path` as well to track only a particular file or folder there.
- All current projects have a source. Future links without a source repository stay at the bottom in their existing order.

`.github/workflows/projects.yml` refreshes the checked-in homepage after pushes to `main`, daily at 06:43 UTC to pick up external repository changes, and on manual dispatch. It commits only when dates or order change, then explicitly requests a [GitHub Pages build](https://docs.github.com/en/rest/pages/pages#request-a-github-pages-build), since [token-generated pushes do not start another workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow). It uses the built-in GitHub token with `contents: write` and `pages: write`; no extra secrets or changes to Pages settings are needed. The automation becomes active when these files are pushed to `main`.

Dates are stored in `data-updated` attributes, so sorting needs no browser API requests or JavaScript. If GitHub is unavailable, external projects retain their previous dates. Equal dates keep their existing order. Homepage-only changes and sorting commits do not affect project dates. External commits are picked up on the next refresh; they cannot trigger this repository's push workflow themselves.

Refresh locally with Python 3.10+ and full Git history:

```sh
python3 scripts/update_projects.py
python3 scripts/update_projects.py --offline # keep cached external dates
python3 -m unittest discover -s tests -p 'test_*.py'
```

To add a project, add its row to `index.html` with the appropriate source attribute, then run the updater after the project files have been committed.
