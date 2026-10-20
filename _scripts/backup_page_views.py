"""Back up public article counters using read-only requests, without credentials."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.client import IncompleteRead
import json
import math
import os
from pathlib import Path
import sys
from threading import Lock
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


TRANSIENT_HTTP = (408, 429, 500, 502, 503, 504)
NETWORK_ERRORS = (URLError, TimeoutError, ConnectionError, IncompleteRead)


def is_transient(error):
    return error.code in TRANSIENT_HTTP if isinstance(error, HTTPError) else isinstance(error, NETWORK_ERRORS)


def retry_after(error):
    header = error.headers.get("Retry-After") if isinstance(error, HTTPError) and error.headers else None
    if header is None:
        return 0
    try:
        delay = float(header)
    except (TypeError, ValueError):
        try:
            delay = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return 0
    return max(0, delay) if math.isfinite(delay) else 0


def read_json(url, headers=None, *, attempts=3, timeout=20):
    request = Request(url, headers=headers or {}, method="GET")
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in TRANSIENT_HTTP or attempt == attempts - 1:
                raise
            delay = max(2 ** (attempt + 1), retry_after(error))
            if delay > 60:
                raise
            reason = str(error)
            error.close()
        except NETWORK_ERRORS as error:
            if attempt == attempts - 1:
                raise
            reason = str(error)
            delay = 2 ** (attempt + 1)
        # 所有请求均为只读 GET；仅重试临时网络错误，不重试无效数据。
        target = request.get_header("X-bsz-referer") or url
        print(f"Read failed for {target}: {reason}; retry {attempt + 1}/{attempts - 1} in {delay}s", file=sys.stderr)
        time.sleep(delay)


def snapshot(manifest, previous=None, reader=read_json, *, samples=None, on_progress=None, deadline=None):
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

    samples = {} if samples is None else samples
    deadline = time.monotonic() + 420 if deadline is None else deadline
    same_source = previous and previous.get("api") == api and previous.get("site") == manifest["site"]
    pacing = Lock()
    next_request = 0

    def count(url):
        nonlocal next_request
        # 最多两路并发，启动间隔至少半秒，避免批量请求集中冲击公共接口。
        with pacing:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Counter collection time budget exhausted")
            time.sleep(min(max(0, next_request - time.monotonic()), remaining))
            next_request = time.monotonic() + 0.5
        result = reader(api, {"x-bsz-referer": url, "Cache-Control": "no-cache"})
        value = result.get("data", {}).get("page_pv")
        if result.get("success") is not True or type(value) is not int or value < 0:
            raise ValueError(f"Invalid count for {url}")
        site_value = result.get("data", {}).get("site_pv")
        if type(site_value) is not int or site_value < 0:
            raise ValueError(f"Invalid site count for {url}")
        if same_source:
            if value < previous["counts"].get(url, 0):
                raise ValueError(f"Counter decreased for {url}; preserving the previous backup")
            if site_value < previous.get("site_pv", 0):
                raise ValueError("Site counter decreased; preserving the previous backup")
        return {"page_pv": value, "site_pv": site_value, "saved_at": datetime.now(timezone.utc).isoformat()}

    errors = {}
    for attempt in range(4):
        pending = [url for url in urls if url not in samples]
        if not pending:
            break
        pause = 10
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(count, url): url for url in pending}
            try:
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        samples[url] = future.result()
                    except Exception as error:
                        if not is_transient(error):
                            raise
                        pause = max(pause, retry_after(error))
                        if isinstance(error, HTTPError):
                            error.close()
                        errors[url] = error
                        print(f"Read failed for {url} (pass {attempt + 1}/4): {error}", file=sys.stderr)
                    else:
                        if on_progress:
                            on_progress(samples)
            finally:
                for future in futures:
                    future.cancel()
        print(f"Counter pass {attempt + 1}/4: {len(samples)}/{len(urls)} articles collected")
        pending = [url for url in urls if url not in samples]
        if not pending:
            break
        if attempt == 3 or time.monotonic() + pause >= deadline:
            raise errors[pending[0]]
        time.sleep(pause)

    counts = {url: samples[url]["page_pv"] for url in urls}
    site_pv = max(sample["site_pv"] for sample in samples.values())

    data = {
        "version": 3 if history is not None else 2,
        # 恢复检查点时不把旧样本标为刚查询的记录；前端可安全沿用这个保守时间。
        "saved_at": min(sample["saved_at"] for sample in samples.values()),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "observed_at": {url: samples[url]["saved_at"] for url in urls},
        "api": api,
        "site": manifest["site"],
        "site_pv": site_pv,
        "counts": counts,
    }
    if history is not None:
        # 保留原始实时计数与固定历史基数，恢复或重复备份时不会再次累加历史。
        data["history"] = history
    return data


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def checkpoint_context(manifest):
    return {key: manifest.get(key) for key in ("api", "site", "history")} | {"urls": sorted(set(manifest["urls"]))}


def load_checkpoint(path, manifest, previous):
    if not path.exists():
        return {}
    try:
        saved = json.loads(path.read_text())
        if saved.get("manifest") != checkpoint_context(manifest):
            return {}
        now = datetime.now(timezone.utc)
        same_source = previous and previous.get("api") == manifest["api"] and previous.get("site") == manifest["site"]
        samples = {}
        for url, sample in saved["samples"].items():
            if url not in manifest["urls"]:
                continue
            age = (now - datetime.fromisoformat(sample["saved_at"])).total_seconds()
            if not 0 <= age <= 1800:
                continue
            if any(type(sample.get(key)) is not int or sample[key] < 0 for key in ("page_pv", "site_pv")):
                continue
            if same_source and (sample["page_pv"] < previous["counts"].get(url, 0) or sample["site_pv"] < previous.get("site_pv", 0)):
                continue
            samples[url] = sample
        print(f"Resuming {len(samples)} recent article samples from the checkpoint")
        return samples
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        print(f"Ignoring invalid checkpoint: {error}", file=sys.stderr)
        return {}


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
    checkpoint = args.output.with_name("page-views.pending.json")
    samples = load_checkpoint(checkpoint, manifest, previous)

    def save_progress(values):
        write_json(checkpoint, {"version": 1, "manifest": checkpoint_context(manifest), "samples": values})

    deadline = time.monotonic() + 420

    def read_counter(url, headers):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Counter collection time budget exhausted")
        # 在轮次之间重试失败文章，不立即为同一篇文章连续建立三次连接。
        return read_json(url, headers, attempts=1, timeout=min(15, remaining))

    try:
        data = snapshot(manifest, previous, reader=read_counter, samples=samples, on_progress=save_progress, deadline=deadline)
    except Exception:
        missing = sorted(set(manifest["urls"]) - set(samples))
        message = f"Backup incomplete: {len(samples)}/{len(set(manifest['urls']))} articles collected; previous complete backup preserved."
        print(message, file=sys.stderr)
        for url in missing:
            print(f"Unrefreshed article: {url}", file=sys.stderr)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write(message + "\n\nRecent valid samples are saved separately in `page-views.pending.json`.\n\n")
                summary.writelines(f"- {url}\n" for url in missing)
        raise
    # 所有查询及校验成功后才替换文件，失败或计数下降时保留上一次成功备份。
    write_json(args.output, data)
    checkpoint.unlink(missing_ok=True)
    print(f"Backed up {len(data['counts'])} article counters at {data['completed_at']}")


if __name__ == "__main__":
    main()
