#!/usr/bin/env python3
"""Subtract user-defined CIDRs from every generated dataset."""
import ipaddress
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXCLUDE_FILE = ROOT / "config" / "custom-exclude.txt"
DEFAULT_EXCLUDE_CONTENT = """\\
# One CIDR per line. Blank lines and lines starting with '#' are ignored.
# Any address here is removed from every generated dataset (all providers,
# all presets, both IPv4 and IPv6) by scripts/apply_excludes.py.
#
# Example:
# 203.0.113.0/24
"""

def load_excludes(path):
    if not path.exists():
        return {4: [], 6: []}
    by_version = {4: [], 6: []}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        try:
            network = ipaddress.ip_network(line, strict=False)
        except ValueError as exc:
            print(f"::error::{path}:{lineno}: invalid CIDR {raw!r}: {exc}", file=sys.stderr)
            raise SystemExit(1)
        by_version[network.version].append(network)
    return by_version

def subtract(networks, excludes):
    result = list(networks)
    for exc in excludes:
        next_result = []
        for net in result:
            if net.version != exc.version:
                next_result.append(net)
            elif net.subnet_of(exc):
                continue
            elif exc.subnet_of(net):
                next_result.extend(net.address_exclude(exc))
            else:
                next_result.append(net)
        result = next_result
    return result

def process_file(path, excludes_by_version):
    lines = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not lines:
        return 0
    version = 6 if path.name.endswith("-v6.txt") else 4
    excludes = excludes_by_version.get(version, [])
    if not excludes:
        return 0
    try:
        networks = [ipaddress.ip_network(line, strict=False) for line in lines]
    except ValueError:
        return 0
    remaining = subtract(networks, excludes)
    collapsed = sorted(ipaddress.collapse_addresses(remaining), key=lambda n: (n.version, int(n.network_address), n.prefixlen))
    if len(collapsed) == len(networks) and collapsed == networks:
        return 0
    path.write_text("\n".join(str(n) for n in collapsed) + "\n", encoding="utf-8")
    return max(0, len(networks) - len(collapsed))

def main():
    if not EXCLUDE_FILE.exists():
        EXCLUDE_FILE.parent.mkdir(parents=True, exist_ok=True)
        EXCLUDE_FILE.write_text(DEFAULT_EXCLUDE_CONTENT, encoding="utf-8")
        print(f"Created empty {EXCLUDE_FILE}; nothing to exclude yet.")
        return 0
    excludes = load_excludes(EXCLUDE_FILE)
    if not excludes[4] and not excludes[6]:
        print("No custom excludes configured; leaving all datasets untouched.")
        return 0
    total = 0
    targets = sorted(DATA.glob("*-v[46].txt")) + sorted((DATA / "presets").glob("*-v[46].txt"))
    for path in targets:
        removed = process_file(path, excludes)
        if removed:
            print(f"{path.relative_to(ROOT)}: changed by excludes ({removed} CIDR line(s))")
            total += removed
    print(f"Done. {total} CIDR line change(s) across {len(targets)} file(s).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
