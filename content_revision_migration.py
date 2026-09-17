from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from content_revision_authority import AdmittedRevision, RevisionFailureReason, approved_lineage
from question_identity import (
    canonical_question_id,
    history_event_matches_question,
    history_event_question_id,
    question_content_fingerprint,
)


class MigrationStatus(StrEnum):
    APPLIED = "APPLIED"
    MIGRATION_ALREADY_APPLIED = "MIGRATION_ALREADY_APPLIED"


class MigrationFailureReason(StrEnum):
    SOURCE_BANK_MISMATCH = "SOURCE_BANK_MISMATCH"
    SOURCE_PROGRESS_FINGERPRINT_MISMATCH = "SOURCE_PROGRESS_FINGERPRINT_MISMATCH"
    TARGET_QUESTION_MISSING = "TARGET_QUESTION_MISSING"
    UNAUTHORIZED_TRANSITION = "UNAUTHORIZED_TRANSITION"
    TARGET_PROGRESS_CONFLICT = "TARGET_PROGRESS_CONFLICT"
    UNEXPECTED_BANK_FINGERPRINT = "UNEXPECTED_BANK_FINGERPRINT"
    INVALID_PROGRESS_PAYLOAD = "INVALID_PROGRESS_PAYLOAD"
    LINEAGE_INCOMPLETE = "LINEAGE_INCOMPLETE"
    LINEAGE_CONFLICT = "LINEAGE_CONFLICT"


class ContentRevisionMigrationError(ValueError):
    def __init__(self, reason: MigrationFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason.value if not detail else f"{reason.value}: {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PayloadMigrationResult:
    payload: dict[str, Any]
    changed: bool
    status: MigrationStatus
    migration_id: str


def derive_migration_id(revision: AdmittedRevision) -> str:
    payload = {
        "kind": "sc900_content_revision_migration_v1",
        "manifest_sha256": revision.manifest_sha256,
        "source_bank_content_fingerprint": revision.source_bank_content_fingerprint,
        "target_bank_content_fingerprint": revision.target_bank_content_fingerprint,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _as_revisions(revision_or_sequence: AdmittedRevision | Sequence[AdmittedRevision] | None) -> tuple[AdmittedRevision, ...]:
    if revision_or_sequence is None:
        return ()
    if isinstance(revision_or_sequence, AdmittedRevision):
        return (revision_or_sequence,)
    if isinstance(revision_or_sequence, Sequence) and all(isinstance(item, AdmittedRevision) for item in revision_or_sequence):
        return tuple(revision_or_sequence)
    return ()


def history_event_matches_approved_revision(
    event: Mapping[str, Any] | None,
    question: Mapping[str, Any] | None,
    revision_or_sequence: AdmittedRevision | Sequence[AdmittedRevision] | None,
) -> bool:
    if history_event_matches_question(event, question):
        return True
    revisions = _as_revisions(revision_or_sequence)
    if not revisions or not isinstance(event, Mapping) or not isinstance(question, Mapping):
        return False
    event_id = history_event_question_id(event)
    question_id = canonical_question_id(question)
    event_fp = str(event.get("question_content_fingerprint") or "").strip()
    if not event_id or not question_id or event_id != question_id or not event_fp:
        return False
    current_fp = question_content_fingerprint(question)
    try:
        chain = approved_lineage(revisions, question_id, event_fp, current_fp)
    except Exception as exc:
        reason = getattr(exc, "reason", None)
        if reason in {RevisionFailureReason.LINEAGE_CONFLICT, MigrationFailureReason.LINEAGE_CONFLICT}:
            return False
        raise
    return chain is not None


def history_events_for_question_revision_aware(
    history_map: Mapping[str, list[Mapping[str, Any]]],
    question: Mapping[str, Any] | None,
    revision_or_sequence: AdmittedRevision | Sequence[AdmittedRevision] | None = None,
) -> list[Mapping[str, Any]]:
    question_id = canonical_question_id(question)
    if not question_id:
        return []
    return [
        event
        for event in history_map.get(question_id, [])
        if history_event_matches_approved_revision(event, question, revision_or_sequence)
    ]


def _lineage_row(question_id: str, from_fp: str, to_fp: str, revision: AdmittedRevision, migrated_at: str, migration_id: str) -> dict[str, str]:
    return {
        "question_id": question_id,
        "from_fingerprint": from_fp,
        "to_fingerprint": to_fp,
        "manifest_sha256": revision.manifest_sha256,
        "migration_id": migration_id,
        "migrated_at": migrated_at,
    }


def _expected_lineage_rows(
    records: Mapping[str, Any],
    revision: AdmittedRevision,
    migrated_at: str,
    migration_id: str,
) -> list[dict[str, str]]:
    edges = {edge.question_id: edge for edge in revision.edges}
    rows: list[dict[str, str]] = []
    for question_id in records:
        edge = edges.get(str(question_id))
        if edge is None:
            continue
        rows.append(
            _lineage_row(
                str(question_id),
                edge.from_content_fingerprint,
                edge.to_content_fingerprint,
                revision,
                migrated_at,
                migration_id,
            )
        )
    return rows


def _verify_target_progress(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    migrated_at: str,
    migration_id: str,
) -> PayloadMigrationResult:
    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    if not isinstance(records, Mapping) or not isinstance(stored_fps, Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    target_index = {canonical_question_id(question): question for question in target_questions}
    target_fps = {qid: question_content_fingerprint(question) for qid, question in target_index.items()}
    edges = {edge.question_id: edge for edge in revision.edges}
    for question_id in records:
        qid = str(question_id)
        if qid not in target_index:
            raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        stored_fp = str(stored_fps.get(qid) or "").strip()
        if stored_fp != target_fps[qid]:
            raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)
        edge = edges.get(qid)
        if edge is not None and stored_fp != edge.to_content_fingerprint:
            raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, qid)
    lineage = payload.get("content_revision_lineage") or []
    if not isinstance(lineage, list):
        raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT)
    expected = _expected_lineage_rows(records, revision, migrated_at, migration_id)
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
    for row in expected:
        key = (
            row["question_id"],
            row["from_fingerprint"],
            row["to_fingerprint"],
            row["manifest_sha256"],
            row["migration_id"],
        )
        if key not in actual_keys:
            raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, row["question_id"])
    return PayloadMigrationResult(copy.deepcopy(dict(payload)), False, MigrationStatus.MIGRATION_ALREADY_APPLIED, migration_id)


def migrate_progress_payload(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    migrated_at: str,
) -> PayloadMigrationResult:
    if not isinstance(payload, Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    migration_id = derive_migration_id(revision)
    bank_fp = str(payload.get("bank_fingerprint") or "").strip()
    if bank_fp == revision.target_bank_content_fingerprint:
        return _verify_target_progress(payload, target_questions, revision, migrated_at, migration_id)
    if bank_fp != revision.source_bank_content_fingerprint:
        raise ContentRevisionMigrationError(MigrationFailureReason.SOURCE_BANK_MISMATCH, bank_fp)
    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    if not isinstance(records, Mapping) or not isinstance(stored_fps, Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    target_index = {canonical_question_id(question): question for question in target_questions}
    target_fps = {qid: question_content_fingerprint(question) for qid, question in target_index.items()}
    edges = {edge.question_id: edge for edge in revision.edges}
    new_fps: dict[str, str] = {}
    new_lineage: list[dict[str, str]] = []
    existing_lineage = payload.get("content_revision_lineage")
    if existing_lineage is None:
        existing_lineage = []
    if not isinstance(existing_lineage, list):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    for question_id, _record in records.items():
        qid = str(question_id)
        if qid not in target_index:
            raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, qid)
        stored_fp = str(stored_fps.get(qid) or "").strip()
        target_fp = target_fps[qid]
        edge = edges.get(qid)
        if edge is None:
            if stored_fp != target_fp:
                raise ContentRevisionMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
            new_fps[qid] = stored_fp
            continue
        if stored_fp == edge.to_content_fingerprint:
            raise ContentRevisionMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
        if stored_fp != edge.from_content_fingerprint:
            raise ContentRevisionMigrationError(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, qid)
        if target_fp != edge.to_content_fingerprint or not revision.permits_fingerprint_transition(qid, stored_fp, target_fp):
            raise ContentRevisionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, qid)
        new_fps[qid] = edge.to_content_fingerprint
        new_lineage.append(_lineage_row(qid, edge.from_content_fingerprint, edge.to_content_fingerprint, revision, migrated_at, migration_id))
    migrated = copy.deepcopy(dict(payload))
    migrated["questions"] = copy.deepcopy(dict(records))
    migrated["question_content_fingerprints"] = new_fps
    migrated["bank_fingerprint"] = revision.target_bank_content_fingerprint
    migrated["history"] = copy.deepcopy(list(payload.get("history") or []))
    if "quarantined_questions" in payload:
        migrated["quarantined_questions"] = copy.deepcopy(payload.get("quarantined_questions"))
    migrated["content_revision_lineage"] = copy.deepcopy(list(existing_lineage)) + new_lineage
    return PayloadMigrationResult(migrated, True, MigrationStatus.APPLIED, migration_id)

