#!/usr/bin/env python3
"""Protect generated CIDR datasets by restoring the previous Git revision on large drops."""
import argparse, json, pathlib, subprocess, sys
from datetime import datetime, timezone

def files(d):
    root = pathlib.Path(d)
    return sorted(list(root.glob("*-v[46].txt")) + list((root / "presets").glob("*.txt")))


def count_text(text):
    return sum(1 for x in text.splitlines() if x.strip())

def count_file(path):
    return count_text(path.read_text(encoding="utf-8", errors="replace"))

def previous_text(ref, relpath):
    try:
        r=subprocess.run(["git","show",f"{ref}:{relpath}"],text=True,capture_output=True,check=True)
        return r.stdout
    except subprocess.CalledProcessError:
        return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("current_dir")
    ap.add_argument("--previous-ref", default="HEAD^")
    ap.add_argument("--max-drop", type=float, default=0.50)
    ap.add_argument("--min-previous", type=int, default=20)
    ap.add_argument("--report", default="data/rollback-report.json")
    args=ap.parse_args()

    cur=pathlib.Path(args.current_dir)
    report={"timestamp":datetime.now(timezone.utc).isoformat(),
            "previous_ref":args.previous_ref,"max_drop":args.max_drop,
            "guarded":False,"restored":False,"datasets":{},"critical":[]}

    for cp in files(cur):
        rel=cp.as_posix()
        old_text=previous_text(args.previous_ref,rel)
        if old_text is None:
            report["datasets"][rel]={"current":count_file(cp),"previous":None,"status":"no_previous"}
            continue
        old,new=count_text(old_text),count_file(cp)
        drop=(old-new)/old if old else 0
        item={"previous":old,"current":new,"drop_percent":round(drop*100,2)}
        if old >= args.min_previous and drop > args.max_drop:
            item["status"]="rollback_required"
            report["critical"].append(rel)
        else:
            item["status"]="ok"
        report["datasets"][rel]=item

    report["guarded"]=bool(report["critical"])
    if report["guarded"]:
        # Restore the complete generated data tree so provider lists, presets,
        # manifests and checksums remain mutually consistent.
        subprocess.run(
            ["git", "checkout", args.previous_ref, "--", "data"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        report["restored"]=True
        report["restored_files"]="data/"

    out=pathlib.Path(args.report); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Rollback guard:", "RESTORED" if report["restored"] else ("TRIGGERED" if report["guarded"] else "OK"))
    if report["critical"]:
        print("Critical:", ", ".join(report["critical"]))
    return 0

if __name__=="__main__":
    sys.exit(main())
