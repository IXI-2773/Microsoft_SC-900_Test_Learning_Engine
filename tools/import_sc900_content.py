from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingestion.importer import compile_question_bank, import_jsonl
from ingestion.models import load_taxonomy


def main() -> None:
    parser = argparse.ArgumentParser(description="Import explicitly provided SC-900 extractor JSONL output.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--store", type=Path, default=Path("data/sc900-content"))
    parser.add_argument("--compile", type=Path)
    args = parser.parse_args()
    report = import_jsonl(args.input, args.store, load_taxonomy())
    if args.compile:
        report.update(compile_question_bank(args.store, args.compile))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
