#!/usr/bin/env python3
"""Validate source-health.json freshness and response sanity."""
import datetime,json,pathlib,sys
p=pathlib.Path("data/source-health.json")
if not p.exists(): print("source-health.json missing");sys.exit(1)
obj=json.loads(p.read_text(encoding="utf-8")); stamp=obj.get("checked_at","")
try: dt=datetime.datetime.strptime(stamp,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc)
except Exception: print("Invalid checked_at:",stamp);sys.exit(1)
age=(datetime.datetime.now(datetime.timezone.utc)-dt).total_seconds()
if age>48*3600: print(f"Source health is stale: {age/3600:.1f}h");sys.exit(1)
sources=obj.get("sources",{}); bad=[]
for name,item in sources.items():
    if item.get("ok") is not True: bad.append(f"{name}: source failed")
    if int(item.get("bytes",0))<=0: bad.append(f"{name}: empty response")
if not sources: bad.append("no sources recorded")
if bad: print("\n".join(bad));sys.exit(1)
print(f"Source health OK: {len(sources)} sources, age {age/3600:.1f}h")
