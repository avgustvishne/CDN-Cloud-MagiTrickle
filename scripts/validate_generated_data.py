#!/usr/bin/env python3
"""Validate generated data artifacts and publication invariants in one place."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OBSOLETE = (
    "cdn-cloud-v4.txt",
    "cdn-cloud-v6.txt",
    "dpi-recommended-v4.txt",
    "dpi-recommended-v6.txt",
    "lite-v4.txt",
    "lite-v6.txt",
)
REQUIRED_PROFILES = (
    "full-v4.txt", "full-v6.txt",
    "performance-v4.txt", "performance-v6.txt",
    "balanced-v4.txt", "balanced-v6.txt",
    "minimal-v4.txt", "minimal-v6.txt",
    "stable-v4.txt", "stable-v6.txt",
    "cdn-v4.txt", "cdn-v6.txt",
    "cloud-v4.txt", "cloud-v6.txt",
    "video-v4.txt", "video-v6.txt",
    "vpn-v4.txt", "vpn-v6.txt",
)


def load_json(name: str):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8"))


def validate_generated_data() -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    for name in ("all-cloud-v4.txt", "all-cloud-v6.txt", "asn-all-v4.txt", "asn-all-v6.txt"):
        require((DATA / name).exists(), f"missing aggregate: {name}")
    for name in ("all-cloud-v4.txt", "asn-all-v4.txt"):
        require((DATA / name).stat().st_size > 0, f"empty aggregate: {name}")

    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    provider_names = set(cfg["providers"])
    generated_names = {
        p.name[:-7]
        for p in DATA.glob("*-v4.txt")
        if p.name not in {"all-cloud-v4.txt", "asn-all-v4.txt", "asn-confirmed-v4.txt"}
    }
    require(
        generated_names == provider_names,
        f"provider files mismatch: generated={sorted(generated_names)} config={sorted(provider_names)}",
    )

    for name in OBSOLETE:
        require(not (DATA / name).exists(), f"obsolete file remains: {name}")

    for name in REQUIRED_PROFILES:
        path = DATA / "presets" / name
        require(path.exists() and path.stat().st_size > 0, f"missing/empty profile: {name}")

    summary = load_json("change-summary.json")
    require(isinstance(summary.get("datasets"), dict), "change-summary.json: datasets must be an object")

    notes = (DATA / "release-notes.md").read_text(encoding="utf-8")
    require(notes.startswith("## Subscription update — v"), "release-notes.md: invalid header")

    manifest = load_json("manifest.json")
    require(manifest.get("global_only") is True, "manifest.global_only must be true")
    require(manifest.get("engine") == "final-v44-source-fusion-ipverse", "manifest.engine changed")
    require(manifest.get("min_provider_prefixes") is None, "manifest.min_provider_prefixes must be null")
    require(manifest.get("max_provider_prefixes") is None, "manifest.max_provider_prefixes must be null")
    require(
        manifest.get("min_prefixlen") == {"ipv4": 8, "ipv6": 16},
        "manifest.min_prefixlen changed",
    )
    require(manifest.get("aggregate", {}).get("ipv4", 0) > 0, "manifest.aggregate.ipv4 must be positive")
    require(manifest.get("aggregate", {}).get("ipv6", 0) >= 0, "manifest.aggregate.ipv6 must be non-negative")

    audit = load_json("source-audit.json")
    require(
        str(audit.get("method", "")).startswith("exact merged address-space"),
        "source-audit.method changed",
    )
    require(isinstance(audit.get("providers"), list), "source-audit.providers must be a list")
    require(isinstance(audit.get("sources"), dict), "source-audit.sources must be an object")

    network = load_json("network-evidence.json")
    require(network.get("schema_version") == 1, "network-evidence schema_version changed")
    policy = network.get("policy", {})
    for key in ("rpki_invalid_deletes_prefix", "bgp_absence_deletes_prefix", "irr_absence_deletes_prefix"):
        require(policy.get(key) is False, f"network-evidence.policy.{key} must remain false")
    require(network.get("queried", 0) <= policy.get("max_prefixes", 0), "network evidence query limit exceeded")
    require(isinstance(network.get("evidence"), list), "network-evidence.evidence must be a list")

    intelligence = load_json("source-intelligence.json")
    require(intelligence.get("schema_version") == 2, "source-intelligence schema_version changed")
    ipolicy = intelligence.get("policy", {})
    cpolicy = intelligence.get("change_policy", {})
    require(ipolicy.get("mutates_subscriptions") is False, "source intelligence may not mutate subscriptions")
    require(ipolicy.get("source_failure_replaces_data") is False, "source failure may not replace data")
    require(cpolicy.get("min_confirming_sources") == 2, "minimum confirming sources changed")
    require(cpolicy.get("confirmed_changes_are_not_auto_published") is True, "confirmed changes publication policy changed")
    require(cpolicy.get("coverage_metric") == "exact_union_address_space", "coverage metric changed")
    require(isinstance(intelligence.get("sources"), list), "source-intelligence.sources must be a list")
    require(isinstance(intelligence.get("providers"), dict), "source-intelligence.providers must be an object")
    require(isinstance(intelligence.get("anomalies"), list), "source-intelligence.anomalies must be a list")
    require(isinstance(intelligence.get("prefix_evidence"), list), "source-intelligence.prefix_evidence must be a list")

    for provider, item in intelligence.get("providers", {}).items():
        coverage = item.get("coverage", {})
        require(set(coverage) == {"ipv4", "ipv6"}, f"{provider}: invalid coverage keys")
        require(
            all(isinstance(coverage.get(family), int) and coverage[family] >= 0 for family in ("ipv4", "ipv6")),
            f"{provider}: invalid coverage values",
        )
    for evidence in intelligence.get("prefix_evidence", []):
        require(
            evidence.get("source_count") == len(evidence.get("sources", [])),
            "prefix evidence source_count mismatch",
        )
        require(evidence.get("status") in {"confirmed", "single_source"}, "invalid prefix evidence status")
    for source in intelligence.get("sources", []):
        score = source.get("reliability_score")
        require(isinstance(score, (int, float)) and 0 <= score <= 100, "invalid source reliability score")

    history_path = DATA / "source-intelligence-history.json"
    require(history_path.exists(), "source-intelligence-history.json missing")
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
        require(isinstance(history, list) and len(history) <= 30, "source intelligence history must contain <=30 entries")

    overlaps = load_json("provider-overlaps.json")
    require(isinstance(overlaps.get("entries"), list), "provider-overlaps.entries must be a list")
    require(overlaps.get("exact_cross_provider_overlaps", 0) >= 0, "invalid provider overlap count")

    checksums = DATA / "checksums.sha256"
    require(checksums.exists() and checksums.read_text(encoding="utf-8").strip(), "checksums.sha256 is missing/empty")
    if checksums.exists():
        for line_no, row in enumerate(checksums.read_text(encoding="utf-8").splitlines(), 1):
            try:
                digest, rel = row.split("  ", 1)
            except ValueError:
                errors.append(f"checksums.sha256:{line_no}: invalid row")
                continue
            path = ROOT / rel
            if not path.exists():
                errors.append(f"checksums.sha256:{line_no}: missing {rel}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append(f"checksums.sha256:{line_no}: checksum mismatch: {rel}")

    return errors


def validate_readme_statistics() -> list[str]:
    errors: list[str] = []
    stats = load_json("statistics.json")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(r"<!-- AUTO-STATS:START -->.*?<!-- AUTO-STATS:END -->", readme, re.DOTALL)
    if not block:
        errors.append("README AUTO-STATS block is missing")
        return errors
    if "Актуальная статистика" not in block.group(0):
        errors.append("README AUTO-STATS heading is missing")
    if stats.get("source_of_truth") != "published normalized CIDR files":
        errors.append("statistics.source_of_truth changed")
    for name in ("full-v4", "full-v6", "balanced-v4", "balanced-v6", "minimal-v4", "minimal-v6"):
        item = stats.get("profiles", {}).get(name)
        if not item or item.get("cidr_count", 0) <= 0:
            errors.append(f"statistics profile missing/empty: {name}")
    return errors


def main() -> int:
    include_readme = "--include-readme-statistics" in sys.argv[1:]
    errors = validate_generated_data()
    if include_readme:
        errors += validate_readme_statistics()
    if errors:
        print("\n".join(errors))
        return 1
    print("Generated data validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
