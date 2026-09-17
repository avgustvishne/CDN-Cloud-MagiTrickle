#!/usr/bin/env python3
"""Resilient RouteViews client with per-process throttling and ASN caching."""

import datetime
import email.utils
import json
import threading
import time
import urllib.error
import urllib.request


BASE_URL = "https://api.routeviews.org/asn/{asn}"
USER_AGENT = "CDN-Cloud-MagiTrickle/RouteViewsClient"
REQUEST_INTERVAL = 1.2
MAX_ATTEMPTS = 4
BACKOFF_BASE = 2.0
MAX_RETRY_AFTER = 30.0

_lock = threading.Lock()
_last_request_at = 0.0
_cache = {}


def _retry_after(value):
    if not value:
        return None
    try:
        return min(MAX_RETRY_AFTER, max(0.0, float(value)))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        return min(MAX_RETRY_AFTER, max(0.0, when.timestamp() - time.time()))
    except (TypeError, ValueError, OverflowError):
        return None


def _throttle():
    global _last_request_at
    now = time.monotonic()
    delay = REQUEST_INTERVAL - (now - _last_request_at)
    if delay > 0:
        time.sleep(delay)
    _last_request_at = time.monotonic()


def _fetch(asn):
    url = BASE_URL.format(asn=asn)
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        with _lock:
            _throttle()
            try:
                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, list):
                    raise ValueError("unexpected RouteViews response shape")
                return payload
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code != 429 or attempt >= MAX_ATTEMPTS:
                    break
                retry_after = _retry_after(exc.headers.get("Retry-After"))
                wait = retry_after if retry_after is not None else BACKOFF_BASE * (2 ** (attempt - 1))
                print(
                    f"[warn] RouteViews rate limited for AS{asn}; retrying in {wait:.1f}s "
                    f"(attempt {attempt}/{MAX_ATTEMPTS - 1})",
                    flush=True,
                )
                time.sleep(min(MAX_RETRY_AFTER, wait))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= MAX_ATTEMPTS:
                    break
                time.sleep(min(MAX_RETRY_AFTER, BACKOFF_BASE * (2 ** (attempt - 1))))
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"RouteViews request failed for AS{asn}")


def routeviews_prefixes(asn):
    """Return current RouteViews-originated prefixes for an ASN.

    RouteViews documents the unfiltered /asn/{ASN} endpoint as returning both
    IPv4 and IPv6 prefixes. Fetching it once per ASN avoids the previous
    two-request-per-ASN burst that frequently triggered HTTP 429 responses.
    """
    key = str(asn)
    if key in _cache:
        return list(_cache[key])
    try:
        payload = _fetch(key)
    except Exception as exc:
        print(f"[warn] RouteViews fetch failed for AS{key}: {exc}", flush=True)
        _cache[key] = tuple()
        return []

    found = set()
    for item in payload:
        value = item if isinstance(item, str) else item.get("prefix") if isinstance(item, dict) else None
        if isinstance(value, str) and "/" in value:
            found.add(value)
    result = tuple(sorted(found))
    _cache[key] = result
    return list(result)


def clear_cache():
    """Clear the process-local cache; intended for tests."""
    _cache.clear()
