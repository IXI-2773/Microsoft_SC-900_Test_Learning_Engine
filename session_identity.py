from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from question_identity import (
    bank_content_fingerprint,
    canonical_question_id,
    validate_canonical_question_ids,
)

SESSION_IDENTITY_VERSION = 1
SESSION_IDENTITY_KIND = "canonical_question_id+bank_fingerprint"

__all__ = [
    "SESSION_IDENTITY_KIND",
    "SESSION_IDENTITY_VERSION",
    "bank_content_fingerprint",
    "canonical_session_signature",
    "ordered_question_ids",
]


def ordered_question_ids(questions: Iterable[Mapping[str, Any]]) -> list[str]:
    materialized = tuple(questions)
    validate_canonical_question_ids(materialized)
    return [canonical_question_id(question) for question in materialized]


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
