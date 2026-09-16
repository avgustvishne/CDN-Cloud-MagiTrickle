#!/usr/bin/env python3
"""Check raw GitHub subscription links referenced by README."""
import concurrent.futures,re,sys,urllib.request
from pathlib import Path
text=Path("README.md").read_text(encoding="utf-8")
urls=sorted(set(re.findall(r'\]\((https://raw\.githubusercontent\.com/[^)]+)\)',text)))
def check(url):
    req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"CDN-Cloud-MagiTrickle-link-check"})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return url,r.status
    except Exception:
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"CDN-Cloud-MagiTrickle-link-check","Range":"bytes=0-32"})
            with urllib.request.urlopen(req,timeout=15) as r:return url,r.status
        except Exception as e:return url,str(e)
bad=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for url,status in ex.map(check,urls):
        if status!=200:bad.append((url,status))
        print(status,url)
if bad:
    print("\nBroken links:")
    for x in bad:print(x[1],x[0])
    sys.exit(1)
print(f"Checked {len(urls)} raw subscription links: OK")
