import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("submit_indexnow", Path(__file__).parents[1] / "_scripts/submit_indexnow.py")
indexnow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indexnow)


def sitemap(*urls):
    return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{url}</loc></url>' for url in urls) + '</urlset>'


class IndexNowTests(unittest.TestCase):
    def test_payload_only_contains_unique_same_host_canonical_urls(self):
        result = indexnow.payload_for("https://stile.cc", "a" * 32, sitemap("https://stile.cc/", "https://stile.cc/", "https://stile.cc/文章/"))
        self.assertEqual(result["host"], "stile.cc")
        self.assertEqual(result["keyLocation"], "https://stile.cc/indexnow-key.txt")
        self.assertEqual(result["urlList"], ["https://stile.cc/", "https://stile.cc/%E6%96%87%E7%AB%A0/"])

    def test_invalid_sitemaps_and_keys_are_rejected(self):
        for xml in (sitemap(), sitemap("https://other.example.test/"), sitemap("https://stile.cc/?query=1"), '<sitemapindex/>'):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                indexnow.payload_for("https://stile.cc", "a" * 32, xml)
        with self.assertRaises(ValueError):
            indexnow.payload_for("https://stile.cc", "short", sitemap("https://stile.cc/"))

    def run_notification(self, replies):
        with tempfile.TemporaryDirectory() as folder:
            key_file = Path(folder) / "indexnow-key.txt"
            key_file.write_text("a" * 32)
            argv = ["indexnow", "--site", "https://stile.cc", "--key-file", str(key_file)]
            with patch.object(sys, "argv", argv), patch.object(indexnow, "request", side_effect=replies) as request:
                indexnow.main()
                return request.call_args_list

    def test_only_submits_after_the_published_key_has_been_verified(self):
        for status in (200, 202):
            with self.subTest(status=status):
                calls = self.run_notification([(200, sitemap("https://stile.cc/").encode()), (200, b"a" * 32), (status, b"")])
                self.assertEqual(calls[0].args, ("https://stile.cc/sitemap.xml",))
                self.assertEqual(calls[1].args, ("https://stile.cc/indexnow-key.txt",))
                self.assertEqual(calls[2].args[0], indexnow.ENDPOINT)
                self.assertEqual(calls[2].args[1]["urlList"], ["https://stile.cc/"])

    def test_key_mismatch_prevents_any_submission(self):
        with self.assertRaisesRegex(ValueError, "Published ownership key"):
            self.run_notification([(200, sitemap("https://stile.cc/").encode()), (200, b"another-key")])


if __name__ == "__main__":
    unittest.main()
