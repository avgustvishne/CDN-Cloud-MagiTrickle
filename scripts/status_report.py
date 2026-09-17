#!/usr/bin/env python3
"""Generate a concise human and machine-readable repository status."""
from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import pathlib
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(name: str, default: Any) -> Any:
    path = DATA / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def count_cidrs(path: pathlib.Path) -> tuple[int, int, int]:
    v4 = v6 = 0
    if not path.exists():
        return 0, 0, 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value:
            continue
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            continue
        if network.version == 4:
            v4 += 1
        else:
            v6 += 1
    return v4 + v6, v4, v6


def read_timestamp() -> str:
    path = DATA / "last-update.txt"
    if not path.exists():
        return "unknown"
    text = path.read_text(encoding="utf-8").strip()
    return text or "unknown"


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def source_summary() -> dict[str, Any]:
    health = load_json("source-health.json", {})
    audit = load_json("source-audit.json", {})
    source_map = health.get("sources", {}) if isinstance(health, dict) else {}
    if not isinstance(source_map, dict):
        source_map = {}
    healthy = sum(1 for item in source_map.values() if isinstance(item, dict) and item.get("ok") is True)
    failed = sum(1 for item in source_map.values() if isinstance(item, dict) and item.get("ok") is False)
    audited = audit.get("providers", []) if isinstance(audit, dict) else []
    return {
        "total": len(source_map),
        "healthy": healthy,
        "failed": failed,
        "audited_providers": len(audited) if isinstance(audited, list) else 0,
        "checked_at": health.get("checked_at", "unknown") if isinstance(health, dict) else "unknown",
    }


def network_summary() -> dict[str, Any]:
    report = load_json("network-evidence.json", {})
    if not isinstance(report, dict):
        return {"queried": 0, "confirmed": 0, "statuses": {}}
    evidence = report.get("evidence", [])
    statuses: dict[str, int] = {}
    for item in evidence if isinstance(evidence, list) else []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "queried": report.get("queried", 0),
        "confirmed": sum(statuses.values()),
        "statuses": statuses,
    }


def provider_summary() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(DATA.glob("*-v4.txt")):
        if path.name in {"all-cloud-v4.txt", "asn-all-v4.txt", "asn-confirmed-v4.txt"}:
            continue
        name = path.name.removesuffix("-v4.txt")
        _, v4, _ = count_cidrs(path)
        _, _, v6 = count_cidrs(DATA / f"{name}-v6.txt")
        rows.append({"provider": name, "ipv4": v4, "ipv6": v6, "total": v4 + v6})
    return rows


def build_status(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json("manifest.json", {})
    summary = load_json("change-summary.json", {})
    rollback = load_json("rollback-report.json", {})
    source = source_summary()
    network = network_summary()
    providers = provider_summary()
    checksum_available = (DATA / "checksums.sha256").exists()
    warnings: list[str] = []

    if source["failed"]:
        warnings.append(f"{source['failed']} source(s) reported failure")
    if rollback.get("guarded"):
        warnings.append("publication was held by the rollback guard")
    if not checksum_available:
        warnings.append("checksums are unavailable")

    if rollback.get("guarded"):
        overall = "hold"
    elif warnings:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "schema_version": 1,
        "status": overall,
        "publication": args.publication,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_commit": git_sha(),
        "last_update": read_timestamp(),
        "engine": manifest.get("engine", "unknown") if isinstance(manifest, dict) else "unknown",
        "aggregate": manifest.get("aggregate", {}) if isinstance(manifest, dict) else {},
        "providers": {"count": len(providers), "items": providers},
        "sources": source,
        "network_evidence": network,
        "changes": summary.get("datasets", {}) if isinstance(summary, dict) else {},
        "rollback": {"guarded": bool(rollback.get("guarded", False)), "report_present": bool(rollback)},
        "checksums": {"available": checksum_available},
        "warnings": warnings,
        "last_failed_run": args.failed_run or None,
    }


def render_markdown(status: dict[str, Any]) -> str:
    aggregate = status.get("aggregate", {})
    sources = status["sources"]
    network = status["network_evidence"]
    rollback = status["rollback"]
    symbol = {"healthy": "🟢", "degraded": "🟡", "hold": "🛑"}.get(status["status"], "⚪")
    lines = [
        "# CDN-Cloud-MagiTrickle — Status",
        "",
        f"## {symbol} {status['status'].upper()}",
        "",
        f"**Публикация:** `{status['publication']}`  ",
        f"**Последнее обновление данных:** `{status['last_update']}`  ",
        f"**Отчёт сформирован:** `{status['generated_at']}`  ",
        f"**Исходный commit:** `{status['source_commit']}`",
        "",
        "## Данные",
        "",
        "| Показатель | Значение |",
        "|---|---:|",
        f"| Провайдеры | **{status['providers']['count']}** |",
        f"| IPv4 CIDR | **{aggregate.get('ipv4', 0):,}** |".replace(",", " "),
        f"| IPv6 CIDR | **{aggregate.get('ipv6', 0):,}** |".replace(",", " "),
        f"| Источники | **{sources['healthy']} / {sources['total']}** healthy |",
        f"| Network evidence | **{network['queried']}** queried |",
        "",
        "## Проверки",
        "",
        f"- Rollback guard: **{'HOLD' if rollback['guarded'] else 'PASS'}**",
        f"- Checksums: **{'available' if status['checksums']['available'] else 'unavailable'}**",
    ]
    warnings = status.get("warnings", [])
    if warnings:
        lines += ["", "## Предупреждения", ""]
        lines.extend(f"- {item}" for item in warnings)
    if status.get("last_failed_run"):
        lines += ["", "## Последний сбой", "", f"`{status['last_failed_run']}`"]
    lines += ["", "Машиночитаемый статус: [`data/status.json`](data/status.json)", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", default="data/status.json")
    parser.add_argument("--output-md", default="STATUS.md")
    parser.add_argument("--publication", choices=("published", "validated", "dry-run", "held"), default="validated")
    parser.add_argument("--failed-run", default="")
    args = parser.parse_args()
    status = build_status(args)
    json_path = ROOT / args.output_json
    md_path = ROOT / args.output_md
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(status), encoding="utf-8")


if __name__ == "__main__":
    main()
