#!/usr/bin/env python3
"""Regression gate: reject catastrophic provider shrink after regeneration."""
import argparse,ipaddress,pathlib,sys

def load(path):
    if not path.exists(): return []
    out=[]
    for s in path.read_text(encoding="utf-8").splitlines():
        s=s.strip()
        if s and not s.startswith("#"):
            try: out.append(ipaddress.ip_network(s,strict=False))
            except ValueError: pass
    return out

def coverage(nets):
    # Exact integer address-space sum is safe because generated CIDRs are deduplicated.
    return sum(n.num_addresses for n in nets)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("old");ap.add_argument("new");args=ap.parse_args()
    old=pathlib.Path(args.old);new=pathlib.Path(args.new)
    bad=[]
    for p in sorted(new.glob("*-v4.txt")):
        if p.name in {"all-cloud-v4.txt","asn-all-v4.txt","asn-confirmed-v4.txt"}: continue
        op=old/p.name
        if not op.exists(): continue
        on,nn=load(op),load(p)
        oc,nc=coverage(on),coverage(nn)
        if len(on)>=20 and len(nn)/len(on)<0.20:
            bad.append(f"{p.name}: CIDR count collapsed {len(on)} -> {len(nn)}")
        if oc and nc/oc<0.20:
            bad.append(f"{p.name}: IPv4 coverage collapsed {oc} -> {nc}")
    for p in sorted(new.glob("*-v6.txt")):
        if p.name in {"all-cloud-v6.txt","asn-all-v6.txt","asn-confirmed-v6.txt"}: continue
        op=old/p.name
        if not op.exists(): continue
        on,nn=load(op),load(p);oc,nc=coverage(on),coverage(nn)
        if len(on)>=20 and len(nn)/len(on)<0.20: bad.append(f"{p.name}: CIDR count collapsed {len(on)} -> {len(nn)}")
        if oc and nc/oc<0.20: bad.append(f"{p.name}: IPv6 coverage collapsed")
    if bad:
        print("\n".join(bad));sys.exit(1)
    print("Regression gate: OK")
if __name__=="__main__":main()
