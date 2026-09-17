#!/usr/bin/env python3
"""Independent live-BGP validation using CAIDA BGPStream."""
import argparse
import datetime as dt
import json
import pathlib
import re

import pybgpstream

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_asns(limit):
    cfg = json.loads((ROOT / "config/providers.json").read_text(encoding="utf-8"))
    out = []
    seen = set()
    for provider, asns in cfg.get("providers", {}).items():
        for asn in asns:
            asn = str(asn)
            if asn not in seen:
                out.append((provider, asn))
                seen.add(asn)
            if len(out) >= limit:
                return out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=0.5, help="Recent BGP update window in hours")
    ap.add_argument("--limit", type=int, default=12, help="Number of distinct ASNs to validate")
    args = ap.parse_args()
    if args.hours <= 0 or args.hours > 2:
        ap.error("--hours must be > 0 and <= 2")
    if args.limit <= 0 or args.limit > 64:
        ap.error("--limit must be between 1 and 64")

    pairs = load_asns(args.limit)
    if not pairs:
        raise SystemExit("No configured ASNs available for BGPStream validation")

    asn_re = "|".join(re.escape(a) for _, a in pairs)
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=args.hours)

    # Updates are much more bounded than RIB dumps for unattended validation.
    # The AS-path filter is applied by BGPStream, so the report still checks the
    # configured provider ASNs without downloading full routing tables.
    stream = pybgpstream.BGPStream(
        from_time=start.strftime("%Y-%m-%d %H:%M:%S"),
        until_time=end.strftime("%Y-%m-%d %H:%M:%S"),
        projects=["routeviews", "ris"],
        record_type="updates",
        filter=f"aspath _({asn_re})$",
    )

    found = {a: set() for _, a in pairs}
    peers = {a: set() for _, a in pairs}
    elements = 0
    for elem in stream:
        fields = elem.fields
        prefix = fields.get("prefix")
        path = fields.get("as-path", "")
        if not prefix or not path:
            continue
        origin = path.split()[-1]
        if origin not in found:
            continue
        elements += 1
        found[origin].add(prefix)
        peer = getattr(elem, "peer_asn", None)
        if peer is not None:
            peers[origin].add(str(peer))

    rows = [
        {
            "provider": provider,
            "asn": asn,
            "prefixes": len(found[asn]),
            "peers": len(peers[asn]),
            "observed": bool(found[asn]),
        }
        for provider, asn in pairs
    ]
    out = {
        "engine": "v44",
        "source": "CAIDA BGPStream",
        "projects": ["routeviews", "ris"],
        "record_type": "updates",
        "window_hours": args.hours,
        "generated_at": end.isoformat(),
        "sample_size": len(rows),
        "elements_observed": elements,
        "results": rows,
        "healthy_asns": sum(r["observed"] for r in rows),
    }
    path = ROOT / "data/bgpstream-health.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
