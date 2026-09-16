#!/usr/bin/env python3
"""Generate provider profiles with conservative FULL/BALANCED/MINIMAL modes.

FULL: every normalized unique source prefix.
BALANCED: mathematically safe CIDR collapse; never broadens coverage.
MINIMAL: collapse plus bounded prefix aggregation only when every address
inside the candidate is already covered by the input union. This means
MINIMAL cannot invent unverified addresses.
"""
import argparse,ipaddress,json,pathlib

def load(path):
    obj=json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return obj.get("records",obj) if isinstance(obj,dict) else obj

def nets(records):
    out={}
    for r in records:
        if not isinstance(r,dict) or not r.get("cidr"): continue
        p=r.get("provider","unknown")
        try: out.setdefault(p,[]).append(ipaddress.ip_network(r["cidr"],strict=False))
        except (ValueError,TypeError): pass
    return {p:sorted(set(v),key=lambda n:(n.version,int(n.network_address),n.prefixlen)) for p,v in out.items()}

def collapse(ns): return list(ipaddress.collapse_addresses(sorted(set(ns),key=lambda n:(n.version,int(n.network_address),n.prefixlen))))

def covered(candidate, source):
    """True only if the entire candidate is covered by source prefixes."""
    remaining=[candidate]
    for n in source:
        if n.version!=candidate.version: continue
        nxt=[]
        for part in remaining:
            if part.subnet_of(n): continue
            if part.overlaps(n):
                nxt.extend(part.address_exclude(n))
            else: nxt.append(part)
        remaining=nxt
        if not remaining:return True
    return not remaining

def minimalize(source):
    current=collapse(source)
    changed=True
    while changed:
        changed=False; out=[]; i=0
        while i<len(current):
            if i+1<len(current):
                a,b=current[i],current[i+1]
                if a.version==b.version and a.prefixlen==b.prefixlen and a.supernet().subnet_of(ipaddress.ip_network("0.0.0.0/0" if a.version==4 else "::/0")):
                    candidate=a.supernet()
                    if covered(candidate,current):
                        out.append(candidate); i+=2; changed=True; continue
            out.append(a); i+=1
        current=sorted(set(out),key=lambda n:(n.version,int(n.network_address),n.prefixlen))
    return current

def write(path, values):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join(map(str,values))+"\n" if values else "",encoding="utf-8")

def build(data,root):
    for provider, raw in data.items():
        safe=provider.lower().replace(" ","-").replace("/","-")
        write(root/"FULL"/(safe+".txt"),raw)
        write(root/"BALANCED"/(safe+".txt"),collapse(raw))
        write(root/"MINIMAL"/(safe+".txt"),minimalize(raw))
    all_raw=[n for ns in data.values() for n in ns]
    write(root/"FULL.txt",sorted(set(all_raw),key=lambda n:(n.version,int(n.network_address),n.prefixlen)))
    all_bal=collapse(all_raw)
    write(root/"BALANCED.txt",all_bal)
    write(root/"MINIMAL.txt",minimalize(all_raw))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",default="data/provenance/cidr.json");ap.add_argument("--output",default="dist")
    a=ap.parse_args();build(nets(load(a.input)),pathlib.Path(a.output))
if __name__=="__main__":main()
