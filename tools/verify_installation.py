
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app
import cert_config
from question_bank import load_bank

REQUIRED = (
    "app.py",
    "cert_config.py",
    "cert_profile_sc900.json",
    "sc900_bank_v8_baseline.json",
    "question_bank.py",
)
BANNED = ("sy0-701", "comptia", "security+", "public_sy0701")


def main() -> int:
    failures = []
    for name in REQUIRED:
        if not (ROOT / name).exists():
            failures.append(f"missing required file: {name}")
    profile = json.loads((ROOT / "cert_profile_sc900.json").read_text(encoding="utf-8"))
    if profile.get("exam_code") != "SC-900":
        failures.append("profile exam_code is not SC-900")
    bank = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)
    if len(bank["questions"]) != 8:
        failures.append(f"runtime bank contains {len(bank['questions'])} questions instead of 8")
    if app.DEFAULT_BANK.name != cert_config.QUESTION_BANK_FILENAME:
        failures.append("app default bank does not use SC-900 config")
    runtime_paths = [ROOT / name for name in (
        "app.py", "app_info.py", "question_bank.py", "cert_config.py",
        "app_analytics_mixin.py", "app_session_builder_mixin.py",
    )]
    for path in runtime_paths:
        text = path.read_text(encoding="utf-8").lower()
        for term in BANNED:
            if term in text:
                failures.append(f"legacy term {term!r} remains in {path.name}")
    if failures:
        for failure in failures:
            print(f"SC-900 installation verification failed: {failure}", file=sys.stderr)
        return 1
    print("SC-900 installation verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
