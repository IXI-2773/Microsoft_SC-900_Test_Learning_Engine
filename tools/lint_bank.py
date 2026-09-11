
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cert_config import QUESTION_BANK_FILENAME
from tools.validate_bank import validate_bank


def main() -> int:
    result = validate_bank(ROOT / QUESTION_BANK_FILENAME)
    failures = []
    if result["question_count"] != 8:
        failures.append(f"expected 8 baseline questions, got {result['question_count']}")
    failures.extend(f"{title}: {body}" for title, body in result["issues"])
    failures.extend(f"warning {title}: {body}" for title, body in result.get("warnings", []))
    if failures:
        for failure in failures:
            print(f"SC-900 bank lint failed: {failure}", file=sys.stderr)
        return 1
    print("SC-900 bank lint passed: 8 clean baseline questions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
