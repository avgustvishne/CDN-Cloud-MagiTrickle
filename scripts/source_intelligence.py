#!/usr/bin/env python3
"""Build a safe, read-only source-intelligence report.

This layer never changes published CIDR files. It summarizes source freshness,
independent-source coverage, consensus evidence and provider-level anomalies.
"""
import datetime as dt
import ipaddress
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REGISTRY = ROOT / "config" / "source_registry.json"
OUTPUT = DATA / "source-intelligence.json"


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def parse_time(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def source_status(registry, audit):
    rows = []
    audit_sources = audit.get("sources", {})
    for source_id, spec in registry.items():
        item = audit_sources.get(source_id, {})
        rows.append({
            "id": source_id,
            "role": spec.get("role", ""),
            "refresh": spec.get("refresh", ""),
            "authority": spec.get("authority", ""),
            "live_fetch_enabled": bool(
                source_id in {
                    "cloud-ip-ranges", "cloud-egress-ip-ranges",
                    "cdn-ip-database", "ipverse-as-ip-blocks"
                }
            ),
            "audit_providers_checked": item.get("providers_checked", 0),
            "new_coverage_ipv4": item.get("new_coverage_ips", {}).get("4", 0),
            "new_coverage_ipv6": item.get("new_coverage_ips", {}).get("6", 0),
        })
    return rows


def consensus_summary():
    providers = {}
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records = payload.get("records", [])
        source_counts = Counter()
        confidence = []
        for row in records:
            if not isinstance(row, dict):
                continue
            for source in row.get("sources", []) or []:
                source_counts[str(source)] += 1
            if isinstance(row.get("confidence"), (int, float)):
                confidence.append(float(row["confidence"]))
        provider = path.name[:-len("-consensus.json")]
        providers[provider] = {
            "records": len(records),
            "sources": dict(sorted(source_counts.items())),
            "mean_confidence": round(sum(confidence) / len(confidence), 2) if confidence else 0,
            "high_confidence_percent": round(
                sum(x >= 80 for x in confidence) * 100 / len(confidence), 2
            ) if confidence else 0,
        }
    return providers


def prefix_intelligence():
    rows = []
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            records = json.loads(path.read_text(encoding="utf-8")).get("records", [])
        except (OSError, json.JSONDecodeError):
            continue
        source_counts = Counter()
        for row in records:
            if not isinstance(row, dict):
                continue
            for source in row.get("sources", []) or []:
                source_counts[str(source)] += 1
        if not source_counts:
            continue
        rows.append({
            "provider": path.name[:-len("-consensus.json")],
            "total_prefixes": len(records),
            "independent_source_types": len(source_counts),
            "top_sources": source_counts.most_common(8),
        })
    return rows


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    audit_path = DATA / "source-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    now = utc_now()
    payload = {
        "schema_version": 1,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": {
            "mode": "observational",
            "mutates_subscriptions": False,
            "source_failure_replaces_data": False,
            "rpki_invalid_deletes_prefix": False,
        },
        "sources": source_status(registry, audit),
        "providers": consensus_summary(),
        "prefix_intelligence": prefix_intelligence(),
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Source intelligence: {len(payload['sources'])} sources, "
        f"{len(payload['providers'])} providers"
    )


if __name__ == "__main__":
    main()
