#!/usr/bin/env python3
"""Stable entry point for the MagiTrickle generator.

The implementation remains intact in ``update_cdn_lists_impl.py``. This small
entry point owns the candidate-selection policy so it can be changed and
regression-tested without rewriting the large generator body.
"""
import ipaddress

import update_cdn_lists_impl as _impl

# Preserve the historical module API used by tests and helper scripts.
globals().update(
    {name: value for name, value in vars(_impl).items() if not name.startswith("__")}
)


def select_ripe_candidates(prefixes, limit=128):
    """Select a bounded deterministic sample with balanced IPv4/IPv6 coverage."""
    if limit <= 0:
        return []

    normalized = set()
    for prefix in prefixes:
        try:
            normalized.add(str(ipaddress.ip_network(str(prefix), strict=False)))
        except (TypeError, ValueError):
            continue

    def prefix_key(value):
        network = ipaddress.ip_network(value, strict=False)
        return (network.prefixlen, int(network.network_address), value)

    families = {
        4: sorted(
            (p for p in normalized if ipaddress.ip_network(p, strict=False).version == 4),
            key=prefix_key,
        ),
        6: sorted(
            (p for p in normalized if ipaddress.ip_network(p, strict=False).version == 6),
            key=prefix_key,
        ),
    }
    total = len(families[4]) + len(families[6])
    if total <= limit:
        return sorted(
            normalized,
            key=lambda p: (ipaddress.ip_network(p, strict=False).version, prefix_key(p)),
        )

    present = [version for version in (4, 6) if families[version]]
    if len(present) == 1:
        return families[present[0]][:limit]

    # Reserve half the budget for each family. If one family has fewer
    # candidates, redistribute only its unused slots to the other family.
    budgets = {4: limit // 2, 6: limit - (limit // 2)}
    for version in present:
        budgets[version] = min(budgets[version], len(families[version]))

    unused = limit - sum(budgets.values())
    while unused:
        candidates = [v for v in present if budgets[v] < len(families[v])]
        if not candidates:
            break
        version = max(candidates, key=lambda v: len(families[v]) - budgets[v])
        budgets[version] += 1
        unused -= 1

    selected = families[4][:budgets[4]] + families[6][:budgets[6]]
    return sorted(
        selected,
        key=lambda p: (ipaddress.ip_network(p, strict=False).version, prefix_key(p)),
    )


_impl.select_ripe_candidates = select_ripe_candidates
main = _impl.main


if __name__ == "__main__":
    raise SystemExit(main())
