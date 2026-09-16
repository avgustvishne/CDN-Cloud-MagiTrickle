#!/usr/bin/env python3
"""Build an immutable evidence manifest from available audit/validation artifacts."""
import datetime,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"
def main():
    items={}
    for name in ("source-audit.json","bgpstream-health.json"):
        p=DATA/name
        if p.exists():
            try:
                items[name]=json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                items[name]={"error":str(e)}
    out={"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"artifacts":items}
    (DATA/"evidence.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Evidence artifacts: {len(items)}")
if __name__=="__main__": main()
