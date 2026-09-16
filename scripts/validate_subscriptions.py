#!/usr/bin/env python3
"""Validate published CIDR subscription files."""
import ipaddress,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
files=list((ROOT/"data").glob("*.txt"))+list((ROOT/"data"/"presets").glob("*.txt"))
bad=[]
for p in files:
    if p.name=="last-update.txt": continue
    seen=set()
    expected=6 if p.name.endswith("-v6.txt") else 4
    for line_no,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
        s=line.strip()
        if not s or s.startswith("#"): continue
        try:n=ipaddress.ip_network(s,strict=False)
        except ValueError: bad.append(f"{p}:{line_no}: invalid CIDR {s}"); continue
        if n.version!=expected: bad.append(f"{p}:{line_no}: wrong IP version")
        if not n.is_global: bad.append(f"{p}:{line_no}: non-global prefix {s}")
        if n.prefixlen < (8 if n.version==4 else 16): bad.append(f"{p}:{line_no}: overly broad prefix {s}")
        if s in seen: bad.append(f"{p}:{line_no}: duplicate {s}")
        seen.add(s)
    if p.stat().st_size==0: bad.append(f"{p}: empty")
if bad:
    print("\n".join(bad));sys.exit(1)
print(f"Validated {len(files)} subscription files: OK")
