#!/usr/bin/env python3
import ipaddress, json, pathlib, urllib.parse, urllib.request, datetime, time, sys, tempfile, os
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
UA="CDN-Cloud-MagiTrickle/4.0"; RIPE="https://stat.ripe.net/data/announced-prefixes/data.json"; MIN_PEERS=5; MIN_PREFIXES={"aws":20,"cloudflare":5,"akamai":10,"default":1}; RETRIES=3
def request(url):
    last=None
    for i in range(RETRIES):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
            with urllib.request.urlopen(req,timeout=60) as r:return r.read()
        except Exception as e:
            last=e
            if i<RETRIES-1: time.sleep(2*(i+1))
    raise last
def get_json(url): return json.loads(request(url).decode("utf-8"))
def ripe(asn):
    q=urllib.parse.urlencode({"resource":f"AS{asn}","min_peers_seeing":MIN_PEERS,"sourceapp":"CDN-Cloud-MagiTrickle"})
    return [x.get("prefix","") for x in get_json(RIPE+"?"+q).get("data",{}).get("prefixes",[])]
def official(name):
    if name=="aws":
        o=get_json("https://ip-ranges.amazonaws.com/ip-ranges.json")
        return [x["ip_prefix"] for x in o.get("prefixes",[])]+[x["ipv6_prefix"] for x in o.get("ipv6_prefixes",[])]
    if name=="cloudflare":
        return request("https://www.cloudflare.com/ips-v4/").decode().splitlines()+request("https://www.cloudflare.com/ips-v6/").decode().splitlines()
    return []
def nets(vals,v):
    s=set()
    for x in vals:
        try:
            n=ipaddress.ip_network(x.strip(),strict=False)
            if n.version==v:s.add(n)
        except: pass
    return sorted(ipaddress.collapse_addresses(s),key=lambda n:(int(n.network_address),n.prefixlen))
def atomic_write(path,ns):
    text="\n".join(map(str,ns))+("\n" if ns else "")
    fd,tmp=tempfile.mkstemp(dir=str(path.parent),prefix="."+path.name+".")
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:f.write(text)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def main():
    cfg=json.loads((ROOT/"config/providers.json").read_text(encoding="utf-8")); all4=[]; all6=[]; rows=[]; failed=[]
    for name,asns in cfg["providers"].items():
        raw=[]; source="RIPEstat"; errors=[]
        try:
            raw=official(name)
            if raw: source="official"
        except Exception as e: errors.append("official: "+str(e))
        if not raw:
            for a in asns:
                try: raw+=ripe(a)
                except Exception as e: errors.append(f"AS{a}: {e}")
                time.sleep(.15)
        v4,v6=nets(raw,4),nets(raw,6); minimum=MIN_PREFIXES.get(name,1)
        if len(v4)<minimum:
            failed.append(name); print(f"[ERROR] {name}: {len(v4)} IPv4 prefixes (<{minimum}); keeping previous files")
            rows.append((name,len(v4),len(v6),source,"KEEP_OLD")); continue
        atomic_write(DATA/f"{name}-v4.txt",v4); atomic_write(DATA/f"{name}-v6.txt",v6)
        all4+=v4; all6+=v6; rows.append((name,len(v4),len(v6),source,"OK")); print(f"{name}: v4={len(v4)} v6={len(v6)} source={source}")
    all4,all6=nets(all4,4),nets(all6,6)
    if not all4: print("[FATAL] No valid aggregate IPv4 data; refusing replacement."); sys.exit(2)
    atomic_write(DATA/"all-cloud-v4.txt",all4); atomic_write(DATA/"all-cloud-v6.txt",all6)
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest={"version":4,"updated":now,"ripe_min_peers":MIN_PEERS,"aggregate":{"ipv4":len(all4),"ipv6":len(all6)},"providers":{}}
    for n,a,b,s,status in rows: manifest["providers"][n]={"ipv4":a,"ipv6":b,"source":s,"status":status}
    (DATA/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    out=[f"Updated: {now}","V4: official source + RIPEstat fallback + retries + safe keep-old",f"RIPE min peers: {MIN_PEERS}",f"ALL IPv4 CIDRs: {len(all4)}",f"ALL IPv6 CIDRs: {len(all6)}",f"Failed/kept old: {len(failed)}","","Provider,IPv4,IPv6,Source,Status"]
    out += [f"{a},{b},{c},{d},{e}" for a,b,c,d,e in rows]
    (DATA/"last-update.txt").write_text("\n".join(out)+"\n",encoding="utf-8")
if __name__=="__main__": main()
