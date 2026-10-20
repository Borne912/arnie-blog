"""Prepare an atomic Redis import of raw PV counts for soxft/busuanzi v2.8.8.

This only writes a local RESP file. It never connects to the old/new API or Redis.
Fixed historical counts stay in Jekyll and must not be imported a second time.
"""

import argparse
from hashlib import md5
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit


SEED_SCRIPT = """
local previous = redis.call('GET', KEYS[1])
local members = redis.call('ZRANGE', KEYS[2], 0, -1, 'WITHSCORES')
if previous or #members > 0 then
    if previous ~= ARGV[1] or #members ~= #ARGV - 1 then
        return redis.error_reply('Destination is not empty; import refused')
    end
    for i = 2, #ARGV, 2 do
        if redis.call('ZSCORE', KEYS[2], ARGV[i]) ~= ARGV[i + 1] then
            return redis.error_reply('Destination differs; import refused')
        end
    end
    return 'Already imported; no changes'
end
redis.call('SET', KEYS[1], ARGV[1])
for i = 2, #ARGV, 2 do
    redis.call('ZADD', KEYS[2], ARGV[i + 1], ARGV[i])
end
return 'Imported raw PV counts; historical baseline not included'
"""


def integer(value):
    if type(value) is not int or not 0 <= value <= 2**53 - 1:
        raise ValueError("Counts must be nonnegative safe integers")
    return value


def digest(value):
    # Matches Bsz.Encrypt=MD516 and Bsz.PathStyle=true in compose.yaml.
    return md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()[8:24]


def command(snapshot, expected_site):
    site = urlsplit(expected_site)
    if site.scheme != "https" or not site.netloc or site.path or site.query or site.fragment or site.username:
        raise ValueError("Expected site must be an HTTPS origin without a trailing slash")
    if snapshot.get("version") not in (2, 3) or snapshot.get("site") != expected_site:
        raise ValueError("Backup version or site does not match")
    if urlsplit(snapshot.get("api", "")).scheme != "https":
        raise ValueError("Backup API must use HTTPS")
    total = integer(snapshot.get("site_pv"))
    counts = snapshot.get("counts")
    if not isinstance(counts, dict) or not counts:
        raise ValueError("Backup contains no article counters")
    paths = {}
    for url, value in counts.items():
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != site.netloc or not parts.path.startswith("/") or parts.query or parts.fragment:
            raise ValueError(f"Article URL does not belong to the expected site: {url}")
        # Go's url.Parse(...).Path decodes percent escapes before hashing.
        member = digest(unquote(parts.path, errors="strict"))
        value = integer(value)
        if member in paths:
            raise ValueError(f"Duplicate decoded article path: {url}")
        paths[member] = value
    if sum(paths.values()) > total:
        raise ValueError("Raw article counters exceed the raw site total")
    host = digest(site.netloc)
    args = ["EVAL", SEED_SCRIPT, "2", f"bsz:site_pv:{host}", f"bsz:page_pv:{host}", str(total)]
    for member, value in sorted(paths.items()):
        args.extend([member, str(value)])
    return args


def encode_resp(args):
    encoded = [str(value).encode("utf-8") for value in args]
    return b"*%d\r\n" % len(encoded) + b"".join(b"$%d\r\n" % len(value) + value + b"\r\n" for value in encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--site", default="https://stile.cc")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    payload = encode_resp(command(snapshot, args.site))
    # Refuse to overwrite a previously reviewed import file.
    with args.output.open("xb") as output:
        output.write(payload)
    print(f"Prepared {len(snapshot['counts'])} raw article counters and site PV {snapshot['site_pv']}; history excluded", file=sys.stderr)


if __name__ == "__main__":
    main()
