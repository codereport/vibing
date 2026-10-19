import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_releases as updater

CHECKED = "2026-10-19T12:00:00+00:00"
SHOW = {"id": 42, "status": "Running", "url": "https://www.tvmaze.com/shows/42/example", "premiered": "2024-01-01", "webChannel": {"name": "Stream"}}
SEASONS = [{"number": 1, "premiereDate": "2024-01-01", "endDate": "2024-02-01", "episodeOrder": 8}]


class SnapshotTests(unittest.TestCase):
    def test_normalizes_seasons_and_ignores_specials(self):
        result = updater.make_snapshot(SHOW, [{"number": 2}, {"number": 0}, *SEASONS], CHECKED)
        self.assertEqual([s["number"] for s in result["seasons"]], [1, 2])
        self.assertEqual(result["network"], "Stream")
        self.assertEqual(result["seasons"][1]["premiereDate"], None)

    def test_series_premiere_fills_missing_first_season(self):
        for seasons in [[], [{"number": 1, "premiereDate": None}]]:
            with self.subTest(seasons=seasons):
                snapshot = updater.make_snapshot(SHOW, seasons, CHECKED)
                self.assertEqual(snapshot["seasons"][0]["premiereDate"], "2024-01-01")

    def test_existing_first_season_date_is_kept(self):
        result = updater.make_snapshot(SHOW, [{"number": 1, "premiereDate": "2024-01-02"}], CHECKED)
        self.assertEqual(result["seasons"][0]["premiereDate"], "2024-01-02")

    def test_invalid_date_is_rejected(self):
        with self.assertRaises(ValueError):
            updater.make_snapshot(SHOW, [{"number": 1, "premiereDate": "not-a-date"}], CHECKED)

    def test_network_fallback(self):
        result = updater.make_snapshot({**SHOW, "webChannel": None, "network": {"name": "BBC"}}, SEASONS, CHECKED)
        self.assertEqual(result["network"], "BBC")

    def test_unknown_premiere_does_not_invent_a_date(self):
        result = updater.make_snapshot({**SHOW, "premiered": None}, [], CHECKED)
        self.assertEqual(result["seasons"], [])


class RefreshTests(unittest.TestCase):
    def test_partial_failure_preserves_old_dates_and_updates_other_shows(self):
        old = {"tvmazeId": 41, "checkedAt": "2026-10-12", "seasons": [{"number": 2, "premiereDate": "2027-01-22"}]}
        config = {"shows": [{"id": "failed", "title": "Failed", "tvmazeId": 41}, {"id": "good", "title": "Good", "tvmazeId": 42}]}

        def fetch(path):
            if path.startswith("/shows/41"):
                raise URLError("Offline")
            return SEASONS if path.endswith("seasons") else SHOW

        result = updater.refresh(config, {"shows": {"failed": old}}, fetch=fetch, checked_at=CHECKED)
        self.assertEqual(result["shows"]["failed"], old)
        self.assertEqual(result["shows"]["good"]["checkedAt"], CHECKED)
        self.assertEqual(result["errors"][0]["id"], "failed")

    def test_retracted_dates_are_cleared_on_successful_refresh(self):
        config = {"shows": [{"id": "good", "title": "Good", "tvmazeId": 42}]}
        old = {"shows": {"good": {"tvmazeId": 42, "seasons": [{"number": 2, "premiereDate": "2027-01-22"}]}}}
        result = updater.refresh(config, old, fetch=lambda path: [*SEASONS, {"number": 2}] if path.endswith("seasons") else SHOW, checked_at=CHECKED)
        self.assertEqual(result["shows"]["good"]["seasons"][1]["premiereDate"], None)

    def test_wrong_show_id_does_not_replace_snapshot(self):
        config = {"shows": [{"id": "bad", "title": "Bad", "tvmazeId": 99}]}
        result = updater.refresh(config, {}, fetch=lambda path: SEASONS if path.endswith("seasons") else SHOW, checked_at=CHECKED)
        self.assertEqual(result["shows"], {})
        self.assertEqual(len(result["errors"]), 1)

    def test_changed_show_id_does_not_reuse_different_show_metadata(self):
        config = {"shows": [{"id": "changed", "title": "Changed", "tvmazeId": 99}]}
        def fail(path):
            raise URLError("Offline")
        result = updater.refresh(config, {"shows": {"changed": {"tvmazeId": 42}}}, fetch=fail, checked_at=CHECKED)
        self.assertNotIn("changed", result["shows"])


class RequestTests(unittest.TestCase):
    @patch.object(updater.time, "sleep")
    @patch.object(updater, "urlopen")
    def test_rate_limit_retries_then_succeeds(self, request, sleep):
        request.side_effect = [HTTPError("url", 429, "limited", {"Retry-After": "3"}, None), io.BytesIO(b'{"ok": true}')]
        self.assertEqual(updater.fetch_json("/shows/42"), {"ok": True})
        self.assertEqual(request.call_count, 2)
        self.assertIn(unittest.mock.call(3), sleep.call_args_list)

    @patch.object(updater.time, "sleep")
    @patch.object(updater, "urlopen")
    def test_server_errors_stop_after_retry_limit(self, request, sleep):
        request.side_effect = HTTPError("url", 503, "unavailable", {}, None)
        with self.assertRaises(HTTPError):
            updater.fetch_json("/shows/42", attempts=3)
        self.assertEqual(request.call_count, 3)

    @patch.object(updater.time, "sleep")
    @patch.object(updater, "urlopen")
    def test_not_found_is_not_retried(self, request, sleep):
        request.side_effect = HTTPError("url", 404, "not found", {}, None)
        with self.assertRaises(HTTPError):
            updater.fetch_json("/shows/42")
        self.assertEqual(request.call_count, 1)


class SeedTests(unittest.TestCase):
    def test_static_snapshot_covers_the_watchlist(self):
        config = json.loads((updater.TV_DIR / "shows.json").read_text())
        snapshot = json.loads((updater.TV_DIR / "releases.json").read_text())
        for show in config["shows"]:
            with self.subTest(show=show["id"]):
                release = snapshot["shows"][show["id"]]
                self.assertEqual(release["tvmazeId"], show["tvmazeId"])
                self.assertTrue(release["checkedAt"])
                for season in release["seasons"]:
                    updater.valid_date(season["premiereDate"])


if __name__ == "__main__":
    unittest.main()
