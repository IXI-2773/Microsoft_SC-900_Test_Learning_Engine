from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from content_fingerprint_bridge import RuntimeBoundRevision, bound_migration_id, unwrap_revision
from content_revision_authority import MANIFEST_KIND, AdmittedRevision, RevisionFailureReason, approved_lineage
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
    INVALID_SOURCE_SESSION = "INVALID_SOURCE_SESSION"
    CHANGED_QUESTION_MISSING_EDGE = "CHANGED_QUESTION_MISSING_EDGE"
    AUTHORITY_KIND_MISMATCH = "AUTHORITY_KIND_MISMATCH"


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


def _ensure_v1_equivalence_revision(revision: AdmittedRevision) -> None:
    kind = getattr(revision, "manifest_kind", MANIFEST_KIND)
    if kind != MANIFEST_KIND:
        raise ContentRevisionMigrationError(MigrationFailureReason.AUTHORITY_KIND_MISMATCH, str(kind))


def derive_migration_id(revision: AdmittedRevision | RuntimeBoundRevision) -> str:
    raw = unwrap_revision(revision)
    payload = {
        "kind": "sc900_content_revision_migration_v1",
        "manifest_sha256": raw.manifest_sha256,
        "source_bank_content_fingerprint": raw.source_bank_content_fingerprint,
        "target_bank_content_fingerprint": raw.target_bank_content_fingerprint,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    base = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return bound_migration_id(base, revision)


# These aliases are intentionally closed over the exact post-canonicalization
# revision bindings. They permit only the two known provenance-only rebinding
# events and never authorize a new semantic transition or future hash change.
_KNOWN_PROVENANCE_EQUIVALENT_MIGRATION_IDENTITIES: dict[
    tuple[str, str, str, str, str, str, str], frozenset[tuple[str, str]]
] = {
    (
        "646ad8ba5a7ccb0ae7f369b019b482fcd3212495ff0ce893aaecf0ceb5237cbe",
        "sc900_bank_v8_length_rebalanced_t1.json",
        "45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8",
        "e0b4394b6faa8d0f9053291521b2dd83983e84990f1a169a25ab745694a7aabb",
        "sc900_bank_v8_length_rebalanced_t2.json",
        "c53ba19ee26992643969d546a73da5aa8396041ebe4e138f6b30db637756aa65",
        "34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b",
    ): frozenset(
        {
            (
                "2f04ae1d2d22bdea1a8b96d470691700d59ea119bf34fb02d686d423b93bc571",
                "24d7b56a36067bd74f000d15c2cf74810c1f575ba248a522b934450408ca6458",
            )
        }
    ),
    (
        "4b9eab410da68bd348b4ae40946cf54a45b1da98bf04d68baaf6a57e3de15338",
        "sc900_bank_v8_length_rebalanced_t2.json",
        "c53ba19ee26992643969d546a73da5aa8396041ebe4e138f6b30db637756aa65",
        "34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b",
        "sc900_bank_v8_length_rebalanced_t3.json",
        "0b0cdf3bf4c8b7885acf0b3b19381dd9f19ee38944fc6af6934b11b5b14588bd",
        "83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2",
    ): frozenset(
        {
            (
                "d89a6708b08f2afc5bfc3a30cbd4c5708b6022acbacdb3a91db360d12c18c2ea",
                "7dd60b6dc130e4c8a16d3c117c832da737c0293957a350f3027826ababe268e2",
            )
        }
    ),
}


def _revision_lineage_identity(revision: AdmittedRevision) -> tuple[str, str, str, str, str, str, str]:
    return (
        revision.manifest_sha256,
        revision.source_bank_filename,
        revision.source_bank_file_sha256,
        revision.source_bank_content_fingerprint,
        revision.target_bank_filename,
        revision.target_bank_file_sha256,
        revision.target_bank_content_fingerprint,
    )


def accepted_migration_lineage_identities(
    revision: AdmittedRevision | RuntimeBoundRevision,
) -> frozenset[tuple[str, str]]:
    raw = unwrap_revision(revision)
    canonical = (raw.manifest_sha256, derive_migration_id(revision))
    raw_canonical = (raw.manifest_sha256, derive_migration_id(raw))
    historical = _KNOWN_PROVENANCE_EQUIVALENT_MIGRATION_IDENTITIES.get(_revision_lineage_identity(raw), frozenset())
    return frozenset({canonical, raw_canonical, *historical})


def _as_revisions(
    revision_or_sequence: AdmittedRevision | Sequence[AdmittedRevision] | None,
) -> tuple[AdmittedRevision, ...]:
    if revision_or_sequence is None:
        return ()
    if isinstance(revision_or_sequence, AdmittedRevision):
        return (revision_or_sequence,)
    if isinstance(revision_or_sequence, Sequence) and all(
        isinstance(item, AdmittedRevision) for item in revision_or_sequence
    ):
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


def _require_progress_payload_shape(payload: Mapping[str, Any]) -> None:
    history = payload.get("history")
    if not isinstance(history, list):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "history")
    records = payload.get("questions")
    stored_fps = payload.get("question_content_fingerprints")
    if not isinstance(records, Mapping) or not isinstance(stored_fps, Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    if "quarantined_questions" in payload and not isinstance(payload.get("quarantined_questions"), Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "quarantined_questions")
    if "content_revision_lineage" in payload and not isinstance(payload.get("content_revision_lineage"), list):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, "content_revision_lineage")


def _lineage_row(
    question_id: str, from_fp: str, to_fp: str, revision: Any, migrated_at: str, migration_id: str
) -> dict[str, str]:
    if isinstance(revision, RuntimeBoundRevision):
        raw_edge = revision.artifact_edge(question_id)
        if raw_edge is None:
            raise ContentRevisionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, question_id)
        from_fp = str(raw_edge.from_content_fingerprint)
        to_fp = str(raw_edge.to_content_fingerprint)
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
    if expected:
        accepted_identities = accepted_migration_lineage_identities(revision)
        complete_identity_found = any(
            all(
                (
                    row["question_id"],
                    row["from_fingerprint"],
                    row["to_fingerprint"],
                    manifest_sha256,
                    accepted_migration_id,
                )
                in actual_keys
                for row in expected
            )
            for manifest_sha256, accepted_migration_id in accepted_identities
        )
        if not complete_identity_found:
            raise ContentRevisionMigrationError(
                MigrationFailureReason.TARGET_PROGRESS_CONFLICT, expected[0]["question_id"]
            )
    return PayloadMigrationResult(
        copy.deepcopy(dict(payload)), False, MigrationStatus.MIGRATION_ALREADY_APPLIED, migration_id
    )


def migrate_progress_payload(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    migrated_at: str,
) -> PayloadMigrationResult:
    _ensure_v1_equivalence_revision(revision)
    if not isinstance(payload, Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD)
    _require_progress_payload_shape(payload)
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
        if target_fp != edge.to_content_fingerprint or not revision.permits_fingerprint_transition(
            qid, stored_fp, target_fp
        ):
            raise ContentRevisionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, qid)
        new_fps[qid] = edge.to_content_fingerprint
        new_lineage.append(
            _lineage_row(
                qid, edge.from_content_fingerprint, edge.to_content_fingerprint, revision, migrated_at, migration_id
            )
        )
    migrated = copy.deepcopy(dict(payload))
    migrated["questions"] = copy.deepcopy(dict(records))
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
    migrated["history"] = copy.deepcopy(payload["history"])
    if "quarantined_questions" in payload:
        migrated["quarantined_questions"] = copy.deepcopy(payload.get("quarantined_questions"))
    migrated["content_revision_lineage"] = copy.deepcopy(list(existing_lineage)) + new_lineage
    return PayloadMigrationResult(migrated, True, MigrationStatus.APPLIED, migration_id)


def migrate_session_payload(
    saved: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    target_bank_file: str | Path,
    *,
    source_questions: Sequence[Mapping[str, Any]] | None = None,
) -> PayloadMigrationResult:
    from session_identity import canonical_session_signature, ordered_question_ids
    from session_store import migrate_session_snapshot

    _ensure_v1_equivalence_revision(revision)
    if not isinstance(saved, Mapping):
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION)
    saved_fp = str(saved.get("bank_fingerprint") or "").strip()
    if saved_fp != revision.source_bank_content_fingerprint:
        raise ContentRevisionMigrationError(MigrationFailureReason.SOURCE_BANK_MISMATCH, saved_fp)
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
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION, str(exc)) from exc
    target_index = {canonical_question_id(question): question for question in target_questions}
    target_fps = {qid: question_content_fingerprint(question) for qid, question in target_index.items()}
    source_index = (
        {canonical_question_id(question): question for question in source_questions}
        if source_questions is not None
        else {}
    )
    edges = {edge.question_id: edge for edge in revision.edges}
    referenced_ids = list(validated.get("question_ids") or []) + list(validated.get("restore_question_ids") or [])
    for question_id in referenced_ids:
        if question_id not in target_index:
            raise ContentRevisionMigrationError(MigrationFailureReason.TARGET_QUESTION_MISSING, question_id)
        target_fp = target_fps[question_id]
        edge = edges.get(question_id)
        source_fp = ""
        if isinstance(revision, RuntimeBoundRevision):
            source_fp = revision.runtime_source_question_fingerprint(question_id)
        elif question_id in source_index:
            source_fp = question_content_fingerprint(source_index[question_id])
        if source_fp and source_fp != target_fp and edge is None:
            raise ContentRevisionMigrationError(MigrationFailureReason.CHANGED_QUESTION_MISSING_EDGE, question_id)
        if edge is not None and source_fp and source_fp != edge.from_content_fingerprint:
            raise ContentRevisionMigrationError(
                MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH,
                question_id,
            )
        if edge is not None and target_fp != edge.to_content_fingerprint:
            raise ContentRevisionMigrationError(MigrationFailureReason.UNAUTHORIZED_TRANSITION, question_id)
    migrated: dict[str, Any] = copy.deepcopy(dict(validated))
    answers = []
    for row in migrated.get("answers") or []:
        updated = copy.deepcopy(dict(row))
        question_id = str(updated.get("question_id") or "")
        if question_id in edges and not updated.get("answered"):
            if updated.get("selected") or updated.get("pending"):
                updated["selected"] = []
                updated["pending"] = []
        answers.append(updated)
    migrated["answers"] = answers
    migrated["session_answer_history"] = copy.deepcopy(list(validated.get("session_answer_history") or []))
    migrated["bank_file"] = str(target_bank_file)
    migrated["bank_fingerprint"] = revision.target_bank_content_fingerprint
    migrated["session_signature"] = canonical_session_signature(
        mode, revision.target_bank_content_fingerprint, list(migrated.get("question_ids") or [])
    )
    migrated["restore_signature"] = canonical_session_signature(
        mode, revision.target_bank_content_fingerprint, list(migrated.get("restore_question_ids") or [])
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
        raise ContentRevisionMigrationError(MigrationFailureReason.INVALID_SOURCE_SESSION, str(exc)) from exc
    return PayloadMigrationResult(dict(target_validated), True, MigrationStatus.APPLIED, derive_migration_id(revision))
