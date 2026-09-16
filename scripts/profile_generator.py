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

def profile_stats(values, source_values=None):
    values=list(values)
    source_values=list(source_values) if source_values is not None else values
    def ip_count(ns, version):
        return sum(n.num_addresses for n in ns if n.version==version)
    v4=[n for n in values if n.version==4]; v6=[n for n in values if n.version==6]
    s4=[n for n in source_values if n.version==4]; s6=[n for n in source_values if n.version==6]
    raw_total=ip_count(s4,4)+ip_count(s6,6)
    total=ip_count(v4,4)+ip_count(v6,6)
    return {
        "cidr_count":len(values),"ipv4_cidr_count":len(v4),"ipv6_cidr_count":len(v6),
        "ipv4_addresses":ip_count(v4,4),"ipv6_addresses":ip_count(v6,6),
        "total_addresses":total,"source_cidr_count":len(source_values),
        "coverage_change_percent":round((total/raw_total-1)*100,4) if raw_total else 0.0
    }

def write(path, values):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join(map(str,values))+"\n" if values else "",encoding="utf-8")

def build(data,root):
    stats={"schema_version":1,"profiles":{}}

    for provider, raw in data.items():
        safe=provider.lower().replace(" ","-").replace("/","-")
        write(root/"FULL"/(safe+".txt"),raw)
        write(root/"BALANCED"/(safe+".txt"),collapse(raw))
        minimal=minimalize(raw)
        write(root/"MINIMAL"/(safe+".txt"),minimal)\n        stats["profiles"].setdefault(provider,{})["FULL"]=profile_stats(raw,raw)\n        stats["profiles"][provider]["BALANCED"]=profile_stats(collapse(raw),raw)\n        stats["profiles"][provider]["MINIMAL"]=profile_stats(minimal,raw)
    all_raw=[n for ns in data.values() for n in ns]
    write(root/"FULL.txt",sorted(set(all_raw),key=lambda n:(n.version,int(n.network_address),n.prefixlen)))
    all_bal=collapse(all_raw)
    write(root/"BALANCED.txt",all_bal)
    minimal_all=minimalize(all_raw)\n    write(root/"MINIMAL.txt",minimal_all)\n    stats["profiles"]["__ALL__"]={"FULL":profile_stats(all_raw,all_raw),"BALANCED":profile_stats(all_bal,all_raw),"MINIMAL":profile_stats(minimal_all,all_raw)}\n    stats["generated_at"]=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")\n    (root/"profile-stats.json").write_text(json.dumps(stats,indent=2,ensure_ascii=False)+"\\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",default="data/provenance/cidr.json");ap.add_argument("--output",default="dist")
    a=ap.parse_args();build(nets(load(a.input)),pathlib.Path(a.output))
if __name__=="__main__":main()
