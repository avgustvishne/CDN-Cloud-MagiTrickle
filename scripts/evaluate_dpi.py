#!/usr/bin/env python3
"""Classify Hyperion TCP 16-20 endpoint results and assign a 0-100 DPI score."""
import argparse
import json
import pathlib
import re

LINE = re.compile(
    r"DPI checking\(#(?P<node>[^)]+)\)/INFO: (?P<body>.*?), reqtime: (?P<ms>[0-9.]+) ms"
)
ALIVE = re.compile(r"alived: (?P<state>yes|no|unknown)")
TCP = re.compile(r"tcp 16-20: (?P<state>not detected|detected|possible detected|unlikely)")

TCP_RANK = {
    "unknown": 0,
    "not detected": 1,
    "unlikely": 2,
    "possible detected": 3,
    "detected": 4,
}


def score_and_class(alive, tcp, latency_ms):
    """Return (score, class) using DPI first, then liveness and latency."""
    if alive == "no":
        return 0, "dead"
    if tcp == "detected":
        return 0, "blocked"
    if tcp == "possible detected":
        return 45, "backup"
    if tcp == "unlikely":
        return 60, "backup"
    if tcp == "not detected":
        if latency_ms <= 1000:
            return 100, "best"
        if latency_ms <= 2000:
            return 95, "best"
        if latency_ms <= 5000:
            return 85, "good"
        if latency_ms <= 8000:
            return 70, "slow"
        return 50, "backup"
    return 25 if alive == "yes" else 0, "unknown"


def parse_log(path):
    endpoints = {}
    for raw in pathlib.Path(path).read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        match = LINE.search(raw)
        if not match:
            continue

        node = match.group("node")
        body = match.group("body")
        latency = float(match.group("ms"))

        entry = endpoints.setdefault(
            node,
            {
                "alive": "unknown",
                "tcp": "unknown",
                "latency_ms": None,
                "_tcp_rank": 0,
                "_tcp_latency": None,
                "_alive_latency": None,
            },
        )

        alive = ALIVE.search(body)
        if alive:
            state = alive.group("state")
            # Prefer a definitive liveness result.
            if state == "no" or entry["alive"] == "unknown":
                entry["alive"] = state
            entry["_alive_latency"] = latency

        tcp = TCP.search(body)
        if tcp:
            state = tcp.group("state")
            rank = TCP_RANK[state]
            # Keep the strongest TCP finding seen for this endpoint.
            if rank >= entry["_tcp_rank"]:
                entry["tcp"] = state
                entry["_tcp_rank"] = rank
                entry["_tcp_latency"] = latency

    for entry in endpoints.values():
        entry["latency_ms"] = (
            entry["_tcp_latency"]
            if entry["_tcp_latency"] is not None
            else entry["_alive_latency"]
        )
        score, classification = score_and_class(
            entry["alive"], entry["tcp"], entry["latency_ms"] or 0
        )
        entry["score"] = score
        entry["class"] = classification
        for key in ("_tcp_rank", "_tcp_latency", "_alive_latency"):
            entry.pop(key, None)

    return endpoints


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("-o", "--output", default="data/dpi-endpoints.json")
    args = parser.parse_args()

    endpoints = parse_log(args.log)
    ordered = dict(
        sorted(
            endpoints.items(),
            key=lambda item: (-item[1]["score"], item[0]),
        )
    )

    summary = {}
    for value in ordered.values():
        summary[value["class"]] = summary.get(value["class"], 0) + 1

    output = {
        "version": 2,
        "score_scale": "0-100",
        "summary": summary,
        "endpoints": ordered,
    }

    target = pathlib.Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("DPI endpoints:", len(ordered))
    print("Summary:", json.dumps(summary, ensure_ascii=False))
    for name, value in list(ordered.items())[:10]:
        print(
            f'{value["score"]:3d} {value["class"]:7s} '
            f'{name} {value["latency_ms"]:.1f} ms'
        )


if __name__ == "__main__":
    main()
