#!/usr/bin/env python3
"""Profile generation facade.

Keeps profile-specific output orchestration separate from source acquisition,
evidence and normalization. The production update script can call this facade
without duplicating profile logic.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def generate_profiles(provider_files, output_dir=DATA):
    """Compatibility facade; delegates to the existing profile generator when present."""
    try:
        from generate_profiles import generate_profiles as _generate
    except ImportError:
        return {"status":"deferred","reason":"generate_profiles module not present"}
    return _generate(provider_files, output_dir)
