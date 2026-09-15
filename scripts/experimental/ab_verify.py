#!/usr/bin/env python3
"""Experimental A/B verifier for the stable generator.

Runs the stable generator in an isolated temporary copy and compares the
generated subscription artifacts with a reference snapshot. It never publishes.
"""
from __future__ import annotations
import hashlib, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts" / "update_cdn_lists.py"
DATA = ROOT / "data"
DEFAULT_REFERENCE = DATA / "ab-reference"

def digest_tree(root: pathlib.Path) -> dict[str, str]:
    out = {}
    if not root.exists():
        return out
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        out[str(p.relative_to(root))] = h
    return out

def main() -> int:
    reference = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REFERENCE
    if not reference.exists():
        print(f"AB-TEST: reference not found: {reference}")
        print("Create a reference snapshot from a known-good stable run first.")
        return 2

    with tempfile.TemporaryDirectory(prefix="cdn-ab-") as tmp:
        work = pathlib.Path(tmp) / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        result = subprocess.run(
            [sys.executable, str(work / "scripts" / "update_cdn_lists.py")],
            cwd=work, text=True, capture_output=True
        )
        if result.returncode:
            print("AB-TEST: stable generator failed")
            print(result.stdout[-4000:])
            print(result.stderr[-4000:])
            return result.returncode

        actual = digest_tree(work / "data")
        expected = digest_tree(reference)
        # Ignore runtime metadata that is expected to differ between runs.
        ignored = {"manifest.json", "release-notes.md", "change-summary.json",
                   "checksums.sha256", ".experimental-state.json"}
        actual = {k:v for k,v in actual.items() if pathlib.Path(k).name not in ignored}
        expected = {k:v for k,v in expected.items() if pathlib.Path(k).name not in ignored}

        added = sorted(set(actual) - set(expected))
        removed = sorted(set(expected) - set(actual))
        changed = sorted(k for k in set(actual) & set(expected) if actual[k] != expected[k])

        print("EXPERIMENTAL A/B TEST — no publication")
        print(f"identical: {not (added or removed or changed)}")
        print(f"added: {len(added)}")
        print(f"removed: {len(removed)}")
        print(f"changed: {len(changed)}")
        for k in changed[:50]:
            print(f"DIFF {k}")

        return 0 if not (added or removed or changed) else 1

if __name__ == "__main__":
    raise SystemExit(main())
