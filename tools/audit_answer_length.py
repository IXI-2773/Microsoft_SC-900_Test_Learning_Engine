"""Generate a deterministic answer-length audit for a question bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from answer_length_audit import audit_questions
from question_identity import bank_content_fingerprint


def _load_bank(bank_path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    bank_bytes = bank_path.read_bytes()
    payload = json.loads(bank_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("bank must be a top-level JSON object")
    if "questions" not in payload:
        raise ValueError("bank must contain questions")
    questions = payload["questions"]
    if not isinstance(questions, list):
        raise ValueError("bank questions must be a list")
    return bank_bytes, questions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bank_bytes, questions = _load_bank(args.bank)
        payload = audit_questions(questions)
        payload["bank_file_sha256"] = hashlib.sha256(bank_bytes).hexdigest()
        payload["bank_content_fingerprint"] = bank_content_fingerprint(questions)
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_bytes(serialized.encode("utf-8"))
    except (AttributeError, OSError, TypeError, UnicodeDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
