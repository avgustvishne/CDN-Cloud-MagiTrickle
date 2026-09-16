#!/usr/bin/env python3
"""Regression gate for catastrophic CIDR shrinkage.

Compares provider files and published presets by both prefix count and
actual address-space coverage. Coverage is calculated from the union of
the prefixes, so overlapping CIDRs cannot inflate the metric.
"""
import argparse
import ipaddress
import pathlib
import sys

EXCLUDED = {"all-cloud-v4.txt", "all-cloud-v6.txt", "asn-all-v4.txt",
            "asn-all-v6.txt", "asn-confirmed-v4.txt", "asn-confirmed-v6.txt"}

def load(path):
    if not path.exists():
        return []
    out = []
    for s in path.read_text(encoding="utf-8").splitlines():
        s = s.strip()
        if s and not s.startswith("#"):
            try:
                out.append(ipaddress.ip_network(s, strict=False))
            except ValueError:
                pass
    return out

def coverage(nets, version):
    family = sorted({n for n in nets if n.version == version},
                    key=lambda n: (int(n.network_address), n.prefixlen))
    return sum(n.num_addresses for n in ipaddress.collapse_addresses(family))

def iter_datasets(root):
    yield from sorted(root.glob("*-v4.txt"))
    yield from sorted(root.glob("*-v6.txt"))
    yield from sorted((root / "presets").glob("*-v4.txt"))
    yield from sorted((root / "presets").glob("*-v6.txt"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--min-previous", type=int, default=20)
    ap.add_argument("--max-drop", type=float, default=0.80)
    args = ap.parse_args()

    old_root = pathlib.Path(args.old)
    new_root = pathlib.Path(args.new)
    bad = []

    for new_path in iter_datasets(new_root):
        if new_path.name in EXCLUDED:
            continue
        old_path = old_root / ("presets" if new_path.parent.name == "presets" else "") / new_path.name
        if not old_path.exists():
            continue

        old_nets = load(old_path)
        new_nets = load(new_path)
        old_count = len(old_nets)
        new_count = len(new_nets)

        if old_count >= args.min_previous and new_count / old_count < (1 - args.max_drop):
            bad.append(f"{new_path}: prefix count {old_count} -> {new_count}")

        version = 6 if new_path.name.endswith("-v6.txt") else 4
        old_cov = coverage(old_nets, version)
        new_cov = coverage(new_nets, version)
        if old_cov and new_cov / old_cov < (1 - args.max_drop):
            bad.append(f"{new_path}: coverage {old_cov} -> {new_cov}")

    if bad:
        print("\n".join(bad))
        sys.exit(1)
    print("Regression gate: OK")

if __name__ == "__main__":
    main()
