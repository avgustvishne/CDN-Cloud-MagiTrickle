#!/usr/bin/env python3
"""Detect stale provider source metadata when available."""
import json, pathlib, re, sys
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
now=datetime.now(timezone.utc)
manifest=json.loads((DATA/"manifest.json").read_text(encoding="utf-8"))
out={"generated_at":now.isoformat(),"providers":{}}
for name,info in manifest.get("providers",{}).items():
    raw=" ".join(str(info.get(k,"")) for k in ("updated_at","last_updated","timestamp"))
    dt=None
    m=re.search(r"(20\d\d-\d\d-\d\d(?:T[^\s]+)?)",raw)
    if m:
        try: dt=datetime.fromisoformat(m.group(1).replace("Z","+00:00"))
        except ValueError: pass
    days=None if dt is None else max(0,(now-dt.astimezone(timezone.utc)).total_seconds()/86400)
    status="unknown" if days is None else ("fresh" if days<3 else "aging" if days<7 else "stale")
    out["providers"][name]={"days_old":None if days is None else round(days,2),"status":status}
(DATA/"source-freshness.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Freshness report written.")
