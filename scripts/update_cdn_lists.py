#!/usr/bin/env python3
import datetime
from normalization import find_exact_duplicates, build_provider_overlap_report, nets, address_coverage
from artifact_store import load_old_raw, write_diff, cache_path, atomic_json, load_previous, atomic, write_text_atomic, sha256
from evidence_store import source_confidence, load_bgpstream_health, evidence_confidence, build_provenance, write_source_health_registry, export_consensus_duckdb
from source_acquisition import (source_probe, discover_asn_notes, request, jsonget, ripe_routing_status, load_ripe_cache, save_ripe_cache, ripe_prefix_overview, validate_prefix_with_ripe, select_ripe_candidates, ipverse_ranges, routeviews_prefixes, ripe, walk_strings, external_ipsets, load_source_registry, parse_cidr_lines, registry_provider_ranges, registry_cloud_ranges, registry_egress_ranges, official)
import concurrent.futures
import hashlib
import ipaddress
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import argparse
try:
    import duckdb
except ImportError:
    duckdb = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
if str(ROOT / "scripts") not in sys.path: sys.path.insert(0, str(ROOT / "scripts"))

from policy_engine import apply as apply_policy
from consensus_engine import build_consensus
DATA.mkdir(exist_ok=True)

VERSION = 44
UA = f"CDN-Cloud-MagiTrickle/{VERSION}.0"
RIPE = "https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS = 1
RETRIES = 5
TIMEOUT = 30
RETRY_BASE = 2
MAX_WORKERS = 8
CACHE_TTL = 21600
MIN_CHANGE_RATIO = 0.50
MIN_CHANGE_RATIO_V6 = 0.35
# Coverage ratios are the primary shrink guard. Prefix count alone is unsafe
# because CIDR aggregation can legitimately reduce the number of lines.
MIN_COVERAGE_RATIO = 0.50
MIN_COVERAGE_RATIO_V6 = 0.35
MAX_AGGREGATE_PREFIXES = 200000
MIN_PREFIXLEN = {4: 8, 6: 16}
MIN_PREFIXES = {"aws": 1, "cloudflare": 1, "akamai": 1, "fastly": 1, "gcore": 1, "backblaze": 1, "bunny": 1, "leaseweb": 1, "upcloud": 1, "ionos": 1, "default": 1}

STATIC = {
    "backblaze": [
        "45.11.36.0/22", "104.153.232.0/21", "149.137.128.0/20",
        "206.190.208.0/21", "207.166.148.0/22", "2605:72c0::/32",
    ]
}

SOURCE_HEALTH = DATA / "source-health.json"
DIFF_DIR = DATA / "diff"
DIFF_DIR.mkdir(exist_ok=True)
HISTORY_LIMIT = 10001

def main():
    parser = argparse.ArgumentParser(description="Build CDN/ASN subscriptions")
    parser.add_argument("--explain", action="store_true", help="generate per-CIDR policy explanations")
    parser.add_argument("--skip-confirmation", action="store_true", help="skip optional RIPE prefix confirmation")
    parser.add_argument("--skip-presets", action="store_true", help="skip preset subscription generation")
    args = parser.parse_args()
    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    registry = load_source_registry()
    bgp_health = load_bgpstream_health()
    write_source_health_registry(registry)
    min_peers = int(cfg.get("min_peers_seeing", MIN_PEERS))
    all4, all6, rows = [], [], []
    all_asn4, all_asn6 = [], []
    audit_rows = []
    policy_explain = {}
    provider_asns = {}
    for name, asns in cfg["providers"].items():
        raw, sources, errors = [], [], []
        source_prefixes = {}
        unique_asns = []
        for asn in asns:
            if asn not in unique_asns:
                unique_asns.append(asn)
            else:
                errors.append(f"duplicate ASN ignored: AS{asn}")
        provider_asns[name] = unique_asns
        try:
            raw = official(name)
            if raw:
                sources.append("official" if name not in STATIC else "static")
                source_prefixes["official" if name not in STATIC else "static"] = list(raw)
        except Exception as exc:
            errors.append("official:" + str(exc))

        try:
            registry_values, registry_source = registry_cloud_ranges(name, registry)
            if registry_values:
                raw.extend(registry_values)
                sources.append("cloud-ip-ranges")
                source_prefixes["cloud-ip-ranges"] = list(registry_values)
            elif registry_source and registry_source.startswith("stale"):
                errors.append(registry_source)
            elif registry_source and registry_source.startswith("cloud-ip-ranges:"):
                errors.append(registry_source)
        except Exception as exc:
            errors.append("cloud-ip-ranges:" + str(exc))

        try:
            egress_values, egress_source = registry_egress_ranges(name, registry)
            if egress_values:
                raw.extend(egress_values)
                sources.append("cloud-egress-ip-ranges")
                source_prefixes["cloud-egress-ip-ranges"] = list(egress_values)
        except Exception as exc:
            errors.append("cloud-egress:" + str(exc))

        # Independent registries are additive only when they expose a stable,
        # machine-readable hosted artifact. Repository-only tools are recorded as
        # references/validators instead of guessing their generated file layout.
        for registry_id, registry_spec in (
            ("cdn-ip-database", registry.get("cdn-ip-database", {})),
        ):
            try:
                values = registry_provider_ranges(name, registry_id, registry_spec)
                if values:
                    raw.extend(values)
                    sources.append(registry_id)
                    source_prefixes[registry_id] = list(values)
            except Exception as exc:
                errors.append(registry_id + ":" + str(exc))

        try:
            extra, extra_sources = external_ipsets(name, unique_asns)
            raw.extend(extra)
            sources.extend(extra_sources)
            for extra_source in extra_sources:
                source_prefixes.setdefault(extra_source, []).extend(extra)
        except Exception as exc:
            errors.append("external-ipset:" + str(exc))
        def fetch_asn(asn):
            try:
                bgp_views = ripe(asn, min_peers)
                ipverse_values = ipverse_ranges(asn)
                return asn, bgp_views, ipverse_values, None
            except Exception as exc:
                return asn, {}, [], exc
        if unique_asns:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(unique_asns))) as pool:
                results = list(pool.map(fetch_asn, unique_asns))
            for asn, bgp_views, ipverse_values, error in results:
                if error:
                    errors.append(f"RIPE-AS{asn}:{error}")
                else:
                    bgp_values = []
                    for source_id, values in bgp_views.items():
                        normalized_values = sorted(set(values))
                        bgp_values.extend(normalized_values)
                        if normalized_values:
                            raw.extend(normalized_values)
                            source_prefixes.setdefault(source_id, []).extend(normalized_values)
                            sources.append(source_id)
                    raw.extend(ipverse_values)
                    all_asn4.extend(v for v in bgp_values + ipverse_values if "/" in v and ":" not in v)
                    all_asn6.extend(v for v in bgp_values + ipverse_values if ":" in v)
                    if ipverse_values:
                        source_prefixes.setdefault("IPVerse", []).extend(ipverse_values)
                        sources.append("IPVerse")
                    routing = ripe_routing_status(asn)
                    if routing:
                        sources.append("RIPE routing-status")
        old4 = DATA / f"{name}-v4.txt"; old6 = DATA / f"{name}-v6.txt"
        old4_raw, old6_raw = load_old_raw(old4), load_old_raw(old6)
        v4, rejected4 = nets(raw, 4); v6, rejected6 = nets(raw, 6)
        v4_raw, v6_raw = list(map(str, v4)), list(map(str, v6))
        v4_policy, exp4 = apply_policy(name, v4_raw, collect_explain=args.explain)
        v6_policy, exp6 = apply_policy(name, v6_raw, collect_explain=args.explain)
        v4, _ = nets(v4_policy, 4); v6, _ = nets(v6_policy, 6)
        if find_exact_duplicates(v4_raw) or find_exact_duplicates(v6_raw):
            errors.append("duplicate source CIDRs normalized before output")
        if args.explain:
            policy_explain[name] = {"ipv4": exp4, "ipv6": exp6}

        prev4 = load_previous(old4, 4); prev6 = load_previous(old6, 6)
        minimum = MIN_PREFIXES.get(name, MIN_PREFIXES["default"])
        status = "OK"; used_fallback = False
        suspicious4 = False
        suspicious6 = False
        prev4_coverage = address_coverage(prev4)
        prev6_coverage = address_coverage(prev6)
        new4_coverage = address_coverage(v4)
        new6_coverage = address_coverage(v6)
        if prev4_coverage and new4_coverage < int(prev4_coverage * MIN_COVERAGE_RATIO):
            suspicious4 = True
        if prev6_coverage and new6_coverage < int(prev6_coverage * MIN_COVERAGE_RATIO_V6):
            suspicious6 = True
        if suspicious4 and prev4:
            v4 = prev4; status = "KEEP_OLD"; used_fallback = True
        if suspicious6 and prev6:
            v6 = prev6; status = "KEEP_OLD" if status == "OK" else status; used_fallback = True
        if suspicious4 and not prev4:
            status = "EMPTY" if not v4 else "ANOMALY"
        if suspicious6 and not prev6 and not v6:
            status = "EMPTY" if status == "OK" else status
        if errors:
            if prev4 and len(v4) < len(prev4):
                v4 = prev4; status = "KEEP_OLD_PARTIAL"; used_fallback = True
            if prev6 and len(v6) < len(prev6):
                v6 = prev6; status = "KEEP_OLD_PARTIAL"; used_fallback = True
            if status == "OK": status = "PARTIAL"
        if rejected4 or rejected6:
            if status == "OK": status = "FILTERED"
        if not used_fallback:
            atomic(old4, v4); atomic(old6, v6)
        diff_info = write_diff(name, old4_raw, list(map(str,v4)), old6_raw, list(map(str,v6)))
        source = "+".join(dict.fromkeys(sources)) or "none"
        consensus = build_consensus(name, list(v4) + list(v6), source_prefixes, unique_asns, bgp_health, DATA)
        write_text_atomic(DATA / f"{name}-consensus.json", json.dumps({"provider": name, "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "asns": unique_asns, "records": consensus}, indent=2, ensure_ascii=False) + "\n")
        all4.extend(v4); all6.extend(v6)
        prev4_count, prev6_count = len(prev4), len(prev6)
        pct4 = None if not prev4_count else round((len(v4) - prev4_count) * 100 / prev4_count, 2)
        pct6 = None if not prev6_count else round((len(v6) - prev6_count) * 100 / prev6_count, 2)
        audit_rows.append({
            "provider": name, "ipv4_prefixes": len(v4), "ipv6_prefixes": len(v6),
            "previous_ipv4_prefixes": prev4_count, "previous_ipv6_prefixes": prev6_count,
            "ipv4_change_percent": pct4, "ipv6_change_percent": pct6,
            "status": status, "source": source, "errors": len(errors),
        })
        rows.append({"name": name, "ipv4": len(v4), "ipv6": len(v6), "source": source, "status": status, "errors": errors[:10], "rejected_ipv4": rejected4, "rejected_ipv6": rejected6})
        print(f"{name}: v4={len(v4)} v6={len(v6)} {source} {status}")
        if errors: print(f"  warnings: {len(errors)}")
        if rejected4 or rejected6: print(f"  filtered: ipv4={rejected4} ipv6={rejected6}")
    provider_networks = {}
    for name in cfg["providers"]:
        provider_networks[name] = load_old_raw(DATA / f"{name}-v4.txt") + load_old_raw(DATA / f"{name}-v6.txt")
    overlap_report = build_provider_overlap_report(provider_networks)

    all4, _ = nets(all4, 4); all6, _ = nets(all6, 6)
    all_asn4, _ = nets(all_asn4, 4); all_asn6, _ = nets(all_asn6, 6)

    validated_asn4 = []
    validated_asn6 = []
    candidates = [] if args.skip_confirmation else select_ripe_candidates(all_asn4 + all_asn6, limit=128)
    ripe_cache = load_ripe_cache()
    if candidates:
        # Cache reads happen before parallel requests; cache writes are merged
        # in the main thread to avoid concurrent mutation of the shared dict.
        cached_checks = {}
        pending = []
        for prefix in candidates:
            entry = ripe_cache.get(prefix)
            try:
                fresh = isinstance(entry, dict) and int(time.time()) - int(entry.get("ts", 0)) < RIPE_CACHE_TTL
            except (TypeError, ValueError):
                fresh = False
            if fresh:
                cached_checks[prefix] = bool(entry.get("confirmed", False))
            else:
                pending.append(prefix)

        def confirm(prefix):
            data = ripe_prefix_overview(prefix)
            return bool(data.get("announced") is True or data.get("asns"))

        if pending:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                results = list(pool.map(confirm, pending))
            now = int(time.time())
            for prefix, confirmed in zip(pending, results):
                ripe_cache[prefix] = {"ts": now, "confirmed": confirmed}
                cached_checks[prefix] = confirmed

        save_ripe_cache(ripe_cache)
        for prefix in candidates:
            confirmed = cached_checks.get(prefix, False)
            if confirmed:
                (validated_asn6 if ":" in prefix else validated_asn4).append(prefix)
    atomic(DATA / "asn-confirmed-v4.txt", validated_asn4)
    atomic(DATA / "asn-confirmed-v6.txt", validated_asn6)
    atomic(DATA / "asn-all-v4.txt", all_asn4)
    atomic(DATA / "asn-all-v6.txt", all_asn6)
    if not all4: sys.exit("[FATAL] no aggregate IPv4")
    if len(all4) > MAX_AGGREGATE_PREFIXES or len(all6) > MAX_AGGREGATE_PREFIXES:
        sys.exit("[FATAL] aggregate prefix count exceeds safety limit")
    atomic(DATA / "all-cloud-v4.txt", all4); atomic(DATA / "all-cloud-v6.txt", all6)
    # Profiles have one generator. Keeping this logic in generate_profiles.py
    # prevents the two engines from drifting apart.
    if not args.skip_presets:
        import subprocess
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_profiles.py")],
            check=True,
        )

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest = {
        "version": VERSION, "updated": now, "ripe_min_peers": min_peers,
        "sources": ["official provider feeds", "disposable/cloud-ip-ranges", "ipanalytics/Cloud-Egress-IP-Ranges", "RIPEstat", "RIPE RIS", "RouteViews fallback", "IPVerse as-ip-blocks", "sw.ext.io", "RussiaFancyLists (independent Russia IP intelligence / validation only)"],
        "features": ["source-fusion","coverage-based-regression-guard","multi-source-asn-discovery","ripe-prefix-overview","asn-confirmed-lists","source-health","deduplication","cidr-aggregation","diff","profiles","sha256","asn-audit","parallel-fetch","source-cache","freshness-gates","ipverse-cross-check","single-profile-generator","consensus-evidence","per-cidr-provenance","anomaly-protection","cross-provider-overlap-audit","russiafancy-validation"],
        "engine": "final-v44-source-fusion-ipverse",
        "provider_asn_counts": {k: len(v) for k, v in provider_asns.items()},
        "provider_asns": provider_asns,
        "retries": RETRIES, "timeout_seconds": TIMEOUT, "max_workers": MAX_WORKERS, "cache_ttl_seconds": CACHE_TTL, "ipverse": "enabled", "min_change_ratio": MIN_CHANGE_RATIO, "min_change_ratio_v6": MIN_CHANGE_RATIO_V6, "min_coverage_ratio": MIN_COVERAGE_RATIO, "min_coverage_ratio_v6": MIN_COVERAGE_RATIO_V6,
        "max_aggregate_prefixes": MAX_AGGREGATE_PREFIXES,
        "min_provider_prefixes": None, "max_provider_prefixes": None, "global_only": True,
        "min_prefixlen": {"ipv4": MIN_PREFIXLEN[4], "ipv6": MIN_PREFIXLEN[6]},
        "aggregate": {"ipv4": len(all4), "ipv6": len(all6)},
        "audit": audit_rows,
        "diff": {name: write_diff(name, load_old_raw(DATA/f"{name}-v4.txt"), [], load_old_raw(DATA/f"{name}-v6.txt"), []) for name in []},
        "providers": {row["name"]: {
            "ipv4": row["ipv4"], "ipv6": row["ipv6"], "source": row["source"],
            "status": row["status"], "rejected_ipv4": row["rejected_ipv4"], "rejected_ipv6": row["rejected_ipv6"],
            **({"errors": row["errors"]} if row["errors"] else {})
        } for row in rows},
    }
    consensus_index = {}
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            provider = payload.get("provider", path.stem.replace("-consensus", ""))
            records = payload.get("records", [])
            consensus_index[provider] = {"file": path.name, "cidrs": len(records), "high_confidence": sum(1 for x in records if x.get("confidence", 0) >= 80), "multi_source": sum(1 for x in records if x.get("source_count", 0) >= 2)}
        except Exception:
            continue
    all_consensus = []
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            all_consensus.extend(payload.get("records", []))
        except Exception:
            continue
    duckdb_enabled = export_consensus_duckdb(all_consensus, audit_rows)
    write_text_atomic(
        DATA / "consensus.json",
        json.dumps({
            "engine": VERSION,
            "generated_at": now,
            "model": "multi-source-evidence",
            "duckdb_enabled": duckdb_enabled,
            "rule": "BGP absence is neutral; a CIDR is never removed solely because a live snapshot did not observe it.",
            "providers": consensus_index,
            "records": all_consensus,
        }, indent=2, ensure_ascii=False) + "\n",
    )
    write_text_atomic(DATA / "provider-overlaps.json", json.dumps(overlap_report, indent=2, ensure_ascii=False) + "\n")
    write_text_atomic(DATA / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if args.explain:
        write_text_atomic(DATA / "policy-explain.json", json.dumps(policy_explain, indent=2, ensure_ascii=False) + "\n")
    checksum_files = sorted(set(DATA.glob("*-v*.txt")) | {DATA / "all-cloud-v4.txt", DATA / "all-cloud-v6.txt", DATA / "asn-all-v4.txt", DATA / "asn-all-v6.txt", DATA / "asn-confirmed-v4.txt", DATA / "asn-confirmed-v6.txt"})
    write_text_atomic(DATA / "checksums.sha256", "\n".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}" for path in checksum_files) + "\n")
    summary = [f"Updated: {now}", f"ALL IPv4: {len(all4)}", f"ALL IPv6: {len(all6)}", f"ALL ASN IPv4: {len(all_asn4)}", f"ALL ASN IPv6: {len(all_asn6)}", "", "Provider,IPv4,IPv6,Source,Status,Errors,RejectedIPv4,RejectedIPv6"]
    summary.extend(f"{row['name']},{row['ipv4']},{row['ipv6']},{row['source']},{row['status']},{len(row['errors'])},{row['rejected_ipv4']},{row['rejected_ipv6']}" for row in rows)
    write_text_atomic(DATA / "last-update.txt", "\n".join(summary) + "\n")
    health = {
        "checked_at": now,
        "sources": {
            "RIPEstat": source_probe(RIPE + "?resource=AS13335&min_peers_seeing=1"),
            "AWS": source_probe("https://ip-ranges.amazonaws.com/ip-ranges.json"),
            "Cloudflare": source_probe("https://www.cloudflare.com/ips-v4/"),
            "cloud-ip-ranges": source_probe("https://raw.githubusercontent.com/disposable/cloud-ip-ranges/master/txt/aws.txt"),
            "cloud-egress-ip-ranges": source_probe("https://github.com/ipanalytics/Cloud-Egress-IP-Ranges/releases/latest/download/cloud-egress-ip-ranges.json"),
            "RouteViews": source_probe("https://api.routeviews.org/"), "IPVerse": source_probe("https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/13335/ipv4-aggregated.txt"), "RussiaFancyLists": source_probe("https://raw.githubusercontent.com/Noktomezo/RussiaFancyLists/main/lists/blacklist/ipsets/full-and-cdn.lst")
        }
    }
    try:
        rf = parse_cidr_lines(request("https://raw.githubusercontent.com/Noktomezo/RussiaFancyLists/main/lists/blacklist/ipsets/full-and-cdn.lst"))
        rf4, _ = nets(rf, 4)
        atomic(DATA / "russiafancy-cdn-v4.txt", rf4)
        rf6, _ = nets(rf, 6)
        atomic(DATA / "russiafancy-cdn-v6.txt", rf6)
    except Exception as exc:
        write_text_atomic(DATA / "russiafancy-error.txt", str(exc) + "\n")
    write_text_atomic(SOURCE_HEALTH, json.dumps(health, indent=2, ensure_ascii=False)+"\n")
    audit_lines = ["Provider,IPv4,IPv6,PreviousIPv4,PreviousIPv6,IPv4Change%,IPv6Change%,Status,Source,Errors"]
    audit_lines.extend(
        f"{r['provider']},{r['ipv4_prefixes']},{r['ipv6_prefixes']},{r['previous_ipv4_prefixes']},{r['previous_ipv6_prefixes']},{r['ipv4_change_percent']},{r['ipv6_change_percent']},{r['status']},{r['source']},{r['errors']}"
        for r in audit_rows
    )
    write_text_atomic(DATA / "audit.csv", "\n".join(audit_lines) + "\n")
    history_path = DATA / "history.csv"
    header = "Timestamp,Provider,IPv4,IPv6,IPv4Change%,IPv6Change%,Status"
    history_lines = history_path.read_text(encoding="utf-8").splitlines() if history_path.exists() else [header]
    for r in audit_rows:
        history_lines.append(
            f"{now},{r['provider']},{r['ipv4_prefixes']},{r['ipv6_prefixes']},{r['ipv4_change_percent']},{r['ipv6_change_percent']},{r['status']}"
        )
    write_text_atomic(history_path, "\n".join(history_lines[-HISTORY_LIMIT:]) + "\n")

if __name__ == "__main__": main()
