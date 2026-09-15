#!/usr/bin/env python3
"""Generate SHA-256 checksums for published subscription files."""
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "checksums.sha256"

files = sorted(
    list(DATA.glob("*-v*.txt")) +
    list((DATA / "presets").glob("*.txt"))
)
lines = []
for path in files:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Checksums: {len(lines)}")
