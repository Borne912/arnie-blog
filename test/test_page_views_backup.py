import importlib.util
from datetime import datetime, timedelta, timezone
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

    def test_http_failure_logs_routing_headers_without_secrets_or_body(self):
        headers = {
            "Server": "cloudflare", "CF-Ray": "test-ray", "CF-Mitigated": "challenge",
            "Set-Cookie": "private-cookie", "Authorization": "private-token",
        }
        body = io.BytesIO(b"private response body")
        error = HTTPError(self.url, 403, "forbidden", headers, body)
        with patch.object(backup, "urlopen", side_effect=error) as opening:
            with self.assertRaises(HTTPError) as raised:
                backup.read_json(self.url)
        self.assertIs(raised.exception, error)
        self.assertEqual(opening.call_count, 1)
        self.assertEqual(body.tell(), 0)
        logged = self.stderr.getvalue()
        self.assertIn('"CF-Mitigated": "challenge"', logged)
        self.assertIn('"CF-Ray": "test-ray"', logged)
        self.assertNotIn("private", logged)
        self.assertNotIn("Authorization", logged)
        self.sleep.assert_not_called()

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

    def test_partial_progress_survives_failure_and_only_missing_articles_are_retried(self):
        first, second = self.manifest["urls"]
        calls = []
        reply = self.reply(15)

        def partial(request, timeout):
            url = request.get_header("X-bsz-referer")
            calls.append(url)
            if url == second:
                raise TimeoutError("temporarily unavailable")
            return reply(request, timeout)

        previous = self.output.read_bytes()
        with self.assertRaises(TimeoutError):
            self.run_backup(partial)
        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(calls.count(first), 1)
        self.assertEqual(calls.count(second), 4)
        checkpoint = self.output.with_name("page-views.pending.json")
        saved = json.loads(checkpoint.read_text())
        self.assertEqual(set(saved["samples"]), {first})
        observed = saved["samples"][first]["saved_at"]
        calls.clear()

        def recovered(request, timeout):
            calls.append(request.get_header("X-bsz-referer"))
            return self.reply(17)(request, timeout)

        self.run_backup(recovered)
        self.assertEqual(calls, [second])
        data = json.loads(self.output.read_text())
        self.assertEqual(data["counts"], {first: 15, second: 17})
        self.assertEqual(data["saved_at"], observed)
        self.assertEqual(data["observed_at"][first], observed)
        self.assertFalse(checkpoint.exists())

    def test_failed_article_can_recover_in_a_later_pass_without_rereading_successes(self):
        first, second = self.manifest["urls"]
        calls = []
        reply = self.reply(15)

        def respond(request, timeout):
            url = request.get_header("X-bsz-referer")
            calls.append(url)
            if url == second and calls.count(second) == 1:
                raise TimeoutError("try a later pass")
            return reply(request, timeout)

        self.run_backup(respond)
        self.assertEqual(calls.count(first), 1)
        self.assertEqual(calls.count(second), 2)
        self.assertEqual(len(json.loads(self.output.read_text())["counts"]), 2)

    def test_old_foreign_and_decreased_checkpoint_samples_are_not_reused(self):
        first = self.manifest["urls"][0]
        checkpoint = self.output.with_name("page-views.pending.json")
        valid = {
            "manifest": backup.checkpoint_context(self.manifest),
            "samples": {first: {"page_pv": 12, "site_pv": 100, "saved_at": datetime.now(timezone.utc).isoformat()}},
        }
        for change in ("old", "foreign", "decreased", "invalid", "future"):
            saved = json.loads(json.dumps(valid))
            sample = saved["samples"][first]
            if change == "old":
                sample["saved_at"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
            elif change == "foreign":
                saved["manifest"]["api"] = "https://other.example.test/api"
            elif change == "decreased":
                sample["page_pv"] = 9
            elif change == "future":
                sample["saved_at"] = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
            else:
                sample["page_pv"] = True
            with self.subTest(change=change):
                checkpoint.write_text(json.dumps(saved))
                self.assertEqual(backup.load_checkpoint(checkpoint, self.manifest, self.previous), {})

    def test_permanent_http_error_does_not_trigger_later_passes(self):
        self.manifest["urls"] = self.manifest["urls"][:1]
        previous = self.output.read_bytes()
        calls = []

        def forbidden(request, timeout):
            calls.append(request)
            raise HTTPError(request.full_url, 403, "forbidden", {}, None)

        with self.assertRaises(HTTPError):
            self.run_backup(forbidden)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.output.read_bytes(), previous)

    def test_collection_budget_prevents_starting_more_requests(self):
        with self.assertRaisesRegex(TimeoutError, "time budget"):
            backup.snapshot(self.manifest, self.previous, reader=lambda *args: self.fail("Unexpected request"), deadline=0)

    def test_recovery_pass_respects_server_retry_after(self):
        self.manifest["urls"] = self.manifest["urls"][:1]
        calls = []

        def reader(url, headers):
            calls.append(url)
            if len(calls) == 1:
                raise HTTPError(url, 429, "rate limit", {"Retry-After": "120"}, None)
            return {"success": True, "data": {"page_pv": 15, "site_pv": 100}}

        with patch("time.sleep") as sleep:
            data = backup.snapshot(self.manifest, self.previous, reader=reader)
        self.assertIn(call(120), sleep.call_args_list)
        self.assertEqual(len(calls), 2)
        self.assertEqual(data["counts"][self.manifest["urls"][0]], 15)

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
