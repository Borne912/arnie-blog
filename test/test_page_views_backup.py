import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

spec = importlib.util.spec_from_file_location(
    "backup_page_views", Path(__file__).parents[1] / "_scripts/backup_page_views.py"
)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


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
        with patch.object(sys, "argv", argv), patch.object(backup, "urlopen", side_effect=response):
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
