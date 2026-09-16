#!/usr/bin/env python3
"""Validate README Raw subscription links and their local targets."""
import concurrent.futures
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

README = Path("README.md").read_text(encoding="utf-8")
BASE = "https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/"

urls = sorted(set(re.findall(r'\]\((https://raw\.githubusercontent\.com/[^)]+)\)', README)))

bad = []

# First fail fast on links pointing to files that do not exist in the repository.
for url in urls:
    if not url.startswith(BASE):
        continue
    rel = url[len(BASE):].split("?", 1)[0].split("#", 1)[0]
    target = Path(rel)
    if not target.is_file():
        bad.append((url, f"missing repository file: {rel}"))

def check(url):
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "CDN-Cloud-MagiTrickle-link-check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return url, r.status
    except Exception:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "CDN-Cloud-MagiTrickle-link-check",
                    "Range": "bytes=0-32",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return url, r.status
        except Exception as e:
            return url, str(e)

network_bad = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for url, status in ex.map(check, urls):
        print(status, url)
        if status not in (200, 206):
            network_bad.append((url, status))

bad.extend(network_bad)

if bad:
    print("\nBroken subscription links:")
    for url, reason in bad:
        print(f"{reason}: {url}")
    sys.exit(1)

print(f"Checked {len(urls)} README Raw subscription links: OK")
