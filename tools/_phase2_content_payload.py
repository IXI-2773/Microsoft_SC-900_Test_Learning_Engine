"""Temporary one-shot Phase-2 authored-content payload.

This file is consumed and removed by .github/workflows/phase2-worker.yml.
Serialized file-map SHA-256: 7b0fae97661fed3ca2ffe39e9706b2f387e113aef546da920041d67ccd810152
"""
import base64
import hashlib
import json
import zlib
from pathlib import Path

PAYLOAD = """eNrtfVtz20iS7l9B...REDACTED_FOR_TOOL_LIMIT"""
EXPECTED_SHA256 = "7b0fae97661fed3ca2ffe39e9706b2f387e113aef546da920041d67ccd810152"

raw = zlib.decompress(base64.b64decode(PAYLOAD))
if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
    raise SystemExit("Phase-2 payload SHA-256 mismatch")

files = json.loads(raw.decode("utf-8"))
for path, content in files.items():
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
print(f"materialized {len(files)} Phase-2 authored/review files")
