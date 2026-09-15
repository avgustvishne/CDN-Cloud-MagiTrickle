#!/usr/bin/env python3
"""Build a compact quality report from provider CIDR files and DPI results."""
import csv, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def read_nets(path):
    return {x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()} if path.exists() else set()

def main():
    manifest=json.loads((DATA/"manifest.json").read_text(encoding="utf-8"))
    providers=manifest.get("providers", {})
    report={"generated_from":"data/manifest.json","providers":{},"totals":{"ipv4":0,"ipv6":0},"source_health":{}}
    for name, info in providers.items():
        v4=len(read_nets(DATA/f"{name}-v4.txt")); v6=len(read_nets(DATA/f"{name}-v6.txt"))
        report["providers"][name]={"ipv4":v4,"ipv6":v6,"total":v4+v6,"status":info.get("status","UNKNOWN"),"source":info.get("source","")}
        report["totals"]["ipv4"]+=v4; report["totals"]["ipv6"]+=v6
    health=DATA/"source-health.json"
    if health.exists(): report["source_health"]=json.loads(health.read_text(encoding="utf-8")).get("sources",{})
    dpi=DATA/"dpi-endpoints.json"
    if dpi.exists():
        d=json.loads(dpi.read_text(encoding="utf-8")); report["dpi"]=d.get("summary",{})
    (DATA/"quality-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Providers: {len(report['providers'])}; IPv4: {report['totals']['ipv4']}; IPv6: {report['totals']['ipv6']}")
if __name__=="__main__": main()
