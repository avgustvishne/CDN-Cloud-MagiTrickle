#!/usr/bin/env python3
"""Generate deterministic CIDR subscription profiles."""
import ipaddress
import json
import os
import pathlib
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_PRESETS = DATA / "presets"

CFG = json.loads((ROOT / "config" / "providers.json").read_text(encoding="utf-8"))
PROVIDERS = sorted(CFG["providers"])

PROFILES = {
    "full": PROVIDERS,
    "performance": ["cloudflare", "fastly", "cdn77", "gcore"],
    "balanced": ["cloudflare", "aws", "akamai", "fastly", "cdn77", "gcore", "digitalocean", "microsoft", "hetzner", "ovh", "vultr", "scaleway"],
    "minimal": ["cloudflare", "akamai", "fastly", "vultr", "hetzner", "ovh"],
}

SPECIAL = {
    "cdn": ["cloudflare", "akamai", "fastly", "cdn77", "gcore"],
    "cloud": ["aws", "cloudflare", "microsoft", "oracle", "alibaba", "digitalocean"],
    "video": ["cloudflare", "fastly", "akamai", "aws", "microsoft"],
    "vpn": ["vultr", "buyvm", "ovh", "hetzner", "digitalocean", "gcore", "contabo", "scaleway", "melbicom"],
}

def read(name, version, data_dir=DATA):
    path = pathlib.Path(data_dir) / f"{name}-v{version}.txt"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()

def collapse(values, version):
    networks = set()
    for value in values:
        try:
            net = ipaddress.ip_network(value.strip(), strict=False)
            if net.version == version and net.is_global and net.prefixlen >= (8 if version == 4 else 16):
                networks.add(net)
        except ValueError:
            continue
    return sorted(
        ipaddress.collapse_addresses(networks),
        key=lambda n: (int(n.network_address), n.prefixlen),
    )

def atomic(path, values):
    path = pathlib.Path(path)
    text = "\n".join(map(str, values)) + ("\n" if values else "")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def generate_profiles(provider_files=None, output_dir=DEFAULT_PRESETS, data_dir=DATA):
    """Generate all public profiles and return their prefix counts."""
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for profile, selected in {**PROFILES, **SPECIAL}.items():
        for version in (4, 6):
            source = []
            names = PROVIDERS if profile == "full" else selected
            if profile == "full":
                source = read("all-cloud", version, data_dir)
            else:
                for name in names:
                    source.extend(read(name, version, data_dir))
            result = collapse(source, version)
            if not result:
                raise RuntimeError(f"empty profile: {profile}-v{version}")
            atomic(output_dir / f"{profile}-v{version}.txt", result)
            counts[f"{profile}-v{version}"] = len(result)
    return counts

if __name__ == "__main__":
    for name, count in generate_profiles().items():
        print(f"{name}: {count} prefixes")
