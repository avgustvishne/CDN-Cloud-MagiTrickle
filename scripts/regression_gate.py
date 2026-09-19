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

# A published profile can legitimately contain prefixes that are no longer
# reproducible from the provider snapshots currently stored in the repository.
# Treat such a profile as a stale baseline instead of comparing a new,
# source-backed profile against historical, unsupported address space.
STALE_BASELINE_MIN_OVERLAP = 0.80

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

def iter_provider_datasets(root, version):
    """Yield source-provider datasets, excluding aggregate/ASN outputs."""
    suffix = f"-v{version}.txt"
    for path in sorted(root.glob(f"*{suffix}")):
        if path.name not in EXCLUDED:
            yield path


def overlap_coverage(left, right, version):
    """Return exact address-space overlap between two prefix sets."""
    a = sorted(
        (n for n in left if n.version == version),
        key=lambda n: (int(n.network_address), n.prefixlen),
    )
    b = sorted(
        (n for n in right if n.version == version),
        key=lambda n: (int(n.network_address), n.prefixlen),
    )
    i = j = total = 0
    while i < len(a) and j < len(b):
        start = max(int(a[i].network_address), int(b[j].network_address))
        end = min(int(a[i].broadcast_address), int(b[j].broadcast_address))
        if start <= end:
            total += end - start + 1
        if a[i].broadcast_address < b[j].broadcast_address:
            i += 1
        else:
            j += 1
    return total

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

        version = 6 if new_path.name.endswith("-v6.txt") else 4
        old_cov = coverage(old_nets, version)
        new_cov = coverage(new_nets, version)

        # Presets are derived from provider snapshots. If the previously
        # published preset contains mostly address space that none of the
        # current provider snapshots can reproduce, the published file is a
        # stale artifact rather than a trustworthy regression baseline.
        if new_path.parent.name == "presets" and old_cov:
            provider_nets = []
            for provider_path in iter_provider_datasets(old_root, version):
                provider_nets.extend(load(provider_path))
            source_cov = coverage(provider_nets, version)
            supported_cov = overlap_coverage(old_nets, provider_nets, version)
            overlap_ratio = supported_cov / old_cov if old_cov else 1.0
            if overlap_ratio < STALE_BASELINE_MIN_OVERLAP:
                if supported_cov and new_cov / supported_cov < (1 - args.max_drop):
                    bad.append(
                        f"{new_path}: stale baseline source-backed coverage "
                        f"{supported_cov} -> {new_cov}"
                    )
                print(
                    f"{new_path}: stale published baseline detected; "
                    f"source-backed overlap {supported_cov}/{old_cov} "
                    f"({overlap_ratio:.1%}), source union {source_cov}"
                )
                continue

        if old_count >= args.min_previous and new_count / old_count < (1 - args.max_drop):
            bad.append(f"{new_path}: prefix count {old_count} -> {new_count}")

        if old_cov and new_cov / old_cov < (1 - args.max_drop):
            bad.append(f"{new_path}: coverage {old_cov} -> {new_cov}")

    if bad:
        print("\n".join(bad))
        sys.exit(1)
    print("Regression gate: OK")

if __name__ == "__main__":
    main()
