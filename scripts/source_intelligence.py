#!/usr/bin/env python3
"""Build a safe, read-only source-intelligence report.

This layer never changes published CIDR files. It summarizes source freshness,
independent-source coverage, consensus evidence, exact address-space coverage
and provider-level anomalies.
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
HISTORY = DATA / "source-intelligence-history.json"
HISTORY_LIMIT = 30
ANOMALY_RATIO = 0.50
MIN_CONFIRMING_SOURCES = 2


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


def network_coverage(records, version):
    """Return exact union size for consensus records in one IP family."""
    networks = []
    for row in records:
        if not isinstance(row, dict):
            continue
        value = row.get("cidr") or row.get("prefix")
        if not value:
            continue
        try:
            network = ipaddress.ip_network(str(value), strict=False)
        except ValueError:
            continue
        if network.version == version:
            networks.append(network)
    return sum(network.num_addresses for network in ipaddress.collapse_addresses(networks)) if networks else 0


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
            "coverage": {
                "ipv4": network_coverage(records, 4),
                "ipv6": network_coverage(records, 6),
            },
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


def prefix_evidence():
    """Build per-prefix evidence without changing published datasets."""
    result = []
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            records = json.loads(path.read_text(encoding="utf-8")).get("records", [])
        except (OSError, json.JSONDecodeError):
            continue
        provider = path.name[:-len("-consensus.json")]
        for row in records:
            if not isinstance(row, dict):
                continue
            cidr = row.get("cidr") or row.get("prefix")
            if not cidr:
                continue
            try:
                network = ipaddress.ip_network(str(cidr), strict=False)
            except ValueError:
                continue
            sources = sorted({str(x) for x in row.get("sources", []) if x})
            result.append({
                "provider": provider,
                "prefix": str(network),
                "version": network.version,
                "source_count": len(sources),
                "sources": sources,
                "status": "confirmed" if len(sources) >= MIN_CONFIRMING_SOURCES else "single_source",
            })
    return result


def reliability_score(status):
    """Compute a transparent source reliability score from observed signals only."""
    checked = status.get("audit_providers_checked", 0) or 0
    coverage = (status.get("new_coverage_ipv4", 0) or 0) + (status.get("new_coverage_ipv6", 0) or 0)
    authority = str(status.get("authority", "")).lower()
    authority_score = 1.0 if authority in {"official", "primary"} else 0.75 if authority else 0.5
    activity_score = 1.0 if checked > 0 and coverage >= 0 else 0.5
    return round((authority_score * 0.55 + activity_score * 0.45) * 100, 2)


def load_history():
    try:
        payload = json.loads(HISTORY.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def confirmation_for_provider(provider, current, previous):
    """Return whether a large change has independent source confirmation."""
    row = current.get("providers", {}).get(provider, {})
    sources = row.get("sources", {})
    independent = [name for name, count in sources.items() if count > 0]
    return {
        "confirmed": len(independent) >= MIN_CONFIRMING_SOURCES,
        "independent_sources": sorted(independent),
        "required_sources": MIN_CONFIRMING_SOURCES,
    }


def provider_anomalies(current, previous):
    """Flag large provider changes by count or exact address-space coverage."""
    if not previous:
        return []
    old = previous.get("providers", {})
    result = []
    for provider, row in current.get("providers", {}).items():
        old_row = old.get(provider, {})
        before = old_row.get("records")
        after = row.get("records")
        if not isinstance(before, int) or not isinstance(after, int) or before <= 0:
            continue

        count_ratio = abs(after - before) / before
        old_coverage = old_row.get("coverage", {})
        current_coverage = row.get("coverage", {})
        family_changes = {}
        coverage_anomaly = False
        for version in ("ipv4", "ipv6"):
            previous_coverage = old_coverage.get(version)
            current_value = current_coverage.get(version)
            if not isinstance(previous_coverage, int) or not isinstance(current_value, int) or previous_coverage <= 0:
                continue
            ratio = current_value / previous_coverage
            drop = max(0, 1 - ratio)
            family_changes[version] = {
                "previous": previous_coverage,
                "current": current_value,
                "ratio": round(ratio, 6),
                "drop_percent": round(drop * 100, 2),
            }
            coverage_anomaly = coverage_anomaly or drop >= ANOMALY_RATIO

        if count_ratio >= ANOMALY_RATIO or coverage_anomaly:
            confirmation = confirmation_for_provider(provider, current, previous)
            result.append({
                "provider": provider,
                "previous_records": before,
                "current_records": after,
                "change_ratio": round(count_ratio, 4),
                "coverage_changes": family_changes,
                "trigger": "coverage" if coverage_anomaly else "prefix_count",
                "action": "confirmed_observation" if confirmation["confirmed"] else "observe_only",
                "confirmation": confirmation,
            })
    return result


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    audit_path = DATA / "source-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    now = utc_now()
    rows = source_status(registry, audit)
    for row in rows:
        row["reliability_score"] = reliability_score(row)
    previous_history = load_history()
    previous = previous_history[-1] if previous_history else None
    providers = consensus_summary()
    payload = {
        "schema_version": 2,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": {
            "mode": "observational",
            "mutates_subscriptions": False,
            "source_failure_replaces_data": False,
            "rpki_invalid_deletes_prefix": False,
        },
        "sources": rows,
        "providers": providers,
        "prefix_intelligence": prefix_intelligence(),
        "prefix_evidence": prefix_evidence(),
        "change_policy": {
            "min_confirming_sources": MIN_CONFIRMING_SOURCES,
            "confirmed_changes_are_not_auto_published": True,
            "anomaly_ratio": ANOMALY_RATIO,
            "coverage_metric": "exact_union_address_space",
        },
        "anomalies": provider_anomalies(
            {"providers": providers},
            previous,
        ),
    }
    history = previous_history
    history.append({
        "generated_at": payload["generated_at"],
        "providers": providers,
        "source_count": len(payload["sources"]),
        "anomaly_count": len(payload["anomalies"]),
    })
    HISTORY.write_text(
        json.dumps(history[-HISTORY_LIMIT:], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Source intelligence: {len(payload['sources'])} sources, "
        f"{len(payload['providers'])} providers, "
        f"{len(payload['anomalies'])} anomalies"
    )


if __name__ == "__main__":
    main()
