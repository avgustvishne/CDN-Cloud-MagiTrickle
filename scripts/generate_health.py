#!/usr/bin/env python3
"""Render data/source-health.json into a short, human-readable HEALTH.md."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source-health.json"
OUT = ROOT / "HEALTH.md"


def fmt_bytes(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def main():
    if not SOURCE.exists():
        print(f"{SOURCE} does not exist yet; skipping HEALTH.md generation.")
        return 0
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    sources = payload.get("sources", {})
    checked_at = payload.get("checked_at", "unknown")
    ok_count = sum(1 for s in sources.values() if s.get("ok"))
    total = len(sources)
    lines = [
        "# Здоровье источников данных", "",
        f"**{ok_count}/{total} источников отвечают.** Проверено: `{checked_at}`.", "",
        "| Источник | Статус | Размер ответа |", "|---|:---:|---:|",
    ]
    for name in sorted(sources):
        info = sources[name]
        status = "✅" if info.get("ok") else "❌"
        size = fmt_bytes(info["bytes"]) if info.get("ok") and "bytes" in info else "—"
        lines.append(f"| {name} | {status} | {size} |")
    if not sources:
        lines.append("| _нет данных_ | | |")
    lines += ["", "Обновляется автоматически при каждом прогоне [update.yml](.github/workflows/update.yml). Полные данные — в [data/source-health.json](data/source-health.json)."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({ok_count}/{total} sources OK)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
