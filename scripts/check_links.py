#!/usr/bin/env python3
"""Validate README Raw subscription links against the PR branch or main."""
import concurrent.futures
import os
import re
import sys
import urllib.request
from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")
BASE = "https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/"
EVENT = os.environ.get("GITHUB_EVENT_NAME", "")
HEAD_REF = os.environ.get("GITHUB_HEAD_REF", "")
CHECK_BASE = (
    f"https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/{HEAD_REF}/"
    if EVENT == "pull_request" and HEAD_REF else BASE
)

urls = sorted(set(re.findall(r'\]\((https://raw\.githubusercontent\.com/[^)]+)\)', README)))
bad = []
local_targets = {}

for url in urls:
    if not url.startswith(BASE):
        continue
    rel = url[len(BASE):].split("?", 1)[0].split("#", 1)[0]
    target = Path(rel)
    local_targets[url] = target.is_file()
    if not target.is_file() and EVENT != "pull_request":
        bad.append((url, f"missing repository file: {rel}"))

def check(url):
    check_url = CHECK_BASE + url[len(BASE):] if url.startswith(BASE) and CHECK_BASE != BASE else url
    req = urllib.request.Request(
        check_url,
        method="HEAD",
        headers={"User-Agent": "CDN-Cloud-MagiTrickle-link-check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return url, r.status
    except Exception:
        try:
            req = urllib.request.Request(
                check_url,
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
            if status == 404 and url.startswith(BASE) and EVENT == "pull_request":
                print(f"PR-BRANCH-ONLY {url} (main publication checked after merge)")
                continue
            network_bad.append((url, status))

bad.extend(network_bad)

if bad:
    print("\nBroken subscription links:")
    for url, reason in bad:
        print(f"{reason}: {url}")
    sys.exit(1)

print(f"Checked {len(urls)} README Raw subscription links: OK")
