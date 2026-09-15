#!/usr/bin/env python3
"""Guard generated datasets against anomalous drops and keep the previous snapshot."""
import argparse, json, pathlib, shutil, sys

def count_lines(path):
    return sum(1 for x in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if x.strip())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("current_dir")
    ap.add_argument("previous_dir")
    ap.add_argument("--max-drop", type=float, default=0.50,
                    help="Maximum allowed relative drop (default: 50%%)")
    ap.add_argument("--min-previous", type=int, default=20,
                    help="Do not guard tiny datasets")
    ap.add_argument("--report", default="data/rollback-report.json")
    args=ap.parse_args()

    cur=pathlib.Path(args.current_dir); prev=pathlib.Path(args.previous_dir)
    report={"guarded":False,"max_drop":args.max_drop,"datasets":{}}
    critical=[]
    for cp in sorted(cur.glob("*-v[46].txt")):
        pp=prev/cp.name
        if not pp.exists(): continue
        old,new=count_lines(pp),count_lines(cp)
        if old < args.min_previous: continue
        drop=(old-new)/old if old else 0
        item={"previous":old,"current":new,"drop_percent":round(drop*100,2)}
        if drop > args.max_drop:
            item["status"]="rollback_required"; critical.append(cp.name)
        else:
            item["status"]="ok"
        report["datasets"][cp.name]=item

    report["guarded"]=bool(critical)
    report["critical"]=critical
    out=pathlib.Path(args.report); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if critical:
        print("ROLLBACK REQUIRED:", ", ".join(critical))
        return 2
    print("Rollback guard: OK")
    return 0

if __name__=="__main__":
    sys.exit(main())
