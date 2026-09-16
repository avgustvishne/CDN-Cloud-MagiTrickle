#!/usr/bin/env python3
"""Generate machine-readable CIDR statistics and refresh README counts."""
import datetime
import ipaddress
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
README = ROOT / "README.md"
STATS = DATA / "statistics.json"

def read_cidrs(path):
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        try:
            values.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return values

def file_stats(path):
    networks = read_cidrs(path)
    v4 = [n for n in networks if n.version == 4]
    v6 = [n for n in networks if n.version == 6]
    return {
        "cidr_count": len(networks),
        "ipv4_count": len(v4),
        "ipv6_count": len(v6),
        "ipv4_coverage": sum(n.num_addresses for n in v4),
        "ipv6_coverage": sum(n.num_addresses for n in v6),
    }

def human_count(value):
    return "{:,}".format(value).replace(",", " ")

def collect():
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    files = {}
    for path in sorted(DATA.glob("*.txt")):
        if path.name == "last-update.txt":
            continue
        files[path.relative_to(ROOT).as_posix()] = file_stats(path)
    for path in sorted((DATA / "presets").glob("*.txt")):
        files[path.relative_to(ROOT).as_posix()] = file_stats(path)
    providers = {}
    config = json.loads((ROOT / "config" / "providers.json").read_text(encoding="utf-8"))
    for name in config.get("providers", {}):
        key = name.lower()
        providers[key] = {}
        for af in ("v4", "v6"):
            rel = "data/{}-{}.txt".format(key, af)
            if rel in files:
                providers[key]["ipv{}".format(4 if af == "v4" else 6)] = files[rel]["cidr_count"]
    profiles = {}
    for path, info in files.items():
        if path.startswith("data/presets/"):
            profiles[path.rsplit("/", 1)[-1][:-4]] = info
    return {
        "schema_version": 1,
        "engine": 44,
        "generated_at": generated_at,
        "source_of_truth": "published normalized CIDR files",
        "files": files,
        "profiles": profiles,
        "providers": providers,
        "datasets": {
            "all_cloud": {
                "ipv4": files.get("data/all-cloud-v4.txt", {}).get("cidr_count", 0),
                "ipv6": files.get("data/all-cloud-v6.txt", {}).get("cidr_count", 0),
            },
            "asn_all": {
                "ipv4": files.get("data/asn-all-v4.txt", {}).get("cidr_count", 0),
                "ipv6": files.get("data/asn-all-v6.txt", {}).get("cidr_count", 0),
            },
        },
    }

def update_readme(stats):
    text = README.read_text(encoding="utf-8")
    changed = 0
    counts = {pathlib.PurePosixPath(path).name: info["cidr_count"] for path, info in stats["files"].items()}
    pattern = re.compile(
        r"(\*\*)[0-9][0-9 ]*(?: CIDR)(\*\*\s*·\s*\[(?:IPv4|IPv6)\]\()"
        r"(https://raw\.githubusercontent\.com/avgustvishne/CDN-Cloud-MagiTrickle/main/(?:data/)?(?:presets/)?([^/)]+\.txt))"
    )
    def repl(match):
        nonlocal changed
        filename = match.group(4)
        if filename not in counts:
            return match.group(0)
        changed += 1
        return "{}{} CIDR{}{}".format(match.group(1), human_count(counts[filename]), match.group(2), match.group(3))
    text = pattern.sub(repl, text)
    marker = "## 🔄 Обновление\n"
    if marker in text:
        generated_at = stats["generated_at"]
        line = "Данные и количество CIDR обновляются автоматически после успешной генерации и проверок. Последняя генерация: `{}`. [Машиночитаемая статистика](data/statistics.json).\n\n".format(generated_at)
        start = text.index(marker) + len(marker)
        end = text.find("\\n\\n", start)
        if end == -1:
            end = start
        current = text[start:end]
        if current != line.rstrip("\\n"):
            text = text[:start] + line + text[end + 2:]
            changed += 1
    if changed:
        README.write_text(text, encoding="utf-8")
    return changed

def main():
    stats = collect()
    DATA.mkdir(exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Statistics generated: {}".format(STATS))
    print("README dynamic count updates: {}".format(update_readme(stats)))

if __name__ == "__main__":
    main()