#!/usr/bin/env python3
import ipaddress
import pathlib
import tempfile
import os

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PRESETS = DATA / "presets"
PRESETS.mkdir(parents=True, exist_ok=True)

PROFILES = {
    "full": None,
    "balanced": ["cloudflare", "aws", "akamai", "fastly", "cdn77", "gcore", "digitalocean", "microsoft", "hetzner", "ovh", "vultr", "scaleway"],
    "minimal": ["cloudflare", "akamai", "fastly", "vultr", "hetzner", "ovh"],
}

def read(name, version):
    path = DATA / f"{name}-v{version}.txt"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()

def collapse(values, version):
    nets = set()
    for value in values:
        try:
            net = ipaddress.ip_network(value.strip(), strict=False)
            if net.version == version and net.is_global:
                nets.add(net)
        except ValueError:
            pass
    return sorted(ipaddress.collapse_addresses(nets), key=lambda n: (int(n.network_address), n.prefixlen))

def atomic(path, values):
    text = "\n".join(map(str, values)) + ("\n" if values else "")
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

providers = sorted(p.name[:-7] for p in DATA.glob("*-v4.txt") if p.name != "all-cloud-v4.txt")

for profile, selected in PROFILES.items():
    names = providers if selected is None else selected
    for version in (4, 6):
        if profile == "full":
            source = read("all-cloud", version)
        else:
            source = []
            for name in names:
                source.extend(read(name, version))
        result = collapse(source, version)
        if not result:
            raise SystemExit(f"empty profile: {profile}-v{version}")
        atomic(PRESETS / f"{profile}-v{version}.txt", result)
        print(f"{profile}-v{version}: {len(result)} prefixes")

# Keep specialized profiles generated here too, so every profile has one owner.
SPECIAL = {
    "cdn": ["cloudflare", "akamai", "fastly", "cdn77", "gcore"],
    "cloud": ["aws", "cloudflare", "microsoft", "oracle", "alibaba", "digitalocean"],
    "video": ["cloudflare", "fastly", "akamai", "aws", "microsoft"],
    "vpn": ["vultr", "buyvm", "ovh", "hetzner", "digitalocean", "gcore", "contabo", "scaleway", "melbicom"],
}
for profile, names in SPECIAL.items():
    for version in (4, 6):
        source = []
        for name in names:
            source.extend(read(name, version))
        result = collapse(source, version)
        if result:
            atomic(PRESETS / f"{profile}-v{version}.txt", result)
            print(f"{profile}-v{version}: {len(result)} prefixes")
