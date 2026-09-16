#!/usr/bin/env python3
"""Static audit of unattended automation safety invariants."""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/update.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")

REQUIRED = {
    "scheduled updates": 'schedule:',
    "concurrency": 'concurrency:',
    "write permission": 'contents: write',
    "unit tests": 'python -m unittest discover',
    "source health": 'python scripts/check_source_health.py',
    "subscription validation": 'python scripts/validate_subscriptions.py',
    "link validation": 'python scripts/check_links.py',
    "rollback guard": 'python scripts/rollback_guard.py',
    "network evidence": 'python scripts/network_evidence.py',
    "failure notification": 'Autonomous failure notification',
    "conditional publish": 'git commit -m "chore: update provider subscriptions"',
}
FORBIDDEN = {
    "force push": "git push --force",
    "hard reset": "git reset --hard",
    "unconditional destructive cleanup": "rm -rf data/",
}

missing = [name for name, token in REQUIRED.items() if token not in TEXT]
forbidden = [name for name, token in FORBIDDEN.items() if token in TEXT]

if missing or forbidden:
    if missing:
        print("Missing automation gates:", ", ".join(missing))
    if forbidden:
        print("Forbidden workflow operations:", ", ".join(forbidden))
    sys.exit(1)

print(f"Autonomous audit: PASS ({len(REQUIRED)} required gates, {len(FORBIDDEN)} forbidden patterns checked)")
