#!/usr/bin/env python3
"""Publication gate: reject malformed, duplicate and catastrophic changes."""
import argparse,json,ipaddress,pathlib,sys
def load(p):
    try:return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:return {}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--current",required=True);ap.add_argument("--previous");ap.add_argument("--output",default="data/health/regression.json");a=ap.parse_args()
    cur=load(a.current); prev=load(a.previous) if a.previous else {}
    recs=cur.get("records",cur if isinstance(cur,list) else [])
    bad=[];seen=set()
    for r in recs:
        c=r.get("cidr") if isinstance(r,dict) else r
        try:n=str(ipaddress.ip_network(c,strict=False))
        except Exception:bad.append({"cidr":c,"reason":"invalid_cidr"});continue
        if n in seen:bad.append({"cidr":n,"reason":"duplicate"})
        seen.add(n)
    old=prev.get("records",[]) if isinstance(prev,dict) else []
    if old and recs and len(recs)<len(old)*0.10: bad.append({"reason":"catastrophic_shrinkage","previous":len(old),"current":len(recs)})
    out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    result={"schema_version":1,"status":"FAIL" if bad else "PASS","current_count":len(recs),"previous_count":len(old),"errors":bad}
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    return 1 if bad else 0
if __name__=="__main__":sys.exit(main())
