#!/usr/bin/env python3
"""Summarize added/removed lines between current datasets and the previous Git revision."""
import pathlib, subprocess, json
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
def prev(path):
    try:return subprocess.run(["git","show",f"HEAD^:{path.as_posix()}"],text=True,capture_output=True,check=True).stdout.splitlines()
    except subprocess.CalledProcessError:return []
out={"datasets":{}}
for p in sorted(DATA.glob("*-v[46].txt")):
    old=set(prev(p)); new=set(x.strip() for x in p.read_text(encoding="utf-8",errors="replace").splitlines() if x.strip())
    out["datasets"][p.name]={"added":len(new-old),"removed":len(old-new),"unchanged":len(new&old)}
(DATA/"change-summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Change summary written.")
