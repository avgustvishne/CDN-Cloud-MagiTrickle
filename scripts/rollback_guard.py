#!/usr/bin/env python3
"""Snapshot healthy datasets and restore the last healthy snapshot on anomaly."""
import argparse, json, pathlib, shutil, sys
from datetime import datetime, timezone

def files(d):
    return sorted(pathlib.Path(d).glob("*-v[46].txt"))

def count(p):
    return sum(1 for x in p.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("current_dir")
    ap.add_argument("snapshot_dir")
    ap.add_argument("--max-drop", type=float, default=0.50)
    ap.add_argument("--min-previous", type=int, default=20)
    ap.add_argument("--report", default="data/rollback-report.json")
    ap.add_argument("--restore", action="store_true",
                    help="Restore the last healthy snapshot when the guard trips")
    args=ap.parse_args()

    cur=pathlib.Path(args.current_dir); snap=pathlib.Path(args.snapshot_dir)
    snap.mkdir(parents=True, exist_ok=True)
    report={"timestamp":datetime.now(timezone.utc).isoformat(),"max_drop":args.max_drop,
            "guarded":False,"restored":False,"datasets":{},"critical":[]}

    for cp in files(cur):
        sp=snap/cp.name
        if not sp.exists():
            shutil.copy2(cp, sp)
            report["datasets"][cp.name]={"current":count(cp),"previous":None,"status":"baseline"}
            continue
        old,new=count(sp),count(cp)
        drop=(old-new)/old if old else 0
        item={"previous":old,"current":new,"drop_percent":round(drop*100,2)}
        if old >= args.min_previous and drop > args.max_drop:
            item["status"]="rollback_required"
            report["critical"].append(cp.name)
        else:
            item["status"]="ok"
            # Only replace a snapshot after the new dataset passes the guard.
            shutil.copy2(cp, sp)
        report["datasets"][cp.name]=item

    report["guarded"]=bool(report["critical"])

    if report["critical"] and args.restore:
        restored=[]
        for name in report["critical"]:
            sp=snap/name; cp=cur/name
            if sp.exists():
                shutil.copy2(sp, cp)
                restored.append(name)
        report["restored"]=bool(restored)
        report["restored_files"]=restored

    out=pathlib.Path(args.report); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Rollback guard:", "RESTORED" if report["restored"] else ("TRIGGERED" if report["guarded"] else "OK"))
    if report["critical"]:
        print("Critical:", ", ".join(report["critical"]))
    return 0 if (not report["guarded"] or report["restored"]) else 2

if __name__=="__main__":
    sys.exit(main())
