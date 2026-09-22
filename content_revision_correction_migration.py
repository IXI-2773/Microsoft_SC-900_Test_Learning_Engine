from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from content_fingerprint_bridge import RuntimeBoundRevision, bound_migration_id, unwrap_revision
from content_revision_authority import AdmittedRevision
from content_revision_correction_authority import (
    MANIFEST_KIND,
    AdmittedCorrectionRevision,
    CorrectionFailureReason,
)
from content_revision_migration import (
    MigrationFailureReason,
    MigrationStatus,
    PayloadMigrationResult,
)
from progress_store import default_progress_record
from question_identity import (
    canonical_question_id,
    history_event_question_id,
    question_content_fingerprint,
)
from session_identity import canonical_session_signature, ordered_question_ids
from session_models import answer_state_from_question
from session_store import migrate_session_snapshot
from smart_practice_concept_graph import audit_graph, calibrate_edges
from smart_practice_measurement import build_measurement_report, normalize_measurement_store
from smart_practice_question_value import normalize_calibration_store, question_quality_record

CORRECTION_MIGRATION_KIND = "sc900_content_revision_correction_migration_v2"


class ContentCorrectionMigrationError(ValueError):
    def __init__(self, reason: CorrectionFailureReason | MigrationFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason.value if not detail else f"{reason.value}: {detail}"
        super().__init__(message)


def derive_correction_migration_id(revision: AdmittedCorrectionRevision | RuntimeBoundRevision) -> str:
    raw = unwrap_revision(revision)
    payload = {
        "kind": CORRECTION_MIGRATION_KIND,
        "manifest_sha256": raw.manifest_sha256,
        "source_bank_content_fingerprint": raw.source_bank_content_fingerprint,
        "target_bank_content_fingerprint": raw.target_bank_content_fingerprint,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    base = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return bound_migration_id(base, revision)


def _require_correction_revision(revision: Any) -> AdmittedCorrectionRevision | RuntimeBoundRevision:
    raw = unwrap_revision(revision)
    if not isinstance(raw, AdmittedCorrectionRevision) or raw.manifest_kind != MANIFEST_KIND:
        raise ContentCorrectionMigrationError(CorrectionFailureReason.AUTHORITY_KIND_MISMATCH)
    return revision


def _as_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _target_index(questions: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {canonical_question_id(question): question for question in questions}


def _target_numbers(questions: Sequence[Mapping[str, Any]], target_ids: set[str]) -> set[int]:
    numbers: set[int] = set()
    for question_id in target_ids:
        question = _target_index(questions).get(question_id)
        if question is None:
            continue
        try:
            numbers.add(_as_int(question.get("question_number")))
        except (TypeError, ValueError):
            continue
    return numbers


def _event_question_id(event: Mapping[str, Any]) -> str:
    return history_event_question_id(event)


def _event_is_target(event: Mapping[str, Any], target_ids: set[str], target_numbers: set[int]) -> bool:
    question_id = _event_question_id(event)
    if question_id:
        return question_id in target_ids
    try:
        return _as_int(event.get("question_number")) in target_numbers
    except (TypeError, ValueError):
        return False


def _lineage_row(
    question_id: str,
    edge: Any,
    revision: Any,
    migrated_at: str,
    migration_id: str,
) -> dict[str, str]:
    if isinstance(revision, RuntimeBoundRevision):
        raw_edge = revision.artifact_edge(question_id)
        if raw_edge is None:
            raise ContentCorrectionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, question_id)
        edge = raw_edge
    return {
        "question_id": question_id,
        "from_fingerprint": edge.from_content_fingerprint,
        "to_fingerprint": edge.to_content_fingerprint,
        "manifest_sha256": revision.manifest_sha256,
        "migration_id": migration_id,
        "migrated_at": migrated_at,
    }


def _reset_progress_record(existing: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(default_progress_record())
    record["flagged"] = bool(existing.get("flagged"))
    record["suspended"] = bool(existing.get("suspended"))
    return record


def _pristine_session_answer(existing: Mapping[str, Any]) -> dict[str, Any]:
    blank = dict(answer_state_from_question({}))
    blank["question_id"] = str(existing.get("question_id") or "")
    blank["flagged"] = bool(existing.get("flagged"))
    blank["suspended"] = bool(existing.get("suspended"))
    blank["selected"] = []
    blank["pending"] = []
    blank["answered"] = False
    blank["last_confidence"] = ""
    blank["last_miss_reason"] = ""
    blank["last_recall_failure"] = ""
    blank["answer_event_id"] = ""
    blank["recall_ready"] = False
    blank["session_tag"] = ""
    blank["smart_primary_role"] = ""
    blank["smart_selection_reasons"] = []
    blank["smart_utility"] = 0.0
    blank["smart_utility_breakdown"] = {}
    blank["smart_policy_version"] = ""
    blank["smart_policy_id"] = ""
    blank["smart_concept_key"] = ""
    blank["smart_root_cause"] = ""
    blank["smart_root_cause_confidence"] = 0.0
    blank["smart_supporting_concepts"] = []
    blank["smart_graph_version"] = ""
    blank["smart_information_value"] = 0.0
    blank["smart_information_breakdown"] = {}
    blank["smart_question_quality_status"] = ""
    blank["smart_question_quality_confidence"] = 0.0
    blank["smart_graph_bottleneck"] = 0.0
    blank["repair_stage"] = ""
    blank["repair_concept_key"] = ""
    blank["legacy_repair_concept_key"] = ""
    blank["prediction_id"] = ""
    blank["prediction_snapshot"] = {}
    return blank


def _repair_row_is_target(row: Mapping[str, Any], target_ids: set[str], target_numbers: set[int]) -> bool:
    last_id = str(row.get("last_question_id") or "").strip()
    if last_id and last_id in target_ids:
        return True
    try:
        return _as_int(row.get("last_question_number")) in target_numbers
    except (TypeError, ValueError):
        return False


def _prediction_is_target(row: Mapping[str, Any], target_ids: set[str], target_numbers: set[int]) -> bool:
    question_id = str(row.get("question_id") or "").strip()
    if question_id and question_id in target_ids:
        return True
    try:
        return _as_int(row.get("question_number")) in target_numbers
    except (TypeError, ValueError):
        return False


def _reconcile_adaptive_state(
    payload: dict[str, Any],
    *,
    remaining_history: list[Mapping[str, Any]],
    target_questions: Sequence[Mapping[str, Any]],
    target_ids: set[str],
    target_numbers: set[int],
    migrated_at: str,
) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, Mapping):
        return
    meta = dict(meta)
    payload["meta"] = meta
    repair_state = meta.get("repair_state")
    if isinstance(repair_state, Mapping):
        meta["repair_state"] = {
            key: copy.deepcopy(dict(row))
            for key, row in repair_state.items()
            if isinstance(row, Mapping) and not _repair_row_is_target(row, target_ids, target_numbers)
        }
    measurement = meta.get("smart_practice_measurement")
    if isinstance(measurement, Mapping):
        store = normalize_measurement_store(measurement)
        active_policy = copy.deepcopy(store.get("active_policy") or {})
        kept_predictions = {
            key: copy.deepcopy(dict(row))
            for key, row in store.get("predictions", {}).items()
            if isinstance(row, Mapping) and not _prediction_is_target(row, target_ids, target_numbers)
        }
        kept_ids = set(kept_predictions)
        kept_links = {
            key: copy.deepcopy(value) for key, value in store.get("outcome_links", {}).items() if key in kept_ids
        }
        store["predictions"] = kept_predictions
        store["outcome_links"] = kept_links
        store["active_policy"] = active_policy
        store["measurement_reports"] = []
        store["calibration_recommendations"] = []
        build_measurement_report(store, remaining_history, evaluation_at=migrated_at)
        meta["smart_practice_measurement"] = store
    calibration = meta.get("smart_practice_question_calibration")
    if isinstance(calibration, Mapping):
        store = normalize_calibration_store(calibration, created_at=migrated_at)
        quality = {
            key: copy.deepcopy(dict(row))
            for key, row in store.get("question_quality", {}).items()
            if isinstance(row, Mapping)
            and str(row.get("question_id") or "") not in target_ids
            and _as_int(row.get("question_number")) not in target_numbers
            and str(key) not in target_ids
        }
        info_history = {
            key: copy.deepcopy(value)
            for key, value in store.get("information_value_history", {}).items()
            if str(key) not in target_ids
        }
        store["question_quality"] = quality
        store["information_value_history"] = info_history
        graph = meta.get("smart_practice_concept_graph")
        if isinstance(graph, Mapping):
            calibrated_graph, _metrics = calibrate_edges(
                copy.deepcopy(dict(graph)),
                list(remaining_history),
                evaluated_at=migrated_at,
            )
            store["edge_calibration"] = copy.deepcopy(calibrated_graph.get("edges") or {})
            store["graph_audits"] = {migrated_at: audit_graph(graph, questions=list(target_questions))}
        store["last_updated_at"] = migrated_at
        meta["smart_practice_question_calibration"] = store
        for question_id in sorted(set(_target_index(target_questions)) - target_ids):
            question = _target_index(target_questions)[question_id]
            outcomes = [
                event
                for event in remaining_history
                if _event_question_id(event) == question_id
                or _as_int(event.get("question_number")) == _as_int(question.get("question_number"), -2)
            ]
            if not outcomes:
                continue
            record = question_quality_record(question, list(outcomes), evaluated_at=migrated_at)
            store["question_quality"][str(question.get("question_number") or question_id)] = record
    graph = meta.get("smart_practice_concept_graph")
    if isinstance(graph, Mapping):
        graph = copy.deepcopy(dict(graph))
        diagnoses = graph.get("diagnoses")
        if isinstance(diagnoses, Mapping):
            kept = {}
            for key, row in diagnoses.items():
                if not isinstance(row, Mapping):
                    continue
                evidence = row.get("evidence")
                evidence_blob = json.dumps(evidence, ensure_ascii=False, default=str) if evidence is not None else ""
                if any(question_id in evidence_blob for question_id in target_ids):
                    continue
                question_id = str(row.get("question_id") or "").strip()
                if question_id in target_ids:
                    continue
                try:
                    if _as_int(row.get("question_number")) in target_numbers:
                        continue
                except (TypeError, ValueError):
                    pass
                kept[key] = row
            graph["diagnoses"] = kept
        meta["smart_practice_concept_graph"] = graph


def _require_progress_shape(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload.get("history"), list):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "history")
    if not isinstance(payload.get("questions"), Mapping) or not isinstance(
        payload.get("question_content_fingerprints"), Mapping
    ):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    if "quarantined_questions" in payload and not isinstance(payload.get("quarantined_questions"), Mapping):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "quarantined_questions")
    if "content_revision_lineage" in payload and not isinstance(payload.get("content_revision_lineage"), list):
        raise ContentCorrectionMigrationError(
            MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "content_revision_lineage"
        )
    if "quarantined_history" in payload and not isinstance(payload.get("quarantined_history"), list):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "quarantined_history")


def _verify_target_progress(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedCorrectionRevision | RuntimeBoundRevision,
    migrated_at: str,
    migration_id: str,
) -> PayloadMigrationResult:
    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    if not isinstance(records, Mapping) or not isinstance(stored_fps, Mapping):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    target_index = _target_index(target_questions)
    target_fps = {qid: question_content_fingerprint(question) for qid, question in target_index.items()}
    edges = {edge.question_id: edge for edge in revision.edges}
    for question_id in records:
        qid = str(question_id)
        if qid not in target_index:
            raise ContentCorrectionMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        stored_fp = str(stored_fps.get(qid) or "").strip()
        if stored_fp != target_fps[qid]:
            raise ContentCorrectionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)
        edge = edges.get(qid)
        if edge is not None and stored_fp != edge.to_content_fingerprint:
            raise ContentCorrectionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)
    lineage = payload.get("content_revision_lineage") or []
    if not isinstance(lineage, list):
        raise ContentCorrectionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT)
    expected = [_lineage_row(qid, edges[qid], revision, migrated_at, migration_id) for qid in records if qid in edges]
    actual_keys = {
        (
            str(row.get("question_id")),
            str(row.get("from_fingerprint")),
            str(row.get("to_fingerprint")),
            str(row.get("manifest_sha256")),
            str(row.get("migration_id")),
        )
        for row in lineage
        if isinstance(row, Mapping)
    }
    if expected:
        complete = all(
            (
                row["question_id"],
                row["from_fingerprint"],
                row["to_fingerprint"],
                revision.manifest_sha256,
                migration_id,
            )
            in actual_keys
            for row in expected
        )
        if not complete:
            raise ContentCorrectionMigrationError(
                MigrationFailureReason.TARGET_PROGRESS_CONFLICT, expected[0]["question_id"]
            )
    return PayloadMigrationResult(
        copy.deepcopy(dict(payload)), False, MigrationStatus.MIGRATION_ALREADY_APPLIED, migration_id
    )


def migrate_correction_progress_payload(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedCorrectionRevision | AdmittedRevision | RuntimeBoundRevision,
    migrated_at: str,
) -> PayloadMigrationResult:
    if isinstance(revision, AdmittedRevision) and not isinstance(revision, AdmittedCorrectionRevision):
        raise ContentCorrectionMigrationError(CorrectionFailureReason.AUTHORITY_KIND_MISMATCH)
    revision = _require_correction_revision(revision)
    if not isinstance(payload, Mapping):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    _require_progress_shape(payload)
    migration_id = derive_correction_migration_id(revision)
    bank_fp = str(payload.get("bank_fingerprint") or "").strip()
    if bank_fp == revision.target_bank_content_fingerprint:
        return _verify_target_progress(payload, target_questions, revision, migrated_at, migration_id)
    if bank_fp != revision.source_bank_content_fingerprint:
        raise ContentCorrectionMigrationError(MigrationFailureReason.SOURCE_BANK_MISMATCH, bank_fp)
    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    if not isinstance(records, Mapping) or not isinstance(stored_fps, Mapping):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    target_index = _target_index(target_questions)
    target_fps = {qid: question_content_fingerprint(question) for qid, question in target_index.items()}
    edges = {edge.question_id: edge for edge in revision.edges}
    target_ids = set(edges)
    target_numbers = _target_numbers(target_questions, target_ids)
    new_records: dict[str, Any] = {}
    new_fps: dict[str, str] = {}
    new_lineage: list[dict[str, str]] = []
    existing_lineage = payload.get("content_revision_lineage") or []
    if not isinstance(existing_lineage, list):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    for question_id, record in records.items():
        qid = str(question_id)
        if qid not in target_index:
            raise ContentCorrectionMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        stored_fp = str(stored_fps.get(qid) or "").strip()
        target_fp = target_fps[qid]
        edge = edges.get(qid)
        if edge is None:
            if stored_fp != target_fp:
                raise ContentCorrectionMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
            new_records[qid] = copy.deepcopy(dict(record))
            new_fps[qid] = stored_fp
            continue
        if stored_fp == edge.to_content_fingerprint:
            raise ContentCorrectionMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
        if stored_fp and stored_fp != edge.from_content_fingerprint:
            raise ContentCorrectionMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
        if target_fp != edge.to_content_fingerprint or not revision.permits_fingerprint_transition(
            qid, edge.from_content_fingerprint, target_fp
        ):
            raise ContentCorrectionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, qid)
        new_records[qid] = _reset_progress_record(record if isinstance(record, Mapping) else {})
        new_fps[qid] = edge.to_content_fingerprint
        new_lineage.append(_lineage_row(qid, edge, revision, migrated_at, migration_id))
    history = [copy.deepcopy(dict(event)) for event in payload.get("history") or [] if isinstance(event, Mapping)]
    remaining_history: list[Mapping[str, Any]] = []
    quarantined = [
        copy.deepcopy(dict(event)) for event in payload.get("quarantined_history") or [] if isinstance(event, Mapping)
    ]
    for event in history:
        if _event_is_target(event, target_ids, target_numbers):
            quarantined.append(event)
        else:
            remaining_history.append(event)
    migrated = copy.deepcopy(dict(payload))
    migrated["questions"] = new_records
    migrated["question_content_fingerprints"] = new_fps
    migrated["bank_fingerprint"] = revision.target_bank_content_fingerprint
    if isinstance(revision, RuntimeBoundRevision):
        from fingerprint_identity import (
            FINGERPRINT_ALGORITHM,
            FINGERPRINT_SCHEMA_VERSION,
            RUNTIME_FINGERPRINT_DOMAIN,
            RUNTIME_LOADER_CONTRACT_VERSION,
        )
        from question_identity import PROGRESS_CONTENT_EPOCH_VERSION

        migrated["progress_content_epoch_version"] = PROGRESS_CONTENT_EPOCH_VERSION
        migrated["fingerprint_schema_version"] = FINGERPRINT_SCHEMA_VERSION
        migrated["fingerprint_domain"] = RUNTIME_FINGERPRINT_DOMAIN
        migrated["fingerprint_algorithm"] = FINGERPRINT_ALGORITHM
        migrated["loader_contract_version"] = RUNTIME_LOADER_CONTRACT_VERSION
        migrated["bank_node_id"] = revision.target_node.bank_node_id
    migrated["history"] = [dict(event) for event in remaining_history]
    migrated["quarantined_history"] = quarantined
    if "quarantined_questions" in payload:
        migrated["quarantined_questions"] = copy.deepcopy(payload.get("quarantined_questions"))
    migrated["content_revision_lineage"] = copy.deepcopy(list(existing_lineage)) + new_lineage
    _reconcile_adaptive_state(
        migrated,
        remaining_history=remaining_history,
        target_questions=target_questions,
        target_ids=target_ids,
        target_numbers=target_numbers,
        migrated_at=migrated_at,
    )
    return PayloadMigrationResult(migrated, True, MigrationStatus.APPLIED, migration_id)


def migrate_correction_session_payload(
    saved: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedCorrectionRevision | AdmittedRevision | RuntimeBoundRevision,
    target_bank_file: str | Path,
    *,
    source_questions: Sequence[Mapping[str, Any]] | None = None,
) -> PayloadMigrationResult:
    del source_questions

    if isinstance(revision, AdmittedRevision) and not isinstance(revision, AdmittedCorrectionRevision):
        raise ContentCorrectionMigrationError(CorrectionFailureReason.AUTHORITY_KIND_MISMATCH)
    revision = _require_correction_revision(revision)
    if not isinstance(saved, Mapping):
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION)
    saved_fp = str(saved.get("bank_fingerprint") or "").strip()
    if saved_fp == revision.target_bank_content_fingerprint:
        return PayloadMigrationResult(
            copy.deepcopy(dict(saved)),
            False,
            MigrationStatus.MIGRATION_ALREADY_APPLIED,
            derive_correction_migration_id(revision),
        )
    if saved_fp != revision.source_bank_content_fingerprint:
        raise ContentCorrectionMigrationError(MigrationFailureReason.SOURCE_BANK_MISMATCH, saved_fp)
    mode = str(saved.get("mode") or "")
    question_numbers = list(saved.get("question_numbers") or [])
    try:
        validated = migrate_session_snapshot(
            saved,
            mode,
            question_numbers,
            bank_fingerprint=revision.source_bank_content_fingerprint,
            question_ids=list(saved.get("question_ids") or []),
            restore_question_ids=list(saved.get("restore_question_ids") or []),
        )
    except ValueError as exc:
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION, str(exc)) from exc
    target_index = _target_index(target_questions)
    target_fps = {qid: question_content_fingerprint(question) for qid, question in target_index.items()}
    edges = {edge.question_id: edge for edge in revision.edges}
    target_ids = set(edges)
    target_numbers = _target_numbers(target_questions, target_ids)
    referenced_ids = list(validated.get("question_ids") or []) + list(validated.get("restore_question_ids") or [])
    for question_id in referenced_ids:
        if question_id not in target_index:
            raise ContentCorrectionMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, question_id)
        if question_id in edges and target_fps[question_id] != edges[question_id].to_content_fingerprint:
            raise ContentCorrectionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, question_id)
    migrated = copy.deepcopy(dict(validated))
    answers: list[dict[str, Any]] = []
    for row in _as_list(migrated.get("answers")):
        if not isinstance(row, Mapping):
            continue
        updated = copy.deepcopy(dict(row))
        question_id = str(updated.get("question_id") or "")
        if question_id in edges:
            preserved_id = question_id
            flagged = bool(updated.get("flagged"))
            suspended = bool(updated.get("suspended"))
            updated = _pristine_session_answer(updated)
            updated["question_id"] = preserved_id
            updated["flagged"] = flagged
            updated["suspended"] = suspended
        answers.append(updated)
    migrated["answers"] = answers
    remaining_history: list[dict[str, Any]] = []
    archived_history: list[dict[str, Any]] = []
    for event in _as_list(validated.get("session_answer_history")):
        if isinstance(event, Mapping) and _event_is_target(event, target_ids, target_numbers):
            archived_history.append(copy.deepcopy(dict(event)))
            continue
        if isinstance(event, Mapping):
            remaining_history.append(copy.deepcopy(dict(event)))
    migrated["session_answer_history"] = remaining_history
    migrated["archived_source_session_answer_history"] = archived_history
    migrated["bank_file"] = str(target_bank_file)
    migrated["bank_fingerprint"] = revision.target_bank_content_fingerprint
    question_ids = [str(item) for item in _as_list(migrated.get("question_ids"))]
    restore_ids = [str(item) for item in _as_list(migrated.get("restore_question_ids"))]
    migrated["session_signature"] = canonical_session_signature(
        mode, revision.target_bank_content_fingerprint, question_ids
    )
    migrated["restore_signature"] = canonical_session_signature(
        mode, revision.target_bank_content_fingerprint, restore_ids
    )
    try:
        target_validated = dict(
            migrate_session_snapshot(
                migrated,
                mode,
                _as_list(migrated.get("question_numbers")),
                bank_fingerprint=revision.target_bank_content_fingerprint,
                question_ids=question_ids,
                restore_question_ids=restore_ids,
                available_question_ids=ordered_question_ids(target_questions),
            )
        )
    except ValueError as exc:
        raise ContentCorrectionMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION, str(exc)) from exc
    target_validated["archived_source_session_answer_history"] = archived_history
    target_validated["session_answer_history"] = remaining_history
    return PayloadMigrationResult(
        target_validated, True, MigrationStatus.APPLIED, derive_correction_migration_id(revision)
    )
