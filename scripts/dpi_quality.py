#!/usr/bin/env python3
"""Classify DPI observations without converting them into provider truth."""
import argparse,json,pathlib,datetime
def main():
 p=argparse.ArgumentParser();p.add_argument("--input",default="data/dpi/observations.json");p.add_argument("--output",default="data/dpi/quality.json");a=p.parse_args()
 try:d=json.loads(pathlib.Path(a.input).read_text(encoding="utf-8"))
 except Exception as e:d={"status":"INVALID","error":str(e)}
 status=d.get("status","UNKNOWN")
 cls={"OK":"OBSERVED_OK","DETECTED_OR_ERROR":"DPI_OR_ERROR","TIMEOUT":"TIMEOUT","UNAVAILABLE":"UNAVAILABLE"}.get(status,"UNKNOWN")
 out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({"schema_version":1,"classified_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"classification":cls,"network_dependent":True,"provider_attribution":False,"observation":d},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__":main()
