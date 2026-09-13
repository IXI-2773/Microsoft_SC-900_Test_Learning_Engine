from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from cand01r3_partition import (
    INTENDED_USE_TRAINING,
    ROLE_TRAIN,
    RuntimeAuthority,
    canonical_question_id,
    partition_eligibility,
)
from cand01r3_runtime import POLICY_RRC1, get_context, persistable_authority_metadata
from progress_store import is_active_weak, is_review_due, question_key

CLASS_REPAIR = "REPAIR"
CLASS_REVIEW = "REVIEW"
CLASS_COVERAGE = "COVERAGE"
SERVICE_ORDER = (CLASS_REPAIR, CLASS_REVIEW, CLASS_COVERAGE)


@dataclass
class Rrc1Selection:
    questions: list[dict[str, Any]]
    service_classes: list[str]
    events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    service_log: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def _record_for(question: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    rec = records.get(question_key(question)) or records.get(canonical_question_id(question)) or {}
    return dict(rec)


def classify_question(
    question: Mapping[str, Any],
    record: Mapping[str, Any] | None,
    authority: RuntimeAuthority,
    *,
    on_date=None,
) -> str | None:
    decision = partition_eligibility(question, INTENDED_USE_TRAINING, authority)
    if decision.role != ROLE_TRAIN:
        return None
    rec = dict(record or {})
    if is_active_weak(rec):
        return CLASS_REPAIR
    if is_review_due(rec, on_date=on_date):
        return CLASS_REVIEW
    return CLASS_COVERAGE


def classify_classes(
    questions: Iterable[Mapping[str, Any]],
    records: Mapping[str, Mapping[str, Any]],
    authority: RuntimeAuthority,
    *,
    on_date=None,
) -> dict[str, list[str]]:
    classes: dict[str, list[str]] = {CLASS_REPAIR: [], CLASS_REVIEW: [], CLASS_COVERAGE: []}
    for question in questions:
        class_name = classify_question(question, _record_for(question, records), authority, on_date=on_date)
        if class_name:
            classes[class_name].append(canonical_question_id(question))
    return classes


def _recent_correctness(record: Mapping[str, Any]) -> float:
    attempts = max(0, int(record.get("attempts", 0) or 0))
    correct = max(0, int(record.get("correct_count", 0) or 0))
    if attempts <= 0:
        return 1.0
    return correct / attempts


def _last_seen_key(record: Mapping[str, Any]) -> str:
    return str(record.get("last_seen") or "") or "0000-01-01"


def _due_timestamp(record: Mapping[str, Any]) -> str:
    memory = record.get("learner_memory") or {}
    return str(memory.get("next_review_at") or record.get("next_review") or "9999-12-31")


def _blueprint_deficit(
    question: Mapping[str, Any], questions: Iterable[Mapping[str, Any]], records: Mapping[str, Mapping[str, Any]]
) -> float:
    domain = str(question.get("domain") or "")
    objective = str(question.get("objective") or question.get("objective_code") or "")
    domain_total = 0
    domain_seen = 0
    objective_total = 0
    objective_seen = 0
    for item in questions:
        rec = _record_for(item, records)
        seen = int(rec.get("attempts", 0) or 0) > 0
        if str(item.get("domain") or "") == domain:
            domain_total += 1
            domain_seen += 1 if seen else 0
        if str(item.get("objective") or item.get("objective_code") or "") == objective:
            objective_total += 1
            objective_seen += 1 if seen else 0
    domain_cov = (domain_seen / domain_total) if domain_total else 1.0
    objective_cov = (objective_seen / objective_total) if objective_total else 1.0
    return (1.0 - domain_cov) + (1.0 - objective_cov)


def in_class_order(
    class_name: str,
    questions: list[Mapping[str, Any]],
    records: Mapping[str, Mapping[str, Any]],
    authority: RuntimeAuthority,
    *,
    universe: list[Mapping[str, Any]] | None = None,
) -> list[Any]:
    universe = list(universe or questions)

    def sort_key(question: Mapping[str, Any]) -> tuple:
        rec = _record_for(question, records)
        question_id = canonical_question_id(question)
        if class_name == CLASS_REPAIR:
            return (_recent_correctness(rec), _last_seen_key(rec), question_id)
        if class_name == CLASS_REVIEW:
            return (_due_timestamp(rec), _last_seen_key(rec), question_id)
        unseen = 0 if int(rec.get("attempts", 0) or 0) <= 0 else 1
        deficit = -_blueprint_deficit(question, universe, records)
        return (deficit, unseen, _last_seen_key(rec), question_id)

    return sorted(questions, key=sort_key)


def _service_event(
    question: Mapping[str, Any], class_name: str, record: Mapping[str, Any], authority: RuntimeAuthority
) -> dict[str, Any]:
    context = get_context()
    metadata = persistable_authority_metadata() if context.active else {}
    decision = partition_eligibility(question, INTENDED_USE_TRAINING, authority)
    return {
        "policy_id": context.policy_id or POLICY_RRC1,
        "service_class": class_name,
        "question_id": canonical_question_id(question),
        "semantic_family_id": decision.family_id,
        "domain": question.get("domain"),
        "objective": question.get("objective") or question.get("objective_code"),
        "session_id": context.experiment_id,
        "evaluation_epoch": context.evaluation_epoch,
        "partition_epoch": metadata.get("partition_epoch") or authority.partition_epoch,
        "manifest_sha256": metadata.get("manifest_sha256") or authority.manifest_sha256,
        "weak_state": bool(is_active_weak(record)),
        "due_state": bool(is_review_due(record)),
        "train_exposure_count": int(record.get("attempts", 0) or 0),
        "policy_exposure_dose": 1,
        "queue_age": _due_timestamp(record) if class_name == CLASS_REVIEW else _last_seen_key(record),
        "blueprint_deficit": _blueprint_deficit(question, [question], {question_key(question): record}),
    }


def _fairness_metrics(
    service_log: list[dict[str, Any]], classes: dict[str, list[str]], questions: list[Mapping[str, Any]]
) -> dict[str, Any]:
    class_counts = {name: 0 for name in SERVICE_ORDER}
    for event in service_log:
        class_counts[str(event.get("service_class"))] = class_counts.get(str(event.get("service_class")), 0) + 1
    total = max(1, len(service_log))
    domain_counts: dict[str, int] = {}
    objective_counts: dict[str, int] = {}
    for event in service_log:
        domain = str(event.get("domain") or "")
        objective = str(event.get("objective") or "")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        objective_counts[objective] = objective_counts.get(objective, 0) + 1
    backlog = sum(len(members) for members in classes.values()) - len(service_log)
    dominance = max(class_counts.values()) / total if service_log else 0.0
    return {
        "MAX_SERVICE_DELAY": None,
        "OVERDUE_RATE": None,
        "STARVATION_RATE": None,
        "QUEUE_AGE": None,
        "COVERAGE_DEBT": len(classes.get(CLASS_COVERAGE) or []),
        "DOMAIN_SERVICE_BALANCE": domain_counts,
        "OBJECTIVE_SERVICE_BALANCE": objective_counts,
        "CLASS_SERVICE_SHARE": {name: class_counts[name] / total for name in SERVICE_ORDER},
        "BACKLOG_SIZE": max(0, backlog),
        "SESSION_CLASS_DOMINANCE": dominance,
    }


def select_rrc1_session(
    questions: Iterable[Mapping[str, Any]],
    records: Mapping[str, Mapping[str, Any]],
    authority: RuntimeAuthority,
    session_size: int,
    *,
    on_date=None,
) -> Rrc1Selection:
    universe = [
        question
        for question in questions
        if partition_eligibility(question, INTENDED_USE_TRAINING, authority).role == ROLE_TRAIN
    ]
    buckets: dict[str, list[Any]] = {CLASS_REPAIR: [], CLASS_REVIEW: [], CLASS_COVERAGE: []}
    for question in universe:
        class_name = classify_question(question, _record_for(question, records), authority, on_date=on_date)
        if class_name:
            buckets[class_name].append(question)
    for class_name, members in buckets.items():
        buckets[class_name] = in_class_order(class_name, members, records, authority, universe=universe)
    events: dict[str, list[dict[str, Any]]] = {}
    for class_name in SERVICE_ORDER:
        if not buckets[class_name]:
            events.setdefault("EMPTY_CLASS_SKIP", []).append({"class_name": class_name, "fake_credit": False})
    selected: list[dict[str, Any]] = []
    service_classes: list[str] = []
    service_log: list[dict[str, Any]] = []
    pointers = {name: 0 for name in SERVICE_ORDER}
    while len(selected) < max(0, int(session_size)):
        progressed = False
        for class_name in SERVICE_ORDER:
            index = pointers[class_name]
            members = buckets[class_name]
            if index >= len(members):
                continue
            question = members[index]
            pointers[class_name] = index + 1
            selected.append(dict(question))
            service_classes.append(class_name)
            service_log.append(_service_event(question, class_name, _record_for(question, records), authority))
            progressed = True
            if len(selected) >= session_size:
                break
        if not progressed:
            remaining = [
                question
                for question in in_class_order(CLASS_COVERAGE, universe, records, authority, universe=universe)
                if canonical_question_id(question) not in {canonical_question_id(item) for item in selected}
            ]
            if not remaining:
                break
            question = remaining[0]
            selected.append(dict(question))
            service_classes.append(CLASS_COVERAGE)
            service_log.append(_service_event(question, CLASS_COVERAGE, _record_for(question, records), authority))
    classes = classify_classes(universe, records, authority, on_date=on_date)
    return Rrc1Selection(
        questions=selected,
        service_classes=service_classes,
        events=events,
        service_log=service_log,
        metrics=_fairness_metrics(service_log, classes, universe),
    )
