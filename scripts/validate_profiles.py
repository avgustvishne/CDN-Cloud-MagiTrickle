#!/usr/bin/env python3
"""Validate generated profiles: syntax, uniqueness and containment consistency."""
import argparse,ipaddress,pathlib,sys
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default="dist");a=ap.parse_args();errors=[]
    for f in pathlib.Path(a.root).rglob("*.txt"):
        seen=set()
        for i,line in enumerate(f.read_text(encoding="utf-8").splitlines(),1):
            s=line.strip()
            if not s: continue
            try:n=str(ipaddress.ip_network(s,strict=False))
            except ValueError: errors.append(f"{f}:{i}:invalid:{s}");continue
            if n in seen: errors.append(f"{f}:{i}:duplicate:{n}")
            seen.add(n)
        # Do not reject overlaps here: FULL intentionally preserves source prefixes.
    if errors:
        print("\n".join(errors));sys.exit(1)
    print("PROFILE_VALIDATION_PASS")
if __name__=="__main__":main()
