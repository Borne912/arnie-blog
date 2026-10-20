import copy
from hashlib import md5
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("page_views_seed", Path(__file__).parents[1] / "_scripts/prepare_page_views_seed.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "version": 3,
            "site": "https://stile.cc",
            "api": "https://busuanzi.9420.ltd/api",
            "site_pv": 12,
            "counts": {"https://stile.cc/tools/%E6%B5%8B%E8%AF%95/": 7},
            "history": {"site_pv": 4453, "counts": {"https://stile.cc/tools/%E6%B5%8B%E8%AF%95/": 54}},
        }

    def test_only_raw_counts_are_imported(self):
        args = seed.command(self.data, "https://stile.cc")
        self.assertEqual(args[5], "12")
        self.assertEqual(args[-1], "7")
        self.assertNotIn("4453", args)
        self.assertNotIn("54", args)

    def test_hashes_decoded_chinese_path_as_go_does(self):
        args = seed.command(self.data, "https://stile.cc")
        expected = md5("/tools/测试/".encode(), usedforsecurity=False).hexdigest()[8:24]
        self.assertEqual(args[-2], expected)
        decoded = copy.deepcopy(self.data)
        decoded["counts"] = {"https://stile.cc/tools/测试/": 7}
        self.assertEqual(args, seed.command(decoded, "https://stile.cc"))

    def test_rejects_foreign_sites_and_ambiguous_urls(self):
        for url in ("http://stile.cc/a/", "https://other.test/a/", "https://stile.cc/a/?x=1", "https://stile.cc/a/#section", "https://user@stile.cc/a/"):
            with self.subTest(url=url):
                self.data["counts"] = {url: 1}
                with self.assertRaises(ValueError):
                    seed.command(self.data, "https://stile.cc")

    def test_rejects_invalid_or_missing_raw_counts(self):
        for value in (True, -1, 1.5, "7", None, 2**53):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["site_pv"] = value
                with self.assertRaises(ValueError):
                    seed.command(data, "https://stile.cc")
                data = copy.deepcopy(self.data)
                data["counts"] = {"https://stile.cc/a/": value}
                with self.assertRaises(ValueError):
                    seed.command(data, "https://stile.cc")
        self.data.pop("site_pv")
        with self.assertRaises(ValueError):
            seed.command(self.data, "https://stile.cc")

    def test_rejects_duplicate_decoded_paths(self):
        self.data["counts"]["https://stile.cc/tools/测试/"] = 4
        with self.assertRaises(ValueError):
            seed.command(self.data, "https://stile.cc")

    def test_rejects_wrong_backup_version_site_or_totals(self):
        for update in ({"version": 1}, {"site": "https://other.test"}, {"site_pv": 6}, {"counts": {}}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                seed.command({**self.data, **update}, "https://stile.cc")

    def test_resp_lengths_use_utf8_bytes(self):
        self.assertEqual(seed.encode_resp(["SET", "中文", "7"]), b"*3\r\n$3\r\nSET\r\n$6\r\n\xe4\xb8\xad\xe6\x96\x87\r\n$1\r\n7\r\n")


if __name__ == "__main__":
    unittest.main()
