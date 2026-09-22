#!/usr/bin/env python3
"""Generate a compact human-readable changelog from provider diffs."""
import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIFF = DATA / "diff"
MANIFEST = DATA / "manifest.json"
OUT = DATA / "release-notes.md"
CHANGELOG = ROOT / "CHANGELOG.md"
CHANGELOG_HEADER = "# Changelog\n\nAutomated log of provider CIDR changes, most recent entry first. Runs with no provider changes are not recorded here; the full report for the latest run always lives in `data/release-notes.md`."
CHANGELOG_SEPARATOR = "\n\n---\n\n"
CHANGELOG_MAX_ENTRIES = 200

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
rows = []
for path in sorted(DIFF.glob("*.json")):
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    added = item.get("added", {})
    removed = item.get("removed", {})
    if any(added.get(k, 0) or removed.get(k, 0) for k in ("ipv4", "ipv6")):
        rows.append(
            f"| {item.get('provider', path.stem)} | "
            f"+{added.get('ipv4', 0)} / -{removed.get('ipv4', 0)} | "
            f"+{added.get('ipv6', 0)} / -{removed.get('ipv6', 0)} |"
        )

generated_at = manifest.get("updated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

lines = [
    f"## Subscription update — v{manifest.get('version', '?')} · {generated_at}",
    "",
    f"Generated: {generated_at}",
    "",
    f"- Aggregate IPv4: **{manifest.get('aggregate', {}).get('ipv4', 0):,}**",
    f"- Aggregate IPv6: **{manifest.get('aggregate', {}).get('ipv6', 0):,}**",
    "",
]
if rows:
    lines += [
        "### Changes",
        "",
        "| Provider | IPv4 (+ / -) | IPv6 (+ / -) |",
        "|---|---:|---:|",
        *rows,
        "",
    ]
else:
    lines += ["## Changes", "", "No provider CIDR changes detected.", ""]

lines += [
    "### Safety",
    "",
    "- Global prefixes only",
    "- Minimum prefix length: IPv4 /8, IPv6 /16",
    "- Generated subscriptions are validated before publication",
    "- SHA-256 checksums are regenerated with every update",
    "",
]
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT}")

def prepend_changelog(entry_text, max_entries=CHANGELOG_MAX_ENTRIES):
    entry_text = entry_text.strip()
    body = ""
    if CHANGELOG.exists():
        existing = CHANGELOG.read_text(encoding="utf-8")
        _, _, body = existing.partition("\n\n")
    old_entries = [e.strip() for e in body.split(CHANGELOG_SEPARATOR) if e.strip()] if body else []
    entries = ([entry_text] + old_entries)[:max_entries]
    CHANGELOG.write_text(CHANGELOG_HEADER + "\n\n" + CHANGELOG_SEPARATOR.join(entries) + "\n", encoding="utf-8")

if rows:
    prepend_changelog("\n".join(lines))
    print(f"Updated {CHANGELOG}")
else:
    print("No provider changes; CHANGELOG.md left untouched")
