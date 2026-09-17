#!/usr/bin/env python3
"""Stable generator entry point with balanced IPv4/IPv6 candidate selection.

The large, existing generator body is kept byte-for-byte in
``update_cdn_lists_impl.py``. It is executed in this module's namespace so the
historical helper API and monkey-patching behavior remain unchanged.
"""
from pathlib import Path

_SOURCE = Path(__file__).with_name("update_cdn_lists_impl.py")
_ORIGINAL_NAME = __name__
__name__ = "_update_cdn_lists_impl_runtime"
exec(compile(_SOURCE.read_text(encoding="utf-8"), str(_SOURCE), "exec"), globals())
__name__ = _ORIGINAL_NAME


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


if _ORIGINAL_NAME == "__main__":
    raise SystemExit(main())
