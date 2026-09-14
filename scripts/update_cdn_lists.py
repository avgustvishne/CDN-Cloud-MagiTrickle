#!/usr/bin/env python3
import ipaddress,json,pathlib,urllib.parse,urllib.request,datetime,time,sys,tempfile,os
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
UA="CDN-Cloud-MagiTrickle/5.0"; RIPE="https://stat.ripe.net/data/announced-prefixes/data.json"; MIN_PEERS=5; RETRIES=3
MIN_PREFIXES={"aws":20,"cloudflare":5,"akamai":10,"default":1}
def request(url):
    last=None
    for i in range(RETRIES):
        try:
            r=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
            with urllib.request.urlopen(r,timeout=60) as x:return x.read()
        except Exception as e:
            last=e
            if i<RETRIES-1:time.sleep(2*(i+1))
    raise last
def jsonget(u):return json.loads(request(u).decode())
def ripe(a):
    q=urllib.parse.urlencode({"resource":"AS"+a,"min_peers_seeing":MIN_PEERS,"sourceapp":"CDN-Cloud-MagiTrickle"})
    return [x.get("prefix","") for x in jsonget(RIPE+"?"+q).get("data",{}).get("prefixes",[])]
def official(n):
    if n=="aws":
        o=jsonget("https://ip-ranges.amazonaws.com/ip-ranges.json")
        return [x["ip_prefix"] for x in o.get("prefixes",[])]+[x["ipv6_prefix"] for x in o.get("ipv6_prefixes",[])]
    if n=="cloudflare":
        return request("https://www.cloudflare.com/ips-v4/").decode().splitlines()+request("https://www.cloudflare.com/ips-v6/").decode().splitlines()
    return []
def nets(v,ver):
    s=set()
    for x in v:
        try:
            n=x if isinstance(x,(ipaddress.IPv4Network,ipaddress.IPv6Network)) else ipaddress.ip_network(x.strip(),strict=False)
            if n.version==ver:s.add(n)
        except:pass
    return sorted(ipaddress.collapse_addresses(s),key=lambda n:(int(n.network_address),n.prefixlen))
def atomic(p,ns):
    t="\n".join(map(str,ns))+("\n" if ns else "")
    fd,tmp=tempfile.mkstemp(dir=str(p.parent),prefix="."+p.name+".")
    try:
        with os.fdopen(fd,"w",encoding="utf8") as f:f.write(t)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def main():
    cfg=json.loads((ROOT/"config/providers.json").read_text()); all4=[];all6=[];rows=[]
    for name,asns in cfg["providers"].items():
        raw=[];src="RIPEstat";err=[]
        try:raw=official(name);src="official" if raw else src
        except Exception as e:err.append("official:"+str(e))
        if not raw:
            for a in asns:
                try:raw+=ripe(a)
                except Exception as e:err.append("AS"+a+":"+str(e))
                time.sleep(.15)
        v4,v6=nets(raw,4),nets(raw,6); old=DATA/(name+"-v4.txt"); minimum=MIN_PREFIXES.get(name,1)
        status="OK"
        if len(v4)<minimum and old.exists() and old.stat().st_size:
            status="KEEP_OLD"
            print(f"[WARN] {name}: {len(v4)} IPv4 (<{minimum}), keeping previous")
            try:v4=nets(old.read_text().splitlines(),4)
            except:v4=[]
        else:
            atomic(DATA/(name+"-v4.txt"),v4);atomic(DATA/(name+"-v6.txt"),v6)
        all4+=v4;all6+=v6;rows.append((name,len(v4),len(v6),src,status));print(f"{name}: v4={len(v4)} v6={len(v6)} {src} {status}")
    all4,all6=nets(all4,4),nets(all6,6)
    if not all4:sys.exit("[FATAL] no aggregate IPv4")
    atomic(DATA/"all-cloud-v4.txt",all4);atomic(DATA/"all-cloud-v6.txt",all6)
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    m={"version":5,"updated":now,"ripe_min_peers":MIN_PEERS,"aggregate":{"ipv4":len(all4),"ipv6":len(all6)},"providers":{}}
    for n,a,b,s,st in rows:m["providers"][n]={"ipv4":a,"ipv6":b,"source":s,"status":st}
    (DATA/"manifest.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n")
    (DATA/"last-update.txt").write_text("\n".join([f"Updated: {now}","V5: official + RIPE fallback + retries + safe keep-old",f"ALL IPv4: {len(all4)}",f"ALL IPv6: {len(all6)}","","Provider,IPv4,IPv6,Source,Status"]+[f"{n},{a},{b},{s},{st}" for n,a,b,s,st in rows])+"\n")
if __name__=="__main__":main()
