#!/usr/bin/env python3
"""Generate SHA-256 checksums for published text subscriptions."""
import hashlib, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; OUT=DATA/"checksums.sha256"
files=sorted(p for p in DATA.rglob("*.txt") if p.name!="checksums.sha256")
lines=[]
for p in files:
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    lines.append(f"{h}  {p.relative_to(DATA)}")
OUT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print(f"Checksums: {len(lines)}")
