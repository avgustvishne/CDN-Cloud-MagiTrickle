#!/usr/bin/env python3
"""DPI observation collector.

This is intentionally separate from provider CIDR generation. DPI observations
describe a probe network/path and are never used as proof of ASN ownership.
"""
import argparse,datetime,json,pathlib,shutil,subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DOMAINS=["cloudflare.com","github.com","youtube.com","discord.com","vk.com"]

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--detector",default="dpi_detector")
 p.add_argument("--domains",nargs="*",default=DEFAULT_DOMAINS)
 p.add_argument("--tests",default="123")
 p.add_argument("--concurrency",default="20")
 p.add_argument("--probe-id",default="local")
 p.add_argument("--output",default="data/dpi/observations.json")
 p.add_argument("--allow-unavailable",action="store_true")
 a=p.parse_args()
 out=ROOT/a.output
 out.parent.mkdir(parents=True,exist_ok=True)
 now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
 result={"schema_version":1,"checked_at":now,"probe_id":a.probe_id,
         "engine":"Runnin4ik/dpi-detector","network_dependent":True,
         "provider_attribution":False,"domains":a.domains,"tests":a.tests}
 exe=shutil.which(a.detector)
 if not exe:
  result.update(status="UNAVAILABLE",reason="detector not installed on this probe")
  out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
  return 0 if a.allow_unavailable else 2
 cmd=[exe,"-t",a.tests,"-c",a.concurrency,"--batch"]
 for d in a.domains: cmd += ["-d",d]
 try:
  proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=900)
  result.update(status="OK" if proc.returncode==0 else "DETECTED_OR_ERROR",
                returncode=proc.returncode,stdout_tail=proc.stdout[-12000:],
                stderr_tail=proc.stderr[-4000:])
 except subprocess.TimeoutExpired as e:
  result.update(status="TIMEOUT",stdout_tail=(e.stdout or "")[-12000:] if isinstance(e.stdout,str) else "")
 out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 return 0 if a.allow_unavailable or result["status"]=="OK" else 1

if __name__=="__main__": raise SystemExit(main())
