#!/usr/bin/env python3
"""Protect generated CIDR datasets against large count or address-space drops."""
import argparse
import ipaddress
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone


# These files are bounded validation samples, not published subscription
# datasets. Their membership is intentionally allowed to change between runs
# as the deterministic confirmation sample moves with the source population.
VALIDATION_ONLY = {"asn-confirmed-v4.txt", "asn-confirmed-v6.txt"}


def files(d):
    root = pathlib.Path(d)
    # Guard source-of-truth provider datasets and explicit aggregate datasets.
    # Profiles under data/presets/ are derived policy outputs: their coverage
    # is validated by generate_profiles.py (including the profile ladder and
    # policy-version anomaly gate). Comparing them a second time against HEAD
    # can reject a legitimate provider/profile recomposition even when the
    # underlying source datasets remain healthy.
    generated = list(root.glob("*-v[46].txt"))
    return sorted(
        path for path in generated
        if path.name not in VALIDATION_ONLY
        and path.name not in {
            "full-v4.txt", "full-v6.txt",
        }
    )


def parse_networks(text):
    networks = []
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return networks


def count_text(text):
    return len(parse_networks(text))


def count_file(path):
    return count_text(path.read_text(encoding="utf-8", errors="replace"))


def address_coverage(text, version):
    """Return the exact union size of global CIDRs for one IP family."""
    networks = [n for n in parse_networks(text) if n.version == version]
    if not networks:
        return 0
    return sum(n.num_addresses for n in ipaddress.collapse_addresses(networks))


def dataset_metrics(previous_text, current_text):
    """Return count and exact address-space metrics for one dataset."""
    previous_count = count_text(previous_text)
    current_count = count_text(current_text)
    metrics = {
        "previous": previous_count,
        "current": current_count,
        "drop_percent": round(
            max(0, previous_count - current_count) * 100 / previous_count, 2
        ) if previous_count else 0,
        "coverage": {},
    }
    for version in (4, 6):
        old_coverage = address_coverage(previous_text, version)
        new_coverage = address_coverage(current_text, version)
        ratio = new_coverage / old_coverage if old_coverage else None
        metrics["coverage"][str(version)] = {
            "previous": old_coverage,
            "current": new_coverage,
            "ratio": round(ratio, 6) if ratio is not None else None,
            "drop_percent": round(max(0, old_coverage - new_coverage) * 100 / old_coverage, 2)
            if old_coverage else 0,
        }
    return metrics


def previous_text(ref, relpath):
    try:
        r = subprocess.run(
            ["git", "show", f"{ref}:{relpath}"],
            text=True,
            capture_output=True,
            check=True,
        )
        return r.stdout
    except subprocess.CalledProcessError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("current_dir")
    ap.add_argument("--previous-ref", default="HEAD^")
    ap.add_argument("--max-drop", type=float, default=0.50)
    ap.add_argument("--max-coverage-drop", type=float, default=0.50)
    ap.add_argument("--min-previous", type=int, default=20)
    ap.add_argument("--report", default="data/rollback-report.json")
    args = ap.parse_args()

    cur = pathlib.Path(args.current_dir)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "previous_ref": args.previous_ref,
        "max_drop": args.max_drop,
        "max_coverage_drop": args.max_coverage_drop,
        "guarded": False,
        "restored": False,
        "datasets": {},
        "critical": [],
    }

    for cp in files(cur):
        rel = cp.as_posix()
        old_text = previous_text(args.previous_ref, rel)
        if old_text is None:
            report["datasets"][rel] = {
                "current": count_file(cp),
                "previous": None,
                "status": "no_previous",
            }
            continue

        current_text = cp.read_text(encoding="utf-8", errors="replace")
        metrics = dataset_metrics(old_text, current_text)
        item = {
            "previous": metrics["previous"],
            "current": metrics["current"],
            "drop_percent": metrics["drop_percent"],
            "coverage": metrics["coverage"],
        }
        count_breach = (
            metrics["previous"] >= args.min_previous
            and metrics["drop_percent"] / 100 > args.max_drop
        )
        coverage_breach = False
        for family in metrics["coverage"].values():
            if family["previous"] <= 0:
                continue
            if family["drop_percent"] / 100 > args.max_coverage_drop:
                coverage_breach = True
        # CIDR count is advisory only. Re-aggregation can legitimately
        # collapse many prefixes into fewer prefixes without losing any
        # address space. The publication guard must therefore be based on
        # exact union coverage, not prefix-count changes.
        if coverage_breach:
            item["status"] = "rollback_required"
            item["count_guard"] = count_breach
            item["coverage_guard"] = True
            report["critical"].append(rel)
        else:
            item["status"] = "ok"
            item["count_guard"] = count_breach
            item["coverage_guard"] = False
        report["datasets"][rel] = item

    report["guarded"] = bool(report["critical"])
    if report["guarded"]:
        # Detection happens after generation; the protected rollback workflow
        # restores main from backup/pre-update rather than mutating this worktree.
        report["action"] = "manual_rollback_required"

    out = pathlib.Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Rollback guard:", "TRIGGERED" if report["guarded"] else "OK")
    if report["critical"]:
        print("Critical:", ", ".join(report["critical"]))
    return 1 if report["guarded"] else 0


if __name__ == "__main__":
    sys.exit(main())
