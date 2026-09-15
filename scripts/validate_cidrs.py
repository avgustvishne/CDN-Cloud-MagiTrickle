#!/usr/bin/env python3
"""Detect invalid, duplicate and overlapping CIDRs across provider datasets."""
import ipaddress, pathlib, json
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"

def load(path, version):
    bad=[]; nets={}
    for i,line in enumerate(path.read_text(encoding="utf-8",errors="replace").splitlines(),1):
        s=line.strip()
        if not s: continue
        try:
            n=ipaddress.ip_network(s,strict=False)
            if n.version!=version: raise ValueError("wrong IP version")
            key=str(n)
            nets.setdefault(key,[]).append(i)
        except Exception as e: bad.append({"line":i,"value":s,"error":str(e)})
    return nets,bad

def main():
    report={"providers":{},"cross_provider_overlap":[],"totals":{"invalid":0,"duplicates":0,"overlaps":0}}
    allnets={4:{},6:{}}
    for p in sorted(DATA.glob("*-v[46].txt")):
        version=int(p.stem[-1]); name=p.stem[:-3]
        nets,bad=load(p,version)
        dups=sum(len(v)-1 for v in nets.values() if len(v)>1)
        report["providers"].setdefault(name,{})[f"ipv{version}"]={"invalid":len(bad),"duplicates":dups}
        report["totals"]["invalid"]+=len(bad); report["totals"]["duplicates"]+=dups
        for cidr in nets: allnets[version].setdefault(cidr,[]).append(name)
    for version in (4,6):
        items=sorted((ipaddress.ip_network(x),owners) for x,owners in allnets[version].items())
        for i,(a,oa) in enumerate(items):
            for b,ob in items[i+1:]:
                if b.network_address>a.broadcast_address: break
                if a.overlaps(b) and set(oa)!=set(ob):
                    report["cross_provider_overlap"].append({"ipv":version,"a":str(a),"a_providers":sorted(set(oa)),"b":str(b),"b_providers":sorted(set(ob))})
                    report["totals"]["overlaps"]+=1
    (DATA/"cidr-validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report["totals"],ensure_ascii=False))
    raise SystemExit(1 if report["totals"]["invalid"] else 0)
if __name__=="__main__": main()
