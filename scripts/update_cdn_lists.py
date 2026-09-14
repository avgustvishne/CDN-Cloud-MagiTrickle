#!/usr/bin/env python3
import ipaddress,json,pathlib,urllib.parse,urllib.request,datetime,time,sys,tempfile,os,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
UA="CDN-Cloud-MagiTrickle/6.0"; RIPE="https://stat.ripe.net/data/announced-prefixes/data.json"; MIN_PEERS=5; RETRIES=3
MIN_PREFIXES={"aws":20,"cloudflare":5,"akamai":10,"default":1}
STATIC={"backblaze":["45.11.36.0/22","104.153.232.0/21","149.137.128.0/20","206.190.208.0/21","207.166.148.0/22","2605:72c0::/32"]}
def request(url):
    last=None
    for i in range(RETRIES):
        try:
            r=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json,text/plain,*/*"})
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
    if n=="fastly":
        o=jsonget("https://api.fastly.com/public-ip-list")
        vals=[]
        def walk(x):
            if isinstance(x,str): vals.append(x)
            elif isinstance(x,dict):
                for v in x.values(): walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(o); return vals
    if n=="gcore":
        o=jsonget("https://api.gcore.com/cdn/public-ip-list")
        vals=[]
        def walk(x):
            if isinstance(x,str): vals.append(x)
            elif isinstance(x,dict):
                for v in x.values(): walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(o); return vals
    if n in STATIC:return STATIC[n]
    return []
def nets(v,ver):
    s=set()
    for x in v:
        try:
            n=x if isinstance(x,(ipaddress.IPv4Network,ipaddress.IPv6Network)) else ipaddress.ip_network(str(x).strip(),strict=False)
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
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(65536),b""):h.update(b)
    return h.hexdigest()
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
        v4,v6=nets(raw,4),nets(raw,6); old4=DATA/(name+"-v4.txt"); old6=DATA/(name+"-v6.txt"); minimum=MIN_PREFIXES.get(name,1); status="OK"
        if len(v4)<minimum and old4.exists() and old4.stat().st_size:
            status="KEEP_OLD"; print(f"[WARN] {name}: {len(v4)} IPv4 (<{minimum}), keeping previous")
            v4=nets(old4.read_text().splitlines(),4)
            if old6.exists() and old6.stat().st_size:v6=nets(old6.read_text().splitlines(),6)
        else:
            atomic(old4,v4); atomic(old6,v6)
        all4+=v4;all6+=v6;rows.append((name,len(v4),len(v6),src,status));print(f"{name}: v4={len(v4)} v6={len(v6)} {src} {status}")
    all4,all6=nets(all4,4),nets(all6,6)
    if not all4:sys.exit("[FATAL] no aggregate IPv4")
    atomic(DATA/"all-cloud-v4.txt",all4);atomic(DATA/"all-cloud-v6.txt",all6)
    now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    m={"version":6,"updated":now,"ripe_min_peers":MIN_PEERS,"aggregate":{"ipv4":len(all4),"ipv6":len(all6)},"providers":{}}
    for n,a,b,s,st in rows:m["providers"][n]={"ipv4":a,"ipv6":b,"source":s,"status":st}
    (DATA/"manifest.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n")
    (DATA/"checksums.sha256").write_text("\n".join(f"{sha256(p)}  {p.relative_to(ROOT).as_posix()}" for p in sorted(DATA.glob("*-v*.txt"))+[f"{sha256(DATA/'all-cloud-v4.txt')}  data/all-cloud-v4.txt",f"{sha256(DATA/'all-cloud-v6.txt')}  data/all-cloud-v6.txt"])+"\n")
    (DATA/"last-update.txt").write_text("\n".join([f"Updated: {now}","V6: official sources + RIPE fallback + retries + keep-old + atomic writes",f"ALL IPv4: {len(all4)}",f"ALL IPv6: {len(all6)}","","Provider,IPv4,IPv6,Source,Status"]+[f"{n},{a},{b},{s},{st}" for n,a,b,s,st in rows])+"\n")
if __name__=="__main__":main()
