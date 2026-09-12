from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

PROGRESS_IDENTITY_VERSION = 1
PROGRESS_IDENTITY_KIND = "canonical_question_id"

MISSING_CANONICAL_QUESTION_ID = "MISSING_CANONICAL_QUESTION_ID"
DUPLICATE_CANONICAL_QUESTION_ID = "DUPLICATE_CANONICAL_QUESTION_ID"
LEGACY_PROGRESS_AMBIGUOUS = "LEGACY_PROGRESS_AMBIGUOUS"
LEGACY_PROGRESS_UNMAPPED = "LEGACY_PROGRESS_UNMAPPED"
LEGACY_PROGRESS_COLLISION = "LEGACY_PROGRESS_COLLISION"
PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS = "PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS"


class ProgressIdentityError(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason if not detail else f"{reason}: {detail}"
        super().__init__(message)


def canonical_question_id(question: Mapping[str, Any] | str | None) -> str:
    if isinstance(question, str):
        return question.strip()
    if not isinstance(question, Mapping):
        return ""
    for key in ("id", "question_id", "canonical_question_id"):
        value = str(question.get(key) or "").strip()
        if value:
            return value
    metadata = question.get("metadata")
    if isinstance(metadata, Mapping):
        value = str(metadata.get("question_id") or metadata.get("canonical_question_id") or "").strip()
        if value:
            return value
    return ""


def require_canonical_question_id(question: Mapping[str, Any] | str | None) -> str:
    value = canonical_question_id(question)
    if not value:
        raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID)
    return value


def validate_canonical_question_ids(questions: Iterable[Mapping[str, Any]]) -> None:
    seen_ids: set[str] = set()
    for question in questions:
        question_id = require_canonical_question_id(question)
        if question_id in seen_ids:
            raise ProgressIdentityError(DUPLICATE_CANONICAL_QUESTION_ID, question_id)
        seen_ids.add(question_id)


def validate_available_canonical_question_ids(questions: Iterable[Mapping[str, Any]]) -> None:
    seen_ids: set[str] = set()
    for question in questions:
        question_id = canonical_question_id(question)
        if not question_id:
            continue
        if question_id in seen_ids:
            raise ProgressIdentityError(DUPLICATE_CANONICAL_QUESTION_ID, question_id)
        seen_ids.add(question_id)


def build_number_to_question_id_index(questions: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    materialized = tuple(questions)
    validate_canonical_question_ids(materialized)
    by_number: dict[str, str] = {}
    for question in materialized:
        question_id = require_canonical_question_id(question)
        raw_number = question.get("question_number")
        if raw_number in (None, ""):
            continue
        try:
            number = str(int(raw_number))
        except (TypeError, ValueError):
            continue
        if number in by_number and by_number[number] != question_id:
            raise ProgressIdentityError(LEGACY_PROGRESS_AMBIGUOUS, number)
        by_number[number] = question_id
    return by_number


def classify_progress_identity_schema(payload: Mapping[str, Any]) -> str:
    version = payload.get("progress_identity_version")
    kind = str(payload.get("question_identity") or "").strip()
    if version == PROGRESS_IDENTITY_VERSION and kind == PROGRESS_IDENTITY_KIND:
        return "canonical"
    questions = payload.get("questions")
    if not isinstance(questions, Mapping):
        raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "questions must be a mapping")
    keys = [str(key) for key in questions]
    if not keys or all(key.lstrip("-").isdigit() for key in keys):
        return "legacy-number"
    raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "unversioned non-numeric progress keys")


def migrate_legacy_progress_keys(
    payload: Mapping[str, Any],
    questions: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], bool]:
    schema = classify_progress_identity_schema(payload)
    if schema == "canonical":
        return copy.deepcopy(dict(payload)), False

    index = build_number_to_question_id_index(questions)
    legacy_questions = payload.get("questions")
    assert isinstance(legacy_questions, Mapping)
    migrated_questions: dict[str, Any] = {}
    for legacy_key, record in legacy_questions.items():
        raw_key = str(legacy_key).strip()
        try:
            normalized_key = str(int(raw_key))
        except (TypeError, ValueError) as exc:
            raise ProgressIdentityError(LEGACY_PROGRESS_UNMAPPED, raw_key) from exc
        question_id = index.get(normalized_key)
        if not question_id:
            raise ProgressIdentityError(LEGACY_PROGRESS_UNMAPPED, normalized_key)
        if question_id in migrated_questions:
            raise ProgressIdentityError(LEGACY_PROGRESS_COLLISION, question_id)
        migrated_questions[question_id] = copy.deepcopy(record)

    migrated = copy.deepcopy(dict(payload))
    migrated["questions"] = migrated_questions
    migrated["progress_identity_version"] = PROGRESS_IDENTITY_VERSION
    migrated["question_identity"] = PROGRESS_IDENTITY_KIND
    return migrated, True


_registered_bank_questions: tuple[Mapping[str, Any], ...] = ()


def register_progress_identity_bank(questions: Iterable[Mapping[str, Any]]) -> None:
    global _registered_bank_questions
    materialized = tuple(questions)
    validate_available_canonical_question_ids(materialized)
    _registered_bank_questions = materialized


def registered_progress_identity_bank() -> tuple[Mapping[str, Any], ...]:
    return _registered_bank_questions
