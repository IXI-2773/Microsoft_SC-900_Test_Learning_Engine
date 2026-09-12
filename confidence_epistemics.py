from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable, Mapping, MutableMapping
from datetime import date, timedelta
from typing import Any

CONFIDENCE_UNKNOWN = "Unknown"
OBSERVED_CONFIDENCE_OPTIONS = ("Sure", "Unsure", "Guessed")
CANONICAL_CONFIDENCE_STATES = ("Sure", "Unsure", "Guessed", CONFIDENCE_UNKNOWN)
ANSWER_EVENT_ID_PREFIX = "ae:"
INVALID_OBSERVED_CONFIDENCE = "INVALID_OBSERVED_CONFIDENCE"
MISSING_ANSWER_EVENT_ID = "MISSING_ANSWER_EVENT_ID"


class InvalidObservedConfidence(ValueError):
    pass


class MissingAnswerEventId(ValueError):
    pass


def normalize_confidence(value) -> str:
    raw = str(value or "").strip()
    if not raw:
        return CONFIDENCE_UNKNOWN
    titled = raw.title()
    if titled in OBSERVED_CONFIDENCE_OPTIONS:
        return titled
    if titled == CONFIDENCE_UNKNOWN or raw == CONFIDENCE_UNKNOWN:
        return CONFIDENCE_UNKNOWN
    return CONFIDENCE_UNKNOWN


def require_observed_confidence(value) -> str:
    titled = str(value or "").strip().title()
    if titled not in OBSERVED_CONFIDENCE_OPTIONS:
        raise InvalidObservedConfidence(INVALID_OBSERVED_CONFIDENCE)
    return titled


def is_observed_confidence(value) -> bool:
    return str(value or "").strip().title() in OBSERVED_CONFIDENCE_OPTIONS


def infer_miss_reason_from_confidence(confidence, is_correct) -> str:
    if is_correct:
        return ""
    observed = str(confidence or "").strip().title()
    if observed == "Guessed":
        return "Did not know"
    if observed == "Unsure":
        return "Narrowed to two"
    if observed == "Sure":
        return "Misread"
    return ""


def classify_recall_failure(is_correct: bool, confidence="", miss_reason="") -> str:
    confidence = str(confidence or "").strip()
    miss_reason = str(miss_reason or "").strip()
    if is_correct:
        if confidence == "Guessed":
            return "Recognition without recall"
        if confidence == "Unsure":
            return "Fragile retrieval"
        return ""
    if miss_reason == "Did not know" or confidence == "Guessed":
        return "Blank recall"
    if miss_reason in ("Narrowed to two", "Changed answer") or confidence == "Unsure":
        return "Concept interference"
    if miss_reason == "Misread" or confidence == "Sure":
        return "Cue / wording miss"
    return "Unclassified miss"


def unobserved_feedback(is_correct: bool) -> dict[str, str]:
    return {
        "confidence": CONFIDENCE_UNKNOWN,
        "miss_reason": infer_miss_reason_from_confidence(CONFIDENCE_UNKNOWN, is_correct),
        "recall_failure": classify_recall_failure(is_correct, CONFIDENCE_UNKNOWN, ""),
    }


def new_answer_event_id() -> str:
    return ANSWER_EVENT_ID_PREFIX + uuid.uuid4().hex


def deterministic_legacy_answer_event_id(
    *,
    question_id: str,
    at: str,
    selected: Iterable[str] | None,
    correct: bool,
    ordinal: int,
) -> str:
    selected_text = ",".join(str(letter) for letter in (selected or []))
    material = f"{question_id}|{at}|{selected_text}|{int(bool(correct))}|{int(ordinal)}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return ANSWER_EVENT_ID_PREFIX + digest


def _question_id_of(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    return str(row.get("question_id") or row.get("id") or "").strip()


def _unbound(row: Mapping[str, Any] | None) -> bool:
    return isinstance(row, Mapping) and not str(row.get("answer_event_id") or "").strip()


def bind_legacy_answer_event_ids(
    *,
    runtime_questions: Iterable[MutableMapping[str, Any]],
    session_history: Iterable[MutableMapping[str, Any]],
    progress_history: Iterable[MutableMapping[str, Any]],
) -> dict[str, Any]:
    runtime_questions = list(runtime_questions or [])
    session_history = list(session_history or [])
    progress_history = list(progress_history or [])
    bound = 0
    ambiguous = False
    for question in runtime_questions:
        if not question.get("answered") or not _unbound(question):
            continue
        question_id = _question_id_of(question)
        if not question_id:
            ambiguous = True
            continue
        session_matches = [
            event for event in session_history if _unbound(event) and _question_id_of(event) == question_id
        ]
        progress_matches = [
            event for event in progress_history if _unbound(event) and _question_id_of(event) == question_id
        ]
        if len(session_matches) > 1 or len(progress_matches) > 1:
            ambiguous = True
            continue
        if len(session_matches) == 0 and len(progress_matches) == 0:
            continue
        if len(session_matches) == 1 and len(progress_matches) not in (0, 1):
            ambiguous = True
            continue
        if len(progress_matches) == 1 and len(session_matches) not in (0, 1):
            ambiguous = True
            continue
        session_event = session_matches[0] if session_matches else None
        progress_event = progress_matches[0] if progress_matches else None
        selected = list(question.get("selected") or (session_event or {}).get("selected") or [])
        correct = bool(
            question.get("last_correct")
            if question.get("last_correct") is not None
            else (session_event or progress_event or {}).get("correct")
        )
        at = str((progress_event or {}).get("at") or (session_event or {}).get("at") or "")
        event_id = deterministic_legacy_answer_event_id(
            question_id=question_id,
            at=at,
            selected=selected,
            correct=correct,
            ordinal=0,
        )
        question["answer_event_id"] = event_id
        if session_event is not None:
            session_event["answer_event_id"] = event_id
        if progress_event is not None:
            progress_event["answer_event_id"] = event_id
        bound += 1
    return {"bound": bound, "ambiguous": ambiguous}


def _event_sort_key(event: Mapping[str, Any]) -> tuple[str, str]:
    return (str(event.get("at") or ""), str(event.get("answer_event_id") or ""))


def rebuild_confidence_counts(events: Iterable[Mapping[str, Any]] | None) -> dict[str, int]:
    counts = {option: 0 for option in CANONICAL_CONFIDENCE_STATES}
    for event in events or []:
        confidence = normalize_confidence(event.get("confidence"))
        counts[confidence] = int(counts.get(confidence, 0)) + 1
    return counts


def rebuild_miss_reason_counts(events: Iterable[Mapping[str, Any]] | None) -> dict[str, int]:
    from progress_store import MISS_REASON_OPTIONS

    counts = {option: 0 for option in MISS_REASON_OPTIONS}
    for event in events or []:
        if event.get("correct"):
            continue
        reason = str(event.get("miss_reason") or "").strip()
        if reason:
            counts[reason] = int(counts.get(reason, 0)) + 1
    return counts


def rebuild_learner_memory_from_history(events: Iterable[Mapping[str, Any]] | None) -> dict[str, Any]:
    from progress_store import LEARNER_MEMORY_DEFAULT, review_interval_for_streak, update_learner_memory

    memory = dict(LEARNER_MEMORY_DEFAULT)
    correct_streak = 0
    wrong_count = 0
    for event in sorted(list(events or []), key=_event_sort_key):
        correct = bool(event.get("correct"))
        seen_on = str(event.get("day") or str(event.get("at") or "")[:10] or "")
        memory = update_learner_memory(
            memory,
            correct,
            confidence=normalize_confidence(event.get("confidence")),
            miss_reason=str(event.get("miss_reason") or ""),
            effective_response_seconds=float(
                event.get("effective_response_seconds", event.get("response_seconds", 0.0)) or 0.0
            ),
            session_tag=str(event.get("session_tag") or ""),
            recall_failure=str(event.get("recall_failure") or ""),
            seen_on=seen_on or None,
        )
        if correct:
            correct_streak += 1
        else:
            wrong_count += 1
            correct_streak = 0
        if correct and wrong_count > 0 and correct_streak <= 2:
            recovery_days = review_interval_for_streak(correct_streak)
            if recovery_days > 0 and seen_on:
                recovery_day = date.fromisoformat(seen_on)
                memory["next_review_at"] = (recovery_day + timedelta(days=recovery_days)).isoformat()
    return memory
