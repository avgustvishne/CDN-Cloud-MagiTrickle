#!/usr/bin/env python3
import datetime
import hashlib
import ipaddress
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

VERSION = 9
UA = f"CDN-Cloud-MagiTrickle/{VERSION}.0"
RIPE = "https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS = 5
RETRIES = 5
TIMEOUT = 30
RETRY_BASE = 2
MAX_PROVIDER_PREFIXES = 50000
MIN_CHANGE_RATIO = 0.50
# Reject prefixes that are unusually broad for CDN/cloud address lists.
MIN_PREFIXLEN = {4: 8, 6: 16}
MIN_PREFIXES = {
    "aws": 20,
    "cloudflare": 5,
    "akamai": 10,
    "fastly": 5,
    "gcore": 10,
    "backblaze": 1,
    "default": 1,
}

STATIC = {
    "backblaze": [
        "45.11.36.0/22",
        "104.153.232.0/21",
        "149.137.128.0/20",
        "206.190.208.0/21",
        "207.166.148.0/22",
        "2605:72c0::/32",
    ]
}


def request(url):
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json,text/plain,*/*",
                    "Cache-Control": "no-cache",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                data = res.read()
                if not data:
                    raise RuntimeError("empty response")
                return data
        except Exception as exc:
            last = exc
            if attempt < RETRIES:
                time.sleep(RETRY_BASE * attempt)
    raise last


def jsonget(url):
    return json.loads(request(url).decode("utf-8"))


def ripe(asn):
    query = urllib.parse.urlencode(
        {
            "resource": "AS" + asn,
            "min_peers_seeing": MIN_PEERS,
            "sourceapp": "CDN-Cloud-MagiTrickle",
        }
    )
    payload = jsonget(RIPE + "?" + query)
    return [item.get("prefix", "") for item in payload.get("data", {}).get("prefixes", [])]


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from walk_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_strings(value)


def official(name):
    if name == "aws":
        obj = jsonget("https://ip-ranges.amazonaws.com/ip-ranges.json")
        return [item["ip_prefix"] for item in obj.get("prefixes", [])] + [
            item["ipv6_prefix"] for item in obj.get("ipv6_prefixes", [])
        ]
    if name == "cloudflare":
        return request("https://www.cloudflare.com/ips-v4/").decode().splitlines() + request(
            "https://www.cloudflare.com/ips-v6/"
        ).decode().splitlines()
    if name == "fastly":
        return list(walk_strings(jsonget("https://api.fastly.com/public-ip-list")))
    if name == "gcore":
        return list(walk_strings(jsonget("https://api.gcore.com/cdn/public-ip-list")))
    if name in STATIC:
        return STATIC[name]
    return []


def nets(values, version, global_only=True):
    parsed = set()
    rejected = 0
    for value in values:
        try:
            net = (
                value
                if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network))
                else ipaddress.ip_network(str(value).strip(), strict=False)
            )
            if net.version != version:
                continue
            if global_only and not net.is_global:
                rejected += 1
                continue
            if net.prefixlen < MIN_PREFIXLEN[version]:
                rejected += 1
                continue
            parsed.add(net)
        except Exception:
            rejected += 1
    collapsed = sorted(
        ipaddress.collapse_addresses(parsed),
        key=lambda network: (int(network.network_address), network.prefixlen),
    )
    return collapsed, rejected


def load_previous(path, version):
    if not path.exists() or path.stat().st_size == 0:
        return []
    networks, _ = nets(path.read_text(encoding="utf-8").splitlines(), version)
    return networks


def atomic(path, networks):
    text = "\n".join(map(str, networks)) + ("\n" if networks else "")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_text_atomic(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    all4, all6, rows = [], [], []

    for name, asns in cfg["providers"].items():
        raw = []
        sources = []
        errors = []

        try:
            raw = official(name)
            if raw:
                sources.append("official" if name not in STATIC else "static")
        except Exception as exc:
            errors.append("official:" + str(exc))

        if not raw:
            for asn in asns:
                try:
                    raw.extend(ripe(asn))
                    sources.append("RIPEstat")
                except Exception as exc:
                    errors.append(f"AS{asn}:{exc}")
                time.sleep(0.12)

        v4, rejected4 = nets(raw, 4)
        v6, rejected6 = nets(raw, 6)
        old4 = DATA / f"{name}-v4.txt"
        old6 = DATA / f"{name}-v6.txt"
        prev4 = load_previous(old4, 4)
        prev6 = load_previous(old6, 6)
        minimum = MIN_PREFIXES.get(name, MIN_PREFIXES["default"])
        status = "OK"
        used_fallback = False

        suspicious = len(v4) < minimum or len(v4) > MAX_PROVIDER_PREFIXES
        if prev4 and len(v4) < int(len(prev4) * MIN_CHANGE_RATIO):
            suspicious = True

        if suspicious and prev4:
            v4, v6 = prev4, (prev6 if prev6 else v6)
            status = "KEEP_OLD"
            used_fallback = True
        elif suspicious and not prev4:
            status = "EMPTY" if not v4 else "ANOMALY"

        if errors:
            if prev4 and len(v4) < len(prev4):
                v4, v6 = prev4, (prev6 if prev6 else v6)
                status = "KEEP_OLD_PARTIAL"
                used_fallback = True
            elif status == "OK":
                status = "PARTIAL"

        if rejected4 or rejected6:
            if status == "OK":
                status = "FILTERED"

        if not used_fallback:
            atomic(old4, v4)
            atomic(old6, v6)

        source = "+".join(dict.fromkeys(sources)) or "none"
        all4.extend(v4)
        all6.extend(v6)
        rows.append(
            {
                "name": name,
                "ipv4": len(v4),
                "ipv6": len(v6),
                "source": source,
                "status": status,
                "errors": errors[:10],
                "rejected_ipv4": rejected4,
                "rejected_ipv6": rejected6,
            }
        )
        print(f"{name}: v4={len(v4)} v6={len(v6)} {source} {status}")
        if errors:
            print(f"  warnings: {len(errors)}")
        if rejected4 or rejected6:
            print(f"  filtered: ipv4={rejected4} ipv6={rejected6}")

    all4, _ = nets(all4, 4)
    all6, _ = nets(all6, 6)
    if not all4:
        sys.exit("[FATAL] no aggregate IPv4")

    atomic(DATA / "all-cloud-v4.txt", all4)
    atomic(DATA / "all-cloud-v6.txt", all6)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest = {
        "version": VERSION,
        "updated": now,
        "ripe_min_peers": MIN_PEERS,
        "retries": RETRIES,
        "timeout_seconds": TIMEOUT,
        "min_change_ratio": MIN_CHANGE_RATIO,
        "max_provider_prefixes": MAX_PROVIDER_PREFIXES,
        "global_only": True,
        "min_prefixlen": {"ipv4": MIN_PREFIXLEN[4], "ipv6": MIN_PREFIXLEN[6]},
        "aggregate": {"ipv4": len(all4), "ipv6": len(all6)},
        "providers": {
            row["name"]: {
                "ipv4": row["ipv4"],
                "ipv6": row["ipv6"],
                "source": row["source"],
                "status": row["status"],
                "rejected_ipv4": row["rejected_ipv4"],
                "rejected_ipv6": row["rejected_ipv6"],
                **({"errors": row["errors"]} if row["errors"] else {}),
            }
            for row in rows
        },
    }
    write_text_atomic(DATA / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    checksum_files = sorted(set(DATA.glob("*-v*.txt")) | {DATA / "all-cloud-v4.txt", DATA / "all-cloud-v6.txt"})
    checksum_text = "\n".join(
        f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}" for path in checksum_files
    ) + "\n"
    write_text_atomic(DATA / "checksums.sha256", checksum_text)

    summary = [
        f"Updated: {now}",
        "V9: global filtering + broad-prefix shield + anomaly protection + partial-source detection + retries + atomic writes + SHA256",
        f"ALL IPv4: {len(all4)}",
        f"ALL IPv6: {len(all6)}",
        "",
        "Provider,IPv4,IPv6,Source,Status,Errors,RejectedIPv4,RejectedIPv6",
    ]
    summary.extend(
        f"{row['name']},{row['ipv4']},{row['ipv6']},{row['source']},{row['status']},{len(row['errors'])},{row['rejected_ipv4']},{row['rejected_ipv6']}"
        for row in rows
    )
    write_text_atomic(DATA / "last-update.txt", "\n".join(summary) + "\n")


if __name__ == "__main__":
    main()
