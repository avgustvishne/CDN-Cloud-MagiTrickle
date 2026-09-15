#!/usr/bin/env python3
"""Classify Hyperion DPI log endpoints into best/good/slow/backup/blocked/dead/unknown."""
import argparse, json, pathlib, re

LINE = re.compile(
    r"DPI checking\(#(?P<node>[^)]+)\)/INFO: (?P<body>.*?), reqtime: (?P<ms>[0-9.]+) ms"
)
ALIVE = re.compile(r"alived: (?P<state>yes|no|unknown)")
TCP = re.compile(r"tcp 16-20: (?P<state>not detected|detected|possible detected|unlikely)")

def classify(alive, tcp, ms):
    if alive == "no":
        return "dead"
    if tcp == "detected":
        return "blocked"
    if tcp in ("possible detected", "unlikely"):
        return "backup"
    if tcp == "not detected":
        if ms <= 2000:
            return "best"
        if ms <= 5000:
            return "good"
        if ms <= 8000:
            return "slow"
        return "backup"
    return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("-o", "--output", default="data/dpi-endpoints.json")
    args = ap.parse_args()
    states = {}
    for raw in pathlib.Path(args.log).read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE.search(raw)
        if not m:
            continue
        node, body, ms = m.group("node"), m.group("body"), float(m.group("ms"))
        alive = ALIVE.search(body)
        tcp = TCP.search(body)
        a = alive.group("state") if alive else None
        t = tcp.group("state") if tcp else None
        # Keep the strongest TCP result; alive is retained as a separate signal.
        score = {"detected": 5, "possible detected": 4, "unlikely": 3, "not detected": 2}.get(t, 0)
        prev = states.get(node)
        if prev and (prev["tcp_rank"] > score or (prev["tcp_rank"] == score and prev["latency_ms"] <= ms)):
            continue
        states[node] = {
            "alive": a or (prev["alive"] if prev else "unknown"),
            "tcp": t or (prev["tcp"] if prev else "unknown"),
            "latency_ms": ms,
            "class": classify(a or (prev["alive"] if prev else "unknown"), t or (prev["tcp"] if prev else None), ms),
            "tcp_rank": score
        }
    for v in states.values():
        v.pop("tcp_rank", None)
    counts = {}
    for v in states.values():
        counts[v["class"]] = counts.get(v["class"], 0) + 1
    out = {"version": 1, "summary": counts, "endpoints": dict(sorted(states.items()))}
    p = pathlib.Path(args.output); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DPI endpoints:", len(states), counts)

if __name__ == "__main__":
    main()
