#!/usr/bin/env python3
"""Extracted normalization helpers for CDN-Cloud-MagiTrickle."""
import ipaddress

MIN_PREFIXLEN = {4: 8, 6: 16}

def find_exact_duplicates(values):
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return sorted(duplicates)


def build_provider_overlap_report(provider_networks):
    owners = {}
    for provider, values in provider_networks.items():
        for value in values:
            owners.setdefault(value, []).append(provider)
    overlaps = {cidr: sorted(names) for cidr, names in owners.items() if len(names) > 1}
    return {
        "exact_cross_provider_overlaps": len(overlaps),
        "entries": [{"cidr": cidr, "providers": providers} for cidr, providers in sorted(overlaps.items())],
        "note": "Cross-provider overlaps are reported, not deleted; all-cloud is globally deduplicated."
    }


def nets(values, version, global_only=True):
    parsed = set(); rejected = 0
    for value in values:
        try:
            net = value if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network)) else ipaddress.ip_network(str(value).strip(), strict=False)
            if net.version != version:
                continue
            if global_only and not net.is_global:
                rejected += 1; continue
            if net.prefixlen < MIN_PREFIXLEN[version]:
                rejected += 1; continue
            parsed.add(net)
        except Exception:
            rejected += 1
    return sorted(ipaddress.collapse_addresses(parsed), key=lambda n: (int(n.network_address), n.prefixlen)), rejected


def address_coverage(networks):
    """Return total covered addresses without expanding CIDRs."""
    return sum(int(net.num_addresses) for net in networks)


