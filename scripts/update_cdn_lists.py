#!/usr/bin/env python3
import datetime
import concurrent.futures
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
if str(ROOT / "scripts") not in sys.path: sys.path.insert(0, str(ROOT / "scripts"))

from policy_engine import apply as apply_policy
DATA.mkdir(exist_ok=True)

VERSION = 46
UA = f"CDN-Cloud-MagiTrickle/{VERSION}.0"
RIPE = "https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS = 2
RETRIES = 5
TIMEOUT = 30
RETRY_BASE = 2
MAX_WORKERS = 8
CACHE_TTL = 21600
MAX_PROVIDER_PREFIXES = 50000
MIN_CHANGE_RATIO = 0.50
MIN_CHANGE_RATIO_V6 = 0.35
MAX_AGGREGATE_PREFIXES = 200000
MIN_PREFIXLEN = {4: 8, 6: 16}
MIN_PREFIXES = {"aws": 20, "cloudflare": 5, "akamai": 10, "fastly": 5, "gcore": 10, "backblaze": 1, "bunny": 1, "leaseweb": 1, "upcloud": 1, "ionos": 1, "default": 1}

STATIC = {
    "backblaze": [
        "45.11.36.0/22", "104.153.232.0/21", "149.137.128.0/20",
        "206.190.208.0/21", "207.166.148.0/22", "2605:72c0::/32",
    ]
}

SOURCE_HEALTH = DATA / "source-health.json"
DIFF_DIR = DATA / "diff"
DIFF_DIR.mkdir(exist_ok=True)
HISTORY_LIMIT = 10001

def source_probe(url):
    try:
        data = request(url)
        return {"ok": True, "bytes": len(data)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:240]}

def load_old_raw(path):
    if not path.exists(): return []
    try: return path.read_text(encoding="utf-8").splitlines()
    except Exception: return []

def write_diff(name, old4, new4, old6, new6):
    def diff(old, new):
        return sorted(set(new)-set(old)), sorted(set(old)-set(new))
    add4, del4 = diff(old4,new4); add6, del6 = diff(old6,new6)
    payload = {
        "provider": name,
        "added": {"ipv4": len(add4), "ipv6": len(add6)},
        "removed": {"ipv4": len(del4), "ipv6": len(del6)},
        "sample_added": {"ipv4": add4[:100], "ipv6": add6[:100]},
        "sample_removed": {"ipv4": del4[:100], "ipv6": del6[:100]}
    }
    write_text_atomic(DIFF_DIR / f"{name}.json", json.dumps(payload, indent=2, ensure_ascii=False)+"\n")
    return payload

def discover_asn_notes(cfg):
    # Record configured ASN coverage; discovery is advisory and never mutates providers.json automatically.
    return {name: sorted(set(asns)) for name, asns in cfg["providers"].items()}
    
def cache_path(url):
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cache_dir = DATA / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / key

def request(url):
    cached = cache_path(url)
    try:
        if cached.exists() and time.time() - cached.stat().st_mtime < CACHE_TTL:
            return cached.read_bytes()
    except OSError:
        pass
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/json,text/plain,*/*",
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                data = res.read()
                if not data:
                    raise RuntimeError("empty response")
                try:
                    cached.write_bytes(data)
                except OSError:
                    pass
                return data
        except Exception as exc:
            last = exc
            if attempt < RETRIES:
                time.sleep(RETRY_BASE * attempt)
    raise last

def jsonget(url):
    return json.loads(request(url).decode("utf-8"))

def ripe_routing_status(asn):
    """Return current RIPEstat routing status for an ASN."""
    url = "https://stat.ripe.net/data/routing-status/data.json?" + urllib.parse.urlencode({
        "resource": "AS" + asn,
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })
    try:
        return jsonget(url).get("data", {})
    except Exception:
        return {}


RIPE_CACHE_FILE = DATA / "ripe-prefix-cache.json"
RIPE_CACHE_TTL = 86400
RIPE_CACHE_MAX_AGE = 7 * 86400


def load_ripe_cache():
    now = int(time.time())
    cutoff = now - RIPE_CACHE_MAX_AGE
    try:
        if not RIPE_CACHE_FILE.exists():
            return {}
        obj = json.loads(RIPE_CACHE_FILE.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return {}
        # Keep the 24h validation TTL, but remove entries older than 7 days
        # so the cache cannot grow indefinitely.
        return {
            prefix: entry for prefix, entry in obj.items()
            if isinstance(entry, dict) and int(entry.get("ts", 0)) >= cutoff
        }
    except Exception:
        return {}


def save_ripe_cache(cache):
    try:
        atomic_json(RIPE_CACHE_FILE, cache)
    except Exception:
        pass


def atomic_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def ripe_prefix_overview(prefix):
    """Return RIPEstat's current view for one candidate prefix."""
    url = "https://stat.ripe.net/data/prefix-overview/data.json?" + urllib.parse.urlencode({
        "resource": prefix,
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })
    try:
        return jsonget(url).get("data", {})
    except Exception:
        return {}


def validate_prefix_with_ripe(prefix, cache=None):
    """Confirm a candidate, reusing a 24-hour RIPEstat cache."""
    now = int(time.time())
    cache = cache if cache is not None else {}
    entry = cache.get(prefix)
    if isinstance(entry, dict):
        try:
            if now - int(entry.get("ts", 0)) < RIPE_CACHE_TTL:
                return bool(entry.get("confirmed", False))
        except (TypeError, ValueError):
            pass

    data = ripe_prefix_overview(prefix)
    confirmed = bool(data.get("announced") is True or data.get("asns"))
    cache[prefix] = {"ts": now, "confirmed": confirmed}
    return confirmed


def select_ripe_candidates(prefixes, limit=128):
    """Select a bounded, deterministic sample of prefixes for confirmation."""
    unique = sorted(set(prefixes), key=lambda p: (":" in p, p))
    if len(unique) <= limit:
        return unique
    # Prefer the least-specific prefixes first: they represent more address
    # space and give a useful sanity check without querying every CIDR.
    def prefix_key(p):
        try:
            return (ipaddress.ip_network(p, strict=False).prefixlen, p)
        except ValueError:
            return (999, p)
    return sorted(unique, key=prefix_key)[:limit]



def routeviews_prefixes(asn):
    """Fallback BGP source using RouteViews current RIB data."""
    found = set()
    for af in (4, 6):
        url = f"https://api.routeviews.org/asn/{asn}?af={af}"
        try:
            payload = jsonget(url)
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, str) and "/" in item:
                        found.add(item)
                    elif isinstance(item, dict) and item.get("prefix"):
                        found.add(item["prefix"])
        except Exception:
            pass
    return sorted(found)


def ripe(asn, min_peers):
    """Merge RIPEstat BGP views and use RouteViews as a fallback."""
    found = set()

    query = urllib.parse.urlencode({
        "resource": "AS" + asn,
        "min_peers_seeing": min_peers,
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })
    try:
        payload = jsonget(RIPE + "?" + query)
        for item in payload.get("data", {}).get("prefixes", []):
            if isinstance(item, dict) and item.get("prefix"):
                found.add(item["prefix"])
    except Exception:
        pass

    ris_query = urllib.parse.urlencode({
        "resource": "AS" + asn,
        "list_prefixes": "true",
        "types": "o",
        "af": "v4,v6",
        "noise": "filter",
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })
    try:
        ris = jsonget("https://stat.ripe.net/data/ris-prefixes/data.json?" + ris_query)
        ripe_ok = True
        for value in walk_strings(ris.get("data", {}).get("prefixes", [])):
            if "/" in value:
                try:
                    ipaddress.ip_network(value, strict=False)
                    found.add(value)
                except ValueError:
                    pass
    except Exception:
        pass

    # Fuse RouteViews with RIPEstat instead of treating it only as a hard
    # fallback. Different collectors can see different announcements; merging
    # both views improves coverage while the normal CIDR normalization and
    # aggregation stage removes duplicates and nested prefixes.
    routeviews = routeviews_prefixes(asn)
    if routeviews:
        found.update(routeviews)

    return sorted(found)

def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from walk_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_strings(value)

def external_ipsets(name, asns):
    """Optional independent IP-set sources. They are additive, never authoritative."""
    values = []
    sources = []

    # sw.ext.io publishes provider-specific ipset files. Use only Cloudflare here,
    # where the source exposes separate IPv4/IPv6 lists.
    if name == "cloudflare":
        for label in ("ipset_full_cf4.list", "ipset_full_cf6.list"):
            url = "https://sw.ext.io/ipset/" + label
            try:
                data = request(url).decode("utf-8", errors="replace")
                found = []
                for line in data.splitlines():
                    value = line.split("#", 1)[0].strip()
                    if value and "/" in value:
                        try:
                            ipaddress.ip_network(value, strict=False)
                            found.append(value)
                        except ValueError:
                            pass
                if found:
                    values.extend(found)
                    sources.append("sw.ext.io")
            except Exception:
                pass

    return values, sources


def official(name): 
    if name == "aws":
        obj = jsonget("https://ip-ranges.amazonaws.com/ip-ranges.json")
        return [item["ip_prefix"] for item in obj.get("prefixes", [])] + [item["ipv6_prefix"] for item in obj.get("ipv6_prefixes", [])]
    if name == "cloudflare":
        return request("https://www.cloudflare.com/ips-v4/").decode().splitlines() + request("https://www.cloudflare.com/ips-v6/").decode().splitlines()
    if name == "digitalocean":
        text = request("https://digitalocean.com/geo/google.csv").decode("utf-8-sig")
        values = []
        for line in text.splitlines()[1:]:
            for value in line.split(","):
                value = value.strip().strip('"')
                if "/" in value:
                    values.append(value)
        return values
    if name == "oracle":
        obj = jsonget("https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json")
        values = []
        for region in obj.get("regions", []):
            for item in region.get("cidrs", []):
                if item.get("cidr"):
                    values.append(item["cidr"])
        return values
    if name == "scaleway":
        # Combine official Scaleway ranges with live AS12876 announcements.
        return [
            "51.15.0.0/16", "51.158.0.0/15", "51.159.0.0/16",
            "62.4.0.0/19", "62.210.0.0/16", "78.232.0.0/16",
            "151.115.0.0/16", "163.172.0.0/16", "195.154.0.0/16",
            "212.47.224.0/19", "212.83.128.0/19", "212.83.160.0/19",
            "212.129.0.0/18", "2001:bc8::/32",
        ]
    if name == "fastly":
        return list(walk_strings(jsonget("https://api.fastly.com/public-ip-list")))
    if name == "gcore":
        return list(walk_strings(jsonget("https://api.gcore.com/cdn/public-ip-list")))
    if name in STATIC:
        return STATIC[name]
    return []

def nets(values, version, global_only=True):
    parsed = set(); rejected = 0
    for value in values:
        try:
            net = value if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network)) else ipaddress.ip_network(str(value).strip(), strict=False)
            if net.version != version:
                continue
            if global_only and not net.is_global:
                rejected += 1; continue
            if net.prefixlen < MIN_PREFIXLEN[version]:
                rejected += 1; continue
            parsed.add(net)
        except Exception:
            rejected += 1
    return sorted(ipaddress.collapse_addresses(parsed), key=lambda n: (int(n.network_address), n.prefixlen)), rejected

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
        if os.path.exists(tmp): os.unlink(tmp)

def write_text_atomic(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bgp_tools_table(text, wanted_asns):
    """Extract CIDRs for wanted origins from bgp.tools table.jsonl."""
    import json as _json
    wanted = {int(a) for a in wanted_asns}
    found = {4: set(), 6: set()}
    for line in text.splitlines():
        try:
            row = _json.loads(line)
            asn = int(row.get("ASN", -1))
            cidr = str(row.get("CIDR", ""))
            hits = int(row.get("Hits", 0))
            if asn not in wanted or hits < 1:
                continue
            net = ipaddress.ip_network(cidr, strict=False)
            found[net.version].add(net)
        except (ValueError, TypeError, _json.JSONDecodeError):
            continue
    return {4: sorted(found[4]), 6: sorted(found[6])}

def main():
    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    min_peers = int(cfg.get("min_peers_seeing", MIN_PEERS))
    all4, all6, rows = [], [], []
    all_asn4, all_asn6 = [], []
    audit_rows = []
    policy_explain = {}
    provider_asns = {}
    for name, asns in cfg["providers"].items():
        raw, sources, errors = [], [], []
        unique_asns = []
        for asn in asns:
            if asn not in unique_asns:
                unique_asns.append(asn)
            else:
                errors.append(f"duplicate ASN ignored: AS{asn}")
        provider_asns[name] = unique_asns
        try:
            raw = official(name)
            if raw: sources.append("official" if name not in STATIC else "static")
        except Exception as exc:
            errors.append("official:" + str(exc))

        try:
            extra, extra_sources = external_ipsets(name, unique_asns)
            raw.extend(extra)
            sources.extend(extra_sources)
        except Exception as exc:
            errors.append("external-ipset:" + str(exc))
        def fetch_asn(asn):
            try:
                return asn, ripe(asn, min_peers), None
            except Exception as exc:
                return asn, [], exc
        if unique_asns:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(unique_asns))) as pool:
                results = list(pool.map(fetch_asn, unique_asns))
            for asn, values, error in results:
                if error:
                    errors.append(f"RIPE-AS{asn}:{error}")
                else:
                    raw.extend(values)
                    all_asn4.extend(v for v in values if "/" in v and ":" not in v)
                    all_asn6.extend(v for v in values if ":" in v)
                    sources.append("RIPEstat")
                    routing = ripe_routing_status(asn)
                    if routing:
                        sources.append("RIPE routing-status")
        old4 = DATA / f"{name}-v4.txt"; old6 = DATA / f"{name}-v6.txt"
        old4_raw, old6_raw = load_old_raw(old4), load_old_raw(old6)
        v4, rejected4 = nets(raw, 4); v6, rejected6 = nets(raw, 6)
        v4_raw, v6_raw = list(map(str, v4)), list(map(str, v6))
        v4_policy, exp4 = apply_policy(name, v4_raw)
        v6_policy, exp6 = apply_policy(name, v6_raw)
        v4, _ = nets(v4_policy, 4); v6, _ = nets(v6_policy, 6)
        policy_explain[name] = {"ipv4": exp4, "ipv6": exp6}

        prev4 = load_previous(old4, 4); prev6 = load_previous(old6, 6)
        minimum = MIN_PREFIXES.get(name, MIN_PREFIXES["default"])
        status = "OK"; used_fallback = False
        suspicious4 = len(v4) < minimum or len(v4) > MAX_PROVIDER_PREFIXES
        suspicious6 = len(v6) > MAX_PROVIDER_PREFIXES
        if prev4 and len(v4) < int(len(prev4) * MIN_CHANGE_RATIO): suspicious4 = True
        if prev6 and len(v6) < int(len(prev6) * MIN_CHANGE_RATIO_V6): suspicious6 = True
        if suspicious4 and prev4:
            v4 = prev4; status = "KEEP_OLD"; used_fallback = True
        if suspicious6 and prev6:
            v6 = prev6; status = "KEEP_OLD" if status == "OK" else status; used_fallback = True
        if suspicious4 and not prev4:
            status = "EMPTY" if not v4 else "ANOMALY"
        if suspicious6 and not prev6 and not v6:
            status = "EMPTY" if status == "OK" else status
        if errors:
            if prev4 and len(v4) < len(prev4):
                v4 = prev4; status = "KEEP_OLD_PARTIAL"; used_fallback = True
            if prev6 and len(v6) < len(prev6):
                v6 = prev6; status = "KEEP_OLD_PARTIAL"; used_fallback = True
            if status == "OK": status = "PARTIAL"
        if rejected4 or rejected6:
            if status == "OK": status = "FILTERED"
        # Persist each address family independently. A fallback in IPv4 must not
        # prevent a healthy IPv6 refresh (and vice versa).
        if not suspicious4 or not prev4:
            atomic(old4, v4)
        if not suspicious6 or not prev6:
            atomic(old6, v6)
        diff_info = write_diff(name, old4_raw, list(map(str,v4)), old6_raw, list(map(str,v6)))
        source = "+".join(dict.fromkeys(sources)) or "none"
        all4.extend(v4); all6.extend(v6)
        prev4_count, prev6_count = len(prev4), len(prev6)
        pct4 = None if not prev4_count else round((len(v4) - prev4_count) * 100 / prev4_count, 2)
        pct6 = None if not prev6_count else round((len(v6) - prev6_count) * 100 / prev6_count, 2)
        audit_rows.append({
            "provider": name, "ipv4_prefixes": len(v4), "ipv6_prefixes": len(v6),
            "previous_ipv4_prefixes": prev4_count, "previous_ipv6_prefixes": prev6_count,
            "ipv4_change_percent": pct4, "ipv6_change_percent": pct6,
            "status": status, "source": source, "errors": len(errors),
        })
        rows.append({"name": name, "ipv4": len(v4), "ipv6": len(v6), "source": source, "status": status, "errors": errors[:10], "rejected_ipv4": rejected4, "rejected_ipv6": rejected6})
        print(f"{name}: v4={len(v4)} v6={len(v6)} {source} {status}")
        if errors: print(f"  warnings: {len(errors)}")
        if rejected4 or rejected6: print(f"  filtered: ipv4={rejected4} ipv6={rejected6}")
    all4, _ = nets(all4, 4); all6, _ = nets(all6, 6)
    all_asn4, _ = nets(all_asn4, 4); all_asn6, _ = nets(all_asn6, 6)

    validated_asn4 = []
    validated_asn6 = []
    candidates = select_ripe_candidates(all_asn4 + all_asn6, limit=128)
    ripe_cache = load_ripe_cache()
    if candidates:
        # Cache reads happen before parallel requests; cache writes are merged
        # in the main thread to avoid concurrent mutation of the shared dict.
        cached_checks = {}
        pending = []
        for prefix in candidates:
            entry = ripe_cache.get(prefix)
            try:
                fresh = isinstance(entry, dict) and int(time.time()) - int(entry.get("ts", 0)) < RIPE_CACHE_TTL
            except (TypeError, ValueError):
                fresh = False
            if fresh:
                cached_checks[prefix] = bool(entry.get("confirmed", False))
            else:
                pending.append(prefix)

        def confirm(prefix):
            data = ripe_prefix_overview(prefix)
            return bool(data.get("announced") is True or data.get("asns"))

        if pending:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                results = list(pool.map(confirm, pending))
            now = int(time.time())
            for prefix, confirmed in zip(pending, results):
                ripe_cache[prefix] = {"ts": now, "confirmed": confirmed}
                cached_checks[prefix] = confirmed

        save_ripe_cache(ripe_cache)
        for prefix in candidates:
            confirmed = cached_checks.get(prefix, False)
            if confirmed:
                (validated_asn6 if ":" in prefix else validated_asn4).append(prefix)
    atomic(DATA / "asn-confirmed-v4.txt", validated_asn4)
    atomic(DATA / "asn-confirmed-v6.txt", validated_asn6)
    atomic(DATA / "asn-all-v4.txt", all_asn4)
    atomic(DATA / "asn-all-v6.txt", all_asn6)
    if not all4: sys.exit("[FATAL] no aggregate IPv4")
    if len(all4) > MAX_AGGREGATE_PREFIXES or len(all6) > MAX_AGGREGATE_PREFIXES:
        sys.exit("[FATAL] aggregate prefix count exceeds safety limit")
    atomic(DATA / "all-cloud-v4.txt", all4); atomic(DATA / "all-cloud-v6.txt", all6)
    # Profiles have a single owner to prevent the stable engine and the standalone
    # profile generator from drifting apart.
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_profiles.py")], check=True)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest = {
        "version": VERSION, "updated": now, "ripe_min_peers": min_peers,
        "sources": ["official", "RIPEstat", "RIPE RIS", "RouteViews", "sw.ext.io"],
        "features": ["source-fusion","multi-collector-bgp","multi-source-asn-discovery","ripe-routing-status","ripe-prefix-overview","asn-confirmed-lists","source-health","deduplication","cidr-aggregation","diff","profiles","sha256","asn-audit","parallel-fetch","source-cache"],
        "engine": "unified-provider-sources-v46",
        "provider_asn_counts": {k: len(v) for k, v in provider_asns.items()},
        "provider_asns": provider_asns,
        "retries": RETRIES, "timeout_seconds": TIMEOUT, "max_workers": MAX_WORKERS, "cache_ttl_seconds": CACHE_TTL, "min_change_ratio": MIN_CHANGE_RATIO, "min_change_ratio_v6": MIN_CHANGE_RATIO_V6,
        "max_aggregate_prefixes": MAX_AGGREGATE_PREFIXES,
        "max_provider_prefixes": MAX_PROVIDER_PREFIXES, "global_only": True,
        "min_prefixlen": {"ipv4": MIN_PREFIXLEN[4], "ipv6": MIN_PREFIXLEN[6]},
        "aggregate": {"ipv4": len(all4), "ipv6": len(all6)},
        "audit": audit_rows,
        "diff": {name: write_diff(name, load_old_raw(DATA/f"{name}-v4.txt"), [], load_old_raw(DATA/f"{name}-v6.txt"), []) for name in []},
        "providers": {row["name"]: {
            "ipv4": row["ipv4"], "ipv6": row["ipv6"], "source": row["source"],
            "status": row["status"], "rejected_ipv4": row["rejected_ipv4"], "rejected_ipv6": row["rejected_ipv6"],
            **({"errors": row["errors"]} if row["errors"] else {})
        } for row in rows},
    }
    write_text_atomic(DATA / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    write_text_atomic(DATA / "policy-explain.json", json.dumps(policy_explain, indent=2, ensure_ascii=False) + "\n")
    summary = [f"Updated: {now}", f"ALL IPv4: {len(all4)}", f"ALL IPv6: {len(all6)}", f"ALL ASN IPv4: {len(all_asn4)}", f"ALL ASN IPv6: {len(all_asn6)}", "", "Provider,IPv4,IPv6,Source,Status,Errors,RejectedIPv4,RejectedIPv6"]
    summary.extend(f"{row['name']},{row['ipv4']},{row['ipv6']},{row['source']},{row['status']},{len(row['errors'])},{row['rejected_ipv4']},{row['rejected_ipv6']}" for row in rows)
    write_text_atomic(DATA / "last-update.txt", "\n".join(summary) + "\n")
    health = {
        "checked_at": now,
        "sources": {
            "RIPEstat": source_probe(RIPE + "?resource=AS13335&min_peers_seeing=1"),
            "AWS": source_probe("https://ip-ranges.amazonaws.com/ip-ranges.json"),
            "Cloudflare": source_probe("https://www.cloudflare.com/ips-v4/")
        }
    }
    write_text_atomic(SOURCE_HEALTH, json.dumps(health, indent=2, ensure_ascii=False)+"\n")
    audit_lines = ["Provider,IPv4,IPv6,PreviousIPv4,PreviousIPv6,IPv4Change%,IPv6Change%,Status,Source,Errors"]
    audit_lines.extend(
        f"{r['provider']},{r['ipv4_prefixes']},{r['ipv6_prefixes']},{r['previous_ipv4_prefixes']},{r['previous_ipv6_prefixes']},{r['ipv4_change_percent']},{r['ipv6_change_percent']},{r['status']},{r['source']},{r['errors']}"
        for r in audit_rows
    )
    write_text_atomic(DATA / "audit.csv", "\n".join(audit_lines) + "\n")
    history_path = DATA / "history.csv"
    header = "Timestamp,Provider,IPv4,IPv6,IPv4Change%,IPv6Change%,Status"
    history_lines = history_path.read_text(encoding="utf-8").splitlines() if history_path.exists() else [header]
    for r in audit_rows:
        history_lines.append(
            f"{now},{r['provider']},{r['ipv4_prefixes']},{r['ipv6_prefixes']},{r['ipv4_change_percent']},{r['ipv6_change_percent']},{r['status']}"
        )
    write_text_atomic(history_path, "\n".join(history_lines[-HISTORY_LIMIT:]) + "\n")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "check_checksums.py")], check=True)

if __name__ == "__main__": main()
