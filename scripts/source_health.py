#!/usr/bin/env python3
"""Detect suspicious source shrinkage before published lists are replaced."""
import argparse,json,pathlib,datetime
def main():
 p=argparse.ArgumentParser();p.add_argument("--current",default="data/source-health.json");p.add_argument("--previous",default="data/source-health.previous.json");p.add_argument("--output",default="data/health/anomalies.json");a=p.parse_args()
 def load(x):
  try:return json.loads(pathlib.Path(x).read_text(encoding="utf-8"))
  except Exception:return {}
 cur=load(a.current);prev=load(a.previous); anomalies=[]
 for sid,item in cur.get("sources",{}).items():
  old=prev.get("sources",{}).get(sid,{})
  n=item.get("count");o=old.get("count")
  if isinstance(n,int) and isinstance(o,int) and o>20 and n < o*0.25:
   anomalies.append({"source":sid,"previous_count":o,"current_count":n,"reason":"source_shrinkage_gt_75_percent"})
 out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"schema_version":1,"checked_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"status":"ANOMALY" if anomalies else "HEALTHY","anomalies":anomalies},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
