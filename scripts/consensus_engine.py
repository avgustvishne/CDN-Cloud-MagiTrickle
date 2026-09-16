#!/usr/bin/env python3
"""Evidence/consensus engine used by the production generator.

Keeps per-CIDR provenance separate from fetching and profile generation.
"""
import datetime
import ipaddress
import json
import pathlib

def build_consensus(provider, prefixes, source_prefixes, asns, bgp_health, data_dir=None):
    """Create exact per-CIDR evidence; BGP absence is neutral."""
    if data_dir is None:
        data_dir = pathlib.Path(__file__).resolve().parents[1] / "data"
    normalized = {}
    for source_id, values in source_prefixes.items():
        canonical = set()
        for value in values:
            try:
                canonical.add(str(ipaddress.ip_network(str(value), strict=False)))
            except ValueError:
                continue
        normalized[source_id] = canonical

    previous = {}
    previous_path = data_dir / f"{provider}-consensus.json"
    if previous_path.exists():
        try:
            previous = {
                r.get("cidr"): r for r in json.loads(
                    previous_path.read_text(encoding="utf-8")
                ).get("records", [])
            }
        except Exception:
            previous = {}

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []
    for value in prefixes:
        try:
            cidr = str(ipaddress.ip_network(str(value), strict=False))
        except ValueError:
            continue

        evidence = sorted(
            source_id for source_id, values in normalized.items() if cidr in values
        )
        bgp_observed_asns = []
        bgp_peer_counts = []
        for asn in asns:
            row = bgp_health.get(str(asn))
            if not isinstance(row, dict):
                continue
            # New validator reports may contain exact observed prefixes.
            # Without that list, an ASN-level observation is deliberately
            # NOT attributed to every CIDR.
            observed_prefixes = set()
            for prefix in row.get("prefixes", row.get("observed_prefixes", [])) or []:
                try:
                    observed_prefixes.add(
                        str(ipaddress.ip_network(str(prefix), strict=False))
                    )
                except ValueError:
                    continue
            if cidr in observed_prefixes:
                bgp_observed_asns.append(str(asn))
                try:
                    bgp_peer_counts.append(int(row.get("peers", 0)))
                except (TypeError, ValueError):
                    pass

        independent_ids = {"IPVerse", "RIPEstat", "RIPE RIS", "RouteViews", "cdn-ip-database"}
        independent = len(set(evidence) & independent_ids)
        official = bool(set(evidence) & {"official", "cloud-ip-ranges", "cloud-egress-ip-ranges", "static"})
        score = min(
            100,
            20
            + (45 if official else 0)
            + min(20, independent * 5)
            + (10 if bgp_observed_asns else 0)
            + (5 if bgp_peer_counts and max(bgp_peer_counts) >= 2 else 0),
        )
        records.append({
            "cidr": cidr,
            "provider": provider,
            "sources": evidence,
            "source_count": len(evidence),
            "bgp_observed_asns": bgp_observed_asns,
            "bgp_max_peers": max(bgp_peer_counts) if bgp_peer_counts else 0,
            "confidence": score,
            "first_seen": previous.get(cidr, {}).get("first_seen") or now,
            "last_seen": now,
        })
    return records

