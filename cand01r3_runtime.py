from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from cand01r3_partition import (
    EXPECTED_COMPILED_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_SEMANTIC_AUDIT_SHA256,
    EXPECTED_STORE_SHA256,
    INTENDED_USE_MEASUREMENT,
    INTENDED_USE_TRAINING,
    PARTITION_EPOCH,
    ROLE_PROBE,
    RuntimeAuthority,
    canonical_question_id,
    filter_questions,
    load_runtime_authority,
    partition_eligibility,
)

POLICY_SMART_PRACTICE = "SMART_PRACTICE_CHAMPION"
POLICY_RRC1 = "RRC_1_CHALLENGER"
POLICY_MEASUREMENT = "PROBE_MEASUREMENT"
DEFAULT_LEARNER_ID = "local-single-user"


class Cand01R3AuthorityError(RuntimeError):
    pass


@dataclass
class Cand01R3RuntimeContext:
    active: bool = False
    partition_epoch: str = ""
    manifest_sha256: str = ""
    store_sha256: str = ""
    semantic_audit_sha256: str = ""
    compiled_sha256: str = ""
    policy_id: str = ""
    experiment_id: str = ""
    evaluation_epoch: str = ""
    candidate_bank_identity: str = ""
    intended_use: str = INTENDED_USE_TRAINING
    learner_id: str = DEFAULT_LEARNER_ID


@dataclass
class RestoreResult:
    accepted: bool
    reason: str
    questions: list[Any] = field(default_factory=list)


_CONTEXT = Cand01R3RuntimeContext()
_AUTHORITY: RuntimeAuthority | None = None


def get_context() -> Cand01R3RuntimeContext:
    return _CONTEXT


def current_authority() -> RuntimeAuthority | None:
    return _AUTHORITY


def is_cand01r3_active() -> bool:
    return bool(_CONTEXT.active)


def reset_cand01r3_runtime() -> None:
    global _CONTEXT, _AUTHORITY
    _CONTEXT = Cand01R3RuntimeContext()
    _AUTHORITY = None


def activate_cand01r3_experiment(
    *,
    policy_id: str,
    experiment_id: str,
    evaluation_epoch: str = "eval-1",
    intended_use: str = INTENDED_USE_TRAINING,
    authority: RuntimeAuthority | None = None,
    learner_id: str = DEFAULT_LEARNER_ID,
) -> Cand01R3RuntimeContext:
    global _CONTEXT, _AUTHORITY
    loaded = authority if authority is not None else load_runtime_authority()
    if not loaded.valid:
        reset_cand01r3_runtime()
        raise Cand01R3AuthorityError(loaded.reason)
    _AUTHORITY = loaded
    _CONTEXT = Cand01R3RuntimeContext(
        active=True,
        partition_epoch=loaded.partition_epoch or PARTITION_EPOCH,
        manifest_sha256=loaded.manifest_sha256 or EXPECTED_MANIFEST_SHA256,
        store_sha256=loaded.store_sha256 or EXPECTED_STORE_SHA256,
        semantic_audit_sha256=loaded.semantic_audit_sha256 or EXPECTED_SEMANTIC_AUDIT_SHA256,
        compiled_sha256=loaded.compiled_sha256 or EXPECTED_COMPILED_SHA256,
        policy_id=policy_id,
        experiment_id=experiment_id,
        evaluation_epoch=evaluation_epoch,
        candidate_bank_identity=loaded.compiled_sha256 or EXPECTED_COMPILED_SHA256,
        intended_use=intended_use or INTENDED_USE_TRAINING,
        learner_id=learner_id or DEFAULT_LEARNER_ID,
    )
    return _CONTEXT


def deactivate_cand01r3_experiment() -> None:
    reset_cand01r3_runtime()


def persistable_authority_metadata() -> dict[str, str]:
    context = get_context()
    return {
        "partition_epoch": context.partition_epoch,
        "manifest_sha256": context.manifest_sha256,
        "store_sha256": context.store_sha256,
        "semantic_audit_sha256": context.semantic_audit_sha256,
        "policy_id": context.policy_id,
        "experiment_id": context.experiment_id,
        "evaluation_epoch": context.evaluation_epoch,
        "candidate_bank_identity": context.candidate_bank_identity,
        "intended_use": context.intended_use,
        "learner_id": context.learner_id,
    }


def partition_cache_identity() -> tuple[Any, ...]:
    if not is_cand01r3_active():
        return ("inactive",)
    context = get_context()
    return (
        context.partition_epoch,
        context.manifest_sha256,
        context.store_sha256,
        context.semantic_audit_sha256,
        context.experiment_id,
        context.evaluation_epoch,
        context.policy_id,
        context.intended_use,
    )


def _active_intended_use(stage: str | None = None) -> str:
    if stage == "MEASUREMENT" or get_context().intended_use == INTENDED_USE_MEASUREMENT:
        return INTENDED_USE_MEASUREMENT
    return INTENDED_USE_TRAINING


def is_measurement_answer_mode() -> bool:
    return bool(is_cand01r3_active() and get_context().intended_use == INTENDED_USE_MEASUREMENT)


def _todays_measurement_probe_ids() -> set[str] | None:
    try:
        from cand01r3_protocol import is_measurement_active, todays_scheduled_probe_ids
    except ImportError:
        return None
    if not is_measurement_active():
        return None
    if get_context().intended_use != INTENDED_USE_MEASUREMENT:
        return None
    return todays_scheduled_probe_ids()


def _todays_measurement_probe_order() -> list[str] | None:
    try:
        from cand01r3_protocol import current_measurement_session, ordered_scheduled_probe_ids_for_day
    except ImportError:
        return None
    session = current_measurement_session()
    if not is_measurement_answer_mode() or session.current_scheduled_day is None:
        return None
    return ordered_scheduled_probe_ids_for_day(int(session.current_scheduled_day))


def filter_training_questions(questions: Iterable[Mapping[str, Any]] | None, stage: str | None = None) -> list[Any]:
    pool = list(questions or [])
    if not is_cand01r3_active():
        return pool
    measurement_ids = _todays_measurement_probe_ids()
    intended = _active_intended_use(stage)
    if measurement_ids is not None and intended == INTENDED_USE_MEASUREMENT:
        probes = filter_questions(pool, INTENDED_USE_MEASUREMENT, current_authority())
        by_id = {canonical_question_id(question): question for question in probes}
        order = _todays_measurement_probe_order() or sorted(measurement_ids)
        return [by_id[question_id] for question_id in order if question_id in by_id]
    if intended != INTENDED_USE_TRAINING:
        return filter_questions(pool, intended, current_authority())
    return filter_questions(pool, INTENDED_USE_TRAINING, current_authority())


def derived_training_questions(questions: Iterable[Mapping[str, Any]] | None, stage: str) -> list[Any]:
    return filter_training_questions(questions, stage=stage)


def revalidate_training_question(question: Mapping[str, Any], action: str = "RENDER") -> Any:
    from cand01r3_partition import EligibilityDecision

    if not is_cand01r3_active():
        return EligibilityDecision(role="TRAIN", reason="INACTIVE", question_id=canonical_question_id(question))
    intended = (
        INTENDED_USE_MEASUREMENT
        if action == "MEASUREMENT" or get_context().intended_use == INTENDED_USE_MEASUREMENT
        else INTENDED_USE_TRAINING
    )
    decision = partition_eligibility(question, intended, current_authority())
    measurement_ids = _todays_measurement_probe_ids()
    if intended == INTENDED_USE_MEASUREMENT and measurement_ids is not None:
        question_id = canonical_question_id(question)
        if question_id not in measurement_ids:
            return EligibilityDecision(
                role="NOT_ELIGIBLE",
                reason="WRONG_MEASUREMENT_DAY",
                question_id=question_id,
            )
    return decision


def training_source_questions(questions: Iterable[Mapping[str, Any]] | None) -> list[Any]:
    return filter_training_questions(questions)


def _snapshot_metadata(snapshot: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(snapshot, Mapping):
        return None
    raw = snapshot.get("cand01r3")
    return raw if isinstance(raw, Mapping) else None


def restore_experimental_session(
    questions: Iterable[Mapping[str, Any]],
    snapshot: Mapping[str, Any] | None,
) -> RestoreResult:
    pool = list(questions or [])
    metadata = _snapshot_metadata(snapshot)
    if metadata is None:
        if not is_cand01r3_active():
            requested = snapshot.get("question_ids") if isinstance(snapshot, Mapping) else None
            if not requested:
                requested = snapshot.get("question_numbers") if isinstance(snapshot, Mapping) else None
            if requested:
                wanted = {str(item) for item in requested}
                restored = [
                    question
                    for question in pool
                    if canonical_question_id(question) in wanted or str(question.get("question_number")) in wanted
                ]
                return RestoreResult(accepted=True, reason="NORMAL", questions=restored or pool)
            return RestoreResult(accepted=True, reason="NORMAL", questions=pool)
        return RestoreResult(accepted=False, reason="STALE_AUTHORITY", questions=[])
    if not is_cand01r3_active():
        return RestoreResult(accepted=False, reason="STALE_AUTHORITY", questions=[])
    context = get_context()
    expected = {
        "partition_epoch": context.partition_epoch,
        "manifest_sha256": context.manifest_sha256,
        "store_sha256": context.store_sha256,
        "semantic_audit_sha256": context.semantic_audit_sha256,
    }
    for key, value in expected.items():
        if str(metadata.get(key) or "") != str(value):
            return RestoreResult(accepted=False, reason="STALE_AUTHORITY", questions=[])
    requested_ids = [str(item) for item in (snapshot or {}).get("question_ids") or []]
    source = pool
    if requested_ids:
        wanted = set(requested_ids)
        source = [question for question in pool if canonical_question_id(question) in wanted]
    if context.intended_use == INTENDED_USE_MEASUREMENT:
        eligible = filter_training_questions(pool, stage="MEASUREMENT")
        expected_ids = [canonical_question_id(question) for question in eligible]
        if requested_ids and requested_ids != expected_ids:
            return RestoreResult(accepted=False, reason="STALE_MEASUREMENT_SESSION", questions=[])
        return RestoreResult(accepted=True, reason="REVALIDATED_MEASUREMENT", questions=eligible)
    eligible = filter_questions(source, context.intended_use or INTENDED_USE_TRAINING, current_authority())
    return RestoreResult(accepted=True, reason="REVALIDATED", questions=eligible)


def _is_probe_question(question_id: str) -> bool:
    authority = current_authority()
    if authority is None:
        return False
    item = authority.items.get(question_id) or {}
    return item.get("role") == ROLE_PROBE


def is_measurement_probe_question(question: Mapping[str, Any] | str) -> bool:
    return _is_probe_question(canonical_question_id(question))


def _redacted_probe_row(row: Mapping[str, Any], question_id: str) -> dict[str, Any]:
    status = str(row.get("measurement_status") or row.get("status") or ("RECORDED" if row.get("answered") else "PENDING"))
    return {
        "question_id": question_id,
        "scheduled_day": row.get("scheduled_day"),
        "status": status,
        "observed": bool(row.get("observed", row.get("answered", status == "RECORDED"))),
        "redacted": True,
    }


def sanitize_learner_export(payload: Mapping[str, Any]) -> dict[str, Any]:
    cloned = dict(payload)
    if not is_cand01r3_active():
        return cloned
    history = cloned.get("history")
    if isinstance(history, list):
        redacted_rows = []
        for row in history:
            if not isinstance(row, Mapping):
                redacted_rows.append(row)
                continue
            question_id = canonical_question_id(row)
            if not _is_probe_question(question_id):
                redacted_rows.append(dict(row))
                continue
            redacted_rows.append(_redacted_probe_row(row, question_id))
        cloned["history"] = redacted_rows
    return cloned


def sanitize_history_event(event: Mapping[str, Any], question: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(event)
    if not is_cand01r3_active():
        return payload
    question_id = canonical_question_id(question or event)
    if not _is_probe_question(question_id):
        return payload
    return _redacted_probe_row(payload, question_id)


def sanitize_measurement_answer_state(question: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(state)
    if not is_cand01r3_active() or not is_measurement_probe_question(question):
        return payload
    return {
        "answered": bool(payload.get("answered")),
        "selected": [],
        "pending": [],
        "flagged": bool(payload.get("flagged")),
        "suspended": bool(payload.get("suspended")),
        "last_confidence": "",
        "last_miss_reason": "",
        "measurement_status": str(question.get("measurement_status") or ("RECORDED" if payload.get("answered") else "PENDING")),
        "redacted": True,
    }


def authority_matches_context(metadata: Mapping[str, Any] | None) -> bool:
    if not is_cand01r3_active() or not isinstance(metadata, Mapping):
        return False
    context = get_context()
    return (
        str(metadata.get("partition_epoch") or "") == context.partition_epoch
        and str(metadata.get("manifest_sha256") or "") == context.manifest_sha256
        and str(metadata.get("store_sha256") or "") == context.store_sha256
        and str(metadata.get("semantic_audit_sha256") or "") == context.semantic_audit_sha256
    )
