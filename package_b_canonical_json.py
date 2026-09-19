"""Canonical JSON materialization for governed Package B artifacts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def canonical_package_b_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize a governed Package B artifact as UTF-8 JSON with LF endings."""
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return serialized.encode("utf-8")


def write_canonical_package_b_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write governed Package B JSON without platform text-newline translation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_package_b_json_bytes(payload))
