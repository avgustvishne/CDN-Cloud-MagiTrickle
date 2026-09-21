#!/usr/bin/env python3
"""Independent live-BGP validation using the current BGPKIT stack.

The report keeps the historical filename ``bgpstream-health.json`` for
backwards compatibility with the evidence pipeline, but the data source is
BGPKIT Broker + BGPKIT Parser, not CAIDA BGPStream.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BROKER_URL = "https://api.bgpkit.com/v3/broker"


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


def select_update_files(items, limit):
    """Select a deterministic, diverse set of recent collectors."""
    by_collector = {}
    for item in items:
        collector = str(getattr(item, "collector_id", "") or "")
        url = str(getattr(item, "url", "") or "")
        if not collector or not url:
            continue
        current = by_collector.get(collector)
        current_end = str(getattr(current, "ts_end", "") or "") if current else ""
        item_end = str(getattr(item, "ts_end", "") or "")
        if current is None or item_end > current_end:
            by_collector[collector] = item
    selected = sorted(
        by_collector.values(),
        key=lambda item: (
            str(getattr(item, "ts_end", "") or ""),
            str(getattr(item, "collector_id", "") or ""),
        ),
        reverse=True,
    )
    return selected[:limit]


def query_update_files(broker, start, end, project):
    """Query one project using only the pybgpkit Broker.query() API."""
    return broker.query(
        ts_start=start,
        ts_end=end,
        project=project,
        data_type="updates",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=0.5, help="Recent BGP update window in hours")
    ap.add_argument("--limit", type=int, default=12, help="Number of distinct ASNs to validate")
    ap.add_argument("--files", type=int, default=12, help="Maximum update files to parse")
    args = ap.parse_args()
    if args.hours <= 0 or args.hours > 2:
        ap.error("--hours must be > 0 and <= 2")
    if args.limit <= 0 or args.limit > 64:
        ap.error("--limit must be between 1 and 64")
    if args.files <= 0 or args.files > 24:
        ap.error("--files must be between 1 and 24")

    try:
        import bgpkit
    except ImportError as exc:
        raise SystemExit("BGPKIT dependency is missing; install pybgpkit==0.8.0") from exc

    pairs = load_asns(args.limit)
    if not pairs:
        raise SystemExit("No configured ASNs available for BGP validation")

    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(hours=args.hours)
    start_s = start.isoformat().replace("+00:00", "Z")
    end_s = end.isoformat().replace("+00:00", "Z")

    broker = bgpkit.Broker(page_size=100)
    items = []
    project_errors = []
    for project in ("routeviews", "riperis"):
        try:
            items.extend(query_update_files(broker, start_s, end_s, project))
        except Exception as exc:  # broker availability is an external dependency
            project_errors.append(f"{project}: {exc}")

    files = select_update_files(items, args.files)
    if not files:
        details = "; ".join(project_errors) if project_errors else "no update files returned"
        raise SystemExit(f"BGPKIT Broker returned no usable update files: {details}")

    found = {asn: set() for _, asn in pairs}
    peers = {asn: set() for _, asn in pairs}
    elements = 0
    parsed_files = 0
    parse_errors = []
    asn_filter = ",".join(asn for _, asn in pairs)

    for item in files:
        url = str(item.url)
        try:
            parser = bgpkit.Parser(url=url, filters={"origin_asns": asn_filter})
            file_elements = 0
            for elem in parser:
                origins = getattr(elem, "origin_asns", None) or []
                prefix = getattr(elem, "prefix", None)
                if not prefix:
                    continue
                matched = {str(asn) for asn in origins} & found.keys()
                if not matched:
                    continue
                file_elements += 1
                elements += 1
                for origin in matched:
                    found[origin].add(str(prefix))
                    peer = getattr(elem, "peer_asn", None)
                    if peer is not None:
                        peers[origin].add(str(peer))
            parsed_files += 1
            print(f"parsed {item.collector_id}: {file_elements} matching elements")
        except Exception as exc:
            parse_errors.append(f"{item.collector_id}: {exc}")
            print(f"warning: failed to parse {item.collector_id}: {exc}", file=sys.stderr)

    if parsed_files == 0:
        raise SystemExit("BGPKIT could not parse any selected update file")

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
        "engine": "v45",
        "source": "BGPKIT Broker + BGPKIT Parser",
        "broker": BROKER_URL,
        "projects": ["routeviews", "riperis"],
        "record_type": "updates",
        "window_hours": args.hours,
        "generated_at": end.isoformat(),
        "sample_size": len(rows),
        "files_selected": len(files),
        "files_parsed": parsed_files,
        "elements_observed": elements,
        "results": rows,
        "healthy_asns": sum(r["observed"] for r in rows),
        "partial": bool(project_errors or parse_errors),
        "warnings": project_errors + parse_errors,
    }
    path = ROOT / "data/bgpstream-health.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
