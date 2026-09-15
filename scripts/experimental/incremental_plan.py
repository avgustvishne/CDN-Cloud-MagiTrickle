#!/usr/bin/env python3
"""Experimental incremental planner.

This module is intentionally isolated from update_cdn_lists.py. It never publishes
data and never changes the stable generator. It only decides which provider
datasets could be rebuilt from source hashes.
"""
from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
STATE = DATA / ".experimental-state.json"
PROVIDERS = DATA / "providers"

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> None:
    current = {}
    if PROVIDERS.exists():
        for p in sorted(PROVIDERS.glob("*")):
            if p.is_file():
                current[p.name] = sha256(p)

    previous = {}
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))

    changed = sorted(k for k, v in current.items() if previous.get(k) != v)
    removed = sorted(k for k in previous if k not in current)
    unchanged = sorted(k for k in current if previous.get(k) == current[k])

    print("EXPERIMENTAL ONLY — no publication")
    print(f"changed: {len(changed)}")
    print(f"unchanged: {len(unchanged)}")
    print(f"removed: {len(removed)}")
    for name in changed:
        print(f"BUILD {name}")
    for name in removed:
        print("REMOVE " + name)
    # Intentionally read-only: the experiment never writes its state file.

if __name__ == "__main__":
    main()
