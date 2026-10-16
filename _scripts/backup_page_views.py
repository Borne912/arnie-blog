"""Back up public article counters using read-only requests, without credentials."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def read_json(url, headers=None):
    request = Request(url, headers=headers or {}, method="GET")
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def snapshot(manifest, previous=None, reader=read_json):
    api = manifest["api"]
    if urlsplit(api).scheme != "https":
        raise ValueError("Statistics API must use HTTPS")
    site = urlsplit(manifest["site"])
    urls = sorted(set(manifest["urls"]))
    if not urls:
        raise ValueError("No published articles found; refusing to replace the backup")
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != site.netloc or parts.query or parts.fragment:
            raise ValueError(f"Invalid article URL: {url}")

    def count(url):
        result = reader(api, {"x-bsz-referer": url, "Cache-Control": "no-cache"})
        value = result.get("data", {}).get("page_pv")
        if result.get("success") is not True or type(value) is not int or value < 0:
            raise ValueError(f"Invalid count for {url}")
        return url, value

    with ThreadPoolExecutor(max_workers=3) as pool:
        counts = dict(pool.map(count, urls))
    if previous and previous.get("api") == api and previous.get("site") == manifest["site"]:
        for url, value in counts.items():
            if value < previous["counts"].get(url, 0):
                raise ValueError(f"Counter decreased for {url}; preserving the previous backup")

    return {
        "version": 1,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "api": api,
        "site": manifest["site"],
        "counts": counts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Published manifest URL or local JSON file")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.manifest.startswith("https://"):
        manifest = read_json(args.manifest)
    else:
        manifest = json.loads(Path(args.manifest).read_text())
    if not manifest.get("enabled") or not manifest.get("api"):
        print("API-mode page views are disabled; no backup changes.")
        return
    previous = json.loads(args.output.read_text()) if args.output.exists() else None
    data = snapshot(manifest, previous)
    # 所有查询及校验成功后才替换文件，失败或计数下降时保留上一次成功备份。
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, args.output)
    print(f"Backed up {len(data['counts'])} article counters at {data['saved_at']}")


if __name__ == "__main__":
    main()
