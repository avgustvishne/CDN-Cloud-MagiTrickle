#!/usr/bin/env python3
"""Discover candidate ASNs adjacent to known provider ASNs via RIPEstat RIS data.

This is an observational discovery layer. It never edits config/providers.json
and never changes published subscriptions. Candidates require human review.
"""
import concurrent.futures
import datetime as dt
import json
import pathlib
import time
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "providers.json"
OUTPUT = ROOT / "data" / "asn-discovery.json"
HISTORY = ROOT / "data" / "asn-discovery-history.json"
API = "https://stat.ripe.net/data"
SOURCEAPP = "cdn-cloud-magitrickle"
WORKERS = 8
RETRIES = 2
TIMEOUT = 15
HISTORY_LIMIT = 30
MAX_CANDIDATES = 100
MIN_KNOWN_CONNECTIONS = 2
MIN_PATH_POWER = 2


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api(endpoint, resource):
    params = {
        "resource": f"AS{resource}",
        "sourceapp": SOURCEAPP,
    }
    url = f"{API}/{endpoint}/data.json?{urllib.parse.urlencode(params)}"
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") != "ok":
                raise RuntimeError(payload.get("messages") or payload.get("status"))
            return payload.get("data", {})
        except Exception as exc:
            last_error = str(exc)
            if attempt < RETRIES:
                time.sleep(1 + attempt)
    return {"_error": last_error or "unknown error"}


def load_config():
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    providers = payload.get("providers", {})
    known = {}
    for provider, asns in providers.items():
        for value in asns:
            try:
                asn = int(value)
            except (TypeError, ValueError):
                continue
            known.setdefault(asn, set()).add(provider)
    return known


def collect_neighbours(known_asns):
    observations = []

    def query(asn):
        return asn, api("asn-neighbours", asn)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for asn, payload in pool.map(query, sorted(known_asns)):
            if "_error" in payload:
                observations.append({
                    "asn": asn,
                    "status": "ERROR",
                    "error": payload["_error"],
                })
                continue
            observations.append({
                "asn": asn,
                "status": "OK",
                "neighbours": payload.get("neighbours", []),
            })
    return observations


def aggregate(observations, known):
    candidates = defaultdict(lambda: {
        "seen_from": set(),
        "relationships": set(),
        "path_power": 0,
        "v4_peers": 0,
        "v6_peers": 0,
        "uncertain_observations": 0,
    })

    for observation in observations:
        if observation.get("status") != "OK":
            continue
        source_asn = observation["asn"]
        for row in observation.get("neighbours", []):
            try:
                neighbour = int(row.get("asn"))
            except (TypeError, ValueError):
                continue
            if neighbour in known:
                continue
            item = candidates[neighbour]
            item["seen_from"].add(source_asn)
            relationship = str(row.get("type") or "")
            if relationship:
                item["relationships"].add(relationship)
            power = row.get("power")
            if isinstance(power, (int, float)):
                item["path_power"] += int(power)
            for field in ("v4_peers", "v6_peers"):
                value = row.get(field)
                if isinstance(value, (int, float)):
                    item[field] += int(value)
            if relationship == "uncertain":
                item["uncertain_observations"] += 1

    result = []
    for asn, item in candidates.items():
        known_connections = len(item["seen_from"])
        if known_connections < MIN_KNOWN_CONNECTIONS and item["path_power"] < MIN_PATH_POWER:
            continue
        # Transparent discovery score. It ranks evidence strength only; it is
        # not a claim of ownership or provider identity.
        score = (
            min(50, known_connections * 15)
            + min(25, item["path_power"])
            + min(15, item["v4_peers"] // 10)
            + min(10, item["v6_peers"] // 10)
        )
        result.append({
            "asn": f"AS{asn}",
            "asn_number": asn,
            "discovery_score": min(100, score),
            "known_provider_connections": known_connections,
            "seen_from": [f"AS{x}" for x in sorted(item["seen_from"])],
            "relationships": sorted(item["relationships"]),
            "path_power": item["path_power"],
            "v4_peers": item["v4_peers"],
            "v6_peers": item["v6_peers"],
            "uncertain_observations": item["uncertain_observations"],
            "status": "candidate",
            "policy": "human_review_required",
        })

    result.sort(
        key=lambda row: (
            -row["discovery_score"],
            -row["known_provider_connections"],
            -row["path_power"],
            row["asn_number"],
        )
    )
    return result[:MAX_CANDIDATES]


def load_history():
    try:
        payload = json.loads(HISTORY.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def main():
    known = load_config()
    observations = collect_neighbours(known)
    candidates = aggregate(observations, known)
    previous = load_history()
    previously_seen = {
        row.get("asn")
        for snapshot in previous
        if isinstance(snapshot, dict)
        for row in snapshot.get("candidates", [])
        if isinstance(row, dict)
    }

    for row in candidates:
        row["first_seen"] = row["asn"] not in previously_seen

    errors = [row for row in observations if row.get("status") == "ERROR"]
    payload = {
        "schema_version": 1,
        "generated_at": now(),
        "provider": "RIPEstat RIS",
        "policy": {
            "mode": "observational",
            "mutates_provider_config": False,
            "mutates_subscriptions": False,
            "candidate_requires_human_review": True,
            "min_known_provider_connections": MIN_KNOWN_CONNECTIONS,
            "min_path_power": MIN_PATH_POWER,
            "max_candidates": MAX_CANDIDATES,
        },
        "known_asns": len(known),
        "queried_asns": len(observations),
        "successful_queries": len(observations) - len(errors),
        "failed_queries": len(errors),
        "candidates": candidates,
    }
    history.append({
        "generated_at": payload["generated_at"],
        "candidates": candidates,
    })
    HISTORY.write_text(
        json.dumps(history[-HISTORY_LIMIT:], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"ASN discovery: {payload['queried_asns']} queried, "
        f"{payload['successful_queries']} successful, "
        f"{len(candidates)} candidates"
    )


if __name__ == "__main__":
    main()
