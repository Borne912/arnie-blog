import importlib.util
from http.client import IncompleteRead
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import call, patch
from urllib.error import HTTPError, URLError

spec = importlib.util.spec_from_file_location(
    "backup_page_views", Path(__file__).parents[1] / "_scripts/backup_page_views.py"
)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class ReadJsonTests(unittest.TestCase):
    def setUp(self):
        self.url = "https://stats.example.test/api"
        self.headers = {"x-bsz-referer": "https://stile.cc/first/", "Cache-Control": "no-cache"}
        self.sleep = self.enterContext(patch("time.sleep"))
        self.stderr = self.enterContext(patch("sys.stderr", new_callable=io.StringIO))

    def response(self):
        return io.BytesIO(b'{"success": true, "data": {"page_pv": 15, "site_pv": 100}}')

    def test_transient_network_errors_recover_without_incrementing(self):
        for error in (TimeoutError("read timed out"), URLError("unavailable"), ConnectionResetError("reset"), IncompleteRead(b"{")):
            with self.subTest(error=error), patch.object(backup, "urlopen", side_effect=[error, self.response()]) as opening:
                self.sleep.reset_mock()
                data = backup.read_json(self.url, self.headers)
                self.assertEqual(data["data"]["page_pv"], 15)
                self.assertEqual(opening.call_count, 2)
                self.sleep.assert_called_once_with(2)
                for request_call in opening.call_args_list:
                    request = request_call.args[0]
                    self.assertEqual(request.full_url, self.url)
                    self.assertEqual(request.get_method(), "GET")
                    self.assertEqual(request.get_header("X-bsz-referer"), self.headers["x-bsz-referer"])
        self.assertIn(self.headers["x-bsz-referer"], self.stderr.getvalue())

    def test_timeout_while_reading_response_is_retried(self):
        response = self.response()
        with patch.object(response, "read", side_effect=TimeoutError("body timed out")), patch.object(
            backup, "urlopen", side_effect=[response, self.response()]
        ) as opening:
            self.assertTrue(backup.read_json(self.url)["success"])
        self.assertEqual(opening.call_count, 2)

    def test_temporary_http_errors_are_retried(self):
        for status in (408, 429, 500, 502, 503, 504):
            error = HTTPError(self.url, status, "temporary failure", {}, None)
            with self.subTest(status=status), patch.object(backup, "urlopen", side_effect=[error, self.response()]) as opening:
                self.assertTrue(backup.read_json(self.url)["success"])
                self.assertEqual(opening.call_count, 2)

    def test_permanent_http_errors_fail_without_retrying(self):
        for status in (400, 401, 403, 404):
            error = HTTPError(self.url, status, "permanent failure", {}, None)
            with self.subTest(status=status), patch.object(backup, "urlopen", side_effect=error) as opening:
                with self.assertRaises(HTTPError):
                    backup.read_json(self.url)
                self.assertEqual(opening.call_count, 1)
        self.sleep.assert_not_called()

    def test_persistent_timeout_stops_after_three_attempts(self):
        error = TimeoutError("still unavailable")
        with patch.object(backup, "urlopen", side_effect=error) as opening:
            with self.assertRaises(TimeoutError) as raised:
                backup.read_json(self.url)
        self.assertIs(raised.exception, error)
        self.assertEqual(opening.call_count, 3)
        self.assertEqual(self.sleep.call_args_list, [call(2), call(4)])

    def test_invalid_json_fails_without_retrying(self):
        with patch.object(backup, "urlopen", return_value=io.BytesIO(b"not json")) as opening:
            with self.assertRaises(json.JSONDecodeError):
                backup.read_json(self.url)
        self.assertEqual(opening.call_count, 1)
        self.sleep.assert_not_called()


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "enabled": True,
            "api": "https://stats.example.test/api",
            "site": "https://stile.cc",
            "urls": ["https://stile.cc/first/", "https://stile.cc/second/"],
        }
        self.previous = {
            "api": self.manifest["api"],
            "site": self.manifest["site"],
            "counts": dict.fromkeys(self.manifest["urls"], 10),
        }
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.output = Path(self.folder.name) / "page-views.json"
        self.output.write_text(json.dumps(self.previous))
        self.manifest_file = Path(self.folder.name) / "manifest.json"

    def run_backup(self, response):
        self.manifest_file.write_text(json.dumps(self.manifest))
        argv = ["backup", "--manifest", str(self.manifest_file), "--output", str(self.output)]
        with patch.object(sys, "argv", argv), patch.object(backup, "urlopen", side_effect=response), patch("time.sleep"):
            backup.main()

    def reply(self, value, site_value=100):
        def respond(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.full_url, self.manifest["api"])
            self.assertIn(request.get_header("X-bsz-referer"), self.manifest["urls"])
            return io.BytesIO(json.dumps({"success": True, "data": {"page_pv": value, "site_pv": site_value}}).encode())
        return respond

    def test_success_reads_without_incrementing_and_saves_all_articles(self):
        self.run_backup(self.reply(15))
        data = json.loads(self.output.read_text())
        self.assertEqual(data["counts"], dict.fromkeys(self.manifest["urls"], 15))
        self.assertEqual(data["site_pv"], 100)
        self.assertIn("saved_at", data)

    def test_network_failure_preserves_last_good_file(self):
        previous = self.output.read_bytes()
        with self.assertRaises(URLError):
            self.run_backup(URLError("unavailable"))
        self.assertEqual(self.output.read_bytes(), previous)

    def test_exhausted_retries_preserve_last_good_file(self):
        self.manifest["urls"] = self.manifest["urls"][:1]
        previous = self.output.read_bytes()
        for error in (TimeoutError("unavailable"), HTTPError(self.manifest["api"], 503, "unavailable", {}, None)):
            with self.subTest(error=error), self.assertRaises(type(error)):
                self.run_backup(error)
            self.assertEqual(self.output.read_bytes(), previous)
            self.assertFalse(self.output.with_suffix(".tmp").exists())

    def test_invalid_counts_preserve_last_good_file(self):
        previous = self.output.read_bytes()
        for value in (None, "12", -1, 3.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_backup(self.reply(value))
            self.assertEqual(self.output.read_bytes(), previous)

    def test_server_reset_does_not_overwrite_higher_counts(self):
        previous = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "Counter decreased"):
            self.run_backup(self.reply(0))
        self.assertEqual(self.output.read_bytes(), previous)

    def test_missing_article_list_cannot_erase_backup(self):
        self.manifest["urls"] = []
        previous = self.output.read_bytes()
        with self.assertRaises(ValueError):
            self.run_backup(self.reply(15))
        self.assertEqual(self.output.read_bytes(), previous)

    def test_invalid_site_count_preserves_last_good_file(self):
        previous = self.output.read_bytes()
        for value in (None, "100", -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_backup(self.reply(15, site_value=value))
            self.assertEqual(self.output.read_bytes(), previous)

    def test_site_counter_reset_preserves_last_good_file(self):
        self.previous["site_pv"] = 100
        self.output.write_text(json.dumps(self.previous))
        previous = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "Site counter decreased"):
            self.run_backup(self.reply(15, site_value=0))
        self.assertEqual(self.output.read_bytes(), previous)

    def test_foreign_urls_are_rejected_before_requesting(self):
        self.manifest["urls"] = ["https://other.example.test/private/"]
        with self.assertRaisesRegex(ValueError, "Invalid article URL"):
            self.run_backup(lambda *args: self.fail("Unexpected network request"))

    def test_disabled_statistics_leave_backup_unchanged(self):
        self.manifest["enabled"] = False
        previous = self.output.read_bytes()
        self.run_backup(lambda *args: self.fail("Unexpected network request"))
        self.assertEqual(self.output.read_bytes(), previous)

    def test_first_backup_accepts_zero_counts(self):
        self.output.unlink()
        self.run_backup(self.reply(0))
        self.assertEqual(json.loads(self.output.read_text())["counts"], dict.fromkeys(self.manifest["urls"], 0))

    def test_history_is_backed_up_without_adding_it_to_live_counters(self):
        history = {
            "site": self.manifest["site"],
            "source": "Google Analytics 4",
            "site_pv": 40,
            "counts": dict(zip(self.manifest["urls"], (7, 11))),
        }
        self.manifest["history"] = history
        for _ in range(2):
            self.run_backup(self.reply(15))
            data = json.loads(self.output.read_text())
            self.assertEqual(data["version"], 3)
            self.assertEqual(data["history"], history)
            self.assertEqual(data["site_pv"], 100)
            self.assertEqual(data["counts"], dict.fromkeys(self.manifest["urls"], 15))

    def test_missing_history_cannot_erase_recovered_data(self):
        self.previous["history"] = {"site_pv": 40}
        self.output.write_text(json.dumps(self.previous))
        previous = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "Historical counts missing"):
            self.run_backup(lambda *args: self.fail("Unexpected network request"))
        self.assertEqual(self.output.read_bytes(), previous)

    def test_invalid_history_is_rejected_without_replacing_backup(self):
        previous = self.output.read_bytes()
        valid = {"site": self.manifest["site"], "site_pv": 40, "counts": {self.manifest["urls"][0]: 7}}
        for change in (
            {"site": "https://other.example.test"},
            {"site_pv": True},
            {"site_pv": 6},
            {"counts": {self.manifest["urls"][0]: -1}},
            {"counts": {"https://other.example.test/": 7}},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.manifest["history"] = {**valid, **change}
                self.run_backup(lambda *args: self.fail("Unexpected network request"))
            self.assertEqual(self.output.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
