from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from fingerprint_identity import (
    FINGERPRINT_ALGORITHM,
    FINGERPRINT_SCHEMA_VERSION,
    RUNTIME_FINGERPRINT_DOMAIN,
    RUNTIME_LOADER_CONTRACT_VERSION,
)

PROGRESS_IDENTITY_VERSION = 1
PROGRESS_IDENTITY_KIND = "canonical_question_id"
PROGRESS_CONTENT_EPOCH_VERSION = 2

MISSING_CANONICAL_QUESTION_ID = "MISSING_CANONICAL_QUESTION_ID"
DUPLICATE_CANONICAL_QUESTION_ID = "DUPLICATE_CANONICAL_QUESTION_ID"
LEGACY_PROGRESS_AMBIGUOUS = "LEGACY_PROGRESS_AMBIGUOUS"
LEGACY_PROGRESS_UNMAPPED = "LEGACY_PROGRESS_UNMAPPED"
LEGACY_PROGRESS_COLLISION = "LEGACY_PROGRESS_COLLISION"
PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS = "PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS"
PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED = "PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED"
INVALID_PROGRESS_RECORD = "INVALID_PROGRESS_RECORD"
CHANGED_CONTENT = "CHANGED_CONTENT"
REMOVED_QUESTION = "REMOVED_QUESTION"
UNMAPPED_QUESTION_NUMBER = "UNMAPPED_QUESTION_NUMBER"

# Durable question content that can change meaning or answer authority.
# Mutable learner/runtime state, provenance bookkeeping, question_number, and
# presentation-only choice-letter order are excluded. Choice identity is the
# answer texts themselves so runtime letter shuffles keep the same fingerprint.
_BANK_CONTENT_FIELDS = (
    "prompt",
    "general_explanation",
    "domain",
    "chapter",
    "subtitle",
    "question_type",
    "topics",
    "objective_code",
    "study_focus",
)


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


def _choice_text_projection(question: Mapping[str, Any]) -> dict[str, Any]:
    choices = question.get("choices")
    if not isinstance(choices, Mapping):
        projection: dict[str, Any] = {}
        if "choices" in question:
            projection["choices"] = _canonicalize_json_value(choices)
        if "correct" in question:
            projection["correct"] = _canonicalize_json_value(question.get("correct"))
        if "choice_explanations" in question:
            projection["choice_explanations"] = _canonicalize_json_value(question.get("choice_explanations"))
        return projection
    texts = [str(text) for text in choices.values()]
    projection = {"choice_texts": _canonicalize_json_value(sorted(texts))}
    correct_letters = question.get("correct") or []
    projection["correct_texts"] = _canonicalize_json_value(
        sorted(str(choices.get(letter, letter)) for letter in correct_letters)
    )
    explanations = question.get("choice_explanations")
    if isinstance(explanations, Mapping) and explanations:
        explained = [
            {
                "choice_text": str(choices.get(letter, letter)),
                "explanation": explanation,
            }
            for letter, explanation in explanations.items()
        ]
        explained.sort(key=lambda row: str(row["choice_text"]))
        projection["choice_explanation_texts"] = _canonicalize_json_value(explained)
    return projection


def question_content_projection(question: Mapping[str, Any]) -> dict[str, Any]:
    question_id = canonical_question_id(question)
    if not question_id:
        raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID)
    projection: dict[str, Any] = {"question_id": question_id}
    for field in _BANK_CONTENT_FIELDS:
        if field in question:
            projection[field] = _canonicalize_json_value(question.get(field))
    projection.update(_choice_text_projection(question))
    return projection


def question_content_fingerprint(question: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        question_content_projection(question),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def bank_content_fingerprint(questions: Iterable[Mapping[str, Any]]) -> str:
    materialized = tuple(questions)
    validate_canonical_question_ids(materialized)
    projections = [question_content_projection(question) for question in materialized]
    projections.sort(key=lambda item: str(item["question_id"]))
    serialized = json.dumps(
        projections,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
    if not event_id or not question_id or event_id != question_id:
        return False
    event_fp = str(event.get("question_content_fingerprint") or "").strip()
    if not event_fp:
        return True
    return event_fp == question_content_fingerprint(question)


def legacy_history_event_matches_question(
    event: Mapping[str, Any] | None, question: Mapping[str, Any] | None
) -> bool:
    if history_event_matches_question(event, question):
        return True
    if not isinstance(event, Mapping) or not isinstance(question, Mapping):
        return False
    if history_event_question_id(event):
        return False
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


def canonical_question_history_map(events: Iterable[Mapping[str, Any] | None]) -> dict[str, list[Mapping[str, Any]]]:
    history_map: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        question_id = history_event_question_id(event)
        if not question_id or not isinstance(event, Mapping):
            continue
        history_map.setdefault(question_id, []).append(event)
    return history_map


def history_events_for_question(
    history_map: Mapping[str, list[Mapping[str, Any]]],
    question: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    question_id = canonical_question_id(question)
    if not question_id:
        return []
    return [
        event
        for event in history_map.get(question_id, [])
        if history_event_matches_question(event, question)
    ]


def migrate_legacy_history_events(
    history: Iterable[Mapping[str, Any] | None],
    questions: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    materialized = tuple(questions)
    validate_canonical_question_ids(materialized)
    number_only = [
        event
        for event in history
        if isinstance(event, Mapping) and not history_event_question_id(event) and event.get("question_number") not in (None, "")
    ]
    index = build_number_to_question_id_index(materialized) if number_only else {}
    fingerprints = {canonical_question_id(question): question_content_fingerprint(question) for question in materialized}
    migrated: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for event in history:
        if not isinstance(event, Mapping):
            continue
        row = copy.deepcopy(dict(event))
        question_id = history_event_question_id(row)
        if question_id:
            migrated.append(row)
            continue
        raw_number = row.get("question_number")
        try:
            normalized = str(int(raw_number))
        except (TypeError, ValueError):
            migrated.append(row)
            continue
        mapped_id = index.get(normalized)
        if not mapped_id:
            quarantined.append({"reason": UNMAPPED_QUESTION_NUMBER, "question_number": normalized, "event": copy.deepcopy(row)})
            migrated.append(row)
            continue
        row["question_id"] = mapped_id
        row["question_content_fingerprint"] = fingerprints[mapped_id]
        migrated.append(row)
    return migrated, quarantined


def _runtime_bank_node_id(current_bank_fingerprint: str) -> str:
    try:
        from content_fingerprint_bridge import runtime_bank_node_id_for_fingerprint

        return runtime_bank_node_id_for_fingerprint(current_bank_fingerprint)
    except Exception:
        return ""


def _epoch_payload_matches_bank(
    payload: Mapping[str, Any],
    current_fingerprints: Mapping[str, str],
    current_bank_fingerprint: str,
    current_bank_node_id: str,
) -> bool:
    if payload.get("progress_content_epoch_version") != PROGRESS_CONTENT_EPOCH_VERSION:
        return False
    if int(payload.get("fingerprint_schema_version") or 0) != FINGERPRINT_SCHEMA_VERSION:
        return False
    if str(payload.get("fingerprint_domain") or "").strip() != RUNTIME_FINGERPRINT_DOMAIN:
        return False
    if str(payload.get("fingerprint_algorithm") or "").strip() != FINGERPRINT_ALGORITHM:
        return False
    if int(payload.get("loader_contract_version") or 0) != RUNTIME_LOADER_CONTRACT_VERSION:
        return False
    if str(payload.get("bank_fingerprint") or "").strip() != current_bank_fingerprint:
        return False
    stored_node = str(payload.get("bank_node_id") or "").strip()
    if current_bank_node_id and stored_node != current_bank_node_id:
        return False
    if stored_node and not current_bank_node_id:
        return False
    stored = payload.get("question_content_fingerprints")
    records = payload.get("questions")
    if not isinstance(stored, Mapping) or not isinstance(records, Mapping):
        return False
    for question_id in records:
        qid = str(question_id)
        if qid not in current_fingerprints:
            return False
        if str(stored.get(qid) or "").strip() != current_fingerprints[qid]:
            return False
    history = payload.get("history") or []
    if not isinstance(history, list):
        return False
    for event in history:
        if not isinstance(event, Mapping):
            return False
        if history_event_question_id(event):
            continue
        if event.get("question_number") not in (None, ""):
            return False
    return True


def migrate_progress_content_epoch(
    payload: Mapping[str, Any],
    questions: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], bool]:
    schema = classify_progress_identity_schema(payload)
    if schema != "canonical":
        raise ProgressIdentityError(
            PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED,
            f"content epoch requires canonical progress, schema={schema!r}",
        )
    materialized = tuple(questions)
    if not materialized:
        return copy.deepcopy(dict(payload)), False
    validate_canonical_question_ids(materialized)
    current_fingerprints = {
        canonical_question_id(question): question_content_fingerprint(question) for question in materialized
    }
    current_bank_fingerprint = bank_content_fingerprint(materialized)
    current_bank_node_id = _runtime_bank_node_id(current_bank_fingerprint)
    migrated = copy.deepcopy(dict(payload))
    if _epoch_payload_matches_bank(
        migrated,
        current_fingerprints,
        current_bank_fingerprint,
        current_bank_node_id,
    ):
        return migrated, False

    records = migrated.get("questions")
    if not isinstance(records, Mapping):
        raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "questions must be a mapping")
    _validate_progress_records(records)
    stored_fingerprints = dict(migrated.get("question_content_fingerprints") or {})
    first_bind = migrated.get("progress_content_epoch_version") != PROGRESS_CONTENT_EPOCH_VERSION
    quarantined = dict(migrated.get("quarantined_questions") or {})
    bound_records: dict[str, Any] = {}
    bound_fingerprints: dict[str, str] = {}
    for raw_id, record in records.items():
        question_id = str(raw_id)
        stored_fp = str(stored_fingerprints.get(question_id) or "").strip()
        if question_id not in current_fingerprints:
            quarantined[question_id] = {
                "reason": REMOVED_QUESTION,
                "record": copy.deepcopy(record),
                "fingerprint": stored_fp,
            }
            continue
        current_fp = current_fingerprints[question_id]
        if stored_fp and stored_fp != current_fp:
            quarantined[question_id] = {
                "reason": CHANGED_CONTENT,
                "record": copy.deepcopy(record),
                "fingerprint": stored_fp,
            }
            continue
        bound_records[question_id] = copy.deepcopy(record)
        bound_fingerprints[question_id] = current_fp

    history, history_quarantine = migrate_legacy_history_events(list(migrated.get("history") or []), materialized)
    stamped_history: list[dict[str, Any]] = []
    for event in history:
        row = copy.deepcopy(event)
        question_id = history_event_question_id(row)
        event_fp = str(row.get("question_content_fingerprint") or "").strip()
        if question_id and question_id in current_fingerprints and not event_fp and (
            first_bind or question_id in bound_fingerprints
        ):
            row["question_content_fingerprint"] = current_fingerprints[question_id]
            event_fp = current_fingerprints[question_id]
        if question_id and question_id in current_fingerprints and event_fp == current_fingerprints[question_id]:
            row["fingerprint_schema_version"] = FINGERPRINT_SCHEMA_VERSION
            row["fingerprint_domain"] = RUNTIME_FINGERPRINT_DOMAIN
            row["fingerprint_algorithm"] = FINGERPRINT_ALGORITHM
            row["loader_contract_version"] = RUNTIME_LOADER_CONTRACT_VERSION
            if current_bank_node_id:
                row["bank_node_id"] = current_bank_node_id
        stamped_history.append(row)

    migrated["questions"] = bound_records
    migrated["history"] = stamped_history
    migrated["progress_content_epoch_version"] = PROGRESS_CONTENT_EPOCH_VERSION
    migrated["fingerprint_schema_version"] = FINGERPRINT_SCHEMA_VERSION
    migrated["fingerprint_domain"] = RUNTIME_FINGERPRINT_DOMAIN
    migrated["fingerprint_algorithm"] = FINGERPRINT_ALGORITHM
    migrated["loader_contract_version"] = RUNTIME_LOADER_CONTRACT_VERSION
    if current_bank_node_id:
        migrated["bank_node_id"] = current_bank_node_id
    else:
        migrated.pop("bank_node_id", None)
    migrated["bank_fingerprint"] = current_bank_fingerprint
    migrated["question_content_fingerprints"] = bound_fingerprints
    if quarantined:
        migrated["quarantined_questions"] = quarantined
    if history_quarantine:
        migrated["quarantined_history"] = history_quarantine
    return migrated, True


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
