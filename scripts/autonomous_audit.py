#!/usr/bin/env python3
"""Static audit of unattended automation safety invariants."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/update.yml"
STATUS_WORKFLOW = ROOT / ".github/workflows/status.yml"
STABLE_WORKFLOW = ROOT / ".github/workflows/stable-release.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
STATUS_TEXT = STATUS_WORKFLOW.read_text(encoding="utf-8") if STATUS_WORKFLOW.exists() else ""
STABLE_TEXT = STABLE_WORKFLOW.read_text(encoding="utf-8") if STABLE_WORKFLOW.exists() else ""

REQUIRED = {
    "scheduled updates": "schedule:",
    "concurrency": "concurrency:",
    "write permission": "contents: write",
    "unit tests": 'python -m unittest discover',
    "source health": "python scripts/check_source_health.py",
    "subscription validation": "python scripts/validate_subscriptions.py",
    "link validation": "python scripts/check_links.py",
    "rollback guard": "python scripts/rollback_guard.py",
    "network evidence": "python scripts/network_evidence.py",
    "failure notification": "Autonomous failure notification",
    "failure summary": "GITHUB_STEP_SUMMARY",
    "conditional publish": 'git commit -m "chore: update provider subscriptions"',
    "main-only automatic push": "branches: [main]",
    "automatic statistics": "python scripts/generate_statistics.py",
    "README statistics validation": "python scripts/validate_generated_data.py --include-readme-statistics",
    "central generated-data validation": "python scripts/validate_generated_data.py",
    "central profile validation": "python scripts/validate_profiles.py",
    "central checksum generation": "python scripts/refresh_checksums.py",
    "central rollback report validation": "python scripts/validate_rollback_report.py",
    "isolated publication job": "  publish:\n",
    "pinned Python minor": 'python-version: "3.12"',
}
STABLE_REQUIRED = {
    "stable checksum refresh": "data/checksums.sha256",
    "stable statistics refresh": "python scripts/generate_statistics.py",
    "stable README publication": "git add data/presets/stable-v4.txt data/presets/stable-v6.txt data/checksums.sha256 data/statistics.json README.md",
    "stable validation": "python scripts/validate_subscriptions.py",
}
STATUS_REQUIRED = {
    "status schedule": "schedule:",
    "status generator": "python scripts/status_report.py",
    "status actions read": "actions: read",
    "status write permission": "contents: write",
    "status schema validation": "Validate status schema",
    "status publication": "Commit status",
}
FORBIDDEN = {
    "force push": "git push --force",
    "hard reset": "git reset --hard",
    "unconditional destructive cleanup": "rm -rf data/",
    "issues write permission": "issues: write",
    "inline Python workflow blocks": "python - <<'PY'",
}

missing = [name for name, token in REQUIRED.items() if token not in TEXT]
missing_status = [name for name, token in STATUS_REQUIRED.items() if token not in STATUS_TEXT]
missing_stable = [name for name, token in STABLE_REQUIRED.items() if token not in STABLE_TEXT]
forbidden = [name for name, token in FORBIDDEN.items() if token in TEXT or token in STATUS_TEXT]

if missing or missing_status or missing_stable or forbidden:
    if missing:
        print("Missing automation gates:", ", ".join(missing))
    if missing_status:
        print("Missing status automation gates:", ", ".join(missing_status))
    if missing_stable:
        print("Missing stable automation gates:", ", ".join(missing_stable))
    if forbidden:
        print("Forbidden workflow operations:", ", ".join(forbidden))
    sys.exit(1)

print(
    f"Autonomous audit: PASS ({len(REQUIRED)} update gates, "
    f"{len(STATUS_REQUIRED)} status gates, {len(STABLE_REQUIRED)} stable gates, {len(FORBIDDEN)} forbidden patterns checked)"
)
