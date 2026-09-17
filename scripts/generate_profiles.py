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

# Main profiles are deliberately different in scope:
# FULL      = every configured provider, maximum coverage.
# BALANCED  = broad cloud/CDN/VPS coverage without the largest catch-all pools.
# PERFORMANCE = focused edge/CDN/VPS sources for a smaller routing set.
# MINIMAL   = compact, high-value edge/VPS set.
PROFILES = {
    "full": PROVIDERS,
    "performance": [
        "cloudflare", "akamai", "fastly", "cdn77", "gcore",
        "digitalocean", "hetzner", "ovh",
    ],
    "balanced": [
        "cloudflare", "aws", "akamai", "fastly", "cdn77", "gcore",
        "digitalocean", "microsoft", "hetzner", "ovh", "vultr", "scaleway",
    ],
    "minimal": ["cloudflare", "akamai", "fastly", "vultr", "hetzner", "ovh"],
}

SPECIAL = {
    "cdn": ["cloudflare", "akamai", "fastly", "cdn77", "gcore"],
    "cloud": ["aws", "cloudflare", "microsoft", "oracle", "alibaba", "digitalocean"],
    "video": ["cloudflare", "fastly", "akamai", "aws", "microsoft"],
    "vpn": ["vultr", "buyvm", "ovh", "hetzner", "digitalocean", "gcore", "contabo", "scaleway", "melbicom"],
}


def _validate_profile_config():
    """Fail early if a profile references an unknown provider."""
    known = set(PROVIDERS)
    for profile, selected in {**PROFILES, **SPECIAL}.items():
        unknown = sorted(set(selected) - known)
        if unknown:
            raise ValueError(f"profile {profile!r} references unknown providers: {unknown}")


_validate_profile_config()


def read(name, version, data_dir=DATA):
    path = pathlib.Path(data_dir) / f"{name}-v{version}.txt"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _valid_networks(values, version):
    """Normalize source prefixes using the same safety rules as generation."""
    networks = set()
    minimum_prefix = 8 if version == 4 else 16
    for value in values:
        try:
            net = value if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network)) else ipaddress.ip_network(value.strip(), strict=False)
            if net.version == version and net.is_global and net.prefixlen >= minimum_prefix:
                networks.add(net)
        except (AttributeError, TypeError, ValueError):
            continue
    return networks


def collapse(values, version):
    return sorted(
        ipaddress.collapse_addresses(_valid_networks(values, version)),
        key=lambda n: (int(n.network_address), n.prefixlen),
    )


def address_space_coverage(values, version):
    """Return exact union coverage in addresses after input normalization."""
    return sum(net.num_addresses for net in _valid_networks(values, version))


def validate_coverage_preserved(source, result, version):
    """Ensure CIDR aggregation changes representation, never address-space coverage."""
    input_coverage = address_space_coverage(source, version)
    output_coverage = address_space_coverage(result, version)
    if input_coverage != output_coverage:
        raise RuntimeError(
            f"coverage changed for IPv{version}: input={input_coverage}, output={output_coverage}"
        )
    return input_coverage


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
        names = PROVIDERS if profile == "full" else selected
        for version in (4, 6):
            source = read("all-cloud", version, data_dir) if profile == "full" else [value for name in names for value in read(name, version, data_dir)]
            result = collapse(source, version)
            if not result:
                raise RuntimeError(f"empty profile: {profile}-v{version}")
            validate_coverage_preserved(source, result, version)
            atomic(output_dir / f"{profile}-v{version}.txt", result)
            counts[f"{profile}-v{version}"] = len(result)
    return counts


if __name__ == "__main__":
    for name, count in generate_profiles().items():
        print(f"{name}: {count} prefixes")
