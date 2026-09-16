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

def load_current_cidrs():
    import ipaddress
    found=set()
    for p in DATA.glob("*.txt"):
        if not p.name.endswith(("-v4.txt","-v6.txt")): continue
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                s=line.strip()
                if s:
                    found.add(str(ipaddress.ip_network(s, strict=False)))
        except Exception:
            continue
    return found

def overlap_and_new(candidate_cidrs, current):
    import ipaddress
    cand=[ipaddress.ip_network(x, strict=False) for x in candidate_cidrs]
    cur=[ipaddress.ip_network(x, strict=False) for x in current]
    total=sum(int(n.num_addresses) for n in cand)
    overlap=0
    for n in cand:
        covered=[]
        for c in cur:
            if n.version == c.version and n.overlaps(c):
                lo=max(int(n.network_address),int(c.network_address))
                hi=min(int(n.broadcast_address),int(c.broadcast_address))
                if hi>=lo: covered.append((lo,hi))
        covered.sort()
        end=-1
        for lo,hi in covered:
            if lo>end+1: overlap += hi-lo+1
            elif hi>end: overlap += hi-end
            end=max(end,hi)
    overlap=min(total,overlap)
    new=total-overlap
    return {"total_coverage":total,"overlap_coverage":overlap,"new_coverage":new,
            "overlap_ratio":round(overlap/total,6) if total else 0,
            "new_ratio":round(new/total,6) if total else 0}

def main():
    if not DISCOVERY.exists():
        print("source-candidates.json missing"); return 1
    rows=json.loads(DISCOVERY.read_text(encoding="utf-8")).get("candidates",[])
    current=load_current_cidrs()
    out=[]; errors=[]
    for item in rows[:100]:
        try:
            audit=audit_repo(item["repository"])
            # Reuse the repository scan to obtain prefixes for coverage comparison.
            data=get_json("https://api.github.com/repos/"+item["repository"])
            branch=data.get("default_branch","main")
            tree=get_json(f"https://api.github.com/repos/{item['repository']}/git/trees/{urllib.parse.quote(branch,safe='')}?recursive=1")
            paths=[x.get("path","") for x in tree.get("tree",[]) if x.get("type")=="blob"]
            repo_prefixes=set()
            for path in [p for p in paths if p.lower().endswith((".txt",".cidr",".list",".csv",".json",".yaml",".yml",".conf")) and any(k in p.lower() for k in ("ip","cidr","prefix","asn","range","cloud","cdn"))][:MAX_FILES]:
                try:
                    import base64
                    obj=get_json(f"https://api.github.com/repos/{item['repository']}/contents/{urllib.parse.quote(path,safe='/')}?ref={urllib.parse.quote(branch)}")
                    raw=base64.b64decode(obj.get("content","")).decode("utf-8","ignore")
                    repo_prefixes.update(CIDR_RE.findall(raw))
                except Exception:
                    pass
            audit["comparison"]=overlap_and_new(repo_prefixes,current)
            audit["audit_status"]="useful-candidate" if audit["comparison"]["new_coverage"] else audit["audit_status"]
            out.append(audit)
        except Exception as e:
            errors.append({"repository":item.get("repository"),"error":str(e)[:300]})
    out.sort(key=lambda x:(x.get("comparison",{}).get("new_coverage",0),x.get("ipv4_coverage",0)),reverse=True)
    payload={"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "policy":{"auto_promote":False,"max_repositories":100,"max_bytes_per_repo":MAX_BYTES,
                       "comparison":"candidate coverage against current generated CIDR files"},
             "current_cidr_count":len(current),"results":out,"errors":errors}
    DATA.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Source candidate audit: {len(out)} audited, {len(errors)} errors; current CIDRs: {len(current)}")
if __name__=="__main__":
    raise SystemExit(main())
