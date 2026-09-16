#!/usr/bin/env python3
"""Extracted evidence helpers for CDN-Cloud-MagiTrickle."""
import datetime
import json
import pathlib
import ipaddress
import os
import tempfile
from pathlib import Path

try:
    import duckdb
except ImportError:
    duckdb = None

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def write_text_atomic(path, text):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def source_confidence(sources):
    """Score independent evidence; official/BGP/RPKI outrank secondary feeds."""
    weights={"official":100,"bgp_rpki":95,"asn_index":90,"independent":85,"secondary":60,"dns":40}
    kinds=[s.get("kind","secondary") for s in sources if isinstance(s,dict)]
    if not kinds: return 0
    score=max(weights.get(k,50) for k in kinds)
    independent=len(set(kinds))
    return min(100, score + min(10, max(0, independent-1)*2))


def load_bgpstream_health():
    """Load the latest optional BGPStream validation report."""
    path = Path(__file__).resolve().parents[1] / "data" / "bgpstream-health.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(row.get("asn")): row for row in payload.get("results", [])}
    except Exception:
        return {}



def evidence_confidence(provider, cidr_sources, asn, bgp_health):
    """Combine source evidence without making live BGP a hard deletion rule."""
    kinds = {s.get("kind", "secondary") for s in cidr_sources if isinstance(s, dict)}
    score = source_confidence(cidr_sources)
    if "official" in kinds:
        score += 2
    if "asn_index" in kinds:
        score += 2
    if "independent" in kinds:
        score += 2
    row = bgp_health.get(str(asn))
    if row:
        if row.get("observed"):
            score += 5
        if int(row.get("peers", 0)) >= 2:
            score += 3
        elif int(row.get("peers", 0)) == 0:
            # A missing observation is neutral: live RIB snapshots are not
            # complete enough to justify deleting a prefix.
            score += 0
    return min(100, score)



def build_provenance(provider, prefixes, source_records, asn=None, bgp_health=None):
    records=[]
    for cidr in sorted(set(prefixes)):
        matched=[s for s in source_records if cidr in set(s.get("prefixes",[]))]
        records.append({"cidr":cidr,"provider":provider,"sources":[{"id":s.get("id"),"kind":s.get("kind","secondary"),"observed_at":s.get("observed_at")} for s in matched],"confidence":evidence_confidence(provider, matched, asn, bgp_health or {})})
    return records



def write_source_health_registry(registry):
    """Record registry capabilities without treating repository tools as live feeds."""
    rows=[]
    for source_id, spec in registry.items():
        rows.append({
            "id": source_id,
            "role": spec.get("role", ""),
            "refresh": spec.get("refresh", ""),
            "live_fetch_enabled": source_id in {"cloud-ip-ranges","cloud-egress-ip-ranges","cdn-ip-database","ipverse-as-ip-blocks"},
            "reference_only": source_id in {"taythebot-cdn-ranges","krainium-cdn-fetcher","projectdiscovery-cdncheck","routesentinel","cloud-provider-ip-addresses"},
        })
    write_text_atomic(DATA / "source-registry-health.json",
        json.dumps({"generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "sources": rows}, indent=2, ensure_ascii=False) + "\n")



def export_consensus_duckdb(records, audit_rows):
    """Optional analytical cache; public JSON/TXT remain authoritative."""
    if duckdb is None:
        return False
    path = DATA / "consensus.duckdb"
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TABLE IF NOT EXISTS prefixes (cidr VARCHAR, provider VARCHAR, source_count INTEGER, confidence INTEGER, first_seen VARCHAR, last_seen VARCHAR)")
        con.execute("CREATE TABLE IF NOT EXISTS prefix_sources (cidr VARCHAR, provider VARCHAR, source VARCHAR, observed_at VARCHAR)")
        con.execute("CREATE TABLE IF NOT EXISTS generation_audit (provider VARCHAR, ipv4_prefixes BIGINT, ipv6_prefixes BIGINT, previous_ipv4_prefixes BIGINT, previous_ipv6_prefixes BIGINT, ipv4_change_percent DOUBLE, ipv6_change_percent DOUBLE, status VARCHAR, source VARCHAR, errors INTEGER, recorded_at VARCHAR)")
        con.execute("DELETE FROM prefixes")
        con.execute("DELETE FROM prefix_sources")
        con.execute("DELETE FROM generation_audit")
        con.executemany("INSERT INTO prefixes VALUES (?, ?, ?, ?, ?, ?)", [(r.get("cidr"), r.get("provider"), int(r.get("source_count",0)), int(r.get("confidence",0)), r.get("first_seen"), r.get("last_seen")) for r in records])
        source_rows=[]
        for r in records:
            for source in r.get("sources",[]):
                source_id = source.get("id") if isinstance(source, dict) else source
                observed_at = source.get("observed_at") if isinstance(source, dict) else r.get("last_seen")
                source_rows.append((r.get("cidr"), r.get("provider"), str(source_id or ""), observed_at))
        if source_rows: con.executemany("INSERT INTO prefix_sources VALUES (?, ?, ?, ?)", source_rows)
        now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        con.executemany("INSERT INTO generation_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [(r["provider"],r["ipv4_prefixes"],r["ipv6_prefixes"],r["previous_ipv4_prefixes"],r["previous_ipv6_prefixes"],r["ipv4_change_percent"],r["ipv6_change_percent"],r["status"],r["source"],r["errors"],now) for r in audit_rows])
        con.commit()
        return True
    finally:
        con.close()

