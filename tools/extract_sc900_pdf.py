from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extraction.pages import PdfExtractionError  # noqa: E402
from extraction.pipeline import extract_pdf_records, write_exchange_jsonl  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract authorized SC-900 PDF text into versioned JSONL.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title")
    parser.add_argument("--license")
    parser.add_argument("--domain")
    parser.add_argument("--objective")
    parser.add_argument("--password")
    args = parser.parse_args()
    try:
        batch = extract_pdf_records(
            args.pdf,
            title=args.title,
            source_license=args.license,
            domain=args.domain,
            objective=args.objective,
            password=args.password,
        )
    except PdfExtractionError as error:
        print(json.dumps({"ok": False, "code": error.code, "error": str(error)}, indent=2, sort_keys=True))
        return 1
    write_exchange_jsonl(args.output, list(batch["records"]) + list(batch["diagnostics"]))
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "pages_processed": batch["pages_processed"],
                "question_candidates": batch["question_candidates"],
                "warnings": batch["warnings"],
                "contract_version": batch["contract_version"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
