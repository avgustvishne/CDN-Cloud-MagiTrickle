#!/usr/bin/env python3
import datetime
import concurrent.futures
import contextlib
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
import argparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
if str(ROOT / "scripts") not in sys.path: sys.path.insert(0, str(ROOT / "scripts"))

from policy_engine import apply as apply_policy
from generate_profiles import ALL_CLOUD_PROVIDERS
DATA.mkdir(exist_ok=True)

VERSION = 44
UA = f"CDN-Cloud-MagiTrickle/{VERSION}.0"
RIPE = "https://stat.ripe.net/data/announced-prefixes/data.json"
MIN_PEERS = 1
RETRIES = 2
TIMEOUT = 15
RETRY_BASE = 2
MAX_WORKERS = 8
# Bound the amount of time one ASN can spend on external source lookups.
ASN_SOURCE_TIMEOUT = 60
CACHE_TTL = 21600
MIN_CHANGE_RATIO = 0.50
MIN_CHANGE_RATIO_V6 = 0.35
# Coverage ratios are the primary shrink guard. Prefix count alone is unsafe
# because CIDR aggregation can legitimately reduce the number of lines.
MIN_COVERAGE_RATIO = 0.50
MIN_COVERAGE_RATIO_V6 = 0.35
MAX_AGGREGATE_PREFIXES = 200000
MIN_PREFIXLEN = {4: 8, 6: 16}
MIN_PREFIXES = {"aws": 1, "cloudflare": 1, "akamai": 1, "fastly": 1, "gcore": 1, "backblaze": 1, "bunny": 1, "leaseweb": 1, "upcloud": 1, "ionos": 1, "default": 1}

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
    except OSError as exc:
        print(f"[warn] cache read failed for {cached}: {exc}", file=sys.stderr)
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
                except OSError as exc:
                    print(f"[warn] cache write failed for {cached}: {exc}", file=sys.stderr)
                return data
        except Exception as exc:
            last = exc
            if attempt < RETRIES:
                time.sleep(RETRY_BASE * attempt)
    if last is not None:
        raise last
    raise RuntimeError(f"request failed without a captured exception: {url}")

def jsonget(url):
    return json.loads(request(url).decode("utf-8"))

def source_family(source):
    """Map evidence channels to an independence family for confidence scoring."""
    families = {
        "official": "official",
        "IPVerse": "ipverse",
        "RIPEstat": "ripe",
        "RIPE RIS": "ripe",
        "RIS-Live": "ripe",
        "RouteViews": "routeviews",
        "RouteViews BMP": "routeviews",
        "BGPStream": "bgpstream",
        "HE BGP": "he",
        "CDNCheck": "cdncheck",
        "RussiaFancyLists": "community",
        "static": "static",
    }
    return families.get(source, source.lower().replace(" ", "_"))


def independent_source_families(sources):
    return sorted({source_family(s) for s in sources if s})


def evidence_score(sources, bgp_peers=0):
    """Score evidence without counting correlated RIPE/RouteViews channels twice."""
    families = independent_source_families(sources)
    score = 0
    if "official" in families:
        score += 40
    if "ipverse" in families:
        score += 20
    if "ripe" in families:
        score += 10
    if "routeviews" in families:
        score += 10
    if "he" in families:
        score += 10
    if "cdncheck" in families:
        score += 5
    if "community" in families:
        score += 5
    if bgp_peers >= 2:
        score += 5
    return min(100, score)


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
    except Exception as exc:
        print(f"[warn] failed to save RIPE cache: {exc}", file=sys.stderr)


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
            # Malformed cache entry (e.g. non-integer ts): treat as cache miss
            # and continue to refresh from RIPE below.
            pass

    data = ripe_prefix_overview(prefix)
    confirmed = bool(data.get("announced") is True or data.get("asns"))
    cache[prefix] = {"ts": now, "confirmed": confirmed}
    return confirmed


def select_ripe_candidates(prefixes, limit=128):
    print(f"[candidates] normalizing {len(prefixes):,} prefixes", flush=True)
    """Select a bounded, deterministic sample of prefixes for confirmation."""
    normalized = set()
    for prefix in prefixes:
        try:
            if isinstance(prefix, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                normalized.add(str(prefix))
            else:
                normalized.add(str(ipaddress.ip_network(str(prefix), strict=False)))
        except (TypeError, ValueError):
            continue
    unique = sorted(
        normalized,
        key=lambda p: (
            1 if ":" in p else 0,
            ipaddress.ip_network(p, strict=False).version,
            int(ipaddress.ip_network(p, strict=False).network_address),
            ipaddress.ip_network(p, strict=False).prefixlen,
        ),
    )
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
    """Fetch IPVerse IPv4/IPv6 aggregates concurrently; source is additive."""
    base = f"https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/{asn}"
    def fetch(filename):
        try:
            return parse_cidr_lines(request(f"{base}/{filename}"))
        except Exception:
            return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        parts = list(pool.map(fetch, ("ipv4-aggregated.txt", "ipv6-aggregated.txt")))
    return sorted(set(parts[0] + parts[1]))


from routeviews_client import routeviews_prefixes

def ripe(asn, min_peers):
    """Fetch independent BGP views concurrently while preserving provenance."""
    query = urllib.parse.urlencode({
        "resource": "AS" + asn,
        "min_peers_seeing": min_peers,
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })
    ris_query = urllib.parse.urlencode({
        "resource": "AS" + asn,
        "list_prefixes": "true",
        "types": "o",
        "af": "v4,v6",
        "noise": "filter",
        "sourceapp": "CDN-Cloud-MagiTrickle",
    })

    def fetch_ripestat():
        found = set()
        try:
            payload = jsonget(RIPE + "?" + query)
            for item in payload.get("data", {}).get("prefixes", []):
                if isinstance(item, dict) and item.get("prefix"):
                    try:
                        found.add(str(ipaddress.ip_network(item["prefix"], strict=False)))
                    except ValueError as exc:
                        print(f"[warn] invalid RIPEstat prefix for AS{asn}: {item.get('prefix')}: {exc}", file=sys.stderr)
        except Exception:
            pass
        return found

    def fetch_ris():
        found = set()
        try:
            ris = jsonget("https://stat.ripe.net/data/ris-prefixes/data.json?" + ris_query)
            for value in walk_strings(ris.get("data", {}).get("prefixes", [])):
                if "/" in value:
                    try:
                        found.add(str(ipaddress.ip_network(value, strict=False)))
                    except ValueError as exc:
                        print(f"[warn] invalid RIPE RIS prefix for AS{asn}: {value}: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"Warning: failed to fetch/parse RIPE RIS prefixes for AS{asn}: {exc}", file=sys.stderr)
        return found

    def fetch_routeviews():
        try:
            return {str(ipaddress.ip_network(value, strict=False)) for value in routeviews_prefixes(asn)}
        except Exception as exc:
            print(f"[warn] RouteViews normalization failed for AS{asn}: {exc}", file=sys.stderr)
            return set()

    funcs = (fetch_ripestat, fetch_ris, fetch_routeviews)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        ripestat, ris, routeviews = list(pool.map(lambda fn: fn(), funcs))
    return {
        "RIPEstat": sorted(ripestat),
        "RIPE RIS": sorted(ris),
        "RouteViews": sorted(routeviews),
        # Live RIS/RouteViews and CAIDA BGPStream remain evidence channels.
        # They are populated by the validation layer when available.
    }

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
                        except ValueError as exc:
                            print(f"[warn] invalid external CIDR for {name}: {value}: {exc}", file=sys.stderr)
                if found:
                    values.extend(found)
                    sources.append("sw.ext.io")
            except Exception as exc:
                print(f"[warn] external IP set fetch failed for {name} ({label}): {exc}", file=sys.stderr)

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
                with contextlib.suppress(ValueError):
                    ipaddress.ip_network(node, strict=False)
                    out.append(node)

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
                    print(
                        f"warning: skipping invalid CIDR '{cidr}' for provider '{name}' from {url}",
                        file=sys.stderr,
                    )
                    continue
        return values, url
    except Exception as exc:
        return [], "cloud-egress:" + str(exc)

def find_exact_duplicates(values):
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return sorted(duplicates)

def build_provider_overlap_report(provider_networks):
    owners = {}
    for provider, values in provider_networks.items():
        for value in values:
            owners.setdefault(value, []).append(provider)
    overlaps = {cidr: sorted(names) for cidr, names in owners.items() if len(names) > 1}
    return {
        "exact_cross_provider_overlaps": len(overlaps),
        "entries": [{"cidr": cidr, "providers": providers} for cidr, providers in sorted(overlaps.items())],
        "note": "Cross-provider overlaps are reported, not deleted; all-cloud is globally deduplicated."
    }

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
    if name == "telegram":
        return request("https://core.telegram.org/resources/cidr.txt").decode().split()
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

def address_coverage(networks):
    """Return total covered addresses without expanding CIDRs."""
    return sum(int(net.num_addresses) for net in networks)


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

def source_confidence(sources):
    """Score independent evidence; official/BGP/RPKI outrank secondary feeds."""
    weights={"official":100,"bgp_rpki":95,"asn_index":90,"independent":85,"secondary":60,"dns":40}
    kinds=[s.get("kind","secondary") for s in sources if isinstance(s,dict)]
    if not kinds: return 0
    score=max(weights.get(k,50) for k in kinds)
    independent=len(set(kinds))
    return min(100, score + min(10, max(0, independent-1)*2))

def load_bgpstream_health():
    """Load the latest optional BGPStream validation report."""
    path = DATA / "bgpstream-health.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(row.get("asn")): row for row in payload.get("results", [])}
    except Exception:
        return {}


def evidence_confidence(provider, cidr_sources, asn, bgp_health):
    """Combine source evidence without making live BGP a hard deletion rule."""
    kinds = {s.get("kind", "secondary") for s in cidr_sources if isinstance(s, dict)}
    score = source_confidence(cidr_sources)
    if "official" in kinds:
        score += 2
    if "asn_index" in kinds:
        score += 2
    if "independent" in kinds:
        score += 2
    row = bgp_health.get(str(asn))
    if row:
        if row.get("observed"):
            score += 5
        if int(row.get("peers", 0)) >= 2:
            score += 3
        elif int(row.get("peers", 0)) == 0:
            # A missing observation is neutral: live RIB snapshots are not
            # complete enough to justify deleting a prefix.
            score += 0
    return min(100, score)


def build_provenance(provider, prefixes, source_records, asn=None, bgp_health=None):
    records=[]
    for cidr in sorted(set(prefixes)):
        matched=[s for s in source_records if cidr in set(s.get("prefixes",[]))]
        records.append({"cidr":cidr,"provider":provider,"sources":[{"id":s.get("id"),"kind":s.get("kind","secondary"),"observed_at":s.get("observed_at")} for s in matched],"confidence":evidence_confidence(provider, matched, asn, bgp_health or {})})
    return records

def build_consensus(provider, prefixes, source_prefixes, asns, bgp_health):
    """Create exact per-CIDR evidence; BGP absence is neutral."""
    normalized = {}
    for source_id, values in source_prefixes.items():
        canonical = set()
        for value in values:
            try:
                canonical.add(str(ipaddress.ip_network(str(value), strict=False)))
            except ValueError:
                continue
        normalized[source_id] = canonical

    previous = {}
    previous_path = DATA / f"{provider}-consensus.json"
    if previous_path.exists():
        try:
            previous = {
                r.get("cidr"): r for r in json.loads(
                    previous_path.read_text(encoding="utf-8")
                ).get("records", [])
            }
        except Exception:
            previous = {}

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []
    for value in prefixes:
        try:
            cidr = str(ipaddress.ip_network(str(value), strict=False))
        except ValueError:
            continue

        evidence = sorted(
            source_id for source_id, values in normalized.items() if cidr in values
        )
        bgp_observed_asns = []
        bgp_peer_counts = []
        for asn in asns:
            row = bgp_health.get(str(asn))
            if not isinstance(row, dict):
                continue
            # New validator reports may contain exact observed prefixes.
            # Without that list, an ASN-level observation is deliberately
            # NOT attributed to every CIDR.
            observed_prefixes = set()
            raw_observed_prefixes = row.get("prefixes", row.get("observed_prefixes", []))
            # External BGP-health producers may use prefixes either for an
            # exact prefix list or for a numeric prefix count. Scalar
            # metadata is not exact evidence and must not crash the update.
            if isinstance(raw_observed_prefixes, dict):
                raw_observed_prefixes = raw_observed_prefixes.get(
                    "prefixes", raw_observed_prefixes.get("observed_prefixes", [])
                )
            if isinstance(raw_observed_prefixes, str):
                raw_observed_prefixes = [raw_observed_prefixes]
            elif not isinstance(raw_observed_prefixes, (list, tuple, set)):
                raw_observed_prefixes = []
            for prefix in raw_observed_prefixes:
                try:
                    observed_prefixes.add(
                        str(ipaddress.ip_network(str(prefix), strict=False))
                    )
                except (TypeError, ValueError):
                    continue
            if cidr in observed_prefixes:
                bgp_observed_asns.append(str(asn))
                try:
                    bgp_peer_counts.append(int(row.get("peers", 0)))
                except (TypeError, ValueError):
                    # Ignore malformed peer counts from external data sources.
                    continue

        independent_ids = {"IPVerse", "RIPEstat", "RIPE RIS", "RouteViews", "cdn-ip-database"}
        independent = len(set(evidence) & independent_ids)
        official = bool(set(evidence) & {"official", "cloud-ip-ranges", "cloud-egress-ip-ranges", "static"})
        score = min(
            100,
            20
            + (45 if official else 0)
            + min(20, independent * 5)
            + (10 if bgp_observed_asns else 0)
            + (5 if bgp_peer_counts and max(bgp_peer_counts) >= 2 else 0),
        )
        records.append({
            "cidr": cidr,
            "provider": provider,
            "sources": evidence,
            "source_count": len(evidence),
            "bgp_observed_asns": bgp_observed_asns,
            "bgp_max_peers": max(bgp_peer_counts) if bgp_peer_counts else 0,
            "confidence": score,
            "first_seen": previous.get(cidr, {}).get("first_seen") or now,
            "last_seen": now,
        })
    return records
def write_source_health_registry(registry):
    """Record registry capabilities without treating repository tools as live feeds."""
    rows=[]
    for source_id, spec in registry.items():
        rows.append({
            "id": source_id,
            "role": spec.get("role", ""),
            "refresh": spec.get("refresh", ""),
            "live_fetch_enabled": source_id in {"cloud-ip-ranges","cloud-egress-ip-ranges","cdn-ip-database","ipverse-as-ip-blocks"},
            "reference_only": source_id in {"taythebot-cdn-ranges","krainium-cdn-fetcher","projectdiscovery-cdncheck","routesentinel","cloud-provider-ip-addresses"},
        })
    write_text_atomic(DATA / "source-registry-health.json",
        json.dumps({"generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "sources": rows}, indent=2, ensure_ascii=False) + "\n")

def apply_global_policy_to_asn_aggregates(all_asn4, all_asn6):
    """Apply global policy rules to ASN-derived aggregate datasets."""
    asn4_policy, _ = apply_policy("__asn_aggregate__", list(map(str, all_asn4)), collect_explain=False)
    asn6_policy, _ = apply_policy("__asn_aggregate__", list(map(str, all_asn6)), collect_explain=False)
    filtered4, _ = nets(asn4_policy, 4)
    filtered6, _ = nets(asn6_policy, 6)
    return filtered4, filtered6

def main():
    parser = argparse.ArgumentParser(description="Build CDN/ASN subscriptions")
    parser.add_argument("--explain", action="store_true", help="generate per-CIDR policy explanations")
    parser.add_argument("--skip-confirmation", action="store_true", help="skip optional RIPE prefix confirmation")
    parser.add_argument("--skip-presets", action="store_true", help="skip preset subscription generation")
    args = parser.parse_args()
    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    registry = load_source_registry()
    bgp_health = load_bgpstream_health()
    write_source_health_registry(registry)
    min_peers = int(cfg.get("min_peers_seeing", MIN_PEERS))
    all4, all6, rows = [], [], []
    all_cloud4, all_cloud6 = [], []
    all_asn4, all_asn6 = [], []
    audit_rows = []
    policy_explain = {}
    provider_asns = {}
    for name, asns in cfg["providers"].items():
        raw, sources, errors = [], [], []
        source_prefixes = {}
        unique_asns = []
        for asn in asns:
            if asn not in unique_asns:
                unique_asns.append(asn)
            else:
                errors.append(f"duplicate ASN ignored: AS{asn}")
        provider_asns[name] = unique_asns
        try:
            raw = official(name)
            if raw:
                sources.append("official" if name not in STATIC else "static")
                source_prefixes["official" if name not in STATIC else "static"] = list(raw)
        except Exception as exc:
            errors.append("official:" + str(exc))

        try:
            registry_values, registry_source = registry_cloud_ranges(name, registry)
            if registry_values:
                raw.extend(registry_values)
                sources.append("cloud-ip-ranges")
                source_prefixes["cloud-ip-ranges"] = list(registry_values)
            elif registry_source and registry_source.startswith("stale"):
                errors.append(registry_source)
            elif registry_source and registry_source.startswith("cloud-ip-ranges:"):
                errors.append(registry_source)
        except Exception as exc:
            errors.append("cloud-ip-ranges:" + str(exc))

        try:
            egress_values, egress_source = registry_egress_ranges(name, registry)
            if egress_values:
                raw.extend(egress_values)
                sources.append("cloud-egress-ip-ranges")
                source_prefixes["cloud-egress-ip-ranges"] = list(egress_values)
        except Exception as exc:
            errors.append("cloud-egress:" + str(exc))

        # Independent registries are additive only when they expose a stable,
        # machine-readable hosted artifact. Repository-only tools are recorded as
        # references/validators instead of guessing their generated file layout.
        for registry_id, registry_spec in (
            ("cdn-ip-database", registry.get("cdn-ip-database", {})),
        ):
            try:
                values = registry_provider_ranges(name, registry_id, registry_spec)
                if values:
                    raw.extend(values)
                    sources.append(registry_id)
                    source_prefixes[registry_id] = list(values)
            except Exception as exc:
                errors.append(registry_id + ":" + str(exc))

        try:
            extra, extra_sources = external_ipsets(name, unique_asns)
            raw.extend(extra)
            sources.extend(extra_sources)
            for extra_source in extra_sources:
                source_prefixes.setdefault(extra_source, []).extend(extra)
        except Exception as exc:
            errors.append("external-ipset:" + str(exc))
        def fetch_asn(asn):
            try:
                bgp_views = ripe(asn, min_peers)
                ipverse_values = ipverse_ranges(asn)
                return asn, bgp_views, ipverse_values, None
            except Exception as exc:
                return asn, {}, [], exc
        if unique_asns:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(unique_asns))) as pool:
                results = list(pool.map(fetch_asn, unique_asns))
            for asn, bgp_views, ipverse_values, error in results:
                if error:
                    errors.append(f"RIPE-AS{asn}:{error}")
                else:
                    bgp_values = []
                    for source_id, values in bgp_views.items():
                        normalized_values = sorted(set(values))
                        bgp_values.extend(normalized_values)
                        if normalized_values:
                            raw.extend(normalized_values)
                            source_prefixes.setdefault(source_id, []).extend(normalized_values)
                            sources.append(source_id)
                    raw.extend(ipverse_values)
                    all_asn4.extend(v for v in bgp_values + ipverse_values if "/" in v and ":" not in v)
                    all_asn6.extend(v for v in bgp_values + ipverse_values if ":" in v)
                    if ipverse_values:
                        source_prefixes.setdefault("IPVerse", []).extend(ipverse_values)
                        sources.append("IPVerse")
                    routing = ripe_routing_status(asn)
                    if routing:
                        sources.append("RIPE routing-status")
        old4 = DATA / f"{name}-v4.txt"; old6 = DATA / f"{name}-v6.txt"
        old4_raw, old6_raw = load_old_raw(old4), load_old_raw(old6)
        v4, rejected4 = nets(raw, 4); v6, rejected6 = nets(raw, 6)
        v4_raw, v6_raw = list(map(str, v4)), list(map(str, v6))
        v4_policy, exp4 = apply_policy(name, v4_raw, collect_explain=args.explain)
        v6_policy, exp6 = apply_policy(name, v6_raw, collect_explain=args.explain)
        v4, _ = nets(v4_policy, 4); v6, _ = nets(v6_policy, 6)
        if find_exact_duplicates(v4_raw) or find_exact_duplicates(v6_raw):
            errors.append("duplicate source CIDRs normalized before output")
        if args.explain:
            policy_explain[name] = {"ipv4": exp4, "ipv6": exp6}

        prev4 = load_previous(old4, 4); prev6 = load_previous(old6, 6)
        minimum = MIN_PREFIXES.get(name, MIN_PREFIXES["default"])
        status = "OK"; used_fallback = False
        suspicious4 = False
        suspicious6 = False
        prev4_coverage = address_coverage(prev4)
        prev6_coverage = address_coverage(prev6)
        new4_coverage = address_coverage(v4)
        new6_coverage = address_coverage(v6)
        if prev4_coverage and new4_coverage < int(prev4_coverage * MIN_COVERAGE_RATIO):
            suspicious4 = True
        if prev6_coverage and new6_coverage < int(prev6_coverage * MIN_COVERAGE_RATIO_V6):
            suspicious6 = True
        if suspicious4 and prev4:
            v4 = prev4; status = "KEEP_OLD" if status == "OK" else status; used_fallback = True
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
        if not used_fallback:
            atomic(old4, v4); atomic(old6, v6)
        diff_info = write_diff(name, old4_raw, list(map(str,v4)), old6_raw, list(map(str,v6)))
        source = "+".join(dict.fromkeys(sources)) or "none"
        consensus = build_consensus(name, list(v4) + list(v6), source_prefixes, unique_asns, bgp_health)
        write_text_atomic(DATA / f"{name}-consensus.json", json.dumps({"provider": name, "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "asns": unique_asns, "records": consensus}, indent=2, ensure_ascii=False) + "\n")
        all4.extend(v4); all6.extend(v6)
        if name in ALL_CLOUD_PROVIDERS:
            all_cloud4.extend(v4)
            all_cloud6.extend(v6)
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
    provider_networks = {}
    for name in cfg["providers"]:
        provider_networks[name] = load_old_raw(DATA / f"{name}-v4.txt") + load_old_raw(DATA / f"{name}-v6.txt")
    overlap_report = build_provider_overlap_report(provider_networks)

    all4, _ = nets(all4, 4); all6, _ = nets(all6, 6)
    all_cloud4, _ = nets(all_cloud4, 4); all_cloud6, _ = nets(all_cloud6, 6)
    all_asn4, _ = nets(all_asn4, 4); all_asn6, _ = nets(all_asn6, 6)
    all_asn4, all_asn6 = apply_global_policy_to_asn_aggregates(all_asn4, all_asn6)

    validated_asn4 = []
    validated_asn6 = []
    candidates = [] if args.skip_confirmation else select_ripe_candidates(all_asn4 + all_asn6, limit=128)
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
    validated_asn4 = sorted(validated_asn4, key=lambda p: (int(ipaddress.ip_network(p, strict=False).network_address), ipaddress.ip_network(p, strict=False).prefixlen))
    validated_asn6 = sorted(validated_asn6, key=lambda p: (int(ipaddress.ip_network(p, strict=False).network_address), ipaddress.ip_network(p, strict=False).prefixlen))
    atomic(DATA / "asn-confirmed-v4.txt", validated_asn4)
    atomic(DATA / "asn-confirmed-v6.txt", validated_asn6)
    atomic(DATA / "asn-all-v4.txt", all_asn4)
    atomic(DATA / "asn-all-v6.txt", all_asn6)
    if not all4: sys.exit("[FATAL] no aggregate IPv4")
    if not all_cloud4: sys.exit("[FATAL] no ALL-CLOUD IPv4")
    if len(all4) > MAX_AGGREGATE_PREFIXES or len(all6) > MAX_AGGREGATE_PREFIXES:
        sys.exit("[FATAL] aggregate prefix count exceeds safety limit")
    if len(all_cloud4) > MAX_AGGREGATE_PREFIXES or len(all_cloud6) > MAX_AGGREGATE_PREFIXES:
        sys.exit("[FATAL] ALL-CLOUD prefix count exceeds safety limit")
    atomic(DATA / "all-cloud-v4.txt", all_cloud4); atomic(DATA / "all-cloud-v6.txt", all_cloud6)
    # Profiles have one generator. Keeping this logic in generate_profiles.py
    # prevents the two engines from drifting apart.
    if not args.skip_presets:
        import subprocess
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_profiles.py")],
            check=True,
        )

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest = {
        "version": VERSION, "updated": now, "ripe_min_peers": min_peers,
        "sources": ["official provider feeds", "disposable/cloud-ip-ranges", "ipanalytics/Cloud-Egress-IP-Ranges", "RIPEstat", "RIPE RIS", "RouteViews fallback", "IPVerse as-ip-blocks", "sw.ext.io", "RussiaFancyLists (independent Russia IP intelligence / validation only)"],
        "features": ["source-fusion","coverage-based-regression-guard","multi-source-asn-discovery","ripe-prefix-overview","asn-confirmed-lists","source-health","deduplication","cidr-aggregation","diff","profiles","sha256","asn-audit","parallel-fetch","source-cache","freshness-gates","ipverse-cross-check","single-profile-generator","consensus-evidence","per-cidr-provenance","anomaly-protection","cross-provider-overlap-audit","russiafancy-validation"],
        "engine": "final-v44-source-fusion-ipverse",
        "provider_asn_counts": {k: len(v) for k, v in provider_asns.items()},
        "provider_asns": provider_asns,
        "retries": RETRIES, "timeout_seconds": TIMEOUT, "max_workers": MAX_WORKERS, "cache_ttl_seconds": CACHE_TTL, "ipverse": "enabled", "min_change_ratio": MIN_CHANGE_RATIO, "min_change_ratio_v6": MIN_CHANGE_RATIO_V6, "min_coverage_ratio": MIN_COVERAGE_RATIO, "min_coverage_ratio_v6": MIN_COVERAGE_RATIO_V6,
        "max_aggregate_prefixes": MAX_AGGREGATE_PREFIXES,
        "min_provider_prefixes": None, "max_provider_prefixes": None, "global_only": True,
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
    consensus_index = {}
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            provider = payload.get("provider", path.stem.replace("-consensus", ""))
            records = payload.get("records", [])
            consensus_index[provider] = {"file": path.name, "cidrs": len(records), "high_confidence": sum(1 for x in records if x.get("confidence", 0) >= 80), "multi_source": sum(1 for x in records if x.get("source_count", 0) >= 2)}
        except Exception:
            continue
    all_consensus = []
    for path in sorted(DATA.glob("*-consensus.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            all_consensus.extend(payload.get("records", []))
        except Exception:
            continue
    write_text_atomic(
        DATA / "consensus.json",
        json.dumps({
            "engine": VERSION,
            "generated_at": now,
            "model": "multi-source-evidence",
            "rule": "BGP absence is neutral; a CIDR is never removed solely because a live snapshot did not observe it.",
            "providers": consensus_index,
            "records": all_consensus,
        }, indent=2, ensure_ascii=False) + "\n",
    )
    write_text_atomic(DATA / "provider-overlaps.json", json.dumps(overlap_report, indent=2, ensure_ascii=False) + "\n")
    write_text_atomic(DATA / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if args.explain:
        write_text_atomic(DATA / "policy-explain.json", json.dumps(policy_explain, indent=2, ensure_ascii=False) + "\n")
    checksum_files = sorted(set(DATA.glob("*-v*.txt")) | {DATA / "all-cloud-v4.txt", DATA / "all-cloud-v6.txt", DATA / "asn-all-v4.txt", DATA / "asn-all-v6.txt", DATA / "asn-confirmed-v4.txt", DATA / "asn-confirmed-v6.txt"})
    write_text_atomic(DATA / "checksums.sha256", "\n".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}" for path in checksum_files) + "\n")
    summary = [f"Updated: {now}", f"ALL IPv4: {len(all4)}", f"ALL IPv6: {len(all6)}", f"ALL ASN IPv4: {len(all_asn4)}", f"ALL ASN IPv6: {len(all_asn6)}", "", "Provider,IPv4,IPv6,Source,Status,Errors,RejectedIPv4,RejectedIPv6"]
    summary.extend(f"{row['name']},{row['ipv4']},{row['ipv6']},{row['source']},{row['status']},{len(row['errors'])},{row['rejected_ipv4']},{row['rejected_ipv6']}" for row in rows)
    write_text_atomic(DATA / "last-update.txt", "\n".join(summary) + "\n")
    health = {
        "checked_at": now,
        "sources": {
            "RIPEstat": source_probe(RIPE + "?resource=AS13335&min_peers_seeing=1"),
            "AWS": source_probe("https://ip-ranges.amazonaws.com/ip-ranges.json"),
            "Cloudflare": source_probe("https://www.cloudflare.com/ips-v4/"),
            "cloud-ip-ranges": source_probe("https://raw.githubusercontent.com/disposable/cloud-ip-ranges/master/txt/aws.txt"),
            "cloud-egress-ip-ranges": source_probe("https://github.com/ipanalytics/Cloud-Egress-IP-Ranges/releases/latest/download/cloud-egress-ip-ranges.json"),
            "RouteViews": source_probe("https://api.routeviews.org/"), "IPVerse": source_probe("https://raw.githubusercontent.com/ipverse/as-ip-blocks/master/as/13335/ipv4-aggregated.txt"), "RussiaFancyLists": source_probe("https://raw.githubusercontent.com/Noktomezo/RussiaFancyLists/main/lists/blacklist/ipsets/full-and-cdn.lst")
        }
    }
    try:
        rf = parse_cidr_lines(request("https://raw.githubusercontent.com/Noktomezo/RussiaFancyLists/main/lists/blacklist/ipsets/full-and-cdn.lst"))
        rf4, _ = nets(rf, 4)
        rf6, _ = nets(rf, 6)
    except Exception as exc:
        health["RussiaFancyLists"]["error"] = str(exc)
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

if __name__ == "__main__": main()