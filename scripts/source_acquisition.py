#!/usr/bin/env python3
"""Source acquisition and external-feed adapters for CDN-Cloud-MagiTrickle."""
import datetime
import ipaddress
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
CACHE=DATA/"cache"
def source_probe(url):
    try:
        data = request(url)
        return {"ok": True, "bytes": len(data)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:240]}


def discover_asn_notes(cfg):
    # Record configured ASN coverage; discovery is advisory and never mutates providers.json automatically.
    return {name: sorted(set(asns)) for name, asns in cfg["providers"].items()}
    

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




def ipverse_ranges(asn):
    """Fetch daily BGP-aggregated prefixes from IPVerse for one ASN.
    IPVerse is an independent BGP-derived source; it is additive and never
    replaces official provider feeds or other BGP views.
    """
    found = []
    base = f"https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/{asn}"
    for filename in ("ipv4-aggregated.txt", "ipv6-aggregated.txt"):
        try:
            data = request(f"{base}/{filename}")
            found.extend(parse_cidr_lines(data))
        except Exception:
            continue
    return sorted(set(found))



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
    """Fetch independent BGP views separately for exact provenance."""
    views = {
        "RIPEstat": set(),
        "RIPE RIS": set(),
        "RouteViews": set(),
    }

    query = urllib.parse.urlencode({
        "resource": "AS" + asn,
        "min_peers_seeing": min_peers,
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })
    try:
        payload = jsonget(RIPE + "?" + query)
        for item in (payload.get("data", {}).get("prefixes", []) or payload.get("prefixes", [])):
            if isinstance(item, str):
                item = {"prefix": item}
            if isinstance(item, dict) and item.get("prefix"):
                value = item["prefix"]
                try:
                    views["RIPEstat"].add(str(ipaddress.ip_network(value, strict=False)))
                except ValueError:
                    pass
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
        for value in walk_strings(ris.get("data", {}).get("prefixes", [])):
            if "/" in value:
                try:
                    views["RIPE RIS"].add(str(ipaddress.ip_network(value, strict=False)))
                except ValueError:
                    pass
    except Exception:
        pass

    try:
        views["RouteViews"].update(
            str(ipaddress.ip_network(value, strict=False))
            for value in routeviews_prefixes(asn)
        )
    except Exception:
        pass

    return {source: sorted(values) for source, values in views.items()}


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




def load_source_registry():
    path = ROOT / "config/source_registry.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_cidr_lines(data):
    values = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        try:
            ipaddress.ip_network(value, strict=False)
            values.append(value)
        except ValueError:
            continue
    return values


def registry_provider_ranges(name, registry_id, spec):
    """Fetch only explicitly documented, stable hosted artifacts.

    Repository-only generators (cdn-ranges/cdn-fetcher) are intentionally not
    scraped by filename guessing. They remain validation/reference sources.
    """
    if registry_id != "cdn-ip-database":
        return []
    base = spec.get("base", "").rstrip("/")
    url = base + "/" + spec.get("resolved_ipv4", "resolved_ips.json")
    obj = json.loads(request(url).decode("utf-8"))
    wanted = name.lower().replace("_", "-")
    out = []

    def walk(node, provider=None):
        if isinstance(node, dict):
            local = str(node.get("provider", node.get("name", provider))).lower()
            for key, value in node.items():
                if key.lower() in ("provider", "name"):
                    continue
                walk(value, local)
        elif isinstance(node, list):
            for value in node:
                walk(value, provider)
        elif isinstance(node, str) and "/" in node:
            if provider is None or wanted in provider or provider in wanted:
                try:
                    ipaddress.ip_network(node, strict=False)
                    out.append(node)
                except ValueError:
                    pass

    walk(obj)
    return sorted(set(out))



def registry_cloud_ranges(name, registry):
    cloud = registry.get("cloud-ip-ranges", {})
    filename = cloud.get("files", {}).get(name)
    if not filename:
        return [], None
    url = cloud.get("base", "").rstrip("/") + "/" + filename
    try:
        data = request(url)
        values = parse_cidr_lines(data)
        import re
        text = data.decode("utf-8", errors="replace")
        match = re.search(r"^#\\s*last_update:\\s*(\\d{4}-\\d{2}-\\d{2})", text, re.M)
        if match:
            stamp = datetime.datetime.fromisoformat(match.group(1)).replace(tzinfo=datetime.timezone.utc)
            if (datetime.datetime.now(datetime.timezone.utc) - stamp).total_seconds() > 14 * 86400:
                return [], "stale cloud-ip-ranges snapshot: " + match.group(1)
        return values, url
    except Exception as exc:
        return [], "cloud-ip-ranges:" + str(exc)


def registry_egress_ranges(name, registry):
    spec = registry.get("cloud-egress-ip-ranges", {})
    if name not in spec.get("providers", []):
        return [], None
    url = spec.get("url")
    if not url:
        return [], None
    try:
        obj = jsonget(url)
        aliases = {
            "microsoft": {"azure", "microsoft", "microsoft-azure"},
            "aws": {"aws", "amazon"},
        }
        wanted = aliases.get(name, {name})
        provider_field = spec.get("provider_field", "provider")
        cidr_field = spec.get("cidr_field", "cidr")
        records = obj if isinstance(obj, list) else obj.get("ranges", obj.get("data", []))
        if isinstance(records, dict):
            records = records.values()
        values = []
        for item in records or []:
            if not isinstance(item, dict):
                continue
            if str(item.get(provider_field, "")).lower() not in wanted:
                continue
            cidr = item.get(cidr_field)
            if cidr:
                try:
                    ipaddress.ip_network(str(cidr), strict=False)
                    values.append(str(cidr))
                except ValueError:
                    pass
        return values, url
    except Exception as exc:
        return [], "cloud-egress:" + str(exc)


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

