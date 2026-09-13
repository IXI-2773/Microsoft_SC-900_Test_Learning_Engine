from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cert_config import QUESTION_BANK_FILENAME, RUNTIME_BANK_QUESTION_COUNT
from pe_validation import validate_pe_file
from tools.bank_warning_policy import evaluate_production_warnings
from tools.build_release import RELEASE_EXE, RELEASE_MANIFEST, RELEASE_README
from tools.validate_bank import validate_bank


def release_bank_gate_failures(result: dict, bank_path: Path) -> list[str]:
    failures: list[str] = []
    if result["question_count"] != RUNTIME_BANK_QUESTION_COUNT or result["issues"]:
        failures.append(f"release bank failed {RUNTIME_BANK_QUESTION_COUNT}-question bank gate")
    decision = evaluate_production_warnings(bank_path, result.get("warnings", []))
    failures.extend(decision.failures)
    return failures


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    failures = []
    bank = ROOT / QUESTION_BANK_FILENAME
    for path in (RELEASE_EXE, RELEASE_README, RELEASE_MANIFEST, bank):
        if not path.exists():
            failures.append(f"missing release component: {path}")
    if RELEASE_EXE.exists():
        pe_failure = validate_pe_file(RELEASE_EXE)
        if pe_failure:
            failures.append(f"invalid release PE: {pe_failure}")
    result = validate_bank(bank)
    failures.extend(release_bank_gate_failures(result, bank))
    if RELEASE_MANIFEST.exists() and RELEASE_EXE.exists():
        manifest = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("executable_sha256") != sha256(RELEASE_EXE):
            failures.append("release executable hash mismatch")
        if manifest.get("question_bank_sha256") != sha256(bank):
            failures.append("release bank hash mismatch")
        if int(manifest.get("expected_bank_count", -1)) != RUNTIME_BANK_QUESTION_COUNT:
            failures.append("release manifest bank count mismatch")
    if failures:
        for failure in failures:
            print(f"Smoke test failed: {failure}", file=sys.stderr)
        return 1
    print("Static release smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
