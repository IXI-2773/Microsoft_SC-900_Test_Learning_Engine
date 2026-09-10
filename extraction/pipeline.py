from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from extraction.contract import CONTRACT_VERSION, diagnostic_record, question_record
from extraction.pages import PdfExtractionError, extract_pdf_pages
from extraction.parse import parse_question_blocks


def extract_pdf_records(
    pdf_path: Path,
    *,
    title: str | None = None,
    source_license: str | None = None,
    domain: str | None = None,
    objective: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    document = extract_pdf_pages(pdf_path, password=password)
    parsed = parse_question_blocks(document.pages, default_domain=domain, default_objective=objective)
    records = [question_record(item, document, title=title, source_license=source_license) for item in parsed]
    diagnostics = []
    if "OCR_REQUIRED" in document.warnings:
        diagnostics.append(
            diagnostic_record(document, "OCR_REQUIRED", "Ordinary text extraction is insufficient; OCR is not enabled.")
        )
    return {
        "pages_processed": document.page_count,
        "question_candidates": len(records),
        "extraction_method": document.extraction_method,
        "source_document_id": document.source_document_id,
        "contract_version": CONTRACT_VERSION,
        "records": records,
        "diagnostics": diagnostics,
        "warnings": list(document.warnings),
    }


def extract_pdf_to_jsonl(
    pdf_path: Path,
    output_path: Path,
    *,
    title: str | None = None,
    source_license: str | None = None,
    domain: str | None = None,
    objective: str | None = None,
    password: str | None = None,
) -> Path:
    batch = extract_pdf_records(
        pdf_path,
        title=title,
        source_license=source_license,
        domain=domain,
        objective=objective,
        password=password,
    )
    return write_exchange_jsonl(output_path, list(batch["records"]) + list(batch["diagnostics"]))


def write_exchange_jsonl(output_path: Path, rows: list[dict[str, Any]]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return output_path


def load_exchange_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, Mapping):
                rows.append(dict(payload))
    return rows


__all__ = [
    "PdfExtractionError",
    "extract_pdf_records",
    "extract_pdf_to_jsonl",
    "load_exchange_rows",
    "write_exchange_jsonl",
]
