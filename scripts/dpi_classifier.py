#!/usr/bin/env python3
"""Classify MagiTrickle DPI-check log lines.

This is a diagnostic/reporting helper only. It does not alter traffic,
probe parameters, or attempt to bypass DPI.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

LINE_RE = re.compile(
    r"DPI checking\(#(?P<node>[^)]+)\)/INFO: (?P<msg>.*)$"
)

def classify_message(message: str) -> str:
    m = message.lower()
    if "tcp 16-20: possible detected" in m:
        return "possible"
    if "tcp 16-20: detected" in m:
        return "detected"
    if "tcp 16-20: unlikely" in m:
        return "unlikely"
    if "tcp 16-20: not detected" in m:
        return "safe"
    if "alived: no" in m:
        return "dead"
    if "alived: yes" in m:
        return "alive"
    if "alived: unknown" in m:
        return "unknown"
    return "other"

RANK = {
    "detected": 6,
    "possible": 5,
    "unlikely": 4,
    "safe": 3,
    "dead": 2,
    "alive": 1,
    "unknown": 0,
    "other": 0,
}

def parse(lines):
    nodes = defaultdict(lambda: {
        "status": "unknown",
        "observations": 0,
        "methods": [],
        "messages": [],
    })
    for line in lines:
        match = LINE_RE.search(line.strip())
        if not match:
            continue
        node = match.group("node")
        message = match.group("msg")
        status = classify_message(message)
        item = nodes[node]
        item["observations"] += 1
        item["messages"].append(message)
        if status == "detected":
            method = re.search(r"method:\s*(\d+)", message, re.I)
            if method and method.group(1) not in item["methods"]:
                item["methods"].append(method.group(1))
        if RANK[status] > RANK[item["status"]]:
            item["status"] = status

    counts = defaultdict(int)
    for item in nodes.values():
        counts[item["status"]] += 1

    return {
        "nodes": dict(sorted(nodes.items())),
        "counts": dict(sorted(counts.items())),
    }

def main():
    parser = argparse.ArgumentParser(description="Classify MagiTrickle DPI-check logs")
    parser.add_argument("log", type=Path, help="path to a MagiTrickle log")
    parser.add_argument("-o", "--output", type=Path, help="write JSON report")
    args = parser.parse_args()

    report = parse(args.log.read_text(encoding="utf-8", errors="replace").splitlines())
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()
