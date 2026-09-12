from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from question_identity import canonical_question_id, validate_canonical_question_ids

SESSION_IDENTITY_VERSION = 1
SESSION_IDENTITY_KIND = "canonical_question_id+bank_fingerprint"

# Durable question content that can change the meaning or answer authority of an item.
# Mutable learner/runtime state, provenance bookkeeping, and question_number are excluded.
_BANK_CONTENT_FIELDS = (
    "prompt",
    "choices",
    "correct",
    "general_explanation",
    "choice_explanations",
    "domain",
    "chapter",
    "subtitle",
    "question_type",
    "topics",
    "objective_code",
    "study_focus",
    "choice_order",
)


def ordered_question_ids(questions: Iterable[Mapping[str, Any]]) -> list[str]:
    materialized = tuple(questions)
    validate_canonical_question_ids(materialized)
    return [canonical_question_id(question) for question in materialized]


def _canonicalize_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _question_content_projection(question: Mapping[str, Any]) -> dict[str, Any]:
    question_id = canonical_question_id(question)
    if not question_id:
        raise ValueError("Session identity requires a canonical question ID.")
    projection: dict[str, Any] = {"question_id": question_id}
    for field in _BANK_CONTENT_FIELDS:
        if field in question:
            projection[field] = _canonicalize_json_value(question.get(field))
    return projection


def bank_content_fingerprint(questions: Iterable[Mapping[str, Any]]) -> str:
    materialized = tuple(questions)
    validate_canonical_question_ids(materialized)
    projections = [_question_content_projection(question) for question in materialized]
    projections.sort(key=lambda item: str(item["question_id"]))
    serialized = json.dumps(
        projections,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def canonical_session_signature(
    mode: str,
    bank_fingerprint: str,
    question_ids: Sequence[str],
) -> str:
    fingerprint = str(bank_fingerprint or "").strip()
    if not fingerprint:
        raise ValueError("Session identity requires a bank fingerprint.")
    ids = [str(question_id or "").strip() for question_id in question_ids]
    if not ids or any(not question_id for question_id in ids):
        raise ValueError("Session identity requires canonical question IDs.")
    if len(ids) != len(set(ids)):
        raise ValueError("Session identity contains duplicate canonical question IDs.")
    payload = {
        "identity_version": SESSION_IDENTITY_VERSION,
        "mode": str(mode or "").strip(),
        "bank_fingerprint": fingerprint,
        "question_ids": ids,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
