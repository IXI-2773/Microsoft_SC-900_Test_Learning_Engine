from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionStatus,
    canonical_manifest_sha256,
    parse_json_duplicate_safe,
    sha256_file,
)
from content_revision_correction_authority import (
    CONTINUITY_POLICY,
    MANIFEST_KIND,
    PERMITTED_CHANGE_CLASS,
    AdmittedCorrectionRevision,
    CorrectionAdmissionResult,
    CorrectionEdge,
    CorrectionFailureReason,
)
from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint

SCHEMA_VERSION = 2
WORK_ID = "SC900-FINAL-TWO-QUESTION-CONTENT-CORRECTION-IMPLEMENTATION-001"
SOURCE_BANK_FILENAME = "sc900_bank_v8_explanation_final_454_repair.json"
TARGET_BANK_FILENAME = "sc900_bank_v8_final_content_correction_002.json"
EXPECTED_SOURCE_BANK_SHA256 = "a3a8b811b3ce14e76f871333fd3a1ba262afda1b2da39fde98ccf6fde6dd522f"
EXPECTED_SOURCE_CONTENT_FINGERPRINT = "bad80fb502fd5d5c8a50de011c21b9df7da6a9117074ad70140f85fcca0e5e5a"
REQUIRED_QUESTION_COUNT = 454
TARGET_IDS = ("sc900_p2_q001", "sc900_p3_q071")
AUTHORIZED_CHANGED_FIELDS = ("choice_explanations", "choices")
REVIEW_DISPOSITION = "APPROVED_FOR_KEY_PRESERVING_CONTENT_CORRECTION"
AUTHORITY_REFS = (
    "https://learn.microsoft.com/en-us/training/modules/describe-security-concepts-methodologies/5-describe-encryption-hashing",
    "https://learn.microsoft.com/en-us/windows/apps/develop/security/cryptography",
)
CHOICE_LABELS = ("A", "B", "C", "D")


def _fail(reason: CorrectionFailureReason) -> CorrectionAdmissionResult:
    return CorrectionAdmissionResult(AdmissionStatus.FAIL, (reason,), None)


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = parse_json_duplicate_safe(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _questions(bank: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    rows = bank.get("questions")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        return None
    return rows


def _index(rows: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]] | None:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        qid = canonical_question_id(row)
        if not qid or qid in result:
            return None
        result[qid] = row
    return result


def _correct_key(question: Mapping[str, Any]) -> tuple[str, ...]:
    value = question.get("correct") or []
    if isinstance(value, str):
        value = [value]
    return tuple(str(item) for item in value) if isinstance(value, list) else ()


def _microsoft_refs(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(ref, str) and ref.strip() for ref in value)
        and any(ref.startswith("https://learn.microsoft.com/") for ref in value)
    )


def _changed_fields(source: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    fields = set(source) | set(target)
    return sorted(field for field in fields if _canonical(source.get(field)) != _canonical(target.get(field)))


def _validate_spec(spec: Mapping[str, Any]) -> bool:
    required = {
        "schema_version",
        "work_id",
        "source_bank",
        "source_bank_raw_sha256",
        "source_bank_content_fingerprint",
        "question_count",
        "target_ids",
        "corrections",
        "currentness_requirements",
        "payload_sha256",
    }
    if set(spec) != required:
        return False
    if (
        spec["schema_version"] != SCHEMA_VERSION
        or spec["work_id"] != WORK_ID
        or spec["source_bank"] != SOURCE_BANK_FILENAME
        or spec["source_bank_raw_sha256"] != EXPECTED_SOURCE_BANK_SHA256
        or spec["source_bank_content_fingerprint"] != EXPECTED_SOURCE_CONTENT_FINGERPRINT
        or spec["question_count"] != REQUIRED_QUESTION_COUNT
        or spec["target_ids"] != list(TARGET_IDS)
        or canonical_manifest_sha256(spec) != spec["payload_sha256"]
    ):
        return False
    corrections = spec["corrections"]
    if not isinstance(corrections, list) or [
        row.get("question_id") for row in corrections if isinstance(row, Mapping)
    ] != list(TARGET_IDS):
        return False
    for row in corrections:
        if not isinstance(row, Mapping):
            return False
        if row.get("authorized_changed_fields") != list(AUTHORIZED_CHANGED_FIELDS):
            return False
        if not _microsoft_refs(row.get("authority_refs")):
            return False
        if row.get("final_validation_status") != "APPROVED":
            return False
    req = spec["currentness_requirements"]
    return isinstance(req, Mapping) and req.get("required_result") == "PASS_FOR_ALL_TARGETS"


def _validate_currentness(record: Mapping[str, Any]) -> bool:
    required = {
        "schema_version",
        "work_id",
        "source_bank",
        "source_bank_raw_sha256",
        "source_bank_content_fingerprint",
        "checked_at",
        "targets",
        "overall_status",
        "payload_sha256",
    }
    if set(record) != required:
        return False
    if (
        record["schema_version"] != 1
        or record["work_id"] != WORK_ID
        or record["source_bank"] != SOURCE_BANK_FILENAME
        or record["source_bank_raw_sha256"] != EXPECTED_SOURCE_BANK_SHA256
        or record["source_bank_content_fingerprint"] != EXPECTED_SOURCE_CONTENT_FINGERPRINT
        or record["overall_status"] != "PASS"
        or canonical_manifest_sha256(record) != record["payload_sha256"]
    ):
        return False
    targets = record["targets"]
    if not isinstance(targets, list) or [row.get("question_id") for row in targets if isinstance(row, Mapping)] != list(
        TARGET_IDS
    ):
        return False
    return all(
        isinstance(row, Mapping) and row.get("status") == "PASS" and _microsoft_refs(row.get("authority_refs"))
        for row in targets
    )


def admit_final_content_correction(
    manifest: Mapping[str, Any],
    *,
    spec: Mapping[str, Any],
    currentness_record: Mapping[str, Any],
    source_bank_path: Path,
    target_bank_path: Path,
    spec_path: Path,
    currentness_path: Path,
    review_root: Path,
) -> CorrectionAdmissionResult:
    required_manifest = {
        "schema_version",
        "manifest_kind",
        "work_id",
        "continuity_policy",
        "permitted_change_class",
        "source_bank",
        "target_bank",
        "correction_spec",
        "currentness_record",
        "edges",
        "payload_sha256",
    }
    if not isinstance(manifest, Mapping) or set(manifest) != required_manifest:
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["manifest_kind"] != MANIFEST_KIND
        or manifest["work_id"] != WORK_ID
        or manifest["continuity_policy"] != CONTINUITY_POLICY
        or manifest["permitted_change_class"] != PERMITTED_CHANGE_CLASS
        or canonical_manifest_sha256(manifest) != manifest["payload_sha256"]
    ):
        return _fail(CorrectionFailureReason.MANIFEST_HASH_MISMATCH)
    if not _validate_spec(spec):
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if not _validate_currentness(currentness_record):
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)
    if sha256_file(source_bank_path) != EXPECTED_SOURCE_BANK_SHA256:
        return _fail(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if sha256_file(spec_path) != manifest["correction_spec"].get("file_sha256"):
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if sha256_file(currentness_path) != manifest["currentness_record"].get("file_sha256"):
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)
    if spec["payload_sha256"] != manifest["correction_spec"].get("payload_sha256"):
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if currentness_record["payload_sha256"] != manifest["currentness_record"].get("payload_sha256"):
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)

    source = _read(source_bank_path)
    target = _read(target_bank_path)
    if source is None or target is None:
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    source_rows = _questions(source)
    target_rows = _questions(target)
    if (
        source_rows is None
        or target_rows is None
        or len(source_rows) != REQUIRED_QUESTION_COUNT
        or len(target_rows) != REQUIRED_QUESTION_COUNT
    ):
        return _fail(CorrectionFailureReason.QUESTION_COUNT_MISMATCH)
    if [canonical_question_id(row) for row in source_rows] != [canonical_question_id(row) for row in target_rows]:
        return _fail(CorrectionFailureReason.QUESTION_ORDER_MISMATCH)
    source_index = _index(source_rows)
    target_index = _index(target_rows)
    if source_index is None or target_index is None:
        return _fail(CorrectionFailureReason.DUPLICATE_QUESTION_ID)
    source_meta = {key: value for key, value in source.items() if key != "questions"}
    target_meta = {key: value for key, value in target.items() if key != "questions"}
    if _canonical(source_meta) != _canonical(target_meta):
        return _fail(CorrectionFailureReason.BANK_METADATA_MISMATCH)
    source_fp = bank_content_fingerprint(source_rows)
    target_fp = bank_content_fingerprint(target_rows)
    if source_fp != EXPECTED_SOURCE_CONTENT_FINGERPRINT:
        return _fail(CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH)
    if source_fp != manifest["source_bank"].get("content_fingerprint") or target_fp != manifest["target_bank"].get(
        "content_fingerprint"
    ):
        return _fail(CorrectionFailureReason.TARGET_BANK_FINGERPRINT_MISMATCH)
    if sha256_file(target_bank_path) != manifest["target_bank"].get("file_sha256"):
        return _fail(CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)

    changed_ids = [
        qid
        for qid in source_index
        if question_content_fingerprint(source_index[qid]) != question_content_fingerprint(target_index[qid])
    ]
    if changed_ids != list(TARGET_IDS):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)

    spec_by_id = {row["question_id"]: row for row in spec["corrections"]}
    edges = manifest["edges"]
    if not isinstance(edges, list) or [edge.get("question_id") for edge in edges if isinstance(edge, Mapping)] != list(
        TARGET_IDS
    ):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    admitted_edges: list[CorrectionEdge] = []
    for edge in edges:
        qid = edge["question_id"]
        before = source_index[qid]
        after = target_index[qid]
        if _correct_key(before) != _correct_key(after):
            return _fail(CorrectionFailureReason.CORRECT_KEY_CHANGED)
        if before.get("objective_code") != after.get("objective_code"):
            return _fail(CorrectionFailureReason.OBJECTIVE_CHANGED)
        if before.get("tested_decision") != after.get("tested_decision"):
            return _fail(CorrectionFailureReason.TESTED_DECISION_CHANGED)
        changed_fields = _changed_fields(before, after)
        if changed_fields != list(AUTHORIZED_CHANGED_FIELDS):
            return _fail(CorrectionFailureReason.NONPERMITTED_FIELD_CHANGED)
        if changed_fields != spec_by_id[qid]["authorized_changed_fields"] or changed_fields != edge.get(
            "changed_fields"
        ):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if before.get("prompt") != after.get("prompt"):
            return _fail(CorrectionFailureReason.NONPERMITTED_FIELD_CHANGED)
        choices = after.get("choices")
        explanations = after.get("choice_explanations")
        if (
            not isinstance(choices, Mapping)
            or set(choices) != set(CHOICE_LABELS)
            or len({str(v).casefold() for v in choices.values()}) != 4
        ):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if (
            not isinstance(explanations, Mapping)
            or set(explanations) != set(CHOICE_LABELS)
            or any(not str(v).strip() for v in explanations.values())
        ):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        from_fp = question_content_fingerprint(before)
        to_fp = question_content_fingerprint(after)
        if edge.get("from_content_fingerprint") != from_fp:
            return _fail(CorrectionFailureReason.FROM_FINGERPRINT_MISMATCH)
        if edge.get("to_content_fingerprint") != to_fp:
            return _fail(CorrectionFailureReason.TO_FINGERPRINT_MISMATCH)
        if edge.get("correct_key_unchanged") is not True or edge.get("objective_unchanged") is not True:
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if not _microsoft_refs(edge.get("authority_refs")):
            return _fail(CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING)
        review_rel = str(edge.get("review_artifact") or "")
        review_path = review_root / review_rel
        review = _read(review_path)
        if review is None or sha256_file(review_path) != edge.get("review_artifact_sha256"):
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        if (
            review.get("question_id") != qid
            or review.get("from_content_fingerprint") != from_fp
            or review.get("to_content_fingerprint") != to_fp
            or review.get("correction_spec_payload_sha256") != spec["payload_sha256"]
            or review.get("disposition") != REVIEW_DISPOSITION
            or _canonical(review.get("before")) != _canonical(spec_by_id[qid]["source_values"])
            or _canonical(review.get("after")) != _canonical(spec_by_id[qid]["target_values"])
        ):
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        admitted_edges.append(
            CorrectionEdge(
                question_id=qid,
                from_content_fingerprint=from_fp,
                to_content_fingerprint=to_fp,
                changed_fields=tuple(changed_fields),
                review_artifact=review_rel,
                review_artifact_sha256=str(edge["review_artifact_sha256"]),
                authority_refs=tuple(str(ref) for ref in edge["authority_refs"]),
            )
        )

    admitted = AdmittedCorrectionRevision(
        manifest_kind=MANIFEST_KIND,
        continuity_policy=CONTINUITY_POLICY,
        permitted_change_class=PERMITTED_CHANGE_CLASS,
        manifest_sha256=str(manifest["payload_sha256"]),
        source_bank_filename=SOURCE_BANK_FILENAME,
        source_bank_file_sha256=EXPECTED_SOURCE_BANK_SHA256,
        source_bank_content_fingerprint=source_fp,
        target_bank_filename=TARGET_BANK_FILENAME,
        target_bank_file_sha256=str(manifest["target_bank"]["file_sha256"]),
        target_bank_content_fingerprint=target_fp,
        correction_spec_payload_sha256=str(spec["payload_sha256"]),
        currentness_record_payload_sha256=str(currentness_record["payload_sha256"]),
        edges=tuple(admitted_edges),
    )
    return CorrectionAdmissionResult(AdmissionStatus.PASS, (), admitted)
