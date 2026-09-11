from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ORIGIN_MAP = {
    "SOURCE_EXTRACTED": "extracted",
    "GENERATED": "generated",
    "MANUALLY_AUTHORED": "manual",
    "extracted": "extracted",
    "generated": "generated",
    "manual": "manual",
}


def adapt_exchange_record(raw: Mapping[str, Any]) -> dict[str, Any]:
    answers = raw.get("source_answer") or raw.get("correct_answer") or []
    if isinstance(answers, str):
        answers = [answers]
    choices = raw.get("choices") or []
    origin = ORIGIN_MAP.get(str(raw.get("origin") or "SOURCE_EXTRACTED"), "extracted")
    question_type = "multi_select" if len(list(answers)) > 1 else "multiple_choice"
    return {
        "exam": "SC-900",
        "record_kind": "question",
        "domain": raw.get("domain"),
        "objective": raw.get("objective"),
        "difficulty": raw.get("difficulty") or "intermediate",
        "type": raw.get("type") or question_type,
        "stem": raw.get("question_text") or raw.get("stem"),
        "choices": choices,
        "correct_answer": list(answers),
        "explanation": raw.get("source_explanation") or raw.get("explanation") or "",
        "source": {
            "book_id": raw.get("source_document_id"),
            "title": raw.get("source_title"),
            "path": raw.get("source_path_or_reference"),
            "page": raw.get("source_page"),
            "page_end": raw.get("source_page_end"),
            "locator": raw.get("source_locator"),
        },
        "tags": list(raw.get("tags") or []),
        "metadata": {
            "origin": origin,
            "extractor_version": raw.get("extractor_version"),
            "extraction_method": raw.get("extraction_method"),
            "warnings": list(raw.get("extraction_warnings") or []),
            "contract_version": raw.get("contract_version"),
            "confidence": raw.get("confidence"),
            "source_license": raw.get("source_license"),
            "raw_source_fragment": raw.get("raw_source_fragment"),
        },
    }


def adapt_exchange_jsonl(input_path: Path, output_path: Path, taxonomy: Mapping[str, Any]) -> dict[str, int]:
    del taxonomy  # taxonomy is applied later by canonicalize_record
    adapted = 0
    skipped = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open(encoding="utf-8") as handle, output_path.open("w", encoding="utf-8") as out:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, Mapping):
                skipped += 1
                continue
            if raw.get("record_type") == "extraction_diagnostic":
                skipped += 1
                continue
            out.write(json.dumps(adapt_exchange_record(raw), ensure_ascii=False) + "\n")
            adapted += 1
    return {"adapted": adapted, "skipped": skipped}


def exchange_question(index: int, *, question_text: str, source_page: int) -> dict[str, Any]:
    return {
        "contract_version": "sc900.extractor.exchange/v1",
        "record_type": "extracted_question",
        "origin": "SOURCE_EXTRACTED",
        "source_document_id": "synthetic-scale",
        "source_title": "Synthetic extractor scale fixture",
        "source_path_or_reference": "synthetic://scale",
        "source_page": source_page,
        "source_page_end": source_page,
        "source_locator": f"page:{source_page}#q{index}",
        "extraction_method": "synthetic",
        "extractor_version": "sc900-extractor-v1",
        "question_text": question_text,
        "choices": [
            {"id": "A", "text": "Microsoft Purview"},
            {"id": "B", "text": f"Microsoft Entra ID token {index:04d}"},
            {"id": "C", "text": "Microsoft Defender"},
            {"id": "D", "text": "Microsoft Intune"},
        ],
        "source_answer": ["B"],
        "source_explanation": "Microsoft Entra ID is the identity service named by this original fixture.",
        "raw_source_fragment": question_text,
        "confidence": 1.0,
        "extraction_warnings": [],
        "source_license": "original-fixture",
        "domain": "microsoft_entra",
        "objective": "entra_identity_access",
    }
