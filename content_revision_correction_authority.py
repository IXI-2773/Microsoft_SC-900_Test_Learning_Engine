from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionStatus,
    ContentRevisionManifestError,
    RevisionFailureReason,
    canonical_manifest_sha256,
    contained_relative_path,
    parse_json_duplicate_safe,
    sha256_file,
)
from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint

SCHEMA_VERSION = 2
MANIFEST_KIND = "sc900_content_revision_correction"
CONTINUITY_POLICY = "PRESERVE_HISTORICAL_EVIDENCE_RESET_ACTIVE_AFFECTED_STATE"
PERMITTED_CHANGE_CLASS = "KEY_PRESERVING_CONTENT_CORRECTION"
WORK_ID = "SC900-SEPARATE-CONTENT-CORRECTION-001-POST-CALIBRATION-IMPLEMENTATION-EXECUTION-001"
SOURCE_VALIDATION_WORK_ID = "SC900-SEPARATE-CONTENT-CORRECTION-001-NINE-QUESTION-FINAL-VALIDATION-CHAT-001"
Q219_REPLACEMENT_WORK_ID = "SC900-SEPARATE-CONTENT-CORRECTION-001-Q219-BOUNDED-REPLACEMENT-FREEZE-001"
Q219_PRIOR_CURRENTNESS_WORK_ID = (
    "SC900-SEPARATE-CONTENT-CORRECTION-001-Q219-PRE-IMPLEMENTATION-CURRENTNESS-REVALIDATION-001"
)
SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t5.json"
TARGET_BANK_FILENAME = "sc900_bank_v8_content_correction_001.json"
EXPECTED_SOURCE_BANK_SHA256 = "13820be0ff959c2229838088eb6380cb801acd753cb857554d0ed1869982ecfd"
EXPECTED_SOURCE_CONTENT_FINGERPRINT = "ec5ec3233c451b80dc6ce09710c8dc7272e19052d9bc2c8d22c53d0945f18766"
EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256 = "654757b22e91e3d47754095035f7c260f8b0f0b6843ca9c122d443041108eac8"
EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256 = "ea957c3657e70d425794215c76dcfef192972a75fb16f219d591d83c5a148ee3"
EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256 = "0f9f2e5f5c971213e550f00d16e6d3013d9fbdc145479a7dfeb0a8340fa95917"
REQUIRED_QUESTION_COUNT = 454
CHOICE_LABELS = ("A", "B", "C", "D")
MS_LEARN_PREFIX = "https://learn.microsoft.com/"
REVIEW_STATUS_APPROVED = "APPROVED"
REVIEW_DISPOSITION_APPROVED = "APPROVED_FOR_KEY_PRESERVING_CONTENT_CORRECTION"
Q219_TESTED_DECISION = "entra_connect_syncs_hybrid_identity"
SUPERSEDED_Q219_MARKER = "hybrid join"
TARGET_IDS = (
    "sc900_mlc_q064",
    "sc900_mlc_q118",
    "sc900_mlc_q150",
    "sc900_mlc_q198",
    "sc900_mlc_q219",
    "sc900_mlc_q226",
    "sc900_mlc_q242",
    "sc900_mlc_q249",
    "sc900_mlc_q269",
)
PROMPT_CHANGED_IDS = (
    "sc900_mlc_q064",
    "sc900_mlc_q150",
    "sc900_mlc_q198",
    "sc900_mlc_q219",
    "sc900_mlc_q242",
    "sc900_mlc_q269",
)
CURRENTNESS_QUESTION_IDS = ["sc900_mlc_q118", "sc900_mlc_q219", "sc900_mlc_q269"]
CURRENTNESS_REQUIREMENTS = {
    "currentness_record_required": True,
    "question_ids": CURRENTNESS_QUESTION_IDS,
    "required_result": "PASS_FOR_ALL_THREE",
}
AUTHORIZED_CONTENT_FIELDS = ("choice_explanations", "choices", "general_explanation", "prompt")
PROTECTED_QUESTION_FIELDS = (
    "correct",
    "currentness_status",
    "difficulty",
    "domain",
    "domain_code",
    "exam_calibration_tier",
    "exam_simulation_eligible",
    "id",
    "objective_code",
    "question_number",
    "question_type",
    "subobjective",
    "tested_decision",
    "topics",
)
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
FINAL_TWO_QUESTION_WORK_ID = "SC900-FINAL-TWO-QUESTION-CONTENT-CORRECTION-IMPLEMENTATION-001"
FINAL_TWO_QUESTION_SOURCE_BANK_FILENAME = "sc900_bank_v8_explanation_final_454_repair.json"
FINAL_TWO_QUESTION_TARGET_BANK_FILENAME = "sc900_bank_v8_final_content_correction_002.json"
FINAL_TWO_QUESTION_SOURCE_SHA256 = "a3a8b811b3ce14e76f871333fd3a1ba262afda1b2da39fde98ccf6fde6dd522f"
FINAL_TWO_QUESTION_SOURCE_FINGERPRINT = "bad80fb502fd5d5c8a50de011c21b9df7da6a9117074ad70140f85fcca0e5e5a"
FINAL_TWO_QUESTION_TARGET_SHA256 = "f97f76591ebb41dd1b92ca5623c6f040b2d9a75ca6f7f1d5b0ebd9adf371581f"
FINAL_TWO_QUESTION_TARGET_FINGERPRINT = "76a2ca2d8779e6e0b422f9192868e19ac1f7e0e0543e555a80a8dde9be14f407"
FINAL_TWO_QUESTION_MANIFEST_SHA256 = "3e62c4a195d2fe8961b29d98694a184a6f4c2a2265da20602f4cd09819f51345"
FINAL_TWO_QUESTION_SPEC_SHA256 = "c77c0fdd514841c25fb08e192b4af485f442d79bad44ffc4dbfd332ec1100b43"
FINAL_TWO_QUESTION_CURRENTNESS_SHA256 = "5a9cdff3042bf732142814f74dbb655dc92ff0f3a79124b29cf5ce03c5508128"
FINAL_TWO_QUESTION_IDS = ("sc900_p2_q001", "sc900_p3_q071")
FINAL_TWO_QUESTION_AUTHORIZED_FIELDS = ("choice_explanations", "choices")
FINAL_TWO_QUESTION_AUTHORITY_REFS = (
    "https://learn.microsoft.com/en-us/training/modules/describe-security-concepts-methodologies/5-describe-encryption-hashing",
    "https://learn.microsoft.com/en-us/windows/apps/develop/security/cryptography",
)
_FINAL_SPEC_FIELDS = (
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
)
_FINAL_CURRENTNESS_FIELDS = (
    "schema_version",
    "work_id",
    "source_bank",
    "source_bank_raw_sha256",
    "source_bank_content_fingerprint",
    "checked_at",
    "targets",
    "overall_status",
    "payload_sha256",
)
_FINAL_CURRENTNESS_REQUIREMENTS = {
    "currentness_record_required": True,
    "question_ids": list(FINAL_TWO_QUESTION_IDS),
    "required_result": "PASS_FOR_ALL_TARGETS",
}
_SPEC_FIELDS = (
    "schema_version",
    "work_id",
    "source_validation_work_id",
    "superseding_validation_work_ids",
    "source_bank",
    "source_bank_raw_sha256",
    "source_bank_content_fingerprint",
    "source_manifest_payload_sha256",
    "question_count",
    "target_ids",
    "corrections",
    "currentness_requirements",
    "payload_sha256",
)
_CORRECTION_ENTRY_FIELDS = (
    "question_id",
    "authorized_changed_fields",
    "source_values",
    "target_values",
    "correct_key",
    "objective_code",
    "authority_refs",
    "semantic_validation_work_id",
    "final_validation_status",
    "currentness_class",
)
_CURRENTNESS_FIELDS = (
    "schema_version",
    "work_id",
    "source_bank",
    "source_bank_raw_sha256",
    "source_bank_content_fingerprint",
    "checked_at",
    "targets",
    "overall_status",
    "q219_prior_device_sync_failure_provenance",
    "q219_prior_failure_work_id",
    "q219_replacement_pass_provenance",
    "q219_replacement_work_id",
    "payload_sha256",
)
_CURRENTNESS_TARGET_FIELDS = (
    "question_id",
    "prior_currentness_work_id",
    "superseding_work_id_if_any",
    "status",
    "authority_refs",
    "checked_at",
    "material_change_detected",
    "notes",
)
_MANIFEST_FIELDS = (
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
)
_BANK_BINDING_FIELDS = ("filename", "file_sha256", "content_fingerprint", "question_count")
_ARTIFACT_BINDING_FIELDS = ("filename", "file_sha256", "payload_sha256")
_EDGE_FIELDS = (
    "question_id",
    "from_content_fingerprint",
    "to_content_fingerprint",
    "changed_fields",
    "correct_key_unchanged",
    "objective_unchanged",
    "domain_unchanged",
    "question_type_unchanged",
    "tier_unchanged",
    "exam_eligibility_unchanged",
    "review_status",
    "review_artifact",
    "review_artifact_sha256",
    "authority_refs",
)
_RECEIPT_FIELDS = (
    "question_id",
    "from_content_fingerprint",
    "to_content_fingerprint",
    "authorized_changed_fields",
    "before",
    "after",
    "correct_key_before",
    "correct_key_after",
    "objective_before",
    "objective_after",
    "authority_refs",
    "correction_spec_payload_sha256",
    "disposition",
)
_EDGE_BOOL_FIELDS = (
    "correct_key_unchanged",
    "objective_unchanged",
    "domain_unchanged",
    "question_type_unchanged",
    "tier_unchanged",
    "exam_eligibility_unchanged",
)


class CorrectionFailureReason(StrEnum):
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    MISSING_FIELD = "MISSING_FIELD"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    MANIFEST_HASH_MISMATCH = "MANIFEST_HASH_MISMATCH"
    SOURCE_BANK_FILE_HASH_MISMATCH = "SOURCE_FILE_HASH_MISMATCH"
    SOURCE_CONTENT_FINGERPRINT_MISMATCH = "SOURCE_CONTENT_FINGERPRINT_MISMATCH"
    SOURCE_IDENTITY_INVALID = "SOURCE_IDENTITY_INVALID"
    QUESTION_ORDER_MISMATCH = "QUESTION_ORDER_MISMATCH"
    BANK_METADATA_MISMATCH = "BANK_METADATA_MISMATCH"
    CORRECTION_SPEC_HASH_MISMATCH = "CORRECTION_SPEC_HASH_MISMATCH"
    CURRENTNESS_GATE_FAILED = "CURRENTNESS_GATE_FAILED"
    AUTHORITY_KIND_MISMATCH = "AUTHORITY_KIND_MISMATCH"
    UNDECLARED_CONTENT_CHANGE = "UNDECLARED_CONTENT_CHANGE"
    TARGET_BANK_FILE_HASH_MISMATCH = "TARGET_BANK_FILE_HASH_MISMATCH"
    TARGET_BANK_FINGERPRINT_MISMATCH = "TARGET_BANK_FINGERPRINT_MISMATCH"
    QUESTION_COUNT_MISMATCH = "QUESTION_COUNT_MISMATCH"
    QUESTION_ID_SET_MISMATCH = "QUESTION_ID_SET_MISMATCH"
    DUPLICATE_QUESTION_ID = "DUPLICATE_QUESTION_ID"
    FROM_FINGERPRINT_MISMATCH = "FROM_FINGERPRINT_MISMATCH"
    TO_FINGERPRINT_MISMATCH = "TO_FINGERPRINT_MISMATCH"
    CORRECT_KEY_CHANGED = "CORRECT_KEY_CHANGED"
    OBJECTIVE_CHANGED = "OBJECTIVE_CHANGED"
    TESTED_DECISION_CHANGED = "TESTED_DECISION_CHANGED"
    NONPERMITTED_FIELD_CHANGED = "NONPERMITTED_FIELD_CHANGED"
    SEMANTIC_REVIEW_MISSING = "SEMANTIC_REVIEW_MISSING"
    SEMANTIC_REVIEW_HASH_MISMATCH = "SEMANTIC_REVIEW_HASH_MISMATCH"
    AUTHORITY_EVIDENCE_MISSING = "AUTHORITY_EVIDENCE_MISSING"
    Q219_SUPERSEDED_TARGET_IMPLEMENTED = "Q219_SUPERSEDED_TARGET_IMPLEMENTED"
    PARTIAL_OR_ALREADY_CORRECTED_SOURCE = "PARTIAL_OR_ALREADY_CORRECTED_SOURCE"


class ContentCorrectionManifestError(ValueError):
    def __init__(self, reason: CorrectionFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason.value if not detail else f"{reason.value}: {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CorrectionEdge:
    question_id: str
    from_content_fingerprint: str
    to_content_fingerprint: str
    changed_fields: tuple[str, ...]
    review_artifact: str
    review_artifact_sha256: str
    authority_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdmittedCorrectionRevision:
    manifest_kind: str
    continuity_policy: str
    permitted_change_class: str
    manifest_sha256: str
    source_bank_filename: str
    source_bank_file_sha256: str
    source_bank_content_fingerprint: str
    target_bank_filename: str
    target_bank_file_sha256: str
    target_bank_content_fingerprint: str
    correction_spec_payload_sha256: str
    currentness_record_payload_sha256: str
    edges: tuple[CorrectionEdge, ...]

    def permits_fingerprint_transition(self, question_id: str, from_fp: str, to_fp: str) -> bool:
        return any(
            edge.question_id == question_id
            and edge.from_content_fingerprint == from_fp
            and edge.to_content_fingerprint == to_fp
            for edge in self.edges
        )


@dataclass(frozen=True, slots=True)
class CorrectionAdmissionResult:
    status: AdmissionStatus
    reasons: tuple[CorrectionFailureReason, ...]
    admitted: AdmittedCorrectionRevision | None


def _fail(*reasons: CorrectionFailureReason) -> CorrectionAdmissionResult:
    return CorrectionAdmissionResult(AdmissionStatus.FAIL, reasons, None)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX64.fullmatch(value))


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _canonical_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical_json(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical_json(item) for item in value]
    return value


def _unknown_or_missing(payload: Mapping[str, Any], required: Sequence[str]) -> CorrectionFailureReason | None:
    required_set = set(required)
    for key in payload:
        if key not in required_set:
            return CorrectionFailureReason.UNKNOWN_FIELD
    for key in required:
        if key not in payload:
            return CorrectionFailureReason.MISSING_FIELD
    return None


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _exact_ad_mapping(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value.keys()) != set(CHOICE_LABELS):
        return False
    return all(isinstance(value[letter], str) for letter in CHOICE_LABELS)


def _microsoft_learn_refs(refs: Sequence[Any]) -> bool:
    if not refs:
        return False
    has_microsoft_learn = False
    for ref in refs:
        if not isinstance(ref, str):
            return False
        if ref.strip().startswith(MS_LEARN_PREFIX):
            has_microsoft_learn = True
    return has_microsoft_learn


def _correct_key(question: Mapping[str, Any]) -> tuple[str, ...] | None:
    correct = question.get("correct")
    if isinstance(correct, str):
        correct = [correct]
    if not isinstance(correct, list):
        return None
    return tuple(str(item) for item in correct)


def _read_object(
    path: Path, missing_reason: CorrectionFailureReason
) -> tuple[dict[str, Any] | None, CorrectionAdmissionResult | None]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None, _fail(missing_reason)
    try:
        payload = parse_json_duplicate_safe(raw)
    except ContentRevisionManifestError as exc:
        if exc.reason == RevisionFailureReason.DUPLICATE_JSON_KEY:
            return None, _fail(CorrectionFailureReason.DUPLICATE_JSON_KEY)
        return None, _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    return payload, None


def _index_questions(questions: Sequence[Any]) -> tuple[dict[str, Mapping[str, Any]], CorrectionFailureReason | None]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        if not isinstance(question, Mapping):
            return {}, CorrectionFailureReason.SCHEMA_UNSUPPORTED
        question_id = canonical_question_id(question)
        if not question_id:
            return {}, CorrectionFailureReason.QUESTION_ID_SET_MISMATCH
        if question_id in indexed:
            return {}, CorrectionFailureReason.DUPLICATE_QUESTION_ID
        indexed[question_id] = question
    return indexed, None


def _validate_bank_binding(payload: Any) -> CorrectionFailureReason | None:
    if not isinstance(payload, Mapping):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    shape = _unknown_or_missing(payload, _BANK_BINDING_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["filename"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["file_sha256"]) or not _is_hex64(payload["content_fingerprint"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_int(payload["question_count"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_artifact_binding(payload: Any) -> CorrectionFailureReason | None:
    if not isinstance(payload, Mapping):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    shape = _unknown_or_missing(payload, _ARTIFACT_BINDING_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["filename"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["file_sha256"]) or not _is_hex64(payload["payload_sha256"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_edge(payload: Any) -> CorrectionFailureReason | None:
    if not isinstance(payload, Mapping):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if "correction_class" in payload or "choice_semantics" in payload:
        return CorrectionFailureReason.UNKNOWN_FIELD
    shape = _unknown_or_missing(payload, _EDGE_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["question_id"]) or not _nonempty_str(payload["review_artifact"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["from_content_fingerprint"]) or not _is_hex64(payload["to_content_fingerprint"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["review_artifact_sha256"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["changed_fields"]) or not _string_list(payload["authority_refs"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    for field in _EDGE_BOOL_FIELDS:
        if payload[field] is not True:
            return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if payload["review_status"] != REVIEW_STATUS_APPROVED:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_receipt(payload: Mapping[str, Any]) -> CorrectionFailureReason | None:
    if "correction_class" in payload:
        return CorrectionFailureReason.UNKNOWN_FIELD
    shape = _unknown_or_missing(payload, _RECEIPT_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["question_id"]) or not _nonempty_str(payload["disposition"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["from_content_fingerprint"]) or not _is_hex64(payload["to_content_fingerprint"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["correction_spec_payload_sha256"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["authorized_changed_fields"]) or not _string_list(payload["authority_refs"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["correct_key_before"]) or not _string_list(payload["correct_key_after"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _nonempty_str(payload["objective_before"]) or not _nonempty_str(payload["objective_after"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not isinstance(payload["before"], Mapping) or not isinstance(payload["after"], Mapping):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_correction_entry(payload: Any) -> CorrectionFailureReason | None:
    if not isinstance(payload, Mapping):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if "correction_class" in payload:
        return CorrectionFailureReason.UNKNOWN_FIELD
    shape = _unknown_or_missing(payload, _CORRECTION_ENTRY_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["question_id"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["authorized_changed_fields"]) or not _string_list(payload["authority_refs"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["correct_key"]):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not isinstance(payload["source_values"], Mapping) or not isinstance(payload["target_values"], Mapping):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if not _microsoft_learn_refs(payload["authority_refs"]):
        return CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING
    return None


def _validate_spec(spec: Mapping[str, Any]) -> CorrectionFailureReason | None:
    if "correction_class" in spec:
        return CorrectionFailureReason.UNKNOWN_FIELD
    shape = _unknown_or_missing(spec, _SPEC_FIELDS)
    if shape is not None:
        return shape
    if spec["schema_version"] != SCHEMA_VERSION or spec["work_id"] != WORK_ID:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if spec["source_validation_work_id"] != SOURCE_VALIDATION_WORK_ID:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if spec["superseding_validation_work_ids"] != [Q219_REPLACEMENT_WORK_ID]:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if spec["source_bank"] != SOURCE_BANK_FILENAME:
        return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
    if spec["source_bank_raw_sha256"] != EXPECTED_SOURCE_BANK_SHA256:
        return CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH
    if spec["source_bank_content_fingerprint"] != EXPECTED_SOURCE_CONTENT_FINGERPRINT:
        return CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH
    if spec["source_manifest_payload_sha256"] != EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256:
        return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
    if spec["question_count"] != REQUIRED_QUESTION_COUNT:
        return CorrectionFailureReason.QUESTION_COUNT_MISMATCH
    if spec["target_ids"] != list(TARGET_IDS):
        return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
    if _canonical_json(spec["currentness_requirements"]) != _canonical_json(CURRENTNESS_REQUIREMENTS):
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if canonical_manifest_sha256(spec) != spec["payload_sha256"]:
        return CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH
    if spec["payload_sha256"] != EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256:
        return CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH
    corrections = spec["corrections"]
    if not isinstance(corrections, list) or len(corrections) != len(TARGET_IDS):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    seen: set[str] = set()
    for entry in corrections:
        entry_reason = _validate_correction_entry(entry)
        if entry_reason is not None:
            return entry_reason
        question_id = str(entry["question_id"])
        if question_id in seen or question_id not in TARGET_IDS:
            return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
        seen.add(question_id)
        expected_semantic = Q219_REPLACEMENT_WORK_ID if question_id == "sc900_mlc_q219" else SOURCE_VALIDATION_WORK_ID
        if entry["semantic_validation_work_id"] != expected_semantic:
            return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if [str(entry["question_id"]) for entry in corrections] != list(TARGET_IDS):
        return CorrectionFailureReason.QUESTION_ORDER_MISMATCH
    return None


def _validate_currentness(record: Mapping[str, Any]) -> CorrectionFailureReason | None:
    shape = _unknown_or_missing(record, _CURRENTNESS_FIELDS)
    if shape is not None:
        return shape
    if record["schema_version"] != 1 or record["work_id"] != WORK_ID:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if record["overall_status"] != "PASS":
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if record["q219_prior_device_sync_failure_provenance"] is not True:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if record["q219_replacement_pass_provenance"] is not True:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if record["q219_prior_failure_work_id"] != Q219_PRIOR_CURRENTNESS_WORK_ID:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if record["q219_replacement_work_id"] != Q219_REPLACEMENT_WORK_ID:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if canonical_manifest_sha256(record) != record["payload_sha256"]:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if record["payload_sha256"] != EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    targets = record["targets"]
    if not isinstance(targets, list) or [row.get("question_id") for row in targets] != CURRENTNESS_QUESTION_IDS:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    for row in targets:
        if not isinstance(row, Mapping):
            return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
        row_shape = _unknown_or_missing(row, _CURRENTNESS_TARGET_FIELDS)
        if row_shape is not None:
            return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
        if row["status"] != "PASS" or not _microsoft_learn_refs(row["authority_refs"]):
            return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
        if row["question_id"] == "sc900_mlc_q219" and row["superseding_work_id_if_any"] != Q219_REPLACEMENT_WORK_ID:
            return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    return None


def _changed_fields(source: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    changed: list[str] = []
    for field in AUTHORIZED_CONTENT_FIELDS:
        if _canonical_json(source.get(field)) != _canonical_json(target.get(field)):
            changed.append(field)
    return changed


def _pair_protected_reason(source: Mapping[str, Any], target: Mapping[str, Any]) -> CorrectionFailureReason | None:
    if _correct_key(source) != _correct_key(target):
        return CorrectionFailureReason.CORRECT_KEY_CHANGED
    if _canonical_json(source.get("objective_code")) != _canonical_json(target.get("objective_code")):
        return CorrectionFailureReason.OBJECTIVE_CHANGED
    if _canonical_json(source.get("tested_decision")) != _canonical_json(target.get("tested_decision")):
        return CorrectionFailureReason.TESTED_DECISION_CHANGED
    skip = set(AUTHORIZED_CONTENT_FIELDS)
    keys = set(source.keys()) | set(target.keys())
    for key in sorted(keys):
        if key in skip:
            continue
        if _canonical_json(source.get(key)) != _canonical_json(target.get(key)):
            return CorrectionFailureReason.NONPERMITTED_FIELD_CHANGED
    return None


def _admit_historical_nine_question_correction(
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
    if not isinstance(manifest, Mapping):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if manifest.get("manifest_kind") == "sc900_content_revision_equivalence" or manifest.get("schema_version") == 1:
        return _fail(CorrectionFailureReason.AUTHORITY_KIND_MISMATCH)
    shape = _unknown_or_missing(manifest, _MANIFEST_FIELDS)
    if shape is not None:
        return _fail(shape)
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["manifest_kind"] != MANIFEST_KIND
        or manifest["continuity_policy"] != CONTINUITY_POLICY
        or manifest["permitted_change_class"] != PERMITTED_CHANGE_CLASS
        or manifest["work_id"] != WORK_ID
    ):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if canonical_manifest_sha256(manifest) != str(manifest["payload_sha256"]):
        return _fail(CorrectionFailureReason.MANIFEST_HASH_MISMATCH)
    spec_reason = _validate_spec(spec)
    if spec_reason is not None:
        return _fail(spec_reason)
    currentness_reason = _validate_currentness(currentness_record)
    if currentness_reason is not None:
        return _fail(currentness_reason)
    source_bind = _validate_bank_binding(manifest["source_bank"])
    if source_bind is not None:
        return _fail(source_bind)
    target_bind = _validate_bank_binding(manifest["target_bank"])
    if target_bind is not None:
        return _fail(target_bind)
    spec_bind = _validate_artifact_binding(manifest["correction_spec"])
    if spec_bind is not None:
        return _fail(spec_bind)
    currentness_bind = _validate_artifact_binding(manifest["currentness_record"])
    if currentness_bind is not None:
        return _fail(currentness_bind)
    edges = manifest["edges"]
    if not isinstance(edges, list) or len(edges) != len(TARGET_IDS):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    for edge in edges:
        edge_reason = _validate_edge(edge)
        if edge_reason is not None:
            return _fail(edge_reason)
        if not contained_relative_path(str(edge["review_artifact"]), review_root):
            return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    try:
        source_file_hash = sha256_file(source_bank_path)
        target_file_hash = sha256_file(target_bank_path)
        spec_file_hash = sha256_file(spec_path)
        currentness_file_hash = sha256_file(currentness_path)
    except OSError:
        return _fail(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if source_file_hash != EXPECTED_SOURCE_BANK_SHA256 or source_file_hash != manifest["source_bank"]["file_sha256"]:
        return _fail(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if target_file_hash != manifest["target_bank"]["file_sha256"]:
        return _fail(CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if spec_file_hash != manifest["correction_spec"]["file_sha256"]:
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if currentness_file_hash != manifest["currentness_record"]["file_sha256"]:
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)
    if manifest["correction_spec"]["payload_sha256"] != EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256:
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if manifest["currentness_record"]["payload_sha256"] != EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256:
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)
    source_bank, source_error = _read_object(source_bank_path, CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if source_error is not None:
        return source_error
    target_bank, target_error = _read_object(target_bank_path, CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if target_error is not None:
        return target_error
    assert source_bank is not None and target_bank is not None
    source_questions = source_bank.get("questions")
    target_questions = target_bank.get("questions")
    if not isinstance(source_questions, list) or not isinstance(target_questions, list):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if (
        len(source_questions) != REQUIRED_QUESTION_COUNT
        or len(target_questions) != REQUIRED_QUESTION_COUNT
        or manifest["source_bank"]["question_count"] != REQUIRED_QUESTION_COUNT
        or manifest["target_bank"]["question_count"] != REQUIRED_QUESTION_COUNT
    ):
        return _fail(CorrectionFailureReason.QUESTION_COUNT_MISMATCH)
    source_ids = [canonical_question_id(question) for question in source_questions]
    target_ids = [canonical_question_id(question) for question in target_questions]
    if source_ids != target_ids:
        return _fail(CorrectionFailureReason.QUESTION_ORDER_MISMATCH)
    source_index, source_id_reason = _index_questions(source_questions)
    if source_id_reason is not None:
        return _fail(source_id_reason)
    target_index, target_id_reason = _index_questions(target_questions)
    if target_id_reason is not None:
        return _fail(target_id_reason)
    if set(source_index) != set(target_index):
        return _fail(CorrectionFailureReason.QUESTION_ID_SET_MISMATCH)
    source_meta = {key: value for key, value in source_bank.items() if key != "questions"}
    target_meta = {key: value for key, value in target_bank.items() if key != "questions"}
    if _canonical_json(source_meta) != _canonical_json(target_meta):
        return _fail(CorrectionFailureReason.BANK_METADATA_MISMATCH)
    source_fp = bank_content_fingerprint(source_questions)
    target_fp = bank_content_fingerprint(target_questions)
    if source_fp != EXPECTED_SOURCE_CONTENT_FINGERPRINT or source_fp != manifest["source_bank"]["content_fingerprint"]:
        return _fail(CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH)
    if target_fp != manifest["target_bank"]["content_fingerprint"]:
        return _fail(CorrectionFailureReason.TARGET_BANK_FINGERPRINT_MISMATCH)
    spec_by_id = {str(entry["question_id"]): entry for entry in spec["corrections"]}
    actual_changed = [
        question_id
        for question_id in source_ids
        if question_content_fingerprint(source_index[question_id])
        != question_content_fingerprint(target_index[question_id])
    ]
    if set(actual_changed) != set(TARGET_IDS):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    admitted_edges: list[CorrectionEdge] = []
    prompt_changed: list[str] = []
    for edge in edges:
        question_id = str(edge["question_id"])
        if question_id not in spec_by_id:
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        protected = _pair_protected_reason(source_question, target_question)
        if protected is not None:
            return _fail(protected)
        actual_fields = _changed_fields(source_question, target_question)
        if actual_fields != list(edge["changed_fields"]) or actual_fields != list(
            spec_by_id[question_id]["authorized_changed_fields"]
        ):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if "prompt" in actual_fields:
            prompt_changed.append(question_id)
        from_fp = question_content_fingerprint(source_question)
        to_fp = question_content_fingerprint(target_question)
        if from_fp != edge["from_content_fingerprint"]:
            return _fail(CorrectionFailureReason.FROM_FINGERPRINT_MISMATCH)
        if to_fp != edge["to_content_fingerprint"]:
            return _fail(CorrectionFailureReason.TO_FINGERPRINT_MISMATCH)
        if question_id == "sc900_mlc_q219":
            if target_question.get("tested_decision") != Q219_TESTED_DECISION:
                return _fail(CorrectionFailureReason.TESTED_DECISION_CHANGED)
            prompt = str(target_question.get("prompt") or "")
            if SUPERSEDED_Q219_MARKER in prompt.casefold() and "earlier on-premises synchronization" not in prompt:
                return _fail(CorrectionFailureReason.Q219_SUPERSEDED_TARGET_IMPLEMENTED)
        review_path = review_root / str(edge["review_artifact"])
        review_payload, review_error = _read_object(review_path, CorrectionFailureReason.SEMANTIC_REVIEW_MISSING)
        if review_error is not None:
            return review_error
        assert review_payload is not None
        try:
            review_hash = sha256_file(review_path)
        except OSError:
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_MISSING)
        if review_hash != edge["review_artifact_sha256"]:
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        receipt_reason = _validate_receipt(review_payload)
        if receipt_reason is not None:
            return _fail(receipt_reason)
        if (
            review_payload["question_id"] != question_id
            or review_payload["from_content_fingerprint"] != from_fp
            or review_payload["to_content_fingerprint"] != to_fp
            or review_payload["correction_spec_payload_sha256"] != EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256
            or review_payload["disposition"] != REVIEW_DISPOSITION_APPROVED
        ):
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        if not _microsoft_learn_refs(edge["authority_refs"]) or not _microsoft_learn_refs(
            review_payload["authority_refs"]
        ):
            return _fail(CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING)
        if _canonical_json(review_payload["authority_refs"]) != _canonical_json(edge["authority_refs"]):
            return _fail(CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING)
        if _canonical_json(review_payload["before"]) != _canonical_json(spec_by_id[question_id]["source_values"]):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if _canonical_json(review_payload["after"]) != _canonical_json(spec_by_id[question_id]["target_values"]):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        target_explanations = target_question.get("choice_explanations")
        general = target_question.get("general_explanation")
        if not _exact_ad_mapping(target_explanations) or not isinstance(target_explanations, Mapping):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if any(target_explanations[letter] != general for letter in CHOICE_LABELS):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        admitted_edges.append(
            CorrectionEdge(
                question_id=question_id,
                from_content_fingerprint=from_fp,
                to_content_fingerprint=to_fp,
                changed_fields=tuple(actual_fields),
                review_artifact=str(edge["review_artifact"]),
                review_artifact_sha256=str(edge["review_artifact_sha256"]),
                authority_refs=tuple(str(item) for item in edge["authority_refs"]),
            )
        )
    if prompt_changed != list(PROMPT_CHANGED_IDS):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    if [edge.question_id for edge in admitted_edges] != list(TARGET_IDS):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    admitted = AdmittedCorrectionRevision(
        manifest_kind=MANIFEST_KIND,
        continuity_policy=CONTINUITY_POLICY,
        permitted_change_class=PERMITTED_CHANGE_CLASS,
        manifest_sha256=str(manifest["payload_sha256"]),
        source_bank_filename=str(manifest["source_bank"]["filename"]),
        source_bank_file_sha256=str(manifest["source_bank"]["file_sha256"]),
        source_bank_content_fingerprint=source_fp,
        target_bank_filename=str(manifest["target_bank"]["filename"]),
        target_bank_file_sha256=str(manifest["target_bank"]["file_sha256"]),
        target_bank_content_fingerprint=target_fp,
        correction_spec_payload_sha256=EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256,
        currentness_record_payload_sha256=EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256,
        edges=tuple(admitted_edges),
    )
    return CorrectionAdmissionResult(AdmissionStatus.PASS, (), admitted)


def _final_changed_fields(source: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    fields = set(source) | set(target)
    return sorted(field for field in fields if _canonical_json(source.get(field)) != _canonical_json(target.get(field)))


def _validate_final_spec(spec: Mapping[str, Any]) -> CorrectionFailureReason | None:
    shape = _unknown_or_missing(spec, _FINAL_SPEC_FIELDS)
    if shape is not None:
        return shape
    if spec["schema_version"] != SCHEMA_VERSION or spec["work_id"] != FINAL_TWO_QUESTION_WORK_ID:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if spec["source_bank"] != FINAL_TWO_QUESTION_SOURCE_BANK_FILENAME:
        return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
    if spec["source_bank_raw_sha256"] != FINAL_TWO_QUESTION_SOURCE_SHA256:
        return CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH
    if spec["source_bank_content_fingerprint"] != FINAL_TWO_QUESTION_SOURCE_FINGERPRINT:
        return CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH
    if spec["question_count"] != REQUIRED_QUESTION_COUNT:
        return CorrectionFailureReason.QUESTION_COUNT_MISMATCH
    if spec["target_ids"] != list(FINAL_TWO_QUESTION_IDS):
        return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
    if _canonical_json(spec["currentness_requirements"]) != _canonical_json(_FINAL_CURRENTNESS_REQUIREMENTS):
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if canonical_manifest_sha256(spec) != spec["payload_sha256"]:
        return CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH
    if spec["payload_sha256"] != FINAL_TWO_QUESTION_SPEC_SHA256:
        return CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH
    corrections = spec["corrections"]
    if not isinstance(corrections, list) or [
        row.get("question_id") for row in corrections if isinstance(row, Mapping)
    ] != list(FINAL_TWO_QUESTION_IDS):
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    for entry in corrections:
        entry_reason = _validate_correction_entry(entry)
        if entry_reason is not None:
            return entry_reason
        if entry["authorized_changed_fields"] != list(FINAL_TWO_QUESTION_AUTHORIZED_FIELDS):
            return CorrectionFailureReason.NONPERMITTED_FIELD_CHANGED
        if entry["semantic_validation_work_id"] != FINAL_TWO_QUESTION_WORK_ID:
            return CorrectionFailureReason.SCHEMA_UNSUPPORTED
        if entry["final_validation_status"] != REVIEW_STATUS_APPROVED:
            return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_final_currentness(record: Mapping[str, Any]) -> CorrectionFailureReason | None:
    shape = _unknown_or_missing(record, _FINAL_CURRENTNESS_FIELDS)
    if shape is not None:
        return shape
    if record["schema_version"] != 1 or record["work_id"] != FINAL_TWO_QUESTION_WORK_ID:
        return CorrectionFailureReason.SCHEMA_UNSUPPORTED
    if record["source_bank"] != FINAL_TWO_QUESTION_SOURCE_BANK_FILENAME:
        return CorrectionFailureReason.SOURCE_IDENTITY_INVALID
    if record["source_bank_raw_sha256"] != FINAL_TWO_QUESTION_SOURCE_SHA256:
        return CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH
    if record["source_bank_content_fingerprint"] != FINAL_TWO_QUESTION_SOURCE_FINGERPRINT:
        return CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH
    if record["overall_status"] != "PASS":
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if canonical_manifest_sha256(record) != record["payload_sha256"]:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    if record["payload_sha256"] != FINAL_TWO_QUESTION_CURRENTNESS_SHA256:
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    targets = record["targets"]
    if not isinstance(targets, list) or [row.get("question_id") for row in targets if isinstance(row, Mapping)] != list(
        FINAL_TWO_QUESTION_IDS
    ):
        return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    for row in targets:
        if (
            not isinstance(row, Mapping)
            or row.get("status") != "PASS"
            or not _microsoft_learn_refs(row.get("authority_refs", ()))
        ):
            return CorrectionFailureReason.CURRENTNESS_GATE_FAILED
    return None


def _admit_final_two_question_correction(
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
    shape = _unknown_or_missing(manifest, _MANIFEST_FIELDS)
    if shape is not None:
        return _fail(shape)
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["manifest_kind"] != MANIFEST_KIND
        or manifest["work_id"] != FINAL_TWO_QUESTION_WORK_ID
        or manifest["continuity_policy"] != CONTINUITY_POLICY
        or manifest["permitted_change_class"] != PERMITTED_CHANGE_CLASS
    ):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if canonical_manifest_sha256(manifest) != str(manifest["payload_sha256"]):
        return _fail(CorrectionFailureReason.MANIFEST_HASH_MISMATCH)
    source_bind = _validate_bank_binding(manifest["source_bank"])
    if source_bind is not None:
        return _fail(source_bind)
    target_bind = _validate_bank_binding(manifest["target_bank"])
    if target_bind is not None:
        return _fail(target_bind)
    if manifest["source_bank"]["filename"] != FINAL_TWO_QUESTION_SOURCE_BANK_FILENAME:
        return _fail(CorrectionFailureReason.SOURCE_IDENTITY_INVALID)
    if manifest["target_bank"]["filename"] != FINAL_TWO_QUESTION_TARGET_BANK_FILENAME:
        return _fail(CorrectionFailureReason.SOURCE_IDENTITY_INVALID)
    if manifest["source_bank"]["file_sha256"] != FINAL_TWO_QUESTION_SOURCE_SHA256:
        return _fail(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if manifest["source_bank"]["content_fingerprint"] != FINAL_TWO_QUESTION_SOURCE_FINGERPRINT:
        return _fail(CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH)
    if manifest["target_bank"]["file_sha256"] != FINAL_TWO_QUESTION_TARGET_SHA256:
        return _fail(CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if manifest["target_bank"]["content_fingerprint"] != FINAL_TWO_QUESTION_TARGET_FINGERPRINT:
        return _fail(CorrectionFailureReason.TARGET_BANK_FINGERPRINT_MISMATCH)
    spec_bind = _validate_artifact_binding(manifest["correction_spec"])
    if spec_bind is not None:
        return _fail(spec_bind)
    currentness_bind = _validate_artifact_binding(manifest["currentness_record"])
    if currentness_bind is not None:
        return _fail(currentness_bind)
    spec_reason = _validate_final_spec(spec)
    if spec_reason is not None:
        return _fail(spec_reason)
    currentness_reason = _validate_final_currentness(currentness_record)
    if currentness_reason is not None:
        return _fail(currentness_reason)
    if manifest["correction_spec"]["payload_sha256"] != FINAL_TWO_QUESTION_SPEC_SHA256:
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if manifest["currentness_record"]["payload_sha256"] != FINAL_TWO_QUESTION_CURRENTNESS_SHA256:
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)
    edges = manifest["edges"]
    if not isinstance(edges, list) or [edge.get("question_id") for edge in edges if isinstance(edge, Mapping)] != list(
        FINAL_TWO_QUESTION_IDS
    ):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    for edge in edges:
        edge_reason = _validate_edge(edge)
        if edge_reason is not None:
            return _fail(edge_reason)
        if list(edge["changed_fields"]) != list(FINAL_TWO_QUESTION_AUTHORIZED_FIELDS):
            return _fail(CorrectionFailureReason.NONPERMITTED_FIELD_CHANGED)
        if not contained_relative_path(str(edge["review_artifact"]), review_root):
            return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    try:
        source_file_hash = sha256_file(source_bank_path)
        spec_file_hash = sha256_file(spec_path)
        currentness_file_hash = sha256_file(currentness_path)
    except OSError:
        return _fail(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if (
        source_file_hash != FINAL_TWO_QUESTION_SOURCE_SHA256
        or source_file_hash != manifest["source_bank"]["file_sha256"]
    ):
        return _fail(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if spec_file_hash != manifest["correction_spec"]["file_sha256"]:
        return _fail(CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH)
    if currentness_file_hash != manifest["currentness_record"]["file_sha256"]:
        return _fail(CorrectionFailureReason.CURRENTNESS_GATE_FAILED)
    source_bank, source_error = _read_object(source_bank_path, CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if source_error is not None:
        return source_error
    target_bank, target_error = _read_object(target_bank_path, CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if target_error is not None:
        return target_error
    assert source_bank is not None and target_bank is not None
    source_questions = source_bank.get("questions")
    target_questions = target_bank.get("questions")
    if not isinstance(source_questions, list) or not isinstance(target_questions, list):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if (
        len(source_questions) != REQUIRED_QUESTION_COUNT
        or len(target_questions) != REQUIRED_QUESTION_COUNT
        or manifest["source_bank"]["question_count"] != REQUIRED_QUESTION_COUNT
        or manifest["target_bank"]["question_count"] != REQUIRED_QUESTION_COUNT
    ):
        return _fail(CorrectionFailureReason.QUESTION_COUNT_MISMATCH)
    source_ids = [canonical_question_id(question) for question in source_questions]
    target_ids = [canonical_question_id(question) for question in target_questions]
    if source_ids != target_ids:
        return _fail(CorrectionFailureReason.QUESTION_ORDER_MISMATCH)
    source_index, source_id_reason = _index_questions(source_questions)
    if source_id_reason is not None:
        return _fail(source_id_reason)
    target_index, target_id_reason = _index_questions(target_questions)
    if target_id_reason is not None:
        return _fail(target_id_reason)
    source_meta = {key: value for key, value in source_bank.items() if key != "questions"}
    target_meta = {key: value for key, value in target_bank.items() if key != "questions"}
    if _canonical_json(source_meta) != _canonical_json(target_meta):
        return _fail(CorrectionFailureReason.BANK_METADATA_MISMATCH)
    source_fp = bank_content_fingerprint(source_questions)
    if (
        source_fp != FINAL_TWO_QUESTION_SOURCE_FINGERPRINT
        or source_fp != manifest["source_bank"]["content_fingerprint"]
    ):
        return _fail(CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH)
    spec_by_id = {str(entry["question_id"]): entry for entry in spec["corrections"]}
    actual_changed = [
        question_id
        for question_id in source_ids
        if question_content_fingerprint(source_index[question_id])
        != question_content_fingerprint(target_index[question_id])
    ]
    if actual_changed != list(FINAL_TWO_QUESTION_IDS):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    admitted_edges: list[CorrectionEdge] = []
    for edge in edges:
        question_id = str(edge["question_id"])
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        if _correct_key(source_question) != _correct_key(target_question):
            return _fail(CorrectionFailureReason.CORRECT_KEY_CHANGED)
        if source_question.get("objective_code") != target_question.get("objective_code"):
            return _fail(CorrectionFailureReason.OBJECTIVE_CHANGED)
        if source_question.get("tested_decision") != target_question.get("tested_decision"):
            return _fail(CorrectionFailureReason.TESTED_DECISION_CHANGED)
        if canonical_question_id(source_question) != canonical_question_id(target_question):
            return _fail(CorrectionFailureReason.QUESTION_ID_SET_MISMATCH)
        changed_fields = _final_changed_fields(source_question, target_question)
        if changed_fields != list(FINAL_TWO_QUESTION_AUTHORIZED_FIELDS) or changed_fields != list(
            edge["changed_fields"]
        ):
            return _fail(CorrectionFailureReason.NONPERMITTED_FIELD_CHANGED)
        if changed_fields != list(spec_by_id[question_id]["authorized_changed_fields"]):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        choices = target_question.get("choices")
        explanations = target_question.get("choice_explanations")
        if not _exact_ad_mapping(choices) or not isinstance(choices, Mapping):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if len({str(value).casefold() for value in choices.values()}) != 4:
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if not _exact_ad_mapping(explanations) or not isinstance(explanations, Mapping):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if any(not str(explanations[letter]).strip() for letter in CHOICE_LABELS):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        from_fp = question_content_fingerprint(source_question)
        to_fp = question_content_fingerprint(target_question)
        if from_fp != edge["from_content_fingerprint"]:
            return _fail(CorrectionFailureReason.FROM_FINGERPRINT_MISMATCH)
        if to_fp != edge["to_content_fingerprint"]:
            return _fail(CorrectionFailureReason.TO_FINGERPRINT_MISMATCH)
        review_path = review_root / str(edge["review_artifact"])
        review_payload, review_error = _read_object(review_path, CorrectionFailureReason.SEMANTIC_REVIEW_MISSING)
        if review_error is not None:
            return review_error
        assert review_payload is not None
        try:
            review_hash = sha256_file(review_path)
        except OSError:
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_MISSING)
        if review_hash != edge["review_artifact_sha256"]:
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        receipt_reason = _validate_receipt(review_payload)
        if receipt_reason is not None:
            return _fail(receipt_reason)
        if (
            review_payload["question_id"] != question_id
            or review_payload["from_content_fingerprint"] != from_fp
            or review_payload["to_content_fingerprint"] != to_fp
            or review_payload["correction_spec_payload_sha256"] != FINAL_TWO_QUESTION_SPEC_SHA256
            or review_payload["disposition"] != REVIEW_DISPOSITION_APPROVED
        ):
            return _fail(CorrectionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        if not _microsoft_learn_refs(edge["authority_refs"]) or not _microsoft_learn_refs(
            review_payload["authority_refs"]
        ):
            return _fail(CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING)
        if _canonical_json(review_payload["authority_refs"]) != _canonical_json(edge["authority_refs"]):
            return _fail(CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING)
        if _canonical_json(review_payload["before"]) != _canonical_json(spec_by_id[question_id]["source_values"]):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        if _canonical_json(review_payload["after"]) != _canonical_json(spec_by_id[question_id]["target_values"]):
            return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
        admitted_edges.append(
            CorrectionEdge(
                question_id=question_id,
                from_content_fingerprint=from_fp,
                to_content_fingerprint=to_fp,
                changed_fields=tuple(changed_fields),
                review_artifact=str(edge["review_artifact"]),
                review_artifact_sha256=str(edge["review_artifact_sha256"]),
                authority_refs=tuple(str(item) for item in edge["authority_refs"]),
            )
        )
    try:
        target_file_hash = sha256_file(target_bank_path)
    except OSError:
        return _fail(CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if (
        target_file_hash != FINAL_TWO_QUESTION_TARGET_SHA256
        or target_file_hash != manifest["target_bank"]["file_sha256"]
    ):
        return _fail(CorrectionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    target_fp = bank_content_fingerprint(target_questions)
    if (
        target_fp != FINAL_TWO_QUESTION_TARGET_FINGERPRINT
        or target_fp != manifest["target_bank"]["content_fingerprint"]
    ):
        return _fail(CorrectionFailureReason.TARGET_BANK_FINGERPRINT_MISMATCH)
    if manifest["payload_sha256"] != FINAL_TWO_QUESTION_MANIFEST_SHA256:
        return _fail(CorrectionFailureReason.MANIFEST_HASH_MISMATCH)
    if [edge.question_id for edge in admitted_edges] != list(FINAL_TWO_QUESTION_IDS):
        return _fail(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE)
    admitted = AdmittedCorrectionRevision(
        manifest_kind=MANIFEST_KIND,
        continuity_policy=CONTINUITY_POLICY,
        permitted_change_class=PERMITTED_CHANGE_CLASS,
        manifest_sha256=str(manifest["payload_sha256"]),
        source_bank_filename=FINAL_TWO_QUESTION_SOURCE_BANK_FILENAME,
        source_bank_file_sha256=FINAL_TWO_QUESTION_SOURCE_SHA256,
        source_bank_content_fingerprint=source_fp,
        target_bank_filename=FINAL_TWO_QUESTION_TARGET_BANK_FILENAME,
        target_bank_file_sha256=FINAL_TWO_QUESTION_TARGET_SHA256,
        target_bank_content_fingerprint=target_fp,
        correction_spec_payload_sha256=FINAL_TWO_QUESTION_SPEC_SHA256,
        currentness_record_payload_sha256=FINAL_TWO_QUESTION_CURRENTNESS_SHA256,
        edges=tuple(admitted_edges),
    )
    return CorrectionAdmissionResult(AdmissionStatus.PASS, (), admitted)


def admit_content_correction(
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
    if not isinstance(manifest, Mapping):
        return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)
    if manifest.get("manifest_kind") == "sc900_content_revision_equivalence" or manifest.get("schema_version") == 1:
        return _fail(CorrectionFailureReason.AUTHORITY_KIND_MISMATCH)
    work_id = manifest.get("work_id")
    if work_id == WORK_ID:
        return _admit_historical_nine_question_correction(
            manifest,
            spec=spec,
            currentness_record=currentness_record,
            source_bank_path=source_bank_path,
            target_bank_path=target_bank_path,
            spec_path=spec_path,
            currentness_path=currentness_path,
            review_root=review_root,
        )
    if work_id == FINAL_TWO_QUESTION_WORK_ID:
        return _admit_final_two_question_correction(
            manifest,
            spec=spec,
            currentness_record=currentness_record,
            source_bank_path=source_bank_path,
            target_bank_path=target_bank_path,
            spec_path=spec_path,
            currentness_path=currentness_path,
            review_root=review_root,
        )
    shape = _unknown_or_missing(manifest, _MANIFEST_FIELDS)
    if shape is not None:
        return _fail(shape)
    return _fail(CorrectionFailureReason.SCHEMA_UNSUPPORTED)


def payload_sha256(payload: Mapping[str, Any]) -> str:
    return canonical_manifest_sha256(payload)


def canonical_file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
