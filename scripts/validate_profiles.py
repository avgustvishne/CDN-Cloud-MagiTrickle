#!/usr/bin/env python3
"""Validate generated profile policy and stability invariants."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/profile-intelligence.json"

def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_profiles import PROFILE_POLICY_VERSION

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    errors = []

    if report.get("schema_version") != 1:
        errors.append("profile-intelligence schema_version changed")
    if report.get("policy_version") != PROFILE_POLICY_VERSION:
        errors.append(
            f"profile-intelligence policy_version={report.get('policy_version')!r} "
            f"but generator defines {PROFILE_POLICY_VERSION!r}"
        )
    if report.get("anomalies") != []:
        errors.append("profile-intelligence contains anomalies")

    order = ("minimal", "performance", "balanced", "full")
    profiles = report.get("profiles", {})
    for family in (4, 6):
        previous = None
        for name in order:
            key = f"{name}-v{family}"
            item = profiles.get(key, {})
            for metric in ("prefixes", "coverage_ips", "coverage_per_prefix"):
                if item.get(metric, 0) <= 0:
                    errors.append(f"{key}: {metric} must be positive")
            if previous is not None and item.get("is_superset") is not True:
                errors.append(f"{key}: profile ladder is not a superset of {previous}")
            previous = key

    stable = report.get("stability_profile", {}).get("profiles", {})
    for family in (4, 6):
        key = f"stable-v{family}"
        item = stable.get(key, {})
        if item.get("bootstrap") not in {True, False}:
            errors.append(f"{key}: bootstrap flag missing")
        if item.get("previous_coverage_ips", 0) < item.get("retained_coverage_ips", 0):
            errors.append(f"{key}: retained coverage exceeds previous coverage")
        if item.get("bootstrap") is False and item.get("retention_coverage_ratio") is None:
            errors.append(f"{key}: non-bootstrap profile lacks retention ratio")

    if errors:
        print("\n".join(errors))
        return 1
    print("Profile intelligence validation: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
