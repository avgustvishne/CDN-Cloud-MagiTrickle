#!/usr/bin/env python3
"""Generate a human-readable autonomous status dashboard from generated data."""
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "STATUS.md"

def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def count_lines(name):
    p = DATA / name
    if not p.exists():
        return 0
    return sum(1 for x in p.read_text(encoding="utf-8").splitlines() if x.strip())

def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    health = load("source-health.json", {})
    network = load("network-evidence.json", {})
    intelligence = load("source-intelligence.json", {})
    summary = load("change-summary.json", {}).get("datasets", {})
    audit = load("source-audit.json", {})
    stats = load("statistics.json", {})
    sources = health.get("sources", {})
    healthy = sum(1 for x in sources.values() if x.get("ok") is True)
    total_sources = len(sources)
    evidence = network.get("evidence", [])
    statuses = {}
    for row in evidence:
        statuses[row.get("status", "unknown")] = statuses.get(row.get("status", "unknown"), 0) + 1
    changes_added = sum(x.get("added", 0) for x in summary.values())
    changes_removed = sum(x.get("removed", 0) for x in summary.values())
    providers = stats.get("providers", {})
    provider_count = len(providers)
    audit_errors = sum(1 for x in audit.get("providers", []) if x.get("status") == "ERROR")
    lines = [
        "# 🤖 MagiTrickle Status",
        "",
        "> Automatically generated after the validation pipeline. This file is informational; it does not control publication.",
        "",
        f"**Generated:** `{now}`",
        "",
        "## 🟢 Overall status",
        "",
        "| Component | Status | Details |",
        "|---|---|---|",
        f"| Sources | {'🟢 OK' if healthy == total_sources and total_sources else '🟡 CHECK'} | {healthy}/{total_sources} healthy |",
        f"| Providers | {'🟢 OK' if provider_count else '🔴 ERROR'} | {provider_count} configured |",
        f"| Network evidence | {'🟢 OK' if evidence else '🟡 NO DATA'} | {len(evidence)} prefixes checked |",
        f"| Source audit | {'🟢 OK' if audit_errors == 0 else '🟡 CHECK'} | {audit_errors} source errors recorded |",
        "",
        "## 📊 Published datasets",
        "",
        f"- **FULL IPv4:** {count_lines('all-cloud-v4.txt'):,} CIDR".replace(",", " "),
        f"- **FULL IPv6:** {count_lines('all-cloud-v6.txt'):,} CIDR".replace(",", " "),
        f"- **ASN IPv4:** {count_lines('asn-all-v4.txt'):,} CIDR".replace(",", " "),
        f"- **ASN IPv6:** {count_lines('asn-all-v6.txt'):,} CIDR".replace(",", " "),
        "",
        "## 🔎 Latest change",
        "",
        f"- Added across generated datasets: **{changes_added:,}**".replace(",", " "),
        f"- Removed across generated datasets: **{changes_removed:,}**".replace(",", " "),
        "",
        "## 🌐 Network evidence",
        "",
        f"- BGP/IRR/RPKI sample: **{len(evidence)} prefixes**",
        f"- Evidence states: `{json.dumps(statuses, ensure_ascii=False, sort_keys=True)}`",
        "- Negative BGP/IRR/RPKI evidence is advisory and cannot delete published prefixes.",
        "",
        "## 🛡️ Automation",
        "",
        "- Scheduled generation: enabled",
        "- Validation gates: enabled",
        "- Rollback safety: enabled",
        "- Automatic failure notification: enabled",
        "- Manual action required for normal updates: **no**",
        "",
        "## 📁 Machine-readable data",
        "",
        "- `data/statistics.json`",
        "- `data/change-summary.json`",
        "- `data/source-health.json`",
        "- `data/source-audit.json`",
        "- `data/network-evidence.json`",
        "- `data/source-intelligence.json`",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Dashboard generated: {OUT}")

if __name__ == "__main__":
    main()
