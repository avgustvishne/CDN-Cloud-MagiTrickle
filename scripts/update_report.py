#!/usr/bin/env python3
"""Render a human-readable update report."""
import argparse,json,pathlib,datetime
def load(p):
    try:return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:return {}
def fmt(n): return f"{n:,}".replace(",", " ")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stats",default="dist/profile-stats.json"); ap.add_argument("--health",default="data/health/regression.json"); ap.add_argument("--anomalies",default="data/health/anomalies.json"); ap.add_argument("--output",default="UPDATE_REPORT.md"); a=ap.parse_args()
    stats=load(a.stats); health=load(a.health); anomalies=load(a.anomalies)
    lines=["# CDN-Cloud-MagiTrickle — Update Report","",f"Generated: {stats.get(\"generated_at\",datetime.datetime.now(datetime.timezone.utc).strftime(\"%Y-%m-%dT%H:%M:%SZ\"))}","","## Overall profiles","","| Profile | CIDR | IPv4 CIDR | IPv6 CIDR | IPv4 addresses | IPv6 addresses | Coverage change |","|---|---:|---:|---:|---:|---:|---:|"]
    allp=stats.get("profiles",{}).get("__ALL__",{})
    for name in ("FULL","BALANCED","MINIMAL"):
        x=allp.get(name,{})
        lines.append(f"| {name} | {fmt(x.get(\"cidr_count\",0))} | {fmt(x.get(\"ipv4_cidr_count\",0))} | {fmt(x.get(\"ipv6_cidr_count\",0))} | {fmt(x.get(\"ipv4_addresses\",0))} | {fmt(x.get(\"ipv6_addresses\",0))} | {x.get(\"coverage_change_percent\",0)}% |")
    lines += ["","## Provider profiles","","| Provider | FULL | BALANCED | MINIMAL |","|---|---:|---:|---:|"]
    for provider,p in sorted(stats.get("profiles",{}).items()):
        if provider=="__ALL__": continue
        lines.append(f"| {provider} | {fmt(p.get(\"FULL\",{}).get(\"cidr_count\",0))} | {fmt(p.get(\"BALANCED\",{}).get(\"cidr_count\",0))} | {fmt(p.get(\"MINIMAL\",{}).get(\"cidr_count\",0))} |")
    lines += ["","## Validation","",f"- Regression gate: **{health.get(\"status\",\"UNKNOWN\")}**",f"- Regression errors: **{len(health.get(\"errors\",[]))}**",f"- Source anomalies: **{len(anomalies.get(\"anomalies\",[]))}**",""]
    pathlib.Path(a.output).write_text("\n".join(lines)+"\n",encoding="utf-8")
if __name__=="__main__": main()