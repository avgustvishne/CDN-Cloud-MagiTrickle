#!/usr/bin/env python3
import ipaddress, urllib.request, pathlib, datetime

URL4 = 'https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/cdn-only/cdn-only_plain_ipv4.txt'
URL6 = 'https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/cdn-only/cdn-only_plain.txt'
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'MagiTrickle-CDN-Cloud-Updater/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', errors='replace')


def parse(text, version):
    out = set()
    for raw in text.splitlines():
        s = raw.strip().split('#', 1)[0].strip()
        if not s:
            continue
        try:
            n = ipaddress.ip_network(s, strict=False)
            if n.version == version:
                out.add(n)
        except ValueError:
            continue
    return sorted(out, key=lambda n: (int(n.network_address), n.prefixlen))


def aggregate(items):
    return list(ipaddress.collapse_addresses(items))

v4 = aggregate(parse(fetch(URL4), 4))
v6 = aggregate(parse(fetch(URL6), 6))
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

for name, items in [('cdn-cloud-v4.txt', v4), ('cdn-cloud-v6.txt', v6)]:
    p = DATA / name
    p.write_text('\n'.join(map(str, items)) + '\n', encoding='utf-8')

(DATA / 'last-update.txt').write_text(f'Updated: {now}\nIPv4 CIDR: {len(v4)}\nIPv6 CIDR: {len(v6)}\nSource: 123jjck/cdn-ip-ranges cdn-only\n', encoding='utf-8')
print(f'IPv4: {len(v4)} CIDRs')
print(f'IPv6: {len(v6)} CIDRs')
