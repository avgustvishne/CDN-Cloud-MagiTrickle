#!/usr/bin/env python3
"""Generate a provider health snapshot consumed by the GitHub Pages dashboard."""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "monitor.json"
PROVIDERS = ROOT / "config/providers.json"
TIMEOUT = 8
CHECK_URLS = {
    "cloudflare": "https://www.cloudflare.com/cdn-cgi/trace",
    "aws": "https://aws.amazon.com/",
    "microsoft": "https://www.microsoft.com/",
    "akamai": "https://www.akamai.com/",
    "fastly": "https://www.fastly.com/",
    "gcore": "https://gcore.com/",
    "digitalocean": "https://www.digitalocean.com/",
    "hetzner": "https://www.hetzner.com/",
    "ovh": "https://www.ovhcloud.com/",
    "scaleway": "https://www.scaleway.com/",
    "oracle": "https://www.oracle.com/",
    "alibaba": "https://www.alibabacloud.com/",
    "cdn77": "https://www.cdn77.com/",
    "vultr": "https://www.vultr.com/",
    "contabo": "https://contabo.com/",
    "buyvm": "https://buyvm.net/",
    "backblaze": "https://www.backblaze.com/",
    "melbicom": "https://melbicom.net/",
}


def check(name: str) -> dict:
    url = CHECK_URLS.get(name)
    if not url:
        return {"provider": name, "status": "unknown", "latency_ms": None, "url": None}
    request = urllib.request.Request(url, headers={"User-Agent": "CDN-Cloud-MagiTrickle-Monitor/2.0"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            latency = round((time.perf_counter() - started) * 1000, 1)
            status = "healthy" if 200 <= response.status < 400 else "degraded"
            return {"provider": name, "status": status, "latency_ms": latency, "http_status": response.status, "url": url}
    except (OSError, urllib.error.URLError) as exc:
        return {"provider": name, "status": "down", "latency_ms": None, "error": type(exc).__name__, "url": url}


def main() -> None:
    cfg = json.loads(PROVIDERS.read_text(encoding="utf-8"))
    names = list(cfg.get("providers", {}))
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(names)))) as pool:
        rows = list(pool.map(check, names))
    rows.sort(key=lambda item: item["provider"])
    counts = {state: sum(item["status"] == state for item in rows) for state in ("healthy", "degraded", "down", "unknown")}
    payload = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "interval_minutes": 10,
        "counts": counts,
        "providers": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"providers": len(rows), "counts": counts, "seconds": round(time.time() - started, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
