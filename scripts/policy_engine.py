#!/usr/bin/env python3
"""Provider CIDR policy engine and explain helper."""
import ipaddress, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config/policy.json"

def load_policy():
    if not CONFIG.exists(): return {"enabled":False,"providers":{},"global":{"exclude":[],"include":[]}}
    return json.loads(CONFIG.read_text(encoding="utf-8"))

def networks(values):
    out=[]
    for x in values:
        try: out.append(ipaddress.ip_network(x, strict=False))
        except ValueError: pass
    return out

def apply(provider, values, collect_explain=True):
    policy=load_policy()
    if not policy.get("enabled"):
        return values, ([{"cidr":str(x),"action":"included","reason":"policy disabled"} for x in values] if collect_explain else [])
    p=policy.get("providers",{}).get(provider,{})
    global_policy=policy.get("global",{})
    includes=networks(global_policy.get("include",[])+p.get("include",[]))
    excludes=networks(global_policy.get("exclude",[])+p.get("exclude",[]))
    result=[]; explain=[]
    for raw in values:
        try: n=ipaddress.ip_network(str(raw).strip(),strict=False)
        except ValueError:
            if collect_explain: explain.append({"cidr":str(raw),"action":"excluded","reason":"invalid CIDR"}); continue
        if any(n.subnet_of(x) or x.subnet_of(n) for x in excludes):
            if collect_explain: explain.append({"cidr":str(n),"action":"excluded","reason":"exclude policy"}); continue
        if includes and not any(n.subnet_of(x) or x.subnet_of(n) for x in includes):
            if collect_explain: explain.append({"cidr":str(n),"action":"excluded","reason":"not in include policy"}); continue
        result.append(str(n))
        if collect_explain: explain.append({"cidr":str(n),"action":"included","reason":"policy match"})
    return result, explain

def explain(provider, cidr):
    _, rows=apply(provider,[cidr])
    return rows[0] if rows else {"cidr":cidr,"action":"excluded","reason":"no policy match"}

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(description="Explain why a CIDR is included or excluded")
    ap.add_argument("provider"); ap.add_argument("cidr")
    args=ap.parse_args()
    print(json.dumps(explain(args.provider,args.cidr),ensure_ascii=False,indent=2))
