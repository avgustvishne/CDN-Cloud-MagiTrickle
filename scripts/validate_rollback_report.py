#!/usr/bin/env python3
"""Fail if the generated rollback report says publication must be held."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "data/rollback-report.json"

def main() -> int:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("guarded"):
        print("publication held by rollback guard")
        return 1
    print("Autonomous safety gate: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
