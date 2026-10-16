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

    def reply(self, value):
        def respond(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(request.full_url, self.manifest["api"])
            self.assertIn(request.get_header("X-bsz-referer"), self.manifest["urls"])
            return io.BytesIO(json.dumps({"success": True, "data": {"page_pv": value}}).encode())
        return respond

    def test_success_reads_without_incrementing_and_saves_all_articles(self):
        self.run_backup(self.reply(15))
        data = json.loads(self.output.read_text())
        self.assertEqual(data["counts"], dict.fromkeys(self.manifest["urls"], 15))
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


if __name__ == "__main__":
    unittest.main()
