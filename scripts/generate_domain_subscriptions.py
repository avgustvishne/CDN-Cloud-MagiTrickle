#!/usr/bin/env python3
"""Generate a conservative domain subscription from independent external feeds.

Only domains present in at least two successful external domain feeds are
published. This is a derived routing list, not provider-ownership evidence.
"""
import concurrent.futures
import ipaddress
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "source_registry.json"
OUTPUT = ROOT / "data" / "domains" / "external-consensus.txt"
TIMEOUT = 20
RETRIES = 3
MAX_BYTES = 64 * 1024 * 1024
UA = "CDN-Cloud-MagiTrickle/domain-consensus"

DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.I)


def fetch(url):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/plain,*/*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                data = response.read(MAX_BYTES + 1)
            if not data:
                raise RuntimeError("empty response")
            if len(data) > MAX_BYTES:
                raise RuntimeError(f"response exceeds {MAX_BYTES} bytes")
            return data
        except Exception as exc:
            last = exc
            if attempt + 1 < RETRIES:
                continue
    raise last


def parse_domains(data):
    values = set()
    for line in data.decode("utf-8", errors="replace").splitlines():
        value = line.strip().lower()
        if not value or value.startswith(("#", ";")):
            continue
        if value.startswith(("domain-suffix,", "domain,")):
            value = value.split(",", 1)[1].strip()
        value = value.removeprefix("*.").rstrip(".")
        if DOMAIN_RE.fullmatch(value):
            values.add(value)
    return values


def domain_feeds(registry):
    return {
        feed_id: spec
        for feed_id, spec in registry.get("external-intelligence", {}).get("feeds", {}).items()
        if spec.get("type") == "domain"
    }


def collect(feeds):
    def one(item):
        feed_id, spec = item
        urls = spec.get("urls") or [spec["url"]]
        chunks = [fetch(url) for url in urls]
        domains = set()
        for chunk in chunks:
            domains.update(parse_domains(chunk))
        return feed_id, domains

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(feeds)))) as pool:
        results = list(pool.map(one, sorted(feeds.items())))
    return dict(results)


def build_consensus(feed_domains, minimum_sources=2):
    seen = {}
    for domains in feed_domains.values():
        for domain in domains:
            seen[domain] = seen.get(domain, 0) + 1
    return sorted(domain for domain, count in seen.items() if count >= minimum_sources)


def write_atomic(path, domains):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(domains) + ("\n" if domains else "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    feeds = domain_feeds(registry)
    if len(feeds) < 2:
        raise RuntimeError("at least two external domain feeds are required")
    feed_domains = collect(feeds)
    successful = {feed_id: domains for feed_id, domains in feed_domains.items() if domains}
    if len(successful) < 2:
        raise RuntimeError(f"fewer than two usable domain feeds: {len(successful)}")
    consensus = build_consensus(successful, minimum_sources=2)
    if not consensus:
        raise RuntimeError("consensus domain subscription is empty")
    write_atomic(OUTPUT, consensus)
    print(f"Domain consensus: {len(consensus)} domains from {len(successful)} successful feeds")


if __name__ == "__main__":
    main()
