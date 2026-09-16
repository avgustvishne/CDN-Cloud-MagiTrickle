#!/usr/bin/env python3
"""Discover provider ASN/prefix evidence from ipverse/as-ip-blocks.

This is discovery evidence, not automatic proof that every ASN is a CDN.
Provider names are matched conservatively against ASN handle/description.
"""
import argparse,datetime,json,pathlib,re,urllib.request

BASE="https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/{asn}/aggregated.json"
INDEX="https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/asns.json"

def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"CDN-Cloud-MagiTrickle/1.0"})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()

def norm(s): return re.sub(r"[^a-z0-9]+","",s.lower())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--providers",default="config/providers.json")
    p.add_argument("--output",default="data/evidence/asn-discovery.json")
    a=p.parse_args()
    providers={}
    path=pathlib.Path(a.providers)
    if path.exists():
        obj=json.loads(path.read_text(encoding="utf-8"))
        providers=obj.get("providers",obj) if isinstance(obj,dict) else obj
    # Fallback to names already known by the generator.
    if not providers: providers={"cloudflare":{}, "fastly":{}, "gcore":{}, "akamai":{}, "cloudfront":{}, "digitalocean":{}, "hetzner":{}, "ovh":{}, "scaleway":{}}
    try:index=json.loads(fetch(INDEX))
    except Exception as e:
        pathlib.Path(a.output).parent.mkdir(parents=True,exist_ok=True)
        pathlib.Path(a.output).write_text(json.dumps({"status":"UNAVAILABLE","error":str(e)},indent=2)+"\n")
        return 0
    records=[]
    items=index.get("asns",index) if isinstance(index,dict) else index
    if isinstance(items,dict): items=[dict(v,asn=k) if isinstance(v,dict) else {"asn":k,"handle":str(v)} for k,v in items.items()]
    for item in items if isinstance(items,list) else []:
        asn=str(item.get("asn","")).replace("AS","")
        text=norm(" ".join(str(item.get(k,"")) for k in ("handle","name","description","org","organization")))
        for provider,meta in providers.items():
            aliases=meta.get("aliases",[]) if isinstance(meta,dict) else []
            terms=[provider]+aliases
            if any(norm(t) and norm(t) in text for t in terms):
                records.append({"provider":provider,"asn":asn,"handle":item.get("handle"),"description":item.get("description"),"source":"ipverse/as-ip-blocks","source_type":"asn_index","match":"name_or_handle"})
    out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"schema_version":1,"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"status":"OK","records":records},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
