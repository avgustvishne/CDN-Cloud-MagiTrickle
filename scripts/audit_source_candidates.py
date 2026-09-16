#!/usr/bin/env python3
"""Audit discovered GitHub repositories for usable CIDR data.

This is an advisory audit. It never modifies source_registry.json.
"""
import datetime,json,os,pathlib,re,urllib.parse,urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; DISCOVERY=DATA/"source-candidates.json"; OUT=DATA/"source-audit-candidates.json"
CIDR_RE=re.compile(r"(?<![A-Za-z0-9:])(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}|(?:[0-9A-Fa-f]*:){2,}[0-9A-Fa-f:]*/\d{1,3}")
MAX_FILES=100
MAX_BYTES=5_000_000

def get_json(url):
    token=os.environ.get("GITHUB_TOKEN","")
    headers={"Accept":"application/vnd.github+json","User-Agent":"CDN-Cloud-MagiTrickle"}
    if token: headers["Authorization"]=f"Bearer {token}"
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)

def audit_repo(full):
    data=get_json("https://api.github.com/repos/"+full)
    branch=data.get("default_branch","main")
    tree=get_json(f"https://api.github.com/repos/{full}/git/trees/{urllib.parse.quote(branch,safe='') }?recursive=1")
    paths=[x.get("path","") for x in tree.get("tree",[]) if x.get("type")=="blob"]
    candidates=[p for p in paths if p.lower().endswith((".txt",".cidr",".list",".csv",".json",".yaml",".yml",".conf")) and any(k in p.lower() for k in ("ip","cidr","prefix","asn","range","cloud","cdn"))][:MAX_FILES]
    found=set(); bytes_read=0; files_hit=0
    for path in candidates:
        try:
            obj=get_json(f"https://api.github.com/repos/{full}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(branch)}")
            import base64
            raw=base64.b64decode(obj.get("content","")).decode("utf-8","ignore")
            if len(raw.encode())+bytes_read>MAX_BYTES: break
            bytes_read+=len(raw.encode()); files_hit+=1
            for m in CIDR_RE.findall(raw): found.add(m)
        except Exception:
            continue
    v4=sum(1 for x in found if ":" not in x); v6=len(found)-v4
    coverage4=coverage(found,4); coverage6=coverage(found,6)
    return {"repository":full,"default_branch":branch,"stars":data.get("stargazers_count",0),
            "last_push":data.get("pushed_at"),"files_scanned":files_hit,"cidr_count":len(found),
            "ipv4_count":v4,"ipv6_count":v6,"ipv4_coverage":coverage4,"ipv6_coverage":coverage6,
            "audit_status":"usable-candidate" if found else "no-cidr-found"}

def coverage(values,version):
    import ipaddress
    nets=[]
    for s in values:
        try:
            n=ipaddress.ip_network(s,strict=False)
            if n.version==version: nets.append(n)
        except ValueError: pass
    if not nets:return 0
    nets=sorted(nets,key=lambda n:(int(n.network_address),-n.prefixlen))
    total=0; end=-1
    for n in nets:
        a=int(n.network_address); b=int(n.broadcast_address)
        if a>end+1: total+=b-a+1
        elif b>end: total+=b-end
        end=max(end,b)
    return total

def main():
    if not DISCOVERY.exists():
        print("source-candidates.json missing"); return 1
    rows=json.loads(DISCOVERY.read_text(encoding="utf-8")).get("candidates",[])
    out=[]; errors=[]
    for item in rows[:100]:
        try: out.append(audit_repo(item["repository"]))
        except Exception as e: errors.append({"repository":item.get("repository"),"error":str(e)[:300]})
    out.sort(key=lambda x:(x["ipv4_coverage"]+x["ipv6_coverage"],x["cidr_count"]),reverse=True)
    payload={"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "policy":{"auto_promote":False,"max_repositories":100,"max_bytes_per_repo":MAX_BYTES},
             "results":out,"errors":errors}
    DATA.mkdir(exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Source candidate audit: {len(out)} audited, {len(errors)} errors")
if __name__=="__main__": raise SystemExit(main())
