#!/usr/bin/env python3
"""Refresh the checksum manifest for published CIDR datasets."""
from __future__ import annotations

import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def main() -> int:
    files = sorted(
        set(DATA.glob("*-v*.txt"))
        | {
            DATA / "all-cloud-v4.txt",
            DATA / "all-cloud-v6.txt",
            DATA / "asn-all-v4.txt",
            DATA / "asn-all-v6.txt",
            DATA / "asn-confirmed-v4.txt",
            DATA / "asn-confirmed-v6.txt",
        }
    )
    files = [path for path in files if path.exists()]
    manifest = "\n".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        for path in files
    ) + "\n"
    (DATA / "checksums.sha256").write_text(manifest, encoding="utf-8")
    print(f"Checksums refreshed: {len(files)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
