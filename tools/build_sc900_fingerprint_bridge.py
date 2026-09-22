from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content_fingerprint_bridge import (  # noqa: E402
    DEFAULT_BRIDGE_PATH,
    FROZEN_BANK_FILENAMES,
    build_bridge_payload,
    canonical_bridge_sha256,
)


def canonical_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_BRIDGE_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_bridge_payload(ROOT, FROZEN_BANK_FILENAMES)
    output = canonical_bytes(payload)
    if args.check:
        if not args.out.exists():
            raise SystemExit(f"Bridge artifact missing: {args.out}")
        existing = args.out.read_bytes()
        if existing != output:
            raise SystemExit("Bridge artifact does not match deterministic regeneration.")
        print(f"PASS {args.out}")
        print(f"payload_sha256={canonical_bridge_sha256(payload)}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(output)
    print(f"WROTE {args.out}")
    print(f"nodes={len(payload['nodes'])}")
    print(f"question_mappings={sum(len(node['questions']) for node in payload['nodes'])}")
    print(f"payload_sha256={payload['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
