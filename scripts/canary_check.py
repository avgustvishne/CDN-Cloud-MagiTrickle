#!/usr/bin/env python3
"""Advisory canary check.

Resolves a small set of well-known domains and checks whether their current
IP falls inside the CIDR set generated for the matching provider. This is
the one check in the pipeline that compares generated data against the live
outside world instead of just checking internal consistency.

Deliberately advisory, not a gate: DNS resolution in CI can be flaky, answers
vary by resolver/anycast location, and a provider can legitimately move a
domain to different infrastructure. A miss here is a prompt to look closer,
not proof the data is wrong -- so this script always exits 0 and never
blocks the pipeline; failures are logged as warnings only.
"""
import ipaddress
import pathlib
import socket

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CANARIES = [("api.telegram.org", "telegram"), ("www.cloudflare.com", "cloudflare"), ("ip-ranges.amazonaws.com", "aws")]


def resolve_ips(domain):
    try:
        infos = socket.getaddrinfo(domain, None)
    except OSError as exc:
        return None, str(exc)
    return sorted({info[4][0] for info in infos}), None


def load_networks(provider):
    networks = {4: [], 6: []}
    for version, suffix in ((4, "v4"), (6, "v6")):
        path = DATA / f"{provider}-{suffix}.txt"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                networks[version].append(ipaddress.ip_network(line, strict=False))
            except ValueError:
                continue
    return networks


def ip_in_networks(ip_str, networks):
    ip = ipaddress.ip_address(ip_str)
    return any(ip in net for net in networks[ip.version])


def main():
    warnings = []
    checked = 0
    for domain, provider in CANARIES:
        ips, error = resolve_ips(domain)
        if error:
            warnings.append(f"{domain}: DNS resolution failed ({error}) -- skipped, not a failure")
            continue
        networks = load_networks(provider)
        if not networks[4] and not networks[6]:
            warnings.append(f"{domain}: no generated data for provider {provider!r} to check against")
            continue
        checked += 1
        matched = [ip for ip in ips if ip_in_networks(ip, networks)]
        if not matched:
            warnings.append(f"{domain} resolved to {ips}, none of which are covered by data/{provider}-v4.txt / -v6.txt -- worth a manual look")
        else:
            print(f"OK: {domain} ({matched[0]}) is covered by provider {provider!r}")
    if warnings:
        print(f"\\n{len(warnings)} canary warning(s) (advisory only, not failing the build):")
        for w in warnings:
            print(f"::warning::{w}")
    print(f"\\nCanary check: {checked}/{len(CANARIES)} domains verified against generated data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
