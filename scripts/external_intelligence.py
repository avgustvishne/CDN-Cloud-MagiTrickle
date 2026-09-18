#!/usr/bin/env python3
"""Collect external restriction/CDN feeds as read-only intelligence.

The feeds are intentionally evidence-only. Nothing collected here is allowed to
replace or mutate provider subscriptions. The report stores counts, hashes and
exact address-space overlap with existing generated profiles, not raw external
lists.
"""
import concurrent.futures
import datetime as dt
import hashlib
import ipaddress
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REGISTRY = ROOT / "config" / "source_registry.json"
OUTPUT = DATA / "external-source-intelligence.json"
TIMEOUT = 20
RETRIES = 3
MAX_BYTES = 64 * 1024 * 1024
UA = "CDN-Cloud-MagiTrickle/external-intelligence"

DOMAIN_RE = re.compile(r"^(?:\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.I)


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


def parse_cidrs(data):
    values = set()
    for line in data.decode("utf-8", errors="replace").splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        try:
            values.add(str(ipaddress.ip_network(value, strict=False)))
        except ValueError:
            continue
    return sorted(values, key=lambda x: (":" in x, ipaddress.ip_network(x)))


def parse_domains(data):
    values = set()
    for line in data.decode("utf-8", errors="replace").splitlines():
        value = line.strip().lower()
        if not value or value.startswith(("#", ";")):
            continue
        if value.startswith("domain-suffix,"):
            value = value.split(",", 1)[1].strip()
        elif value.startswith("domain,"):
            value = value.split(",", 1)[1].strip()
        value = value.removeprefix("*.").rstrip(".")
        if DOMAIN_RE.fullmatch(value):
            values.add(value)
    return sorted(values)


def merge_intervals(networks, version):
    intervals = []
    for value in networks:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            continue
        if network.version == version:
            intervals.append((int(network.network_address), int(network.broadcast_address)))
    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return merged


def coverage(networks, version):
    return sum(end - start + 1 for start, end in merge_intervals(networks, version))


def intersection_coverage(left, right, version):
    a = merge_intervals(left, version)
    b = merge_intervals(right, version)
    i = j = total = 0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if lo <= hi:
            total += hi - lo + 1
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def load_generated(path):
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def generated_profile(profile):
    return {
        "ipv4": load_generated(DATA / "presets" / f"{profile}-v4.txt"),
        "ipv6": load_generated(DATA / "presets" / f"{profile}-v6.txt"),
    }


def ip_metrics(values, profiles):
    result = {}
    for version in (4, 6):
        family = [v for v in values if ipaddress.ip_network(v).version == version]
        row = {
            "prefixes": len(family),
            "coverage_ips": coverage(family, version),
        }
        for profile, generated in profiles.items():
            target = generated["ipv4" if version == 4 else "ipv6"]
            row[f"overlap_{profile}_ips"] = intersection_coverage(family, target, version)
        result[str(version)] = row
    return result


def fetch_feed(feed_id, spec, profiles):
    started = dt.datetime.now(dt.timezone.utc)
    try:
        urls = spec.get("urls") or [spec["url"]]
        chunks = [fetch(url) for url in urls]
        raw = b"\n".join(chunks)
        digest = hashlib.sha256(b"".join(url.encode() + b"\0" + chunk for url, chunk in zip(urls, chunks))).hexdigest()
        if spec["type"] == "ip":
            parsed_by_category = {}
            if spec.get("categories"):
                for category, chunk in zip(spec["categories"], chunks):
                    parsed_by_category[category] = parse_cidrs(chunk)
                values = sorted(
                    set().union(*(set(items) for items in parsed_by_category.values())),
                    key=lambda x: (":" in x, ipaddress.ip_network(x)),
                )
            else:
                values = parse_cidrs(raw)
            row = {
                "id": feed_id,
                "type": "ip",
                "url": urls[0] if len(urls) == 1 else urls,
                "status": "OK",
                "bytes": len(raw),
                "sha256": digest,
                "entries": len(values),
                "metrics": ip_metrics(values, profiles),
                "checked_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            if parsed_by_category:
                row["categories"] = {
                    category: {"prefixes": len(items), "coverage_ips": coverage(items, 4)}
                    for category, items in parsed_by_category.items()
                }
            return row
        values = parse_domains(raw)
        return {
            "id": feed_id,
            "type": "domain",
            "url": urls[0] if len(urls) == 1 else urls,
            "status": "OK",
            "bytes": len(raw),
            "sha256": digest,
            "entries": len(values),
            "_domains": values,
            "checked_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    except Exception as exc:
        return {
            "id": feed_id,
            "type": spec.get("type", "unknown"),
            "url": spec.get("url") or spec.get("urls", []),
            "status": "ERROR",
            "error": str(exc)[:500],
            "checked_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    feeds = registry.get("external-intelligence", {}).get("feeds", {})
    profiles = {name: generated_profile(name) for name in ("full", "performance")}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(feeds)))) as pool:
        futures = [pool.submit(fetch_feed, feed_id, spec, profiles) for feed_id, spec in sorted(feeds.items())]
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda row: row["id"])

    successful_domains = {}
    for row in results:
        if row["status"] != "OK" or row["type"] != "domain":
            continue
        for domain in row.pop("_domains", []):
            successful_domains.setdefault(domain, set()).add(row["id"])

    multi_source_domains = sum(1 for sources in successful_domains.values() if len(sources) >= 2)
    payload = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": {
            "mode": "observational",
            "mutates_subscriptions": False,
            "external_ip_lists_are_evidence_only": True,
            "external_domains_are_evidence_only": True,
            "source_failure_replaces_data": False,
            "raw_external_lists_stored": False,
        },
        "sources": results,
        "domain_consensus": {
            "unique_domains_across_successful_feeds": len(successful_domains),
            "domains_seen_in_at_least_two_feeds": multi_source_domains,
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    errors = sum(row["status"] == "ERROR" for row in results)
    print(f"External intelligence: {len(results) - errors} successful feeds, {errors} errors, {multi_source_domains} multi-source domains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
