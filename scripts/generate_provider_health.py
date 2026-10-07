#!/usr/bin/env python3
"""Build provider-level subscription freshness and health intelligence."""
import csv
import hashlib
import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "providers.json"
AUDIT = DATA / "audit.csv"
OUTPUT = DATA / "provider-health.json"
README = ROOT / "README.md"

DISPLAY_NAMES = {
    "aws": "AWS", "akamai": "Akamai", "alibaba": "Alibaba Cloud",
    "backblaze": "Backblaze", "buyvm": "BuyVM", "cdn77": "CDN77",
    "cloudflare": "Cloudflare", "contabo": "Contabo", "digitalocean": "DigitalOcean",
    "fastly": "Fastly", "gcore": "Gcore", "hetzner": "Hetzner",
    "melbicom": "Melbicom", "microsoft": "Microsoft Azure", "oracle": "Oracle Cloud",
    "ovh": "OVH", "scaleway": "Scaleway", "telegram": "Telegram",
    "twitter": "Twitter/X", "vultr": "Vultr",
}

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_audit():
    if not AUDIT.exists():
        return {}
    with AUDIT.open(encoding="utf-8", newline="") as handle:
        return {row["Provider"]: row for row in csv.DictReader(handle)}

def load_diff(name):
    path = DATA / "diff" / f"{name}.json"
    if not path.exists():
        return {"added": {"ipv4": 0, "ipv6": 0}, "removed": {"ipv4": 0, "ipv6": 0}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"added": {"ipv4": 0, "ipv6": 0}, "removed": {"ipv4": 0, "ipv6": 0}}

def classify(status, exists):
    if not exists:
        return "missing"
    if status.startswith("KEEP_OLD"):
        return "protected"
    if status in {"PARTIAL", "FILTERED"}:
        return "warning"
    if status in {"EMPTY", "ANOMALY"}:
        return "problem"
    if status == "OK":
        return "healthy"
    return "unknown"

def freshness(diff, status, exists):
    if not exists:
        return "missing"
    if status.startswith("KEEP_OLD"):
        return "protected"
    changed = sum(
        int(diff.get(kind, {}).get(f"ipv{family}", 0))
        for kind in ("added", "removed")
        for family in (4, 6)
    )
    return "updated" if changed else "unchanged"

def status_label(status, health, fresh):
    if health == "missing":
        return "❌ нет данных"
    if health == "protected":
        return "🛡️ старая версия"
    if health == "problem":
        return f"🔴 {status}"
    if health == "warning":
        return f"🟡 {status}"
    if fresh == "unchanged":
        return "🟢 OK · без изменений"
    return "🟢 OK · обновлено"

def build():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    audit = load_audit()
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    providers = []

    for name in sorted(config.get("providers", {})):
        row = audit.get(name, {})
        status = row.get("Status", "UNKNOWN")
        paths = {family: DATA / f"{name}-v{family}.txt" for family in (4, 6)}
        exists = all(path.is_file() for path in paths.values())
        diff = load_diff(name)
        files = {}
        for family, path in paths.items():
            files[f"ipv{family}"] = {
                "path": path.relative_to(ROOT).as_posix(),
                "exists": path.is_file(),
                "sha256": sha256(path) if path.is_file() else None,
                "cidr_count": len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0,
            }

        health = classify(status, exists)
        fresh = freshness(diff, status, exists)
        providers.append({
            "provider": name,
            "display_name": DISPLAY_NAMES.get(name, name),
            "status": status,
            "health": health,
            "freshness": fresh,
            "ipv4": int(row.get("IPv4", files["ipv4"]["cidr_count"] or 0)),
            "ipv6": int(row.get("IPv6", files["ipv6"]["cidr_count"] or 0)),
            "previous_ipv4": int(row.get("PreviousIPv4", 0) or 0),
            "previous_ipv6": int(row.get("PreviousIPv6", 0) or 0),
            "change": {
                "added_ipv4": int(diff.get("added", {}).get("ipv4", 0)),
                "removed_ipv4": int(diff.get("removed", {}).get("ipv4", 0)),
                "added_ipv6": int(diff.get("added", {}).get("ipv6", 0)),
                "removed_ipv6": int(diff.get("removed", {}).get("ipv6", 0)),
            },
            "errors": int(row.get("Errors", 0) or 0),
            "source": row.get("Source", ""),
            "files": files,
        })

    return {
        "schema_version": 1,
        "checked_at": checked_at,
        "source_of_truth": "published provider CIDR files + audit.csv + provider diff reports",
        "providers": providers,
        "summary": {
            "total": len(providers),
            "healthy": sum(p["health"] == "healthy" for p in providers),
            "warning": sum(p["health"] == "warning" for p in providers),
            "protected": sum(p["health"] == "protected" for p in providers),
            "problem": sum(p["health"] == "problem" for p in providers),
            "missing": sum(p["health"] == "missing" for p in providers),
            "updated": sum(p["freshness"] == "updated" for p in providers),
            "unchanged": sum(p["freshness"] == "unchanged" for p in providers),
        },
    }

def update_readme(report):
    text = README.read_text(encoding="utf-8")
    lines = text.splitlines()
    start_marker = "<!-- PROVIDER-HEALTH:START -->"
    end_marker = "<!-- PROVIDER-HEALTH:END -->"
    start = next((i for i, line in enumerate(lines) if line == start_marker), None)
    end = next((i for i, line in enumerate(lines) if line == end_marker), None)

    rows = [start_marker, "", "| Провайдер | IPv4 | IPv6 | Состояние |", "|---|:---:|:---:|---|"]
    for provider in report["providers"]:
        name = provider["display_name"]
        n = provider["provider"]
        rows.append(
            f"| {name} | [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/{n}-v4.txt) "
            f"| [скачать](https://raw.githubusercontent.com/avgustvishne/CDN-Cloud-MagiTrickle/main/data/{n}-v6.txt) "
            f"| {status_label(provider['status'], provider['health'], provider['freshness'])} |"
        )
    rows.extend([
        "",
        "> 🟢 OK = опубликовано нормально · 🟡 PARTIAL/FILTERED = опубликовано с предупреждением · "
        "🛡️ старая версия = сработала защита от плохого обновления.",
        "",
        f"> Последняя проверка: {report['checked_at']} · [машиночитаемый отчёт](data/provider-health.json)",
        end_marker,
    ])

    if start is not None and end is not None and start < end:
        new_lines = lines[:start] + rows + lines[end + 1:]
    else:
        heading = "## Отдельные провайдеры"
        h = lines.index(heading)
        table_start = next(i for i in range(h + 1, len(lines)) if lines[i].startswith("| Провайдер |"))
        table_end = table_start + 1
        while table_end < len(lines) and lines[table_end].startswith("|"):
            table_end += 1
        new_lines = lines[:table_start] + rows + lines[table_end:]

    new_text = "\n".join(new_lines) + "\n"
    if new_text != text:
        README.write_text(new_text, encoding="utf-8")
        return True
    return False

def main():
    report = build()
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    changed = update_readme(report)
    print(f"Provider health: {report['summary']}")
    print(f"README refreshed: {changed}")

if __name__ == "__main__":
    main()
