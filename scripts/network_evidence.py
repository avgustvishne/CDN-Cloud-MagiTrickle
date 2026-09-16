#!/usr/bin/env python3
"""Collect observational BGP/IRR/RPKI evidence for a bounded prefix sample.

RIPEstat is used only as an evidence source. A failed API call, an RPKI INVALID
state, or absence from BGP never changes published subscription data.
"""
import concurrent.futures
import datetime as dt
import ipaddress
import json
import os
import pathlib
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INPUT = DATA / "source-intelligence.json"
OUTPUT = DATA / "network-evidence.json"
API = "https://stat.ripe.net/data"
MAX_PREFIXES = int(os.environ.get("MAX_NETWORK_EVIDENCE", "128"))
WORKERS = int(os.environ.get("NETWORK_EVIDENCE_WORKERS", "8"))
TIMEOUT = 15
RETRIES = 2
SOURCEAPP = "cdn-cloud-magitrickle"


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def api(endpoint, resource, extra=None):
    params = {"resource": resource, "sourceapp": SOURCEAPP}
    if extra:
        params.update(extra)
    url = f"{API}/{endpoint}/data.json?{urllib.parse.urlencode(params)}"
    last = None
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") != "ok":
                raise RuntimeError(payload.get("messages") or payload.get("status"))
            return payload.get("data", {})
        except Exception as exc:
            last = str(exc)
            if attempt < RETRIES:
                time.sleep(1 + attempt)
    return {"_error": last or "unknown error"}


def validate_prefix(value):
    try:
        return str(ipaddress.ip_network(value, strict=False))
    except ValueError:
        return None


def evidence_for(row):
    prefix = validate_prefix(row.get("prefix", ""))
    result = {
        "provider": row.get("provider", ""),
        "prefix": prefix,
        "queried_at": now(),
        "sources": {"ripestat": "RIPEstat"},
        "bgp": {"announced": None, "origins": [], "visibility": None},
        "irr": {"present": None, "sources": []},
        "rpki": {"checked": False, "statuses": []},
        "status": "unavailable",
    }
    if not prefix:
        result["error"] = "invalid prefix"
        return result

    consistency = api("prefix-routing-consistency", prefix)
    if "_error" in consistency:
        result["error"] = consistency["_error"]
        return result

    result["bgp"]["announced"] = bool(consistency.get("in_bgp"))
    result["irr"]["present"] = bool(consistency.get("in_whois"))
    result["irr"]["sources"] = sorted(set(consistency.get("irr_sources") or []))

    origin = consistency.get("origin")
    origins = []
    if origin is not None:
        try:
            origins.append(int(origin))
        except (TypeError, ValueError):
            pass
    for item in consistency.get("origins") or []:
        if isinstance(item, dict):
            try:
                origins.append(int(item.get("origin")))
            except (TypeError, ValueError):
                pass
        elif isinstance(item, (int, str)):
            try:
                origins.append(int(item))
            except ValueError:
                pass
    origins = sorted(set(origins))
    result["bgp"]["origins"] = [f"AS{x}" for x in origins]

    rpki = []
    for asn in origins[:8]:
        data = api("rpki-validation", prefix, {"resource": asn})
        if "_error" not in data:
            rpki.append({
                "asn": f"AS{asn}",
                "status": data.get("status"),
            })
    result["rpki"]["checked"] = bool(rpki)
    result["rpki"]["statuses"] = rpki

    if result["bgp"]["announced"] and result["irr"]["present"] and rpki:
        result["status"] = "evidence_collected"
    elif result["bgp"]["announced"] or result["irr"]["present"]:
        result["status"] = "partial"
    return result


def main():
    intelligence = json.loads(INPUT.read_text(encoding="utf-8"))
    candidates = intelligence.get("prefix_evidence", [])
    unique = {}
    for row in candidates:
        prefix = validate_prefix(row.get("prefix", ""))
        if prefix and prefix not in unique:
            unique[prefix] = row
    selected = [unique[key] for key in sorted(unique)[:MAX_PREFIXES]]

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(evidence_for, selected))

    payload = {
        "schema_version": 1,
        "generated_at": now(),
        "provider": "RIPEstat",
        "policy": {
            "mode": "observational",
            "max_prefixes": MAX_PREFIXES,
            "rpki_invalid_deletes_prefix": False,
            "bgp_absence_deletes_prefix": False,
            "irr_absence_deletes_prefix": False,
        },
        "queried": len(results),
        "evidence": results,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    counts = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(f"Network evidence: {len(results)} prefixes; {counts}")


if __name__ == "__main__":
    main()
