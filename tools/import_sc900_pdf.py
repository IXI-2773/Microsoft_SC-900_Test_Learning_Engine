from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extraction.pages import PdfExtractionError  # noqa: E402
from extraction.pipeline import extract_pdf_to_jsonl  # noqa: E402
from ingestion.adapter import adapt_exchange_jsonl  # noqa: E402
from ingestion.importer import compile_question_bank, import_jsonl  # noqa: E402
from ingestion.models import load_taxonomy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract an authorized SC-900 PDF to JSONL, then import it as pending content. Import is not approval."
    )
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, help="JSONL path for extracted exchange records")
    parser.add_argument("--store", type=Path, default=Path("data/sc900-content"))
    parser.add_argument("--title")
    parser.add_argument("--license")
    parser.add_argument("--domain")
    parser.add_argument("--objective")
    parser.add_argument("--password")
    parser.add_argument("--compile", type=Path, help="Optional runtime bank path; still compiles approved records only")
    args = parser.parse_args()
    jsonl = args.output or args.store / "incoming" / f"{args.pdf.stem}.jsonl"
    try:
        extract_pdf_to_jsonl(
            args.pdf,
            jsonl,
            title=args.title,
            source_license=args.license,
            domain=args.domain,
            objective=args.objective,
            password=args.password,
        )
    except PdfExtractionError as error:
        print(json.dumps({"ok": False, "code": error.code, "error": str(error)}, indent=2, sort_keys=True))
        return 1
    taxonomy = load_taxonomy()
    canonical = jsonl.with_suffix(".canonical.jsonl")
    adapted = adapt_exchange_jsonl(jsonl, canonical, taxonomy)
    report = import_jsonl(canonical, args.store, taxonomy)
    report.update({"ok": True, "extracted_jsonl": str(jsonl), "canonical_jsonl": str(canonical), **adapted})
    if args.compile:
        report.update(compile_question_bank(args.store, args.compile))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
