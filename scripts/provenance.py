#!/usr/bin/env python3
"""Normalize CIDR evidence into one deduplicated provenance index."""
import argparse,datetime,ipaddress,json,pathlib

KIND_WEIGHT={"official":100,"bgp_rpki":95,"asn_index":90,"independent":85,"secondary":60,"dns":40}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="data/evidence")
    p.add_argument("--output",default="data/provenance/cidr.json")
    a=p.parse_args()
    root=pathlib.Path(a.input); rows={}
    for f in sorted(root.glob("*.json")) if root.exists() else []:
        try: obj=json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        records=obj if isinstance(obj,list) else obj.get("records",[])
        for rec in records:
            cidr=rec.get("cidr") or rec.get("prefix") or rec.get("range")
            provider=rec.get("provider","unknown")
            if not cidr: continue
            try: cidr=str(ipaddress.ip_network(cidr,strict=False))
            except ValueError: continue
            key=(provider.lower(),cidr)
            entry=rows.setdefault(key,{"cidr":cidr,"provider":provider,"sources":[]})
            src={"id":rec.get("source",f.stem),"kind":rec.get("source_type",rec.get("kind","secondary")),
                 "observed_at":rec.get("observed_at")}
            if src not in entry["sources"]: entry["sources"].append(src)
    out=[]
    for entry in rows.values():
        kinds={x["kind"] for x in entry["sources"]}
        base=max((KIND_WEIGHT.get(k,50) for k in kinds),default=0)
        bonus=min(10,max(0,len(kinds)-1)*2)
        entry["confidence"]=min(100,base+bonus)
        entry["source_count"]=len(entry["sources"])
        out.append(entry)
    out.sort(key=lambda x:(x["provider"].lower(),ipaddress.ip_network(x["cidr"]).version,ipaddress.ip_network(x["cidr"]).network_address))
    dest=pathlib.Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps({"schema_version":1,"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"records":out},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__": main()
