#!/usr/bin/env python3
"""Build a provider-independent DPI health matrix from probe results.

This intentionally records observations; it never changes provider attribution.
"""
import argparse, json, pathlib, datetime

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dpi",default="data/dpi-health.json")
    p.add_argument("--output",default="data/dpi/matrix.json")
    a=p.parse_args()
    src=pathlib.Path(a.dpi)
    out=pathlib.Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    if src.exists():
        try: data=json.loads(src.read_text(encoding="utf-8"))
        except Exception as e: data={"status":"INVALID","error":str(e)}
    else: data={"status":"MISSING"}
    matrix={
      "generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
      "network_dependent":True,
      "provider_attribution_from_dpi":False,
      "detector":"Runnin4ik/dpi-detector",
      "compatibility_tools":["zapret","zapret2","DPI-Checker","GoodbyeDPI","SpoofDPI"],
      "observation":data,
    }
    out.write_text(json.dumps(matrix,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__": main()
