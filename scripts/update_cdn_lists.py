#!/usr/bin/env python3
import ipaddress, json, pathlib, urllib.parse, urllib.request, datetime, time, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
UA="CDN-Cloud-MagiTrickle/3.0"; RIPE="https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS=5; MIN_PREFIXES={"aws":20,"cloudflare":5,"akamai":10,"default":1}

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def ripe(asn):
    q=urllib.parse.urlencode({"resource":f"AS{asn}","min_peers_seeing":MIN_PEERS,"sourceapp":"CDN-Cloud-MagiTrickle"})
    return [x.get("prefix","") for x in get_json(RIPE+"?"+q).get("data",{}).get("prefixes",[])]

def nets(vals,v):
    s=set()
    for x in vals:
        try:
            n=ipaddress.ip_network(x,strict=False)
            if n.version==v:s.add(n)
        except: pass
    return sorted(ipaddress.collapse_addresses(s),key=lambda n:(int(n.network_address),n.prefixlen))

def fetch_text(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=60) as r:return r.read().decode()

def official(name):
    if name=="aws":
        obj=get_json("https://ip-ranges.amazonaws.com/ip-ranges.json")
        return [x["ip_prefix"] for x in obj.get("prefixes",[])]+[x["ipv6_prefix"] for x in obj.get("ipv6_prefixes",[])]
    if name=="cloudflare":
        return fetch_text("https://www.cloudflare.com/ips-v4/").splitlines()+fetch_text("https://www.cloudflare.com/ips-v6/").splitlines()
    return []

def write(path,ns): path.write_text("\n".join(map(str,ns))+("\n" if ns else ""),encoding="utf-8")

def main():
    cfg=json.loads((ROOT/"config/providers.json").read_text())
    all4=[];all6=[];rows=[]
    for name,asns in cfg["providers"].items():
        raw=[]; source="RIPEstat"
        try:
            raw=official(name)
            if raw: source="official"
        except Exception as e: print(f"[WARN] official {name}: {e}")
        if not raw:
            for a in asns:
                try: raw+=ripe(a)
                except Exception as e: print(f"[WARN] {name} AS{a}: {e}")
                time.sleep(.15)
        v4,v6=nets(raw,4),nets(raw,6)
        minimum=MIN_PREFIXES.get(name,MIN_PREFIXES["default"])
        if len(v4)<minimum:
            old=DATA/f"{name}-v4.txt"
            if old.exists() and old.stat().st_size>0:
                print(f"[ERROR] {name}: only {len(v4)} IPv4 prefixes; refusing destructive update")
                sys.exit(2)
        write(DATA/f"{name}-v4.txt",v4); write(DATA/f"{name}-v6.txt",v6)
        all4+=v4;all6+=v6;rows.append((name,len(v4),len(v6),source))
        print(f"{name}: v4={len(v4)} v6={len(v6)} source={source}")
    all4,all6=nets(all4,4),nets(all6,6)
    write(DATA/"all-cloud-v4.txt",all4);write(DATA/"all-cloud-v6.txt",all6)
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    out=[f"Updated: {now}","V3 source policy: official where available, RIPEstat fallback",f"RIPE min peers: {MIN_PEERS}",f"ALL IPv4 CIDRs: {len(all4)}",f"ALL IPv6 CIDRs: {len(all6)}","","Provider,IPv4,IPv6,Source"]
    out += [f"{a},{b},{c},{d}" for a,b,c,d in rows]
    (DATA/"last-update.txt").write_text("\n".join(out)+"\n",encoding="utf-8")
if __name__=="__main__":main()
