#!/usr/bin/env python3
"""Validate the shape of config/providers.json and config/policy.json.

Deliberately dependency-free (no jsonschema package) to match the rest of
this project's stdlib-only scripts. Meant to run as the very first CI step,
so a typo'd ASN or malformed policy file fails in seconds with a clear
message instead of surfacing halfway through a 20-provider fetch run.
"""
import ipaddress
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROVIDER_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
ASN_RE = re.compile(r"^\\d+$")


def fail(errors):
    for e in errors:
        print(f"::error::{e}", file=sys.stderr)
    print(f"{len(errors)} config validation error(s).", file=sys.stderr)
    raise SystemExit(1)


def validate_providers(path):
    errors = []
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot parse JSON: {exc}"]
    if not isinstance(cfg, dict) or "providers" not in cfg:
        return [f'{path}: missing top-level "providers" object']
    providers = cfg["providers"]
    if not isinstance(providers, dict) or not providers:
        return [f'{path}: "providers" must be a non-empty object']
    for name, asns in providers.items():
        if not PROVIDER_NAME_RE.match(name):
            errors.append(f"{path}: provider name {name!r} must be lowercase letters/digits/hyphens")
        if not isinstance(asns, list):
            errors.append(f"{path}: providers.{name} must be a list of ASN strings")
            continue
        seen = set()
        for asn in asns:
            if not isinstance(asn, str) or not ASN_RE.match(asn):
                errors.append(f"{path}: providers.{name} has a non-numeric-string ASN: {asn!r}")
                continue
            if asn in seen:
                errors.append(f"{path}: providers.{name} lists ASN {asn} more than once")
            seen.add(asn)
    return errors


def validate_cidr_list(path, label, values):
    errors = []
    if not isinstance(values, list):
        return [f"{path}: {label} must be a list"]
    for v in values:
        if not isinstance(v, str):
            errors.append(f"{path}: {label} entry {v!r} is not a string")
            continue
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError as exc:
            errors.append(f"{path}: {label} entry {v!r} is not a valid CIDR: {exc}")
    return errors


def validate_policy(path):
    if not path.exists():
        return []
    errors = []
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot parse JSON: {exc}"]
    if not isinstance(cfg, dict):
        return [f"{path}: top level must be an object"]
    if "enabled" not in cfg or not isinstance(cfg["enabled"], bool):
        errors.append(f'{path}: "enabled" must be present and a boolean')
    global_policy = cfg.get("global", {})
    if not isinstance(global_policy, dict):
        errors.append(f'{path}: "global" must be an object')
    else:
        errors += validate_cidr_list(path, "global.exclude", global_policy.get("exclude", []))
        errors += validate_cidr_list(path, "global.include", global_policy.get("include", []))
    providers_policy = cfg.get("providers", {})
    if not isinstance(providers_policy, dict):
        errors.append(f'{path}: "providers" must be an object')
    else:
        for name, rules in providers_policy.items():
            if not isinstance(rules, dict):
                errors.append(f"{path}: providers.{name} must be an object")
                continue
            errors += validate_cidr_list(path, f"providers.{name}.exclude", rules.get("exclude", []))
            errors += validate_cidr_list(path, f"providers.{name}.include", rules.get("include", []))
    return errors


def main():
    errors = []
    errors += validate_providers(ROOT / "config" / "providers.json")
    errors += validate_policy(ROOT / "config" / "policy.json")
    if errors:
        fail(errors)
    print("Config validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
