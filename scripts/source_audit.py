#!/usr/bin/env python3
"""Audit independent IP/CIDR sources against generated provider datasets.

The audit measures address-space coverage, not just line counts. It is
observational: a source outage or a disagreement never changes subscriptions.
"""
import concurrent.futures
import datetime
import ipaddress
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts"))

import update_cdn_lists as engine


def merge_intervals(networks, version):
    intervals = []
    for value in networks:
        try:
            n = ipaddress.ip_network(str(value), strict=False)
        except ValueError:
            continue
        if n.version != version:
            continue
        intervals.append((int(n.network_address), int(n.broadcast_address)))
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


def provider_metrics(generated, source):
    result = {}
    for version in (4, 6):
        g = [x for x in generated if ":" in x] if version == 6 else [x for x in generated if ":" not in x]
        s = [x for x in source if ":" in x] if version == 6 else [x for x in source if ":" not in x]
        sc = coverage(s, version)
        gc = coverage(g, version)
        overlap = intersection_coverage(s, g, version)
        result[str(version)] = {
            "source_prefixes": len(set(s)),
            "generated_prefixes": len(set(g)),
            "source_coverage_ips": sc,
            "generated_coverage_ips": gc,
            "overlap_coverage_ips": overlap,
            "new_coverage_ips": max(0, sc - overlap),
            "source_coverage_already_present_percent": round(overlap * 100 / sc, 4) if sc else 0.0,
            "new_coverage_percent_of_source": round(max(0, sc - overlap) * 100 / sc, 4) if sc else 0.0,
        }
    return result


def load_generated(name):
    values = []
    for suffix in ("-v4.txt", "-v6.txt"):
        path = DATA / f"{name}{suffix}"
        if path.exists():
            values.extend(x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip())
    return values


def load_cloud_ip_ranges(name, registry):
    values, source = engine.registry_cloud_ranges(name, registry)
    if source and source.startswith("stale"):
        raise RuntimeError(source)
    return values, source


def load_cdn_database(name, registry):
    spec = registry.get("cdn-ip-database", {})
    return engine.registry_provider_ranges(name, "cdn-ip-database", spec), "cdn-ip-database"


def load_ipverse(name, asns):
    values = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(asns)))) as pool:
        for result in pool.map(engine.ipverse_ranges, asns):
            values.extend(result)
    return sorted(set(values)), "IPVerse"


def main():
    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    registry = engine.load_source_registry()
    rows = []
    for name, asns in cfg["providers"].items():
        generated = load_generated(name)
        sources = [
            ("cloud-ip-ranges", lambda n=name: load_cloud_ip_ranges(n, registry)),
            ("cdn-ip-database", lambda n=name: load_cdn_database(n, registry)),
            ("IPVerse", lambda a=sorted(set(asns)): load_ipverse(name, a)),
        ]
        for source_name, loader in sources:
            started = datetime.datetime.now(datetime.timezone.utc)
            try:
                source_values, source_ref = loader()
                metrics = provider_metrics(generated, source_values)
                rows.append({
                    "provider": name,
                    "source": source_name,
                    "status": "OK",
                    "source_ref": source_ref,
                    "generated_prefixes_total": len(set(generated)),
                    "source_prefixes_total": len(set(source_values)),
                    "coverage": metrics,
                    "checked_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })
            except Exception as exc:
                rows.append({
                    "provider": name,
                    "source": source_name,
                    "status": "ERROR",
                    "error": str(exc)[:500],
                    "checked_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
                })

    summary = {}
    for source in sorted({r["source"] for r in rows}):
        ok = [r for r in rows if r["source"] == source and r["status"] == "OK"]
        summary[source] = {
            "providers_checked": len(ok),
            "providers_with_new_coverage": sum(
                1 for r in ok if any(r["coverage"][v]["new_coverage_ips"] > 0 for v in ("4", "6"))
            ),
            "new_coverage_ips": {
                v: sum(r["coverage"][v]["new_coverage_ips"] for r in ok)
                for v in ("4", "6")
            },
            "source_coverage_ips": {
                v: sum(r["coverage"][v]["source_coverage_ips"] for r in ok)
                for v in ("4", "6")
            },
        }

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "exact merged address-space intervals; prefix count is secondary",
        "policy": "audit-only; no source disagreement removes or replaces generated CIDRs",
        "sources": summary,
        "providers": rows,
    }
    (DATA / "source-audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    errors = sum(1 for r in rows if r["status"] == "ERROR")
    print(f"Source audit: {len(rows) - errors} successful checks, {errors} errors")
    for source, item in summary.items():
        print(f"{source}: new IPv4={item['new_coverage_ips']['4']} IPv6={item['new_coverage_ips']['6']}")
    # External source outages are recorded, not fatal. Malformed successful
    # datasets are handled by the parser and simply contribute no valid CIDRs.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
