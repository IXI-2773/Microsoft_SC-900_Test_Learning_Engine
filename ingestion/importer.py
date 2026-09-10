from __future__ import annotations

import difflib
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from ingestion.models import ValidationError, canonicalize_record, normalize_text


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _stem_key(record: Mapping[str, Any]) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", normalize_text(record.get("stem")).casefold())
    return " ".join(text.split())


def _choice_key(record: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted(normalize_text(item.get("text")).casefold() for item in record.get("choices", [])))


def _comparison_bucket(record: Mapping[str, Any]) -> tuple[str, ...]:
    """Keep fuzzy comparison bounded to records with the same leading concept words."""
    terms = [term for term in _stem_key(record).split() if term not in {"a", "an", "the"}]
    return tuple(terms[:5])


def classify_duplicate(candidate: Mapping[str, Any], accepted: list[Mapping[str, Any]]) -> tuple[str, str | None]:
    if candidate.get("record_kind") != "question":
        return "unique", None
    stem = _stem_key(candidate)
    choices = _choice_key(candidate)
    bucket = _comparison_bucket(candidate)
    for current in accepted:
        if current.get("record_kind") != "question":
            continue
        if bucket != _comparison_bucket(current):
            continue
        if stem == _stem_key(current) and choices == _choice_key(current):
            return "exact", str(current["id"])
        if candidate.get("objective") == current.get("objective"):
            ratio = difflib.SequenceMatcher(a=stem, b=_stem_key(current)).ratio()
            if ratio >= 0.90:
                return "probable", str(current["id"])
            if ratio >= 0.72:
                return "related", str(current["id"])
    return "unique", None


def import_jsonl(input_path: Path, store_dir: Path, taxonomy: Mapping[str, Any]) -> dict[str, Any]:
    questions_path = store_dir / "questions.json"
    materials_path = store_dir / "source_material.json"
    existing_questions = _read_rows(questions_path)
    existing_materials = _read_rows(materials_path)
    accepted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    counts = Counter()
    reasons = Counter()
    known_ids = {row["id"] for row in existing_questions + existing_materials}
    source_counts = Counter()
    with input_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                if not isinstance(raw, Mapping):
                    raise ValidationError([{"code": "MALFORMED_RECORD", "message": "JSONL row must be an object"}])
                record = canonicalize_record(raw, taxonomy)
            except (json.JSONDecodeError, ValidationError) as error:
                codes = getattr(error, "reason_codes", ["MALFORMED_JSON"])
                reasons.update(codes)
                quarantined.append(
                    {"line": line_number, "reason_codes": codes, "diagnostic": str(error), "raw": line.rstrip()}
                )
                counts["rejected"] += 1
                continue
            source_key = str(record.get("provenance", {}).get("source", {}).get("book_id") or "unknown")
            source_counts[source_key] += 1
            if record["id"] in known_ids:
                counts["skipped"] += 1
                reasons["DUPLICATE_ID"] += 1
                continue
            pool = existing_questions + [row for row in accepted if row["record_kind"] == "question"]
            classification, related_to = classify_duplicate(record, pool)
            if classification == "exact":
                counts["skipped"] += 1
                reasons["EXACT_DUPLICATE"] += 1
                continue
            if classification == "probable":
                record["duplicate_review"] = {"classification": classification, "related_to": related_to}
                review.append(record)
                counts["review"] += 1
                reasons["PROBABLE_DUPLICATE"] += 1
                continue
            if classification == "related":
                record["related_to"] = related_to
            accepted.append(record)
            known_ids.add(record["id"])
            counts["accepted"] += 1
    new_questions = [row for row in accepted if row["record_kind"] == "question"]
    new_materials = [row for row in accepted if row["record_kind"] == "source_material"]
    _write_rows(questions_path, existing_questions + new_questions)
    _write_rows(materials_path, existing_materials + new_materials)
    _write_rows(store_dir / "quarantine.json", _read_rows(store_dir / "quarantine.json") + quarantined)
    _write_rows(store_dir / "review.json", _read_rows(store_dir / "review.json") + review)
    fingerprint = hashlib.sha256(input_path.read_bytes()).hexdigest()
    report = {
        "batch_fingerprint": fingerprint,
        "accepted": counts["accepted"],
        "rejected": counts["rejected"],
        "skipped": counts["skipped"],
        "review": counts["review"],
        "reason_codes": dict(sorted(reasons.items())),
        "source_statistics": dict(sorted(source_counts.items())),
    }
    _write_rows(store_dir / "reports" / f"{fingerprint}.json", [report])
    return report


def compile_question_bank(store_dir: Path, output_path: Path) -> Path:
    questions = _read_rows(store_dir / "questions.json")
    compiled = []
    for number, record in enumerate(questions, start=1):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        choice_map = {letters[index]: item["text"] for index, item in enumerate(record["choices"])}
        id_to_letter = {item["id"]: letters[index] for index, item in enumerate(record["choices"])}
        compiled.append(
            {
                "id": record["id"],
                "question_number": number,
                "prompt": record["stem"],
                "choices": choice_map,
                "correct": [id_to_letter[value] for value in record["correct_answer"]],
                "general_explanation": record["explanation"],
                "choice_explanations": {letter: record["explanation"] for letter in choice_map},
                "domain": record["domain"],
                "domain_code": record["domain"],
                "chapter": record["objective"],
                "topics": record["tags"] or [record["objective"]],
                "objective_code": record["objective"],
                "question_type": "single" if len(record["correct_answer"]) == 1 else "multi",
                "source_name": str(
                    record["provenance"]["source"].get("title")
                    or record["provenance"]["source"].get("book_id")
                    or "Imported SC-900 content"
                ),
                "provenance": record["provenance"],
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"title": "Imported SC-900 Question Bank", "questions": compiled}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return output_path
