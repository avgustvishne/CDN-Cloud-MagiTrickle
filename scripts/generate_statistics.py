#!/usr/bin/env python3
"""Generate machine-readable CIDR statistics and refresh the README."""
import datetime
import ipaddress
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
README = ROOT / "README.md"
STATS = DATA / "statistics.json"

PROFILE_ORDER = (
    "full", "balanced", "performance", "minimal", "stable",
    "cdn", "cloud", "video", "vpn", "messaging",
)


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


RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def human_datetime(iso_string):
    """Render an ISO-8601 UTC timestamp (with trailing 'Z') for a human
    reader, e.g. '22 сентября 2026, 06:14 UTC'. The raw ISO string stays
    in data/statistics.json for anything that parses it programmatically;
    this is display-only, for the README."""
    dt = datetime.datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%SZ")
    return f"{dt.day} {RU_MONTHS[dt.month]} {dt.year}, {dt.strftime('%H:%M')} UTC"


def collect():
    generated_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    files = {}

    for path in sorted(DATA.glob("*.txt")):
        if path.name == "last-update.txt":
            continue
        files[path.relative_to(ROOT).as_posix()] = file_stats(path)

    presets = DATA / "presets"
    if presets.exists():
        for path in sorted(presets.glob("*.txt")):
            files[path.relative_to(ROOT).as_posix()] = file_stats(path)

    config = json.loads((ROOT / "config" / "providers.json").read_text(encoding="utf-8"))
    providers = {}
    for name in config.get("providers", {}):
        key = name.lower()
        providers[key] = {}
        for family in (4, 6):
            rel = "data/{}-v{}.txt".format(key, family)
            if rel in files:
                providers[key]["ipv{}".format(family)] = files[rel]["cidr_count"]

    profiles = {}
    for path, info in files.items():
        if path.startswith("data/presets/") and path.endswith(".txt"):
            profiles[path.rsplit("/", 1)[-1][:-4]] = info

    return {
        "schema_version": 1,
        "engine": 45,
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
    lines = text.splitlines()

    published_files = stats.get("files", {})
    messaging_ready = (
        "data/presets/messaging-v4.txt" in published_files
        and "data/presets/messaging-v6.txt" in published_files
    )
    messaging_row = (
        "| Telegram + Twitter/X | **MESSAGING** | "
        "[↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/messaging-v4.txt) | "
        "[↓](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/presets/messaging-v6.txt) |"
    )
    note_prefix = "> **MESSAGING (Telegram + Twitter/X)** временно убран из этой таблицы:"

    lines = [
        line for line in lines
        if not line.startswith("| Telegram + Twitter/X | **MESSAGING** |")
        and not line.startswith(note_prefix)
    ]

    if messaging_ready:
        for index, line in enumerate(lines):
            if line.startswith("| Тот же набор, что FULL, но обновляется раз в неделю | **STABLE**"):
                lines.insert(index, messaging_row)
                break
    else:
        for index, line in enumerate(lines):
            if line.startswith("**FULL** включает"):
                lines.insert(
                    index + 1,
                    note_prefix
                    + " провайдерские файлы для Telegram/Twitter ещё ни разу не были успешно опубликованы "
                    + "(data/telegram-v4.txt/twitter-v4.txt отсутствуют), и держать в README ссылку "
                    + "на несуществующий файл ломает check_links.py на каждом прогоне. Вернём строку в таблицу, "
                    + "как только пайплайн один раз успешно сгенерирует реальные данные для обоих провайдеров."
                )
                break

    text = "\n".join(lines) + "\n"

    rows = []
    for profile in PROFILE_ORDER:
        v4 = stats["profiles"].get("{}-v4".format(profile))
        v6 = stats["profiles"].get("{}-v6".format(profile))
        if not v4 and not v6:
            continue
        rows.append(
            "| **{}** | **{} CIDR** | **{} CIDR** |".format(
                profile.upper(),
                human_count(v4["cidr_count"] if v4 else 0),
                human_count(v6["cidr_count"] if v6 else 0),
            )
        )

    datasets = stats["datasets"]
    rows.extend(
        [
            "| **ASN ALL** | **{} CIDR** | **{} CIDR** |".format(
                human_count(datasets["asn_all"]["ipv4"]),
                human_count(datasets["asn_all"]["ipv6"]),
            ),
            "| **ALL-CLOUD** | **{} CIDR** | **{} CIDR** |".format(
                human_count(datasets["all_cloud"]["ipv4"]),
                human_count(datasets["all_cloud"]["ipv6"]),
            ),
        ]
    )

    block = "\n".join(
        [
            "<!-- AUTO-STATS:START -->",
            "## 📊 Актуальная статистика",
            "",
            "| Набор | IPv4 | IPv6 |",
            "|---|---:|---:|",
            *rows,
            "",
            "**Обновлено:** {} · [полная статистика](data/statistics.json)".format(
                human_datetime(stats["generated_at"])
            ),
            "",
            "> Статистика рассчитывается из опубликованных нормализованных CIDR-файлов после успешного прохождения проверок.",
            "<!-- AUTO-STATS:END -->",
        ]
    )

    start = "<!-- AUTO-STATS:START -->"
    end = "<!-- AUTO-STATS:END -->"
    if start in text and end in text:
        prefix, remainder = text.split(start, 1)
        _, suffix = remainder.split(end, 1)
        new_text = prefix + block + suffix
    else:
        marker = "## 🔄 Обновление\n"
        if marker in text:
            new_text = text.replace(marker, block + "\n\n" + marker, 1)
        else:
            new_text = text.rstrip() + "\n\n" + block + "\n"

    if new_text != text:
        README.write_text(new_text, encoding="utf-8")
        return 1
    return 0


def main():
    stats = collect()
    DATA.mkdir(exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Statistics generated: {}".format(STATS))
    print("README statistics refreshed: {}".format(update_readme(stats)))


if __name__ == "__main__":
    main()
