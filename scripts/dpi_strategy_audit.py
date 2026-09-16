#!/usr/bin/env python3
"""Static compatibility audit for DPI tools; no traffic interception is performed."""
import argparse,json,pathlib,datetime,shutil

TOOLS={"zapret":"zapret","zapret2":"zapret2","DPI-Checker":"dpi-checker.sh","GoodbyeDPI":"goodbyedpi.exe","SpoofDPI":"spoofdpi"}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--output",default="data/dpi/strategies.json"); a=p.parse_args()
 rows=[]
 for name,exe in TOOLS.items():
  rows.append({"name":name,"installed":bool(shutil.which(exe)),"executable":exe})
 out=pathlib.Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"tools":rows,"note":"Presence check only; no bypass is activated by this audit."},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__": main()
