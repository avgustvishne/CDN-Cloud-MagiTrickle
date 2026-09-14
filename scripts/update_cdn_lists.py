#!/usr/bin/env python3
import datetime, hashlib, ipaddress, json, os, pathlib, sys, tempfile, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

VERSION = 7
UA = f"CDN-Cloud-MagiTrickle/{VERSION}.0"
RIPE = "https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS = 5
RETRIES = 4
TIMEOUT = 45
RETRY_BASE = 2
MAX_PROVIDER_PREFIXES = 50000
MIN_PREFIXES = {"aws": 20, "cloudflare": 5, "akamai": 10, "default": 1}

# Stable fallback for providers that publish a small fixed edge range set.
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
    return [x.get("prefix", "") for x in payload.get("data", {}).get("prefixes", [])]


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
        return [x["ip_prefix"] for x in obj.get("prefixes", [])] + [
            x["ipv6_prefix"] for x in obj.get("ipv6_prefixes", [])
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


def nets(values, version):
    parsed = set()
    for value in values:
        try:
            net = (
                value
                if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network))
                else ipaddress.ip_network(str(value).strip(), strict=False)
            )
            if net.version == version:
                parsed.add(net)
        except Exception:
            continue
    return sorted(
        ipaddress.collapse_addresses(parsed),
        key=lambda net: (int(net.network_address), net.prefixlen),
    )


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


def load_previous(path, version):
    if not path.exists() or path.stat().st_size == 0:
        return []
    return nets(path.read_text(encoding="utf-8").splitlines(), version)


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

        v4, v6 = nets(raw, 4), nets(raw, 6)
        old4 = DATA / f"{name}-v4.txt"
        old6 = DATA / f"{name}-v6.txt"
        minimum = MIN_PREFIXES.get(name, 1)
        status = "OK"
        used_fallback = False

        # Reject clearly broken upstream responses and preserve the last good data.
        if len(v4) < minimum or len(v4) > MAX_PROVIDER_PREFIXES:
            prev4 = load_previous(old4, 4)
            prev6 = load_previous(old6, 6)
            if prev4:
                v4, v6 = prev4, (prev6 if prev6 else v6)
                status = "KEEP_OLD"
                used_fallback = True
            elif len(v4) == 0:
                status = "EMPTY"

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
            }
        )
        print(f"{name}: v4={len(v4)} v6={len(v6)} {source} {status}")
        if errors:
            print(f"  warnings: {len(errors)}")

    all4 = nets(all4, 4)
    all6 = nets(all6, 6)
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
        "max_provider_prefixes": MAX_PROVIDER_PREFIXES,
        "aggregate": {"ipv4": len(all4), "ipv6": len(all6)},
        "providers": {
            row["name"]: {
                "ipv4": row["ipv4"],
                "ipv6": row["ipv6"],
                "source": row["source"],
                "status": row["status"],
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
        "V7: quality gates + source tracking + resilient retries + keep-old + atomic writes + SHA256",
        f"ALL IPv4: {len(all4)}",
        f"ALL IPv6: {len(all6)}",
        "",
        "Provider,IPv4,IPv6,Source,Status,Errors",
    ]
    summary.extend(
        f"{row['name']},{row['ipv4']},{row['ipv6']},{row['source']},{row['status']},{len(row['errors'])}"
        for row in rows
    )
    write_text_atomic(DATA / "last-update.txt", "\n".join(summary) + "\n")


if __name__ == "__main__":
    main()
