#!/usr/bin/env python3
"""Build deterministic service-domain and DNS evidence artifacts.

Service identity is kept separate from provider/CDN CIDR subscriptions. Official
service documentation is the registry authority; DNS-resolved IPs are evidence
only because addresses can be shared, delegated, or change without notice.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
from collections import defaultdict
from pathlib import Path
from typing import Callable


Resolver = Callable[[str, int], list[str]]


def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported services.json schema_version")
    services = data.get("services")
    if not isinstance(services, dict) or not services:
        raise ValueError("services registry is empty")
    for name, service in services.items():
        if not isinstance(name, str) or not name:
            raise ValueError("service name must be non-empty")
        domains = service.get("domains")
        if not isinstance(domains, list) or not domains:
            raise ValueError(f"{name}: domains must be a non-empty list")
        if len(domains) != len(set(domains)):
            raise ValueError(f"{name}: duplicate domain")
        for domain in domains:
            if not isinstance(domain, str) or not domain or domain != domain.lower():
                raise ValueError(f"{name}: invalid domain {domain!r}")
        ports = service.get("ports")
        if not isinstance(ports, list) or any(not isinstance(p, int) or not 1 <= p <= 65535 for p in ports):
            raise ValueError(f"{name}: invalid ports")
    return data


def dns_resolver(domain: str, family: int) -> list[str]:
    family_value = socket.AF_INET if family == 4 else socket.AF_INET6
    values = set()
    for result in socket.getaddrinfo(domain, None, family_value, socket.SOCK_STREAM):
        address = result[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip.version == family:
            values.add(str(ip))
    return sorted(values, key=lambda value: int(ipaddress.ip_address(value)))


def normalize_ip(value: str) -> str:
    return str(ipaddress.ip_address(value))


def build_report(registry: dict, resolver: Resolver = dns_resolver) -> dict:
    services = registry["services"]
    resolved_by_service: dict[str, dict[str, list[str]]] = {}
    ip_services: defaultdict[str, set[str]] = defaultdict(set)

    for name in sorted(services):
        item = services[name]
        domains: dict[str, dict[str, list[str]]] = {}
        for domain in sorted(item["domains"]):
            families = {"ipv4": [], "ipv6": [], "errors": []}
            for version in (4, 6):
                try:
                    addresses = sorted({normalize_ip(v) for v in resolver(domain, version)})
                except (OSError, socket.gaierror) as exc:
                    addresses = []
                    families["errors"].append(f"ipv{version}: {exc.__class__.__name__}")
                key = "ipv4" if version == 4 else "ipv6"
                families[key] = addresses
                for address in addresses:
                    ip_services[address].add(name)
            domains[domain] = families
        resolved_by_service[name] = domains

    reports = {}
    for name in sorted(services):
        item = services[name]
        domains = resolved_by_service[name]
        ipv4 = sorted({ip for values in domains.values() for ip in values["ipv4"]})
        ipv6 = sorted({ip for values in domains.values() for ip in values["ipv6"]})
        resolved_domains = sum(bool(v["ipv4"] or v["ipv6"]) for v in domains.values())
        resolution_ratio = resolved_domains / len(domains) if domains else 0.0
        confidence = round(70 + 30 * resolution_ratio, 2)
        shared = sorted(ip for ip in ipv4 + ipv6 if len(ip_services[ip]) > 1)
        reports[name] = {
            "category": item["category"],
            "domains": sorted(domains),
            "ports": sorted(item["ports"]),
            "official_sources": item["official_sources"],
            "resolution": {
                "domains": domains,
                "ipv4": ipv4,
                "ipv6": ipv6,
                "resolved_domain_ratio": round(resolution_ratio, 4)
            },
            "shared_infrastructure": {
                "detected": bool(shared),
                "ips": shared,
                "policy": "evidence-only; do not publish shared IPs as exclusive service routes"
            },
            "confidence": confidence,
            "routing": {
                "domain_ready": True,
                "ip_ready": False,
                "reason": "DNS addresses are volatile and may be shared across services"
            }
        }

    return {
        "schema_version": 1,
        "engine": "service-intelligence-v1",
        "policy": registry["policy"],
        "services": reports,
        "shared_ips": {
            ip: sorted(names) for ip, names in sorted(ip_services.items()) if len(names) > 1
        }
    }


def write_outputs(report: dict, output: Path) -> None:
    service_dir = output / "services"
    service_dir.mkdir(parents=True, exist_ok=True)
    for name, item in report["services"].items():
        (service_dir / f"{name}-domains.txt").write_text(
            "\n".join(item["domains"]) + "\n", encoding="utf-8"
        )
    (output / "service-intelligence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/services.json")
    parser.add_argument("--output", default="data")
    args = parser.parse_args()
    registry = load_registry(Path(args.config))
    report = build_report(registry)
    write_outputs(report, Path(args.output))
    print(f"Service intelligence: {len(report['services'])} services")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
