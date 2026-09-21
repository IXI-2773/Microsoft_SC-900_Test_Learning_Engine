from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from question_identity import canonical_question_id

MINIMUM_SCORE_DELTA_FOR_REPLACEMENT = 5.0
MAX_REPLACEMENTS_PER_ANSWER = 1
PROTECTED_ROLES = ("weak_repair", "due_retention", "blueprint_coverage")


@dataclass(frozen=True)
class OnlineReplacement:
    victim_id: str
    challenger_id: str
    score_delta: float


@dataclass(frozen=True)
class OnlineQueueProposal:
    expected_ids: tuple[str, ...]
    proposed_ids: tuple[str, ...]
    replacement: OnlineReplacement | None
    protected_before: dict[str, int]
    protected_after: dict[str, int]
    policy_id: str
    policy_version: str
    policy_checksum: str
    learner_revision: Any
    builder_context_fingerprint: str
    evaluation_time_key: str


def _score(question: Mapping[str, Any] | None) -> float | None:
    if not question or "smart_utility" not in question:
        return None
    try:
        score = float(question.get("smart_utility"))
    except (TypeError, ValueError):
        return None
    return score if math.isfinite(score) else None


def _required_score(question: Mapping[str, Any] | None) -> float:
    score = _score(question)
    if score is None:
        raise ValueError("INCOMPARABLE_SMART_UTILITY")
    return score


def _role(question: Mapping[str, Any] | None) -> str:
    return str((question or {}).get("smart_primary_role") or "")


def _protected_counts(ids: Sequence[str], scored: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    counts = {role: 0 for role in PROTECTED_ROLES}
    for question_id in ids:
        role = _role(scored.get(question_id))
        if role in counts:
            counts[role] += 1
    return counts


def _preserves(after: Mapping[str, int], before: Mapping[str, int]) -> bool:
    return all(int(after.get(role, 0)) >= int(before.get(role, 0)) for role in PROTECTED_ROLES)


def build_online_queue_proposal(
    session_questions: Sequence[Mapping[str, Any]],
    rescored_universe: Sequence[Mapping[str, Any]],
    *,
    eligible_challenger_ids: set[str],
    current_index: int,
    policy_id: str,
    policy_version: str,
    policy_checksum: str,
    learner_revision: Any,
    builder_context_fingerprint: str,
    evaluation_time_key: str,
    minimum_score_delta: float = MINIMUM_SCORE_DELTA_FOR_REPLACEMENT,
    max_replacements: int = MAX_REPLACEMENTS_PER_ANSWER,
) -> OnlineQueueProposal:
    expected = tuple(canonical_question_id(question) for question in session_questions)
    scored = {
        canonical_question_id(question): question for question in rescored_universe if canonical_question_id(question)
    }
    proposed = list(expected)
    mutable_indices: list[int] = []
    for index, question in enumerate(session_questions):
        if index <= current_index + 1:
            continue
        if question.get("answered") or question.get("flagged") or question.get("suspended"):
            continue
        if str(question.get("session_tag") or "").strip():
            continue
        if str(question.get("repair_stage") or "").strip():
            continue
        question_id = canonical_question_id(question)
        if question_id and question_id in scored and _score(scored.get(question_id)) is not None:
            mutable_indices.append(index)

    mutable_ids = [expected[index] for index in mutable_indices]
    mutable_ids.sort(key=lambda qid: (-_required_score(scored.get(qid)), qid))
    for index, question_id in zip(mutable_indices, mutable_ids, strict=True):
        proposed[index] = question_id

    remaining_ids = list(expected[current_index + 1 :])
    protected_before = _protected_counts(remaining_ids, scored)
    replacement: OnlineReplacement | None = None

    if max_replacements > 0 and mutable_indices:
        session_ids = set(expected)
        challengers = [
            question_id
            for question_id in eligible_challenger_ids
            if question_id in scored and question_id not in session_ids and _score(scored.get(question_id)) is not None
        ]
        challengers.sort(key=lambda qid: (-_required_score(scored[qid]), qid))
        victims = [proposed[index] for index in mutable_indices]
        victims.sort(key=lambda qid: (_required_score(scored.get(qid)), qid))
        for challenger_id in challengers:
            challenger_score = _required_score(scored[challenger_id])
            for victim_id in victims:
                victim_score = _required_score(scored.get(victim_id))
                delta = challenger_score - victim_score
                if delta < float(minimum_score_delta):
                    continue
                trial = list(proposed)
                victim_index = next(
                    (index for index in mutable_indices if trial[index] == victim_id),
                    None,
                )
                if victim_index is None:
                    continue
                trial[victim_index] = challenger_id
                after = _protected_counts(trial[current_index + 1 :], scored)
                if not _preserves(after, protected_before):
                    continue
                replacement = OnlineReplacement(
                    victim_id=victim_id,
                    challenger_id=challenger_id,
                    score_delta=round(delta, 3),
                )
                proposed = trial
                break
            if replacement is not None:
                break

    final_mutable = [proposed[index] for index in mutable_indices]
    final_mutable.sort(key=lambda qid: (-_required_score(scored.get(qid)), qid))
    for index, question_id in zip(mutable_indices, final_mutable, strict=True):
        proposed[index] = question_id
    protected_after = _protected_counts(proposed[current_index + 1 :], scored)
    return OnlineQueueProposal(
        expected_ids=expected,
        proposed_ids=tuple(proposed),
        replacement=replacement,
        protected_before=protected_before,
        protected_after=protected_after,
        policy_id=str(policy_id),
        policy_version=str(policy_version),
        policy_checksum=str(policy_checksum),
        learner_revision=learner_revision,
        builder_context_fingerprint=str(builder_context_fingerprint),
        evaluation_time_key=str(evaluation_time_key),
    )
