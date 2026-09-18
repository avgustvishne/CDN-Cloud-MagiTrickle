#!/usr/bin/env python3
"""Convert a local dpi-ch full-check JSON into sanitized profile evidence.

The raw dpi-ch report is intentionally never stored in the public repository.
Only provider/prefix/check evidence is written to data/dpi-intelligence.json.
"""
import argparse
import hashlib
import ipaddress
import json
import pathlib
import re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "providers.json"
POLICY = ROOT / "config" / "dpi_policy.json"
ISP_PROFILES = ROOT / "config" / "isp_profiles.json"
DEFAULT_OUTPUT = DATA / "dpi-intelligence.json"


def load_isp_context():
    """Load optional user-network ASN context without affecting provider classification."""
    if not ISP_PROFILES.exists():
        return {"enabled": False, "asns": []}
    try:
        value = json.loads(ISP_PROFILES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"enabled": False, "asns": []}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return {"enabled": False, "asns": []}
    entries = []
    for item in value.get("asns", []):
        if not isinstance(item, dict):
            continue
        try:
            asn = int(item["asn"])
        except (KeyError, TypeError, ValueError):
            continue
        if asn > 0:
            entries.append({
                "asn": asn,
                "name": str(item.get("name", "")),
                "country": str(item.get("country", "")),
            })
    return {"enabled": bool(value.get("enabled", False)), "asns": entries}

cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
policy = json.loads(POLICY.read_text(encoding="utf-8"))
provider_asns = {
    name: {str(asn) for asn in asns}
    for name, asns in cfg["providers"].items()
}
aliases = {
    "cloudflare": ("cloudflare",),
    "akamai": ("akamai",),
    "hetzner": ("hetzner",),
    "ovh": ("ovh",),
    "digitalocean": ("digitalocean",),
    "fastly": ("fastly",),
    "cdn77": ("cdn77", "datacamp"),
    "gcore": ("gcore",),
    "melbicom": ("melbicom", "melbikomas"),
    "buyvm": ("buyvm", "frantech"),
    "contabo": ("contabo",),
    "vultr": ("vultr",),
    "scaleway": ("scaleway",),
    "aws": ("amazon", "aws"),
    "microsoft": ("microsoft", "azure"),
    "oracle": ("oracle",),
    "alibaba": ("alibaba",),
    "backblaze": ("backblaze",),
}


def code(value):
    if isinstance(value, dict):
        return str(value.get("Code", value.get("code", ""))).upper()
    return str(value or "").upper()


def asn_digits(value):
    match = re.search(r"(\d+)", str(value or ""))
    return match.group(1) if match else ""


def provider_for(item):
    asn = asn_digits(item.get("AS", item.get("as", item.get("asn", ""))))
    for name, values in provider_asns.items():
        if asn and asn in values:
            return name
    org = str(item.get("Org", item.get("org", ""))).lower()
    for name, names in aliases.items():
        if any(alias in org for alias in names):
            return name
    return None


def webhost_items(report):
    webhost = report.get("Webhost", report.get("webhost", {}))
    if isinstance(webhost, dict):
        for group, value in webhost.items():
            for item in (value or {}).get("Items", (value or {}).get("items", [])):
                item = dict(item)
                item["_group"] = group
                yield item
    for item in report.get("results", []):
        if isinstance(item, dict):
            yield item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path, required=True, help="local dpi-ch JSON result")
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    raw_bytes = args.input.read_bytes()
    raw = json.loads(raw_bytes)
    qualification = policy["qualification"]
    isp_context = load_isp_context()
    candidates = {
        name
        for names in policy["candidates"].values()
        for name in names
    }

    grouped = {}
    for item in webhost_items(raw):
        prefix = item.get("Prefix", item.get("prefix", ""))
        try:
            network = ipaddress.ip_network(str(prefix), strict=False)
        except ValueError:
            continue
        if network.version != 4 or not network.is_global:
            continue

        provider = provider_for(item)
        if provider not in candidates:
            continue

        checks = {
            "alive": code(item.get("Alive", item.get("alive"))),
            "tcp1620": code(item.get("Tcp1620", item.get("tcp1620"))),
            "siberian": code(item.get("Siberian", item.get("siberian"))),
        }
        passed = (
            checks["alive"] in qualification["alive"]
            and checks["tcp1620"] in qualification["tcp1620"]
            and checks["siberian"] in qualification["siberian"]
        )
        key = (provider, str(network))
        grouped.setdefault(key, []).append({
            "checks": checks,
            "passed": passed,
        })

    qualified = {}
    evidence = []
    for (provider, prefix), samples in sorted(grouped.items()):
        passed = bool(samples) and (
            all(sample["passed"] for sample in samples)
            if qualification["require_all_samples_in_prefix_to_pass"]
            else any(sample["passed"] for sample in samples)
        )
        if not passed:
            continue
        qualified.setdefault(provider, []).append(prefix)
        evidence.append({
            "provider": provider,
            "prefix": prefix,
            "samples": len(samples),
            "checks": [sample["checks"] for sample in samples],
            "status": "qualified",
        })

    for provider in qualified:
        qualified[provider] = sorted(
            set(qualified[provider]),
            key=lambda value: (
                int(ipaddress.ip_network(value).network_address),
                ipaddress.ip_network(value).prefixlen,
            ),
        )

    digest = hashlib.sha256(raw_bytes).hexdigest()
    previous = None
    if args.output.exists():
        try:
            previous = json.loads(args.output.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None

    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(previous, dict) and previous.get("source_sha256") == digest:
        checked_at = previous.get("checked_at", checked_at)

    report = {
        "schema_version": 1,
        "status": "ready",
        "source": "hyperion-cs/dpi-checkers",
        "checker": "dpi-ch",
        "checked_at": checked_at,
        "source_sha256": digest,
        "qualification": qualification,
        "candidates": policy["candidates"],
        "network_context": isp_context,
        "qualified_prefixes": {
            provider: {"ipv4": values}
            for provider, values in sorted(qualified.items())
        },
        "evidence": evidence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"DPI evidence: qualified {sum(len(v) for v in qualified.values())} "
        f"IPv4 prefixes across {len(qualified)} candidate providers."
    )


if __name__ == "__main__":
    main()
