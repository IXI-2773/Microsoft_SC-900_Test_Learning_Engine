from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from content_revision_explanation_authority import (
    MANIFEST_KIND,
    AdmittedExplanationRevision,
    ExplanationFailureReason,
)
from content_revision_migration import MigrationFailureReason, MigrationStatus, PayloadMigrationResult
from question_identity import (
    canonical_question_id,
    history_event_matches_question,
    history_event_question_id,
    question_content_fingerprint,
)
from session_identity import canonical_session_signature, ordered_question_ids
from session_store import migrate_session_snapshot

EXPLANATION_MIGRATION_KIND = "sc900_content_revision_explanation_migration_v2"


class ContentExplanationMigrationError(ValueError):
    def __init__(
        self,
        reason: ExplanationFailureReason | MigrationFailureReason,
        detail: str = "",
    ) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason.value if not detail else f"{reason.value}: {detail}")


def _require_revision(revision: Any) -> AdmittedExplanationRevision:
    if not isinstance(revision, AdmittedExplanationRevision) or revision.manifest_kind != MANIFEST_KIND:
        raise ContentExplanationMigrationError(ExplanationFailureReason.AUTHORITY_KIND_MISMATCH)
    return revision


def derive_explanation_migration_id(revision: AdmittedExplanationRevision) -> str:
    revision = _require_revision(revision)
    payload = {
        "kind": EXPLANATION_MIGRATION_KIND,
        "manifest_sha256": revision.manifest_sha256,
        "source_bank_content_fingerprint": revision.source_bank_content_fingerprint,
        "target_bank_content_fingerprint": revision.target_bank_content_fingerprint,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def accepted_explanation_migration_lineage_identities(
    revision: AdmittedExplanationRevision,
) -> frozenset[tuple[str, str]]:
    revision = _require_revision(revision)
    return frozenset({(revision.manifest_sha256, derive_explanation_migration_id(revision))})


def _target_index(
    questions: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {canonical_question_id(question): question for question in questions}


def _lineage_row(
    question_id: str,
    from_fp: str,
    to_fp: str,
    revision: AdmittedExplanationRevision,
    migrated_at: str,
    migration_id: str,
) -> dict[str, str]:
    return {
        "question_id": question_id,
        "from_fingerprint": from_fp,
        "to_fingerprint": to_fp,
        "manifest_sha256": revision.manifest_sha256,
        "migration_id": migration_id,
        "migrated_at": migrated_at,
    }


def _require_progress_shape(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload.get("history"), list):
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "history")
    if not isinstance(payload.get("questions"), Mapping) or not isinstance(
        payload.get("question_content_fingerprints"), Mapping
    ):
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    if "content_revision_lineage" in payload and not isinstance(payload.get("content_revision_lineage"), list):
        raise ContentExplanationMigrationError(
            MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "content_revision_lineage"
        )


def _verify_target_progress(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedExplanationRevision,
    migrated_at: str,
    migration_id: str,
) -> PayloadMigrationResult:
    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    if not isinstance(records, Mapping) or not isinstance(stored_fps, Mapping):
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    target_index = _target_index(target_questions)
    edges = {edge.question_id: edge for edge in revision.edges}
    for question_id in records:
        qid = str(question_id)
        if qid not in target_index:
            raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        target_fp = question_content_fingerprint(target_index[qid])
        stored_fp = str(stored_fps.get(qid) or "").strip()
        if stored_fp != target_fp:
            raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)
        if qid in edges and stored_fp != edges[qid].to_content_fingerprint:
            raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)

    lineage = payload.get("content_revision_lineage") or []
    if not isinstance(lineage, list):
        raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT)
    actual = {
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
    for qid in records:
        qid = str(qid)
        edge = edges.get(qid)
        if edge is None:
            continue
        expected = (
            qid,
            edge.from_content_fingerprint,
            edge.to_content_fingerprint,
            revision.manifest_sha256,
            migration_id,
        )
        if expected not in actual:
            raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)
    return PayloadMigrationResult(
        copy.deepcopy(dict(payload)),
        False,
        MigrationStatus.MIGRATION_ALREADY_APPLIED,
        migration_id,
    )


def migrate_explanation_progress_payload(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedExplanationRevision,
    migrated_at: str,
) -> PayloadMigrationResult:
    revision = _require_revision(revision)
    if not isinstance(payload, Mapping):
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    _require_progress_shape(payload)
    migration_id = derive_explanation_migration_id(revision)
    bank_fp = str(payload.get("bank_fingerprint") or "").strip()
    if bank_fp == revision.target_bank_content_fingerprint:
        return _verify_target_progress(payload, target_questions, revision, migrated_at, migration_id)
    if bank_fp != revision.source_bank_content_fingerprint:
        raise ContentExplanationMigrationError(MigrationFailureReason.SOURCE_BANK_MISMATCH, bank_fp)

    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    assert isinstance(records, Mapping) and isinstance(stored_fps, Mapping)
    target_index = _target_index(target_questions)
    edges = {edge.question_id: edge for edge in revision.edges}
    new_fps: dict[str, str] = {}
    new_lineage: list[dict[str, str]] = []

    for question_id in records:
        qid = str(question_id)
        if qid not in target_index:
            raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        stored_fp = str(stored_fps.get(qid) or "").strip()
        target_fp = question_content_fingerprint(target_index[qid])
        edge = edges.get(qid)
        if edge is None:
            if stored_fp != target_fp:
                raise ContentExplanationMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
            new_fps[qid] = stored_fp
            continue
        if stored_fp != edge.from_content_fingerprint:
            raise ContentExplanationMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
        if target_fp != edge.to_content_fingerprint or not revision.permits_fingerprint_transition(
            qid, stored_fp, target_fp
        ):
            raise ContentExplanationMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, qid)
        new_fps[qid] = edge.to_content_fingerprint
        new_lineage.append(
            _lineage_row(
                qid,
                edge.from_content_fingerprint,
                edge.to_content_fingerprint,
                revision,
                migrated_at,
                migration_id,
            )
        )

    migrated = copy.deepcopy(dict(payload))
    migrated["questions"] = copy.deepcopy(dict(records))
    migrated["question_content_fingerprints"] = new_fps
    migrated["bank_fingerprint"] = revision.target_bank_content_fingerprint
    migrated["history"] = copy.deepcopy(list(payload["history"]))
    existing_lineage = payload.get("content_revision_lineage") or []
    if not isinstance(existing_lineage, list):
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    migrated["content_revision_lineage"] = copy.deepcopy(existing_lineage) + new_lineage
    return PayloadMigrationResult(migrated, True, MigrationStatus.APPLIED, migration_id)


def migrate_explanation_session_payload(
    saved: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedExplanationRevision,
    target_bank_file: str | Path,
    *,
    source_questions: Sequence[Mapping[str, Any]] | None = None,
) -> PayloadMigrationResult:
    revision = _require_revision(revision)
    if not isinstance(saved, Mapping):
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION)
    saved_fp = str(saved.get("bank_fingerprint") or "").strip()
    if saved_fp != revision.source_bank_content_fingerprint:
        raise ContentExplanationMigrationError(MigrationFailureReason.SOURCE_BANK_MISMATCH, saved_fp)

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
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION, str(exc)) from exc

    target_index = _target_index(target_questions)
    source_index = _target_index(source_questions) if source_questions is not None else {}
    edges = {edge.question_id: edge for edge in revision.edges}
    referenced_ids = list(validated.get("question_ids") or []) + list(validated.get("restore_question_ids") or [])
    for qid in referenced_ids:
        if qid not in target_index:
            raise ContentExplanationMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        target_fp = question_content_fingerprint(target_index[qid])
        edge = edges.get(qid)
        if edge is not None and target_fp != edge.to_content_fingerprint:
            raise ContentExplanationMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, qid)
        if qid in source_index:
            source_fp = question_content_fingerprint(source_index[qid])
            if edge is None and source_fp != target_fp:
                raise ContentExplanationMigrationError(MigrationFailureReason.CHANGED_QUESTION_MISSING_EDGE, qid)
            if edge is not None and source_fp != edge.from_content_fingerprint:
                raise ContentExplanationMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)

    migrated = copy.deepcopy(dict(validated))
    # FULL_CONTINUITY_EXPLANATION_ONLY: answer state and session history are preserved
    # exactly; only active bank identity/signatures are rebound to the admitted target.
    migrated["answers"] = copy.deepcopy(list(validated.get("answers") or []))
    migrated["session_answer_history"] = copy.deepcopy(list(validated.get("session_answer_history") or []))
    migrated["bank_file"] = str(target_bank_file)
    migrated["bank_fingerprint"] = revision.target_bank_content_fingerprint
    migrated["session_signature"] = canonical_session_signature(
        mode,
        revision.target_bank_content_fingerprint,
        list(migrated.get("question_ids") or []),
    )
    migrated["restore_signature"] = canonical_session_signature(
        mode,
        revision.target_bank_content_fingerprint,
        list(migrated.get("restore_question_ids") or []),
    )
    try:
        target_validated = migrate_session_snapshot(
            migrated,
            mode,
            list(migrated.get("question_numbers") or []),
            bank_fingerprint=revision.target_bank_content_fingerprint,
            question_ids=list(migrated.get("question_ids") or []),
            restore_question_ids=list(migrated.get("restore_question_ids") or []),
            available_question_ids=ordered_question_ids(target_questions),
        )
    except ValueError as exc:
        raise ContentExplanationMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION, str(exc)) from exc
    return PayloadMigrationResult(
        dict(target_validated),
        True,
        MigrationStatus.APPLIED,
        derive_explanation_migration_id(revision),
    )


def history_event_matches_explanation_revision(
    event: Mapping[str, Any] | None,
    question: Mapping[str, Any] | None,
    revision: AdmittedExplanationRevision | None,
) -> bool:
    if history_event_matches_question(event, question):
        return True
    if revision is None or not isinstance(event, Mapping) or not isinstance(question, Mapping):
        return False
    event_id = history_event_question_id(event)
    qid = canonical_question_id(question)
    event_fp = str(event.get("question_content_fingerprint") or "").strip()
    if not event_id or event_id != qid or not event_fp:
        return False
    current_fp = question_content_fingerprint(question)
    return revision.permits_fingerprint_transition(qid, event_fp, current_fp)


def history_events_for_question_explanation_revision_aware(
    history_map: Mapping[str, list[Mapping[str, Any]]],
    question: Mapping[str, Any] | None,
    revision: AdmittedExplanationRevision | None,
) -> list[Mapping[str, Any]]:
    qid = canonical_question_id(question)
    if not qid:
        return []
    return [
        event
        for event in history_map.get(qid, [])
        if history_event_matches_explanation_revision(event, question, revision)
    ]
