from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from extraction.pages import EXTRACTOR_VERSION, PdfDocumentText
from extraction.parse import ParsedQuestion

CONTRACT_VERSION = "sc900.extractor.exchange/v1"


def _origin_for_pdf() -> str:
    return "SOURCE_EXTRACTED"


def question_record(
    parsed: ParsedQuestion,
    document: PdfDocumentText,
    *,
    title: str | None = None,
    source_license: str | None = None,
) -> dict[str, Any]:
    warnings = list(parsed.warnings)
    warnings.extend(code for code in document.warnings if code not in warnings)
    return {
        "contract_version": CONTRACT_VERSION,
        "record_type": "extracted_question",
        "origin": _origin_for_pdf(),
        "source_document_id": document.source_document_id,
        "source_title": title or document.source_title,
        "source_path_or_reference": document.source_path,
        "source_page": parsed.source_page,
        "source_page_end": parsed.source_page_end,
        "source_locator": parsed.source_locator,
        "extraction_method": document.extraction_method,
        "extractor_version": document.extractor_version or EXTRACTOR_VERSION,
        "question_text": parsed.question_text,
        "choices": [dict(choice) for choice in parsed.choices],
        "source_answer": list(parsed.source_answer),
        "source_explanation": parsed.source_explanation,
        "raw_source_fragment": parsed.raw_source_fragment,
        "confidence": parsed.confidence,
        "extraction_warnings": warnings,
        "source_license": source_license,
        "domain": parsed.domain,
        "objective": parsed.objective,
    }


def diagnostic_record(document: PdfDocumentText, code: str, message: str) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "record_type": "extraction_diagnostic",
        "origin": _origin_for_pdf(),
        "source_document_id": document.source_document_id,
        "source_title": document.source_title,
        "source_path_or_reference": document.source_path,
        "source_page": None,
        "extraction_method": document.extraction_method,
        "extractor_version": document.extractor_version,
        "code": code,
        "message": message,
        "extraction_warnings": list(document.warnings),
        "extracted_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
