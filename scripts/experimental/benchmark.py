#!/usr/bin/env python3
"""Experimental benchmark for the stable generator.

This is a measurement tool only. It does not publish results or modify the
working tree. It runs the stable generator in isolated temporary copies and
reports wall time, output file count/bytes, and HTTP request counters when
the generator exposes them in its log.
"""
from __future__ import annotations
import pathlib, re, shutil, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "update_cdn_lists.py"

def run_once() -> tuple[float, int, int, str]:
    with tempfile.TemporaryDirectory(prefix="cdn-bench-") as tmp:
        work = pathlib.Path(tmp) / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        start = time.perf_counter()
        p = subprocess.run(
            [sys.executable, str(work / "scripts" / "update_cdn_lists.py")],
            cwd=work, text=True, capture_output=True
        )
        elapsed = time.perf_counter() - start
        if p.returncode:
            raise RuntimeError((p.stdout + "\n" + p.stderr)[-6000:])
        files = [x for x in (work / "data").rglob("*") if x.is_file()]
        total = sum(x.stat().st_size for x in files)
        log = p.stdout + "\n" + p.stderr
        return elapsed, len(files), total, log

def main() -> int:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if runs < 1 or runs > 5:
        print("runs must be 1..5")
        return 2

    print("EXPERIMENTAL BENCHMARK — no publication")
    for i in range(runs):
        try:
            elapsed, count, total, log = run_once()
        except Exception as e:
            print(f"run {i+1}: FAILED")
            print(e)
            return 1
        reqs = len(re.findall(r"\b(?:GET|POST|HEAD)\b", log))
        print(f"run {i+1}: {elapsed:.2f}s | files={count} | bytes={total} | logged_http_methods={reqs}")

    print("Note: request count is best-effort and only counts HTTP verbs visible in logs.")
    print("Use this benchmark to establish the stable baseline before implementing incremental caching.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
