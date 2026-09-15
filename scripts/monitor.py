#!/usr/bin/env python3
"""Generate a lightweight live provider status snapshot for GitHub Pages."""
import concurrent.futures, datetime, ipaddress, json, socket, time, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; OUT=DATA/"monitor.json"
PROVIDERS=ROOT/"config/providers.json"
TIMEOUT=6
CHECK_URLS={"cloudflare":"https://www.cloudflare.com/cdn-cgi/trace","aws":"https://aws.amazon.com/","microsoft":"https://www.microsoft.com/","akamai":"https://www.akamai.com/","fastly":"https://www.fastly.com/","gcore":"https://gcore.com/","digitalocean":"https://www.digitalocean.com/","hetzner":"https://www.hetzner.com/","ovh":"https://www.ovhcloud.com/","scaleway":"https://www.scaleway.com/","oracle":"https://www.oracle.com/","alibaba":"https://www.alibabacloud.com/","cdn77":"https://www.cdn77.com/","vultr":"https://www.vultr.com/","contabo":"https://contabo.com/","buyvm":"https://buyvm.net/","backblaze":"https://www.backblaze.com/","melbicom":"https://melbicom.net/"}

def check(name):
    url=CHECK_URLS.get(name)
    if not url: return {"provider":name,"status":"unknown","latency_ms":None,"url":None}
    req=urllib.request.Request(url,headers={"User-Agent":"CDN-Cloud-MagiTrickle-Monitor/1.0"})
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT) as r:
            latency=round((time.perf_counter()-started)*1000,1)
            status="healthy" if 200<=r.status<400 else "degraded"
            return {"provider":name,"status":status,"latency_ms":latency,"http_status":r.status,"url":url}
    except Exception as e:
        return {"provider":name,"status":"down","latency_ms":None,"error":type(e).__name__,"url":url}

def main():
    cfg=json.loads(PROVIDERS.read_text(encoding="utf-8"))
    names=list(cfg["providers"])
    started=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8,len(names))) as pool:
        rows=list(pool.map(check,names))
    rows.sort(key=lambda x:x["provider"])
    counts={s:sum(x["status"]==s for x in rows) for s in ("healthy","degraded","down","unknown")}
    payload={"generated_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"interval_minutes":10,"counts":counts,"providers":rows}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"
",encoding="utf-8")
    print(json.dumps({"providers":len(rows),"counts":counts,"seconds":round(time.time()-started,1)},ensure_ascii=False))

if __name__=="__main__": main()
