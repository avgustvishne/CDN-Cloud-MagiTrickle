#!/usr/bin/env python3
"""Generate deterministic CIDR subscription profiles and profile intelligence."""
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

# Increment this when the intentional profile composition changes. A policy
# version change tells the anomaly gate that the resulting size change is
# expected and establishes a fresh baseline for subsequent updates.
PROFILE_POLICY_VERSION = 2
PROFILE_ORDER = ("minimal", "performance", "balanced", "full")
ANOMALY_LIMITS = {
    "count_min_ratio": 0.25,
    "count_max_ratio": 4.0,
    "coverage_min_ratio": 0.50,
    "coverage_max_ratio": 2.0,
}

# Main profiles have deliberately separated scopes:
# FULL       = every configured provider, maximum coverage.
# BALANCED   = core CDN + major hosting providers, without hyperscale catch-all pools.
# PERFORMANCE= core CDN + a small edge/cloud set for a compact routing list.
# MINIMAL    = core CDN only; no general cloud or VPS-only providers.
PROFILES = {
    "full": PROVIDERS,
    "balanced": [
        "cloudflare", "akamai", "fastly", "cdn77", "gcore",
        "digitalocean", "hetzner", "ovh", "vultr", "scaleway",
    ],
    "performance": [
        "cloudflare", "akamai", "fastly", "cdn77", "gcore",
        "digitalocean", "scaleway",
    ],
    "minimal": [
        "cloudflare", "akamai", "fastly", "cdn77", "gcore",
    ],
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
    networks = _valid_networks(values, version)
    return sum(net.num_addresses for net in ipaddress.collapse_addresses(networks))


def validate_coverage_preserved(source, result, version):
    """Ensure CIDR aggregation changes representation, never address-space coverage."""
    input_coverage = address_space_coverage(source, version)
    output_coverage = address_space_coverage(result, version)
    if input_coverage != output_coverage:
        raise RuntimeError(
            f"coverage changed for IPv{version}: input={input_coverage}, output={output_coverage}"
        )
    return input_coverage


def _intervals(values, version):
    return [
        (int(net.network_address), int(net.broadcast_address))
        for net in collapse(values, version)
    ]


def intersection_coverage(left, right, version):
    """Return exact address-space intersection of two prefix sets."""
    a = _intervals(left, version)
    b = _intervals(right, version)
    i = j = total = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if start <= end:
            total += end - start + 1
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def is_coverage_subset(subset, superset, version):
    """Return True when every address in subset is also in superset."""
    subset_coverage = address_space_coverage(subset, version)
    return subset_coverage == intersection_coverage(subset, superset, version)


def profile_metrics(current, previous=None, version=4):
    """Calculate compactness, coverage and incremental value for one profile."""
    normalized = collapse(current, version)
    coverage = address_space_coverage(normalized, version)
    count = len(normalized)
    metrics = {
        "prefixes": count,
        "coverage_ips": coverage,
        "coverage_per_prefix": coverage // count if count else 0,
        "average_prefixlen": (
            round(sum(net.prefixlen for net in normalized) / count, 2) if count else 0
        ),
    }
    if previous is not None:
        previous_coverage = address_space_coverage(previous, version)
        overlap = intersection_coverage(normalized, previous, version)
        metrics["new_coverage_ips"] = max(0, coverage - overlap)
        metrics["overlap_ips"] = overlap
        metrics["previous_coverage_ips"] = previous_coverage
        metrics["is_superset"] = overlap == previous_coverage
    return metrics


def _ratio_changed(previous, current):
    if previous == 0:
        return None if current == 0 else float("inf")
    return current / previous


def _load_previous_report(data_dir):
    path = pathlib.Path(data_dir) / "profile-intelligence.json"
    if not path.exists():
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return report if report.get("policy_version") == PROFILE_POLICY_VERSION else None


def build_profile_intelligence(profile_data, provider_map, data_dir=DATA):
    """Build a machine-readable profile quality report and anomaly gate."""
    previous = _load_previous_report(data_dir)
    profiles = {}
    anomalies = []

    for version in (4, 6):
        for index, name in enumerate(PROFILE_ORDER):
            current = profile_data[name][version]
            previous_name = PROFILE_ORDER[index - 1] if index else None
            previous_values = profile_data[previous_name][version] if previous_name else None
            metrics = profile_metrics(current, previous_values, version)
            metrics["providers"] = provider_map[name]
            profiles[f"{name}-v{version}"] = metrics

            if previous:
                old = previous.get("profiles", {}).get(f"{name}-v{version}", {})
                old_count = old.get("prefixes")
                old_coverage = old.get("coverage_ips")
                if isinstance(old_count, int) and isinstance(old_coverage, int):
                    count_ratio = _ratio_changed(old_count, metrics["prefixes"])
                    coverage_ratio = _ratio_changed(old_coverage, metrics["coverage_ips"])
                    if count_ratio is not None and (
                        count_ratio < ANOMALY_LIMITS["count_min_ratio"]
                        or count_ratio > ANOMALY_LIMITS["count_max_ratio"]
                    ):
                        anomalies.append({
                            "profile": name,
                            "family": version,
                            "metric": "prefixes",
                            "previous": old_count,
                            "current": metrics["prefixes"],
                            "ratio": count_ratio,
                        })
                    if coverage_ratio is not None and (
                        coverage_ratio < ANOMALY_LIMITS["coverage_min_ratio"]
                        or coverage_ratio > ANOMALY_LIMITS["coverage_max_ratio"]
                    ):
                        anomalies.append({
                            "profile": name,
                            "family": version,
                            "metric": "coverage_ips",
                            "previous": old_coverage,
                            "current": metrics["coverage_ips"],
                            "ratio": coverage_ratio,
                        })

    # The main profile ladder must never lose address space as it grows.
    for version in (4, 6):
        for previous_name, current_name in zip(PROFILE_ORDER, PROFILE_ORDER[1:]):
            previous_values = profile_data[previous_name][version]
            current_values = profile_data[current_name][version]
            if not is_coverage_subset(previous_values, current_values, version):
                raise RuntimeError(
                    f"profile ladder lost coverage: {previous_name}-v{version} is not a subset of {current_name}-v{version}"
                )

    report = {
        "schema_version": 1,
        "policy_version": PROFILE_POLICY_VERSION,
        "source_of_truth": "published normalized CIDR files",
        "anomaly_policy": {
            "count_min_ratio": ANOMALY_LIMITS["count_min_ratio"],
            "count_max_ratio": ANOMALY_LIMITS["count_max_ratio"],
            "coverage_min_ratio": ANOMALY_LIMITS["coverage_min_ratio"],
            "coverage_max_ratio": ANOMALY_LIMITS["coverage_max_ratio"],
            "baseline_comparison": "same policy_version only",
        },
        "profiles": profiles,
        "anomalies": anomalies,
    }
    if anomalies:
        raise RuntimeError(
            "profile anomaly gate blocked publication: "
            + json.dumps(anomalies, sort_keys=True)
        )
    return report


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
    """Generate all public profiles, report quality metrics and return counts."""
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = pathlib.Path(data_dir)
    counts = {}
    profile_data = {name: {} for name in PROFILE_ORDER}
    provider_map = {}

    for profile, selected in {**PROFILES, **SPECIAL}.items():
        names = PROVIDERS if profile == "full" else selected
        if profile in PROFILE_ORDER:
            provider_map[profile] = list(names)
        for version in (4, 6):
            source = (
                read("all-cloud", version, data_dir)
                if profile == "full"
                else [value for name in names for value in read(name, version, data_dir)]
            )
            result = collapse(source, version)
            if not result:
                raise RuntimeError(f"empty profile: {profile}-v{version}")
            validate_coverage_preserved(source, result, version)
            atomic(output_dir / f"{profile}-v{version}.txt", result)
            counts[f"{profile}-v{version}"] = len(result)
            if profile in PROFILE_ORDER:
                profile_data[profile][version] = result

    report = build_profile_intelligence(profile_data, provider_map, data_dir)
    atomic(
        data_dir / "profile-intelligence.json",
        [json.dumps(report, ensure_ascii=False, indent=2) + "\n"],
    )
    return counts


if __name__ == "__main__":
    for name, count in generate_profiles().items():
        print(f"{name}: {count} prefixes")
