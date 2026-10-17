"""Notify Bing through IndexNow after verifying the published ownership key."""

import argparse
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import json


ENDPOINT = "https://www.bing.com/indexnow"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def request(url, payload=None):
    headers = {"User-Agent": "STiLE-IndexNow/1.0"}
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    for attempt in range(4):
        try:
            with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
                return response.status, response.read()
        except HTTPError as error:
            if error.code not in (404, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except URLError:
            if attempt == 3:
                raise
        # Pages 刚发布时文件可能尚未传播完成；短暂等待后重新验证。
        time.sleep(5 * (attempt + 1))


def payload_for(site, key, sitemap):
    origin = urlsplit(site)
    if origin.scheme != "https" or not origin.hostname or origin.netloc != origin.hostname:
        raise ValueError("Site must be an HTTPS origin without a port")
    if origin.path not in ("", "/") or origin.query or origin.fragment:
        raise ValueError("Site must not contain a path, query or fragment")
    if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", key):
        raise ValueError("Invalid IndexNow ownership key")
    root = ET.fromstring(sitemap)
    if root.tag != SITEMAP_NS + "urlset":
        raise ValueError("Expected a URL sitemap")
    urls = set()
    for node in root.findall(SITEMAP_NS + "url/" + SITEMAP_NS + "loc"):
        url = (node.text or "").strip()
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != origin.netloc or parts.query or parts.fragment:
            raise ValueError(f"Invalid canonical sitemap URL: {url}")
        urls.add(quote(url, safe=":/%!$&'()*+,;=@-._~"))
    if not urls or len(urls) > 10000:
        raise ValueError("IndexNow requires between 1 and 10000 URLs per submission")
    return {
        "host": origin.hostname,
        "key": key,
        "keyLocation": site.rstrip("/") + "/indexnow-key.txt",
        "urlList": sorted(urls),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--key-file", type=Path, default=Path("indexnow-key.txt"))
    parser.add_argument("--sitemap", type=Path, help="Optional local sitemap for validation")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    key = args.key_file.read_text().strip()
    sitemap = args.sitemap.read_bytes() if args.sitemap else request(args.site.rstrip("/") + "/sitemap.xml")[1]
    payload = payload_for(args.site, key, sitemap)
    if args.dry_run:
        print(f"Validated {len(payload['urlList'])} canonical URLs for IndexNow")
        return
    published_key = request(payload["keyLocation"])[1].decode("utf-8").strip()
    if published_key != key:
        raise ValueError("Published ownership key does not match; refusing to notify IndexNow")
    status, _ = request(ENDPOINT, payload)
    if status not in (200, 202):
        raise ValueError(f"Unexpected IndexNow status: {status}")
    suffix = "; ownership verification pending" if status == 202 else ""
    print(f"IndexNow HTTP {status}: received {len(payload['urlList'])} URLs{suffix}. Receipt does not guarantee indexing.")


if __name__ == "__main__":
    main()
