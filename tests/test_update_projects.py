from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from urllib.error import URLError

from scripts.update_projects import ROWS, RowAttributes, sort_projects


def row(name, source="", updated=""):
    cached = f' data-updated="{updated}"' if updated else ""
    return (
        f'<tr {source}{cached} onclick="window.location.href=\'{name}/\'">'
        f'<td class="project-name">{name}</td>'
        f'<td class="project-desc">Description for {name}</td></tr>'
    )


def page(*rows):
    return '<header>Before</header><table class="projects-table">' + "\n".join(rows) + '</table><footer>After</footer>'


class ProjectOrderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Project order tests")
        self.git("config", "user.email", "tests@example.com")
        self.commit("old/index.html", "2025-01-01T00:00:00Z")
        self.commit("new/index.html", "2025-02-01T00:00:00Z")

    def git(self, *args, env=None):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True, env=env).strip()

    def commit(self, path, date):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(date)
        self.git("add", path)
        self.git("commit", "--quiet", "-m", f"Update {path}", env={
            **os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date,
        })

    def sort(self, html, fetch_commit=None):
        return sort_projects(html, self.root, fetch_commit)

    def test_actual_folder_commits_control_order_and_homepage_commits_do_not(self):
        html = page(row("old", 'data-project-path="old"'), row("new", 'data-project-path="new"'))
        self.commit("index.html", "2025-03-01T00:00:00Z")
        first = self.sort(html)
        self.assertLess(first.index('>new</td>'), first.index('>old</td>'))
        self.assertIn('data-updated="2025-01-01T00:00:00Z"', first)
        self.commit("old/data.json", "2025-04-01T00:00:00Z")
        second = self.sort(first)
        self.assertLess(second.index('>old</td>'), second.index('>new</td>'))
        self.assertEqual(self.sort(second), second)

    def test_survivor_seasons_have_separate_dates(self):
        self.commit("survivor/50/index.html", "2025-03-01T00:00:00Z")
        self.commit("survivor/51/index.html", "2025-04-01T00:00:00Z")
        result = self.sort(page(
            row("s50", 'data-project-path="survivor/50"'),
            row("s51", 'data-project-path="survivor/51"'),
        ))
        dates = [RowAttributes(item).attrs["data-updated"] for item in ROWS.findall(result)]
        self.assertEqual(dates, ["2025-04-01T00:00:00Z", "2025-03-01T00:00:00Z"])

    def test_external_commit_uses_repository_and_optional_path(self):
        calls = []

        def fetch(repo, path):
            calls.append((repo, path))
            return "2025-03-01T01:00:00+02:00"

        result = self.sort(page(
            row("new", 'data-project-path="new"'),
            row("remote", 'data-project-repo="owner/repo" data-project-path="linked/file.html"'),
        ), fetch)
        self.assertEqual(calls, [("owner/repo", "linked/file.html")])
        self.assertIn('data-updated="2025-02-28T23:00:00Z"', result)
        self.assertLess(result.index('>remote</td>'), result.index('>new</td>'))

    def test_network_failure_preserves_cached_date_and_all_rows(self):
        def unavailable(*args):
            raise URLError("GitHub is unavailable")

        result = self.sort(page(
            row("new", 'data-project-path="new"'),
            row("remote", 'data-project-repo="owner/repo"', "2025-03-01T00:00:00Z"),
        ), unavailable)
        self.assertEqual(len(ROWS.findall(result)), 2)
        self.assertLess(result.index('>remote</td>'), result.index('>new</td>'))
        self.assertIn('data-updated="2025-03-01T00:00:00Z"', result)

    def test_offline_mode_retains_external_dates(self):
        html = page(
            row("new", 'data-project-path="new"'),
            row("remote", 'data-project-repo="owner/repo"', "2025-03-01T00:00:00Z"),
        )
        result = self.sort(html)
        self.assertLess(result.index('>remote</td>'), result.index('>new</td>'))

    def test_invalid_api_date_preserves_cache(self):
        html = page(row("remote", 'data-project-repo="owner/repo"', "2025-03-01T00:00:00Z"))
        result = self.sort(html, lambda *args: "invalid date")
        self.assertIn('data-updated="2025-03-01T00:00:00Z"', result)

    def test_equal_dates_and_undated_links_keep_their_relative_order(self):
        html = page(
            row("unknown-first"),
            row("tie-first", 'data-project-path="new"'),
            row("unknown-second"),
            row("tie-second", 'data-project-path="new"'),
        )
        result = self.sort(html)
        names = [RowAttributes(item).attrs["onclick"] for item in ROWS.findall(result)]
        self.assertEqual(names, [f"window.location.href='{name}/'" for name in [
            "tie-first", "tie-second", "unknown-first", "unknown-second",
        ]])
        for name in ["unknown-first", "tie-first", "unknown-second", "tie-second"]:
            self.assertIn(f'<td class="project-desc">Description for {name}</td>', result)
        self.assertTrue(result.startswith('<header>Before</header>'))
        self.assertTrue(result.endswith('<footer>After</footer>'))

    def test_missing_local_history_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "No Git history"):
            self.sort(page(row("missing", 'data-project-path="missing"')))

    def test_shallow_history_is_rejected(self):
        (self.root / ".git/shallow").write_text(self.git("rev-parse", "HEAD") + "\n")
        with self.assertRaisesRegex(ValueError, "Full Git history"):
            self.sort(page(row("new", 'data-project-path="new"')))

    def test_missing_or_empty_table_is_an_error(self):
        for html in ["<main>No projects table</main>", page()]:
            with self.subTest(html=html), self.assertRaises(ValueError):
                self.sort(html)


if __name__ == "__main__":
    unittest.main()
