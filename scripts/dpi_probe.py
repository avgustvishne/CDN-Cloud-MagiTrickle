#!/usr/bin/env python3
"""
Optional DPI health probe for CDN-Cloud-MagiTrickle.

Important: DPI is path/ISP dependent. This module deliberately does NOT
label a CIDR "DPI-clean" from a GitHub-hosted runner. It validates the
current probe network against a curated domain set using Runnin4ik/dpi-detector
when the detector is installed locally. Its result is an input to source
health, not provider attribution.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_DOMAINS = [
    "cloudflare.com",
    "github.com",
    "youtube.com",
    "discord.com",
    "vk.com",
]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--detector", default="dpi_detector", help="dpi-detector executable")
    p.add_argument("--domains", nargs="*", default=DEFAULT_DOMAINS)
    p.add_argument("--tests", default="123")
    p.add_argument("--concurrency", default="20")
    p.add_argument("--output", default=str(DATA / "dpi-health.json"))
    p.add_argument("--allow-fail", action="store_true")
    a = p.parse_args()

    exe = shutil.which(a.detector)
    result = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "engine": "Runnin4ik/dpi-detector",
        "network_dependent": True,
        "provider_cidr_filtering": False,
        "domains": a.domains,
        "status": "NOT_RUN",
    }

    if not exe:
        result["status"] = "UNAVAILABLE"
        result["reason"] = "dpi-detector is not installed on this probe host"
        pathlib.Path(a.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if not a.allow_fail:
            return 2
        return 0

    cmd = [exe, "-t", a.tests, "-c", a.concurrency, "--batch"]
    for domain in a.domains:
        cmd += ["-d", domain]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=900)
    result["returncode"] = proc.returncode
    result["stdout_tail"] = proc.stdout[-12000:]
    result["stderr_tail"] = proc.stderr[-4000:]
    result["status"] = "OK" if proc.returncode == 0 else "DETECTED_OR_ERROR"
    pathlib.Path(a.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if proc.returncode == 0 or a.allow_fail else proc.returncode

if __name__ == "__main__":
    raise SystemExit(main())
