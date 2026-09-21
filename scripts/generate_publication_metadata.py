#!/usr/bin/env python3
"""Write provenance metadata for a validated publication bundle."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
data = ROOT / "data"
files = sorted(
    p for p in data.rglob("*")
    if p.is_file() and p.name != "publication-metadata.json"
)

payload = {
    "schema_version": 1,
    "engine": "publication-provenance-v1",
    "source_sha": os.environ.get("GITHUB_SHA", ""),
    "workflow_run_id": os.environ.get("GITHUB_RUN_ID", ""),
    "repository": os.environ.get("GITHUB_REPOSITORY", ""),
    "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "data_sha256": hashlib.sha256(
        "\n".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}"
            for p in files
        ).encode("utf-8")
    ).hexdigest(),
}
(data / "publication-metadata.json").write_text(
    json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(json.dumps(payload, indent=2, ensure_ascii=False))
