#!/usr/bin/env python3
"""Extracted storage helpers for CDN-Cloud-MagiTrickle."""
import hashlib
import json
import pathlib
import os
import tempfile
import ipaddress

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIFF_DIR = DATA / "diff"
DIFF_DIR.mkdir(parents=True, exist_ok=True)

def nets(values, version):
    parsed = set()
    for value in values:
        try:
            net = value if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network)) else ipaddress.ip_network(str(value).strip(), strict=False)
            if net.version == version:
                parsed.add(net)
        except (TypeError, ValueError):
            continue
    return sorted(ipaddress.collapse_addresses(parsed), key=lambda n: (int(n.network_address), n.prefixlen)), 0

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


def cache_path(url):
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cache_dir = DATA / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / key


def atomic_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)



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

