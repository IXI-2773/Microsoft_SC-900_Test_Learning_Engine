from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.importer import apply_review_decision, compile_question_bank, promotion_counts  # noqa: E402
from ingestion.models import ValidationError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record an explicit SC-900 content promotion decision. Import is not approval."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    decide = subparsers.add_parser("decide", help="Approve, withhold, or return a question to pending.")
    decide.add_argument("decision", choices=("approved", "withheld", "pending"))
    decide.add_argument("question_id")
    decide.add_argument("--store", type=Path, default=Path("data/sc900-content"))
    decide.add_argument("--actor", default="operator")
    report = subparsers.add_parser("report", help="Show approved, pending, withheld, and compiled counts.")
    report.add_argument("--store", type=Path, default=Path("data/sc900-content"))
    report.add_argument("--compile", type=Path)
    args = parser.parse_args()
    if args.command == "report":
        questions_path = args.store / "questions.json"
        questions = json.loads(questions_path.read_text(encoding="utf-8")) if questions_path.exists() else []
        payload = promotion_counts(questions)
        payload["compiled"] = payload["approved"]
        if args.compile:
            payload.update(compile_question_bank(args.store, args.compile))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    try:
        entry = apply_review_decision(args.store, args.question_id, args.decision, actor=args.actor)
    except ValidationError as error:
        print(json.dumps({"ok": False, "reason_codes": error.reason_codes, "error": str(error)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps({"ok": True, **entry}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
