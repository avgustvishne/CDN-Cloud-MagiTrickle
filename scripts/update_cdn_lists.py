#!/usr/bin/env python3
import ipaddress, json, urllib.request, pathlib, datetime

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
DATA.mkdir(exist_ok=True)

URL="https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/all/all_plain_ipv4.txt"

def fetch(url):
    req=urllib.request.Request(url, headers={"User-Agent":"CDN-Cloud-MagiTrickle/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8","replace")

def normalize(lines, version):
    nets=set()
    for line in lines.splitlines():
        s=line.strip().split("#",1)[0].strip()
        if not s: continue
        try:
            n=ipaddress.ip_network(s, strict=False)
            if n.version==version:
                nets.add(n)
        except ValueError:
            pass
    return sorted(ipaddress.collapse_addresses(nets), key=lambda n:(int(n.network_address), n.prefixlen))

v4=normalize(fetch(URL),4)
(DATA/"cdn-cloud-v4.txt").write_text("\n".join(map(str,v4))+"\n",encoding="utf-8")
(DATA/"cdn-cloud-v6.txt").write_text("",encoding="utf-8")

now=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
(DATA/"last-update.txt").write_text(f"Updated: {now}\nIPv4 CIDRs: {len(v4)}\nSource: {URL}\n",encoding="utf-8")
print(f"IPv4 CIDRs: {len(v4)}")
