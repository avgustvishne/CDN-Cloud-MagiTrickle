#!/usr/bin/env python3
"""Generate CDN v3: CDN-only, conservative, independently sourced."""
import ipaddress
import json
import os
import pathlib
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "cdn_v3.json"
OUTPUT = DATA / "presets"
TIMEOUT = 20
RETRIES = 3
UA = "CDN-Cloud-MagiTrickle/cdn-v3"

CORE = {"cloudflare", "akamai", "fastly", "cdn77", "gcore"}


def request(url):
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/plain,application/json,*/*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                data = response.read()
            if not data:
                raise RuntimeError("empty response")
            return data
        except Exception as exc:
            last = exc
            if attempt + 1 < RETRIES:
                continue
    raise last


def parse_cidrs(data):
    values = set()
    for line in data.decode("utf-8", errors="replace").splitlines():
        value = line.split("#", 1)[0].strip().strip('"').strip(",")
        if not value:
            continue
        try:
            if "/" in value:
                values.add(str(ipaddress.ip_network(value, strict=False)))
        except ValueError:
            continue
    return values


def load_provider(name, mode, asn=None):
    if mode == "existing-provider":
        values = set()
        for version in (4, 6):
            path = DATA / f"{name}-v{version}.txt"
            if not path.exists():
                raise RuntimeError(f"missing existing provider dataset: {path.name}")
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    values.add(str(ipaddress.ip_network(line.strip(), strict=False)))
        return values

    if mode == "ipverse-asn":
        if not asn:
            raise RuntimeError(f"missing ASN for {name}")
        base = f"https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/{asn}"
        return parse_cidrs(request(base + "/ipv4-aggregated.txt")) | parse_cidrs(
            request(base + "/ipv6-aggregated.txt")
        )

    if mode == "official":
        return parse_cidrs(request("https://cachefly.cachefly.net/ips/cdn.txt"))

    raise RuntimeError(f"unsupported CDN v3 source mode: {mode}")


def normalize(values):
    parsed = []
    for value in values:
        try:
            net = ipaddress.ip_network(value, strict=False)
            if net.is_global and net.prefixlen >= (8 if net.version == 4 else 16):
                parsed.append(net)
        except ValueError:
            continue
    return sorted(set(parsed), key=lambda n: (n.version, int(n.network_address), n.prefixlen))


def coverage(values):
    return sum(net.num_addresses for net in ipaddress.collapse_addresses(values))


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    providers = config["providers"]
    names = {item["id"] for item in providers}
    if not CORE.issubset(names):
        raise RuntimeError(f"CDN v3 lost core providers: {sorted(CORE - names)}")

    all_values = set()
    source_report = []
    for item in providers:
        values = load_provider(item["id"], item["mode"], item.get("asn"))
        if not values:
            raise RuntimeError(f"empty CDN v3 source: {item['id']}")
        all_values.update(values)
        source_report.append({"id": item["id"], "mode": item["mode"], "raw_prefixes": len(values), "_values": values})

    normalized = normalize(all_values)
    if not normalized:
        raise RuntimeError("empty CDN v3 output")

    for version in (4, 6):
        source = [ipaddress.ip_network(v) for v in all_values if ipaddress.ip_network(v).version == version]
        result = [n for n in normalized if n.version == version]
        if not result:
            raise RuntimeError(f"empty CDN v3 IPv{version} output")
        if coverage(source) != coverage(result):
            raise RuntimeError(f"coverage changed for IPv{version}")
        atomic(OUTPUT / f"cdn-v3-v{version}.txt", "\n".join(map(str, result)) + "\n")

    for row in source_report:
        provider_values = row.pop("_values")
        row["ipv4_prefixes"] = sum(ipaddress.ip_network(v).version == 4 for v in provider_values)
        row["ipv6_prefixes"] = sum(ipaddress.ip_network(v).version == 6 for v in provider_values)

    atomic(
        DATA / "cdn-v3-sources.json",
        json.dumps({"schema_version": 1, "policy": config["policy"], "providers": source_report}, ensure_ascii=False, indent=2) + "\n",
    )


if __name__ == "__main__":
    main()
