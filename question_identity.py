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
PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED = "PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED"
INVALID_PROGRESS_RECORD = "INVALID_PROGRESS_RECORD"


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
    if value:
        return value
    raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID)


def validate_canonical_question_ids(questions: Iterable[Mapping[str, Any]]) -> None:
    seen_ids: set[str] = set()
    for question in questions:
        question_id = canonical_question_id(question)
        if not question_id:
            raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID)
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
        question_id = canonical_question_id(question)
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
    version_present = "progress_identity_version" in payload
    kind_present = "question_identity" in payload
    version = payload.get("progress_identity_version")
    kind = str(payload.get("question_identity") or "").strip()
    if version == PROGRESS_IDENTITY_VERSION and kind == PROGRESS_IDENTITY_KIND:
        return "canonical"
    if version_present or kind_present:
        raise ProgressIdentityError(
            PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED,
            f"version={version!r}, kind={kind!r}",
        )
    questions = payload.get("questions")
    if not isinstance(questions, Mapping):
        raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "questions must be a mapping")
    keys = [str(key) for key in questions]
    if not keys or all(key.lstrip("-").isdigit() for key in keys):
        return "legacy-number"
    raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "unversioned non-numeric progress keys")


def _validate_progress_records(records: Mapping[Any, Any]) -> None:
    for key, record in records.items():
        if not isinstance(record, Mapping):
            raise ProgressIdentityError(INVALID_PROGRESS_RECORD, str(key))


def migrate_legacy_progress_keys(
    payload: Mapping[str, Any],
    questions: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], bool]:
    schema = classify_progress_identity_schema(payload)
    payload_questions = payload.get("questions")
    if not isinstance(payload_questions, Mapping):
        raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "questions must be a mapping")
    _validate_progress_records(payload_questions)
    if schema == "canonical":
        return copy.deepcopy(dict(payload)), False

    legacy_questions = payload_questions
    assert isinstance(legacy_questions, Mapping)
    if not legacy_questions:
        migrated = copy.deepcopy(dict(payload))
        migrated["progress_identity_version"] = PROGRESS_IDENTITY_VERSION
        migrated["question_identity"] = PROGRESS_IDENTITY_KIND
        return migrated, True

    index = build_number_to_question_id_index(questions)
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


def history_event_question_id(event: Mapping[str, Any] | None) -> str:
    if not isinstance(event, Mapping):
        return ""
    for key in ("question_id", "canonical_question_id"):
        value = str(event.get(key) or "").strip()
        if value:
            return value
    return ""


def history_event_matches_question(
    event: Mapping[str, Any] | None, question: Mapping[str, Any] | None
) -> bool:
    if not isinstance(event, Mapping) or not isinstance(question, Mapping):
        return False
    event_id = history_event_question_id(event)
    question_id = canonical_question_id(question)
    if event_id:
        return bool(question_id) and event_id == question_id
    try:
        return int(event.get("question_number")) == int(question.get("question_number"))
    except (TypeError, ValueError):
        return False


def question_for_history_event(
    event: Mapping[str, Any] | None, questions: Iterable[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    matches = [question for question in questions if history_event_matches_question(event, question)]
    return matches[0] if len(matches) == 1 else None


_registered_bank_questions: tuple[Mapping[str, Any], ...] = ()


def register_progress_identity_bank(questions: Iterable[Mapping[str, Any]]) -> None:
    global _registered_bank_questions
    materialized = tuple(questions)
    validate_available_canonical_question_ids(materialized)
    _registered_bank_questions = materialized


def registered_progress_identity_bank() -> tuple[Mapping[str, Any], ...]:
    return _registered_bank_questions


def resolve_registered_question_id_from_number(question_number: Any) -> str:
    try:
        target = int(question_number)
    except (TypeError, ValueError) as exc:
        raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID) from exc
    matches: set[str] = set()
    for question in _registered_bank_questions:
        try:
            number = int(question.get("question_number"))
        except (TypeError, ValueError):
            continue
        if number != target:
            continue
        question_id = canonical_question_id(question)
        if question_id:
            matches.add(question_id)
    if len(matches) == 1:
        return next(iter(matches))
    if len(matches) > 1:
        raise ProgressIdentityError(LEGACY_PROGRESS_AMBIGUOUS, str(target))
    raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID, str(target))
