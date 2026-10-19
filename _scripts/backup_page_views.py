"""Back up public article counters using read-only requests, without credentials."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def read_json(url, headers=None):
    request = Request(url, headers=headers or {}, method="GET")
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
            reason = str(error)
            error.close()
        except (URLError, TimeoutError, ConnectionError, IncompleteRead) as error:
            if attempt == 2:
                raise
            reason = str(error)
        # 所有请求均为只读 GET；仅重试临时网络错误，不重试无效数据。
        delay = 2 ** (attempt + 1)
        target = request.get_header("X-bsz-referer") or url
        print(f"Read failed for {target}: {reason}; retry {attempt + 1}/2 in {delay}s", file=sys.stderr)
        time.sleep(delay)


def snapshot(manifest, previous=None, reader=read_json):
    api = manifest["api"]
    if urlsplit(api).scheme != "https":
        raise ValueError("Statistics API must use HTTPS")
    site = urlsplit(manifest["site"])
    urls = sorted(set(manifest["urls"]))
    if not urls:
        raise ValueError("No published articles found; refusing to replace the backup")
    history = manifest.get("history")
    if history is None and previous and previous.get("site") == manifest["site"] and previous.get("history"):
        raise ValueError("Historical counts missing; preserving the previous backup")
    if history is not None:
        if not isinstance(history, dict) or history.get("site") != manifest["site"]:
            raise ValueError("Invalid historical statistics site")
        historical_total = history.get("site_pv")
        historical_counts = history.get("counts")
        if type(historical_total) is not int or historical_total < 0 or not isinstance(historical_counts, dict):
            raise ValueError("Invalid historical counts")
        if any(type(value) is not int or value < 0 for value in historical_counts.values()):
            raise ValueError("Invalid historical article count")
        if sum(historical_counts.values()) > historical_total:
            raise ValueError("Historical article counts exceed the site total")
    else:
        historical_counts = {}
    for url in set(urls) | set(historical_counts):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != site.netloc or parts.query or parts.fragment:
            raise ValueError(f"Invalid article URL: {url}")

    def count(url):
        result = reader(api, {"x-bsz-referer": url, "Cache-Control": "no-cache"})
        value = result.get("data", {}).get("page_pv")
        if result.get("success") is not True or type(value) is not int or value < 0:
            raise ValueError(f"Invalid count for {url}")
        site_value = result.get("data", {}).get("site_pv")
        if type(site_value) is not int or site_value < 0:
            raise ValueError(f"Invalid site count for {url}")
        return url, value, site_value

    with ThreadPoolExecutor(max_workers=3) as pool:
        values = list(pool.map(count, urls))
    counts = {url: value for url, value, _ in values}
    site_pv = max(total for _, _, total in values)
    if previous and previous.get("api") == api and previous.get("site") == manifest["site"]:
        for url, value in counts.items():
            if value < previous["counts"].get(url, 0):
                raise ValueError(f"Counter decreased for {url}; preserving the previous backup")
        if site_pv < previous.get("site_pv", 0):
            raise ValueError("Site counter decreased; preserving the previous backup")

    data = {
        "version": 3 if history is not None else 2,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "api": api,
        "site": manifest["site"],
        "site_pv": site_pv,
        "counts": counts,
    }
    if history is not None:
        # 保留原始实时计数与固定历史基数，恢复或重复备份时不会再次累加历史。
        data["history"] = history
    return data


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
