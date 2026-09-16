#!/usr/bin/env python3
"""Check source-health metadata produced by the updater."""
import datetime,json,pathlib,sys
p=pathlib.Path("data/source-health.json")
if not p.exists(): print("source-health.json missing");sys.exit(1)
obj=json.loads(p.read_text(encoding="utf-8")); sources=obj.get("sources",{})
bad=[]
for name,item in sources.items():
    if item.get("ok") is not True: bad.append(f"{name}: source reports failure")
    if not isinstance(item.get("bytes"),int) or item["bytes"]<=0: bad.append(f"{name}: empty response")
if bad:
    print("\n".join(bad));sys.exit(1)
print(f"Checked {len(sources)} sources: HEALTHY")
