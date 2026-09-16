#!/usr/bin/env python3
"""Generate FULL/BALANCED/MINIMAL provider profiles without arbitrary CIDR caps."""
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
        except ValueError: pass
    return {p:sorted(set(v),key=lambda n:(n.version,int(n.network_address),n.prefixlen)) for p,v in out.items()}

def write(path, values):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join(map(str,values))+"\n" if values else "",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="data/provenance/cidr.json")
    ap.add_argument("--output",default="dist")
    a=ap.parse_args()
    data=nets(load(a.input)); root=pathlib.Path(a.output)
    for provider, raw in data.items():
        safe=provider.lower().replace(" ","-").replace("/","-")
        full=raw
        balanced=list(ipaddress.collapse_addresses(raw))
        minimal=balanced
        write(root/"FULL"/(safe+".txt"),full)
        write(root/"BALANCED"/(safe+".txt"),balanced)
        write(root/"MINIMAL"/(safe+".txt"),minimal)
        # Combined provider-independent profiles are useful for subscriptions.
    all_nets=sorted({n for ns in data.values() for n in ns},key=lambda n:(n.version,int(n.network_address),n.prefixlen))
    write(root/"FULL.txt",all_nets)
    write(root/"BALANCED.txt",list(ipaddress.collapse_addresses(all_nets)))
    write(root/"MINIMAL.txt",list(ipaddress.collapse_addresses(all_nets)))
if __name__=="__main__":main()
