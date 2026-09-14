#!/usr/bin/env python3
import ipaddress
import json
import pathlib
import urllib.parse
import urllib.request
import datetime
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "providers.json"
DATA.mkdir(exist_ok=True)

USER_AGENT = "CDN-Cloud-MagiTrickle/2.0"
RIPE_URL = "https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS = 5

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def get_prefixes(asn):
    query = urllib.parse.urlencode({
        "resource": f"AS{asn}",
        "min_peers_seeing": MIN_PEERS,
        "sourceapp": "CDN-Cloud-MagiTrickle"
    })
    obj = fetch_json(f"{RIPE_URL}?{query}")
    return [x.get("prefix", "") for x in obj.get("data", {}).get("prefixes", [])]

def normalize(values, version):
    nets = set()
    for value in values:
        try:
            n = ipaddress.ip_network(value, strict=False)
            if n.version == version:
                nets.add(n)
        except ValueError:
            continue
    return sorted(
        ipaddress.collapse_addresses(nets),
        key=lambda n: (int(n.network_address), n.prefixlen)
    )

def write_list(path, networks):
    text = "\n".join(map(str, networks))
    path.write_text((text + "\n") if text else "", encoding="utf-8")

def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    providers = cfg["providers"]
    stats = []
    all4, all6 = [], []

    for name, asns in providers.items():
        raw = []
        for asn in asns:
            try:
                raw.extend(get_prefixes(asn))
            except Exception as e:
                print(f"[WARN] {name} AS{asn}: {e}")
        v4 = normalize(raw, 4)
        v6 = normalize(raw, 6)
        write_list(DATA / f"{name}-v4.txt", v4)
        write_list(DATA / f"{name}-v6.txt", v6)
        all4.extend(v4)
        all6.extend(v6)
        stats.append((name, len(v4), len(v6)))
        print(f"{name}: IPv4={len(v4)} IPv6={len(v6)}")
        time.sleep(0.2)

    all4 = normalize(all4, 4)
    all6 = normalize(all6, 6)
    write_list(DATA / "all-cloud-v4.txt", all4)
    write_list(DATA / "all-cloud-v6.txt", all6)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"Updated: {now}",
        f"Source: {RIPE_URL}",
        f"Minimum RIS peers seeing prefix: {MIN_PEERS}",
        f"Providers: {len(providers)}",
        f"ALL IPv4 CIDRs: {len(all4)}",
        f"ALL IPv6 CIDRs: {len(all6)}",
        "",
        "Provider,IPv4 CIDRs,IPv6 CIDRs",
    ]
    lines.extend(f"{name},{v4},{v6}" for name, v4, v6 in stats)
    (DATA / "last-update.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
