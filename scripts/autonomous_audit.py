#!/usr/bin/env python3
"""Static audit of unattended automation safety invariants."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/update.yml"
STATUS_WORKFLOW = ROOT / ".github/workflows/status.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
STATUS_TEXT = STATUS_WORKFLOW.read_text(encoding="utf-8") if STATUS_WORKFLOW.exists() else ""

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
    "conditional publish": 'git commit -m "chore: update provider subscriptions"',
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
}

missing = [name for name, token in REQUIRED.items() if token not in TEXT]
missing_status = [name for name, token in STATUS_REQUIRED.items() if token not in STATUS_TEXT]
forbidden = [name for name, token in FORBIDDEN.items() if token in TEXT or token in STATUS_TEXT]

if missing or missing_status or forbidden:
    if missing:
        print("Missing automation gates:", ", ".join(missing))
    if missing_status:
        print("Missing status automation gates:", ", ".join(missing_status))
    if forbidden:
        print("Forbidden workflow operations:", ", ".join(forbidden))
    sys.exit(1)

print(
    f"Autonomous audit: PASS ({len(REQUIRED)} update gates, "
    f"{len(STATUS_REQUIRED)} status gates, {len(FORBIDDEN)} forbidden patterns checked)"
)
