#!/usr/bin/env python3
"""Prepare an auditable source-registry update proposal.

The script never writes config/source_registry.json. It creates a patch-like
proposal for eligible candidates so CI can open a review PR safely.
"""
import datetime,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; IN=DATA/"source-approval.json"; OUT=DATA/"source-registry-proposals.json"
REG=ROOT/"config/source_registry.json"

def main():
    if not IN.exists():
        print("source-approval.json missing"); return 1
    approved=json.loads(IN.read_text(encoding="utf-8"))
    current={}
    if REG.exists():
        try: current=json.loads(REG.read_text(encoding="utf-8"))
        except Exception: current={}
    existing=set(current.keys()) if isinstance(current,dict) else set()
    proposals=[]
    for row in approved.get("results",[]):
        if not row.get("approval",{}).get("eligible"): continue
        repo=row.get("repository")
        if not repo or repo in existing: continue
        proposals.append({
            "repository":repo,
            "url":row.get("url") or f"https://github.com/{repo}",
            "stars":row.get("stars",0),
            "last_push":row.get("last_push"),
            "cidr_count":row.get("cidr_count",0),
            "comparison":row.get("comparison",{}),
            "decision":"review-required",
        })
    payload={
        "generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auto_merge":False,
        "proposals":proposals,
    }
    DATA.mkdir(exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Registry proposals: {len(proposals)}")
if __name__=="__main__": raise SystemExit(main())
