#!/usr/bin/env python3
"""Source collection entrypoint.

This module is intentionally thin. Source-specific fetching remains in the
existing engine/registry for compatibility; this command produces a manifest
so collection can be scheduled independently from generation.
"""
import datetime, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
REGISTRY=ROOT/"config/source_registry.json"

def main():
    DATA.mkdir(exist_ok=True)
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    manifest={
        "generated_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status":"delegated-to-engine-registry",
        "source_count":len(registry),
    }
    (DATA/"source-fetch-manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))
if __name__=="__main__":
    main()
