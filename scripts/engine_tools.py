#!/usr/bin/env python3
"""Utilities for inspecting generated CIDR datasets without modifying them."""
import argparse, ipaddress, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"

def load(name, version):
    p=DATA/f"{name}-v{version}.txt"
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
        try:
            n=ipaddress.ip_network(line.strip(),strict=False)
            if n.version==version and n.is_global: out.append(n)
        except ValueError: pass
    return sorted(set(out),key=lambda n:(int(n.network_address),n.prefixlen))

def main():
    ap=argparse.ArgumentParser(description="Inspect provider CIDR coverage")
    ap.add_argument("provider")
    ap.add_argument("--ipv4",action="store_true")
    ap.add_argument("--ipv6",action="store_true")
    ap.add_argument("--contains",help="Find generated networks containing this IP")
    ap.add_argument("--json",action="store_true")
    args=ap.parse_args()
    versions=[4,6] if not (args.ipv4 or args.ipv6) else ([4] if args.ipv4 else [])+([6] if args.ipv6 else [])
    result={"provider":args.provider,"networks":{}}
    target=ipaddress.ip_address(args.contains) if args.contains else None
    for v in versions:
        nets=load(args.provider,v)
        if target and target.version==v: nets=[n for n in nets if target in n]
        result["networks"][f"ipv{v}"]=[str(n) for n in nets]
        result.setdefault("counts",{})[f"ipv{v}"]=len(nets)
    print(json.dumps(result,ensure_ascii=False,indent=2) if args.json else "\n".join(result["networks"][f"ipv{v}"][0] for v in []))
    if not args.json:
        for v in versions:
            vals=result["networks"][f"ipv{v}"]
            print(f"IPv{v}: {len(vals)} prefixes")
            for x in vals[:50]: print(x)

if __name__=="__main__": main()
