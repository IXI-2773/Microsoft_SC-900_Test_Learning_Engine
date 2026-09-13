from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cert_config import QUESTION_BANK_FILENAME, RUNTIME_BANK_QUESTION_COUNT  # noqa: E402
from tools.bank_warning_policy import evaluate_production_warnings  # noqa: E402
from tools.validate_bank import validate_bank  # noqa: E402


def lint_bank(
    bank_path: Path,
    *,
    expected_count: int | None,
    fail_on_warnings: bool,
    label: str,
) -> int:
    result = validate_bank(bank_path)
    failures: list[str] = []
    actual = int(result["question_count"])
    if expected_count is not None and actual != expected_count:
        failures.append(f"expected {expected_count} questions, got {actual}")
    failures.extend(f"{title}: {body}" for title, body in result["issues"])
    warnings = list(result.get("warnings", []))
    warning_lines = [f"warning {title}: {body}" for title, body in warnings]
    decision = None
    if fail_on_warnings:
        decision = evaluate_production_warnings(bank_path, warnings)
        failures.extend(decision.failures)
    if failures:
        for failure in failures:
            print(f"{label} failed: {failure}", file=sys.stderr)
        return 1
    if decision is not None and decision.governed:
        print(
            f"{label} passed: {actual} questions. "
            f"KNOWN_FROZEN_WARNING_COUNT = {decision.known_frozen_warning_count} "
            f"UNEXPECTED_WARNING_COUNT = {decision.unexpected_warning_count}"
        )
    elif warning_lines and not fail_on_warnings:
        print(
            f"{label} passed: {actual} questions. "
            f"({len(warning_lines)} warnings reported, diagnostic --allow-warnings)"
        )
    else:
        print(f"{label} passed: {actual} questions.")
    if warning_lines:
        for line in warning_lines[:20]:
            print(line, file=sys.stderr)
        if len(warning_lines) > 20:
            print(f"... {len(warning_lines) - 20} more warnings", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint an SC-900 question bank JSON file.")
    parser.add_argument(
        "--bank",
        type=Path,
        default=ROOT / QUESTION_BANK_FILENAME,
        help="Bank JSON to lint. Default is the launch/default bank.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="Required question count. Defaults to the active runtime bank count for the configured launch bank.",
    )
    parser.add_argument(
        "--allow-warnings",
        action="store_true",
        help=(
            "Diagnostic override: report validator warnings without failing. "
            "Not a production acceptance gate."
        ),
    )
    parser.add_argument(
        "--label",
        default="",
        help="Status label printed in pass/fail output.",
    )
    args = parser.parse_args()
    bank_path = args.bank if args.bank.is_absolute() else ROOT / args.bank
    is_default = bank_path.resolve() == (ROOT / QUESTION_BANK_FILENAME).resolve()
    expected = (
        args.expected_count
        if args.expected_count is not None
        else (RUNTIME_BANK_QUESTION_COUNT if is_default else None)
    )
    fail_on_warnings = not args.allow_warnings
    label = args.label or ("SC-900 default-bank lint" if is_default else "SC-900 bank lint")
    return lint_bank(bank_path, expected_count=expected, fail_on_warnings=fail_on_warnings, label=label)


def final_candidate_bank_path() -> Path:
    return ROOT / "content" / "sc900" / "microsoft-learn-corpus" / "compiled" / "sc900_microsoft_learn_corpus_bank.json"


if __name__ == "__main__":
    raise SystemExit(main())
