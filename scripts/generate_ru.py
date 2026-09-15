#!/usr/bin/env python3
"""Generate independent RU FULL / RU COMMON subscriptions."""
import ipaddress, json, pathlib, tempfile, urllib.request, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VERSION = 1
UA = "CDN-Cloud-MagiTrickle-RU/" + str(VERSION)
URL = "https://stat.ripe.net/data/country-resource-list/data.json?resource=RU"

# Compact fallback only; RU FULL normally comes from RIPE's country resource list.
RU_COMMON = [
    "5.8.0.0/13","5.16.0.0/14","5.32.0.0/12","31.128.0.0/11",
    "37.0.0.0/8","45.8.0.0/16","46.0.0.0/8","62.76.0.0/14",
    "77.0.0.0/9","78.24.0.0/13","80.64.0.0/10","81.176.0.0/13",
    "83.136.0.0/13","87.224.0.0/11","89.108.0.0/14","91.192.0.0/11",
    "92.100.0.0/14","93.80.0.0/13","95.24.0.0/13","109.120.0.0/13",
    "176.192.0.0/11","178.64.0.0/10","185.0.0.0/8","188.64.0.0/10",
    "212.0.0.0/8",
]

def fetch():
    req=urllib.request.Request(URL,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode())

def strings(obj):
    if isinstance(obj,str): yield obj
    elif isinstance(obj,dict):
        for v in obj.values(): yield from strings(v)
    elif isinstance(obj,list):
        for v in obj: yield from strings(v)

def collapse(values, version):
    s=set()
    for x in values:
        try:
            n=ipaddress.ip_network(str(x).strip(),strict=False)
            if n.version==version and n.is_global:
                s.add(n)
        except ValueError:
            pass
    return sorted(ipaddress.collapse_addresses(s),key=lambda n:(int(n.network_address),n.prefixlen))

def write(path,nets):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix="."+path.name+".")
    try:
        with open(fd,"w",encoding="utf-8") as f:
            f.write("\n".join(map(str,nets))+"\n")
        pathlib.Path(tmp).replace(path)
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)

def main():
    try:
        full=list(strings(fetch()))
        source="RIPE country-resource-list"
    except Exception as e:
        full=RU_COMMON[:]
        source="compact fallback"
        print("WARNING:",e)

    for version in (4,6):
        write(DATA/f"ru-full-v{version}.txt",collapse(full,version))
        write(DATA/f"ru-common-v{version}.txt",collapse(RU_COMMON,version))

    meta={"version":VERSION,"source":source,"files":[
        "ru-full-v4.txt","ru-full-v6.txt","ru-common-v4.txt","ru-common-v6.txt"]}
    write(DATA/"ru-manifest.json",[json.dumps(meta,ensure_ascii=False)])
    print("RU profiles generated:",source)

if __name__=="__main__": main()
