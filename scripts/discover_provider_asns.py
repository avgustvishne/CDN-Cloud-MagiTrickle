#!/usr/bin/env python3
"""Discover provider ASN/prefix evidence from ipverse/as-ip-blocks.

This is discovery evidence, not automatic proof that every ASN is a CDN.
Provider names are matched conservatively against ASN handle/description.
"""
import argparse,datetime,json,pathlib,re,urllib.request

BASE="https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/{asn}/aggregated.json"
INDEX="https://raw.githubusercontent.com/projectdiscovery/cdncheck/main/cmd/generate-index/provider.yaml"

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
    try:
        raw=fetch(INDEX).decode("utf-8")
    except Exception as e:
        pathlib.Path(a.output).parent.mkdir(parents=True,exist_ok=True)
        pathlib.Path(a.output).write_text(json.dumps({"status":"UNAVAILABLE","error":str(e)},indent=2)+"\\n")
        return 0
    # cdncheck's provider.yaml is the maintained seed registry. Extract ASN
    # declarations conservatively, then let ipverse supply current prefixes.
    current=None
    section=None
    wanted={norm(k):k for k in providers}
    for line in raw.splitlines():
        if not line or line[0].isspace() is False and not line.startswith(" "):
            m=re.match(r"^([A-Za-z0-9_ .()/-]+):\\s*$",line)
            if m:
                current=m.group(1).strip()
                section=None
            elif line.strip() in ("asn:","cidr:","urls:"):
                section=line.strip()[:-1]
            continue
        s=line.strip()
        if s=="asn:":
            section="asn"; continue
        if section=="asn" and s.startswith("- AS"):
            asn=s[2:].strip()
            key=norm(current or "")
            for pk,pname in wanted.items():
                aliases=providers[pname].get("aliases",[]) if isinstance(providers[pname],dict) else []
                terms=[pname]+aliases
                if any(norm(t) and (norm(t) in key or key in norm(t)) for t in terms):
                    records.append({"provider":pname,"asn":asn,"handle":current,"source":"projectdiscovery/cdncheck","source_type":"asn_index","match":"cdncheck_registry"})
    out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"schema_version":1,"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"status":"OK","records":records},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
