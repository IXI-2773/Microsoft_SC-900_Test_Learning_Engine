from __future__ import annotations

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
    parse_json_duplicate_safe,
    sha256_file,
)
from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint

SCHEMA_VERSION = 2
MANIFEST_KIND = "sc900_content_revision_explanation"
PERMITTED_CHANGE_CLASS = "EXPLANATION_ONLY_INSTRUCTIONAL_REVISION"
CONTINUITY_POLICY = "FULL_CONTINUITY_EXPLANATION_ONLY"
WORK_ID = "SC900-EXPLANATION-IMPLEMENTATION-TRANCHE-1-STALE-DISTRACTOR-REFERENCE-IMPLEMENTATION-001"
SEMANTIC_REVIEW_WORK_ID = "SC900-QUESTION-EXPLANATION-QUALITY-FIRST-TRANCHE-SEMANTIC-REVIEW-CHAT-001"
SOURCE_BANK_FILENAME = "sc900_bank_v8_content_correction_001.json"
TARGET_BANK_FILENAME = "sc900_bank_v8_explanation_tranche_1.json"
EXPECTED_SOURCE_BANK_SHA256 = "cd699a0e8af7c366bf5672bb2b1d90547c7071e87a47cbd766512bef59b2c791"
EXPECTED_SOURCE_CONTENT_FINGERPRINT = "a0f0f57cd3919863d7878a02949c8862c6a31dbbc9ce0ee4ffc6f84a91c9358d"
REQUIRED_QUESTION_COUNT = 454
AUTHORIZED_CHANGED_FIELDS = ("choice_explanations", "general_explanation")
MS_LEARN_PREFIX = "https://learn.microsoft.com/"
Q118_WORK_ID = "SC900-EXPLANATION-Q118-POST-CORRECTION-AUTHOR-NOTE-REPAIR-001"
Q118_SEMANTIC_REVIEW_WORK_ID = "SC900-EXPLANATION-Q118-POST-CORRECTION-AUTHOR-NOTE-REPAIR-001"
Q118_SOURCE_BANK_FILENAME = "sc900_bank_v8_explanation_tranche_1.json"
Q118_TARGET_BANK_FILENAME = "sc900_bank_v8_explanation_q118_repair.json"
Q118_TARGET_COUNT = 1
Q118_WORDING_AUTHORITY = "EXPLICIT_IMPLEMENTATION_DIRECTIVE"
Q118_SEMANTIC_REVIEW_DISPOSITION = "EXPLICIT_IMPLEMENTATION_DIRECTIVE"


@dataclass(frozen=True, slots=True)
class ExplanationPackageProfile:
    work_id: str
    semantic_review_work_id: str
    source_bank_filename: str
    target_bank_filename: str
    target_count: int
    semantic_review_disposition: str = "APPROVED"
    wording_authority: str = ""


TRANCHE_1_PROFILE = ExplanationPackageProfile(
    work_id=WORK_ID,
    semantic_review_work_id=SEMANTIC_REVIEW_WORK_ID,
    source_bank_filename=SOURCE_BANK_FILENAME,
    target_bank_filename=TARGET_BANK_FILENAME,
    target_count=48,
)
Q118_PROFILE = ExplanationPackageProfile(
    work_id=Q118_WORK_ID,
    semantic_review_work_id=Q118_SEMANTIC_REVIEW_WORK_ID,
    source_bank_filename=Q118_SOURCE_BANK_FILENAME,
    target_bank_filename=Q118_TARGET_BANK_FILENAME,
    target_count=Q118_TARGET_COUNT,
    semantic_review_disposition=Q118_SEMANTIC_REVIEW_DISPOSITION,
    wording_authority=Q118_WORDING_AUTHORITY,
)
EXPLANATION_PACKAGE_PROFILES = {
    TRANCHE_1_PROFILE.work_id: TRANCHE_1_PROFILE,
    Q118_PROFILE.work_id: Q118_PROFILE,
}


class ExplanationFailureReason(StrEnum):
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    MISSING_FIELD = "MISSING_FIELD"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    MANIFEST_HASH_MISMATCH = "MANIFEST_HASH_MISMATCH"
    AUTHORITY_KIND_MISMATCH = "AUTHORITY_KIND_MISMATCH"
    SOURCE_BANK_FILE_HASH_MISMATCH = "SOURCE_BANK_FILE_HASH_MISMATCH"
    SOURCE_CONTENT_FINGERPRINT_MISMATCH = "SOURCE_CONTENT_FINGERPRINT_MISMATCH"
    TARGET_BANK_FILE_HASH_MISMATCH = "TARGET_BANK_FILE_HASH_MISMATCH"
    TARGET_CONTENT_FINGERPRINT_MISMATCH = "TARGET_CONTENT_FINGERPRINT_MISMATCH"
    QUESTION_COUNT_MISMATCH = "QUESTION_COUNT_MISMATCH"
    QUESTION_ORDER_MISMATCH = "QUESTION_ORDER_MISMATCH"
    SPEC_MISSING = "SPEC_MISSING"
    SPEC_HASH_MISMATCH = "SPEC_HASH_MISMATCH"
    LEDGER_MISSING = "LEDGER_MISSING"
    LEDGER_HASH_MISMATCH = "LEDGER_HASH_MISMATCH"
    SEMANTIC_REVIEW_BINDING_MISMATCH = "SEMANTIC_REVIEW_BINDING_MISMATCH"
    SOURCE_FINGERPRINT_MISMATCH = "SOURCE_FINGERPRINT_MISMATCH"
    TARGET_FINGERPRINT_MISMATCH = "TARGET_FINGERPRINT_MISMATCH"
    NONPERMITTED_FIELD_CHANGED = "NONPERMITTED_FIELD_CHANGED"
    EXACT_CHANGED_FIELDS_MISMATCH = "EXACT_CHANGED_FIELDS_MISMATCH"
    AUTHORITY_EVIDENCE_MISSING = "AUTHORITY_EVIDENCE_MISSING"
    INVALID_SPARSE_FEEDBACK = "INVALID_SPARSE_FEEDBACK"
    REVIEW_NOT_APPROVED = "REVIEW_NOT_APPROVED"
    TARGET_SET_MISMATCH = "TARGET_SET_MISMATCH"


class ContentExplanationManifestError(ValueError):
    def __init__(self, reason: ExplanationFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason.value if not detail else f"{reason.value}: {detail}")


@dataclass(frozen=True, slots=True)
class ExplanationEdge:
    question_id: str
    from_content_fingerprint: str
    to_content_fingerprint: str
    changed_fields: tuple[str, ...]
    review_entry_identity: str
    authority_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AdmittedExplanationRevision:
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
    revision_spec_payload_sha256: str
    semantic_review_ledger_payload_sha256: str
    edges: tuple[ExplanationEdge, ...]

    def permits_fingerprint_transition(self, question_id: str, from_fp: str, to_fp: str) -> bool:
        return any(
            edge.question_id == question_id
            and edge.from_content_fingerprint == from_fp
            and edge.to_content_fingerprint == to_fp
            for edge in self.edges
        )


@dataclass(frozen=True, slots=True)
class ExplanationAdmissionResult:
    status: AdmissionStatus
    reasons: tuple[ExplanationFailureReason, ...]
    admitted: AdmittedExplanationRevision | None


def _fail(*reasons: ExplanationFailureReason) -> ExplanationAdmissionResult:
    return ExplanationAdmissionResult(AdmissionStatus.FAIL, reasons, None)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _unknown_or_missing(payload: Mapping[str, Any], required: Sequence[str]) -> ExplanationFailureReason | None:
    required_set = set(required)
    if any(key not in required_set for key in payload):
        return ExplanationFailureReason.UNKNOWN_FIELD
    if any(key not in payload for key in required):
        return ExplanationFailureReason.MISSING_FIELD
    return None


def _read_object(
    path: Path, missing: ExplanationFailureReason
) -> tuple[dict[str, Any] | None, ExplanationAdmissionResult | None]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None, _fail(missing)
    try:
        return parse_json_duplicate_safe(raw), None
    except ContentRevisionManifestError as exc:
        if exc.reason == RevisionFailureReason.DUPLICATE_JSON_KEY:
            return None, _fail(ExplanationFailureReason.DUPLICATE_JSON_KEY)
        return None, _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)


def _bank_questions(payload: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    questions = payload.get("questions")
    if not isinstance(questions, list) or not all(isinstance(q, Mapping) for q in questions):
        return None
    return questions


def _index(questions: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]] | None:
    result: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        qid = canonical_question_id(question)
        if not qid or qid in result:
            return None
        result[qid] = question
    return result


def _microsoft_refs(refs: Any) -> bool:
    return (
        isinstance(refs, list)
        and bool(refs)
        and all(isinstance(ref, str) and ref.strip() for ref in refs)
        and any(str(ref).startswith(MS_LEARN_PREFIX) for ref in refs)
    )


def _validate_sparse_feedback(question: Mapping[str, Any]) -> bool:
    general = question.get("general_explanation")
    feedback = question.get("choice_explanations")
    choices = question.get("choices")
    correct = question.get("correct") or []
    if not _nonempty(general) or not isinstance(feedback, Mapping) or not isinstance(choices, Mapping):
        return False
    if any(key not in choices for key in feedback):
        return False
    if any(not _nonempty(value) for value in feedback.values()):
        return False
    if any(key in set(correct) for key in feedback):
        return False
    return True


_MANIFEST_FIELDS = (
    "schema_version",
    "manifest_kind",
    "work_id",
    "continuity_policy",
    "permitted_change_class",
    "source_bank",
    "target_bank",
    "revision_spec",
    "semantic_review_ledger",
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
    "review_entry_identity",
    "authority_refs",
)


def _validate_binding(binding: Any, fields: Sequence[str]) -> bool:
    if not isinstance(binding, Mapping) or _unknown_or_missing(binding, fields) is not None:
        return False
    if not _nonempty(binding.get("filename")):
        return False
    for key in ("file_sha256", "content_fingerprint", "payload_sha256"):
        if key in binding and (not isinstance(binding[key], str) or len(binding[key]) != 64):
            return False
    if "question_count" in binding and binding["question_count"] != REQUIRED_QUESTION_COUNT:
        return False
    return True


def admit_explanation_revision(
    manifest: Mapping[str, Any],
    *,
    source_bank_path: Path,
    target_bank_path: Path,
    spec_path: Path,
    ledger_path: Path,
) -> ExplanationAdmissionResult:
    if not isinstance(manifest, Mapping):
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
    shape = _unknown_or_missing(manifest, _MANIFEST_FIELDS)
    if shape is not None:
        return _fail(shape)
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["manifest_kind"] != MANIFEST_KIND
        or manifest["continuity_policy"] != CONTINUITY_POLICY
        or manifest["permitted_change_class"] != PERMITTED_CHANGE_CLASS
    ):
        return _fail(ExplanationFailureReason.AUTHORITY_KIND_MISMATCH)
    profile = EXPLANATION_PACKAGE_PROFILES.get(manifest["work_id"]) if isinstance(manifest["work_id"], str) else None
    if profile is None:
        return _fail(ExplanationFailureReason.AUTHORITY_KIND_MISMATCH)
    if canonical_manifest_sha256(manifest) != manifest["payload_sha256"]:
        return _fail(ExplanationFailureReason.MANIFEST_HASH_MISMATCH)
    if not _validate_binding(manifest["source_bank"], _BANK_BINDING_FIELDS):
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
    if not _validate_binding(manifest["target_bank"], _BANK_BINDING_FIELDS):
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
    if not _validate_binding(manifest["revision_spec"], _ARTIFACT_BINDING_FIELDS):
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
    if not _validate_binding(manifest["semantic_review_ledger"], _ARTIFACT_BINDING_FIELDS):
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)

    source, error = _read_object(Path(source_bank_path), ExplanationFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if error is not None:
        return error
    target, error = _read_object(Path(target_bank_path), ExplanationFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if error is not None:
        return error
    spec, error = _read_object(Path(spec_path), ExplanationFailureReason.SPEC_MISSING)
    if error is not None:
        return error
    ledger, error = _read_object(Path(ledger_path), ExplanationFailureReason.LEDGER_MISSING)
    if error is not None:
        return error
    assert source is not None and target is not None and spec is not None and ledger is not None

    if sha256_file(source_bank_path) != manifest["source_bank"]["file_sha256"]:
        return _fail(ExplanationFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if sha256_file(target_bank_path) != manifest["target_bank"]["file_sha256"]:
        return _fail(ExplanationFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if sha256_file(spec_path) != manifest["revision_spec"]["file_sha256"]:
        return _fail(ExplanationFailureReason.SPEC_HASH_MISMATCH)
    if sha256_file(ledger_path) != manifest["semantic_review_ledger"]["file_sha256"]:
        return _fail(ExplanationFailureReason.LEDGER_HASH_MISMATCH)
    if canonical_manifest_sha256(spec) != manifest["revision_spec"]["payload_sha256"]:
        return _fail(ExplanationFailureReason.SPEC_HASH_MISMATCH)
    if canonical_manifest_sha256(ledger) != manifest["semantic_review_ledger"]["payload_sha256"]:
        return _fail(ExplanationFailureReason.LEDGER_HASH_MISMATCH)

    if (
        spec.get("work_id") != profile.work_id
        or spec.get("semantic_review_work_id") != profile.semantic_review_work_id
        or spec.get("permitted_change_class") != PERMITTED_CHANGE_CLASS
        or spec.get("continuity_policy") != CONTINUITY_POLICY
        or ledger.get("work_id") != profile.work_id
        or ledger.get("semantic_review_work_id") != profile.semantic_review_work_id
        or ledger.get("target_count") != profile.target_count
    ):
        return _fail(ExplanationFailureReason.SEMANTIC_REVIEW_BINDING_MISMATCH)
    if profile.wording_authority and (
        ledger.get("independent_pre_implementation_semantic_review") is not False
        or ledger.get("wording_authority") != profile.wording_authority
        or spec.get("independent_pre_implementation_semantic_review") is not False
        or spec.get("wording_authority") != profile.wording_authority
    ):
        return _fail(ExplanationFailureReason.SEMANTIC_REVIEW_BINDING_MISMATCH)

    source_questions = _bank_questions(source)
    target_questions = _bank_questions(target)
    if source_questions is None or target_questions is None:
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
    if len(source_questions) != REQUIRED_QUESTION_COUNT or len(target_questions) != REQUIRED_QUESTION_COUNT:
        return _fail(ExplanationFailureReason.QUESTION_COUNT_MISMATCH)
    source_ids = [canonical_question_id(q) for q in source_questions]
    target_ids = [canonical_question_id(q) for q in target_questions]
    if source_ids != target_ids:
        return _fail(ExplanationFailureReason.QUESTION_ORDER_MISMATCH)
    if bank_content_fingerprint(source_questions) != manifest["source_bank"]["content_fingerprint"]:
        return _fail(ExplanationFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH)
    if bank_content_fingerprint(target_questions) != manifest["target_bank"]["content_fingerprint"]:
        return _fail(ExplanationFailureReason.TARGET_CONTENT_FINGERPRINT_MISMATCH)
    if manifest["source_bank"]["filename"] != profile.source_bank_filename:
        return _fail(ExplanationFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH)
    if manifest["target_bank"]["filename"] != profile.target_bank_filename:
        return _fail(ExplanationFailureReason.TARGET_CONTENT_FINGERPRINT_MISMATCH)

    source_index = _index(source_questions)
    target_index = _index(target_questions)
    if source_index is None or target_index is None:
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)

    revisions = spec.get("revisions")
    edges = manifest.get("edges")
    ledger_entries = ledger.get("entries")
    if not isinstance(revisions, list) or not isinstance(edges, list) or not isinstance(ledger_entries, list):
        return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
    spec_by_id = {str(row.get("question_id")): row for row in revisions if isinstance(row, Mapping)}
    ledger_by_id = {str(row.get("question_id")): row for row in ledger_entries if isinstance(row, Mapping)}
    expected_ids = list(spec.get("target_ids") or [])
    if (
        len(expected_ids) != profile.target_count
        or set(spec_by_id) != set(expected_ids)
        or set(ledger_by_id) != set(expected_ids)
    ):
        return _fail(ExplanationFailureReason.TARGET_SET_MISMATCH)
    if len(edges) != profile.target_count:
        return _fail(ExplanationFailureReason.TARGET_SET_MISMATCH)

    actual_changed_ids = [qid for qid in source_ids if source_index[qid] != target_index[qid]]
    if set(actual_changed_ids) != set(expected_ids) or len(actual_changed_ids) != profile.target_count:
        return _fail(ExplanationFailureReason.TARGET_SET_MISMATCH)

    admitted_edges: list[ExplanationEdge] = []
    seen: set[str] = set()
    for edge in edges:
        if not isinstance(edge, Mapping) or _unknown_or_missing(edge, _EDGE_FIELDS) is not None:
            return _fail(ExplanationFailureReason.SCHEMA_UNSUPPORTED)
        qid = str(edge["question_id"])
        if qid in seen or qid not in spec_by_id or qid not in ledger_by_id:
            return _fail(ExplanationFailureReason.TARGET_SET_MISMATCH)
        seen.add(qid)
        if list(edge["changed_fields"]) != list(AUTHORIZED_CHANGED_FIELDS):
            return _fail(ExplanationFailureReason.EXACT_CHANGED_FIELDS_MISMATCH)
        if not _microsoft_refs(edge["authority_refs"]):
            return _fail(ExplanationFailureReason.AUTHORITY_EVIDENCE_MISSING)

        source_q = source_index[qid]
        target_q = target_index[qid]
        spec_row = spec_by_id[qid]
        ledger_row = ledger_by_id[qid]
        source_fp = question_content_fingerprint(source_q)
        target_fp = question_content_fingerprint(target_q)
        if source_fp != edge["from_content_fingerprint"] or source_fp != spec_row.get("source_content_fingerprint"):
            return _fail(ExplanationFailureReason.SOURCE_FINGERPRINT_MISMATCH)
        if target_fp != edge["to_content_fingerprint"] or target_fp != spec_row.get("target_content_fingerprint"):
            return _fail(ExplanationFailureReason.TARGET_FINGERPRINT_MISMATCH)

        changed_fields = sorted(key for key in set(source_q) | set(target_q) if source_q.get(key) != target_q.get(key))
        if changed_fields != list(AUTHORIZED_CHANGED_FIELDS):
            return _fail(ExplanationFailureReason.NONPERMITTED_FIELD_CHANGED, qid)

        if (
            target_q.get("general_explanation") != spec_row.get("target_general_explanation")
            or target_q.get("choice_explanations") != spec_row.get("target_choice_explanations")
            or source_q.get("general_explanation") != spec_row.get("source_general_explanation")
            or source_q.get("choice_explanations") != spec_row.get("source_choice_explanations")
        ):
            return _fail(ExplanationFailureReason.SEMANTIC_REVIEW_BINDING_MISMATCH)
        if not _validate_sparse_feedback(target_q):
            return _fail(ExplanationFailureReason.INVALID_SPARSE_FEEDBACK, qid)
        if (
            ledger_row.get("source_content_fingerprint") != source_fp
            or ledger_row.get("target_content_fingerprint") != target_fp
            or ledger_row.get("semantic_review_disposition") != profile.semantic_review_disposition
        ):
            return _fail(ExplanationFailureReason.REVIEW_NOT_APPROVED, qid)
        if profile.wording_authority and (
            ledger_row.get("independent_pre_implementation_semantic_review") is not False
            or ledger_row.get("wording_authority") != profile.wording_authority
            or ledger_row.get("semantic_review_disposition") != profile.wording_authority
        ):
            return _fail(ExplanationFailureReason.SEMANTIC_REVIEW_BINDING_MISMATCH, qid)
        if canonical_manifest_sha256(ledger_row) != edge["review_entry_identity"]:
            return _fail(ExplanationFailureReason.SEMANTIC_REVIEW_BINDING_MISMATCH, qid)
        if list(edge["authority_refs"]) != list(spec_row.get("authority_refs") or []):
            return _fail(ExplanationFailureReason.AUTHORITY_EVIDENCE_MISSING, qid)

        admitted_edges.append(
            ExplanationEdge(
                question_id=qid,
                from_content_fingerprint=source_fp,
                to_content_fingerprint=target_fp,
                changed_fields=tuple(edge["changed_fields"]),
                review_entry_identity=str(edge["review_entry_identity"]),
                authority_refs=tuple(str(x) for x in edge["authority_refs"]),
            )
        )

    admitted = AdmittedExplanationRevision(
        manifest_kind=MANIFEST_KIND,
        continuity_policy=CONTINUITY_POLICY,
        permitted_change_class=PERMITTED_CHANGE_CLASS,
        manifest_sha256=str(manifest["payload_sha256"]),
        source_bank_filename=str(manifest["source_bank"]["filename"]),
        source_bank_file_sha256=str(manifest["source_bank"]["file_sha256"]),
        source_bank_content_fingerprint=str(manifest["source_bank"]["content_fingerprint"]),
        target_bank_filename=str(manifest["target_bank"]["filename"]),
        target_bank_file_sha256=str(manifest["target_bank"]["file_sha256"]),
        target_bank_content_fingerprint=str(manifest["target_bank"]["content_fingerprint"]),
        revision_spec_payload_sha256=str(manifest["revision_spec"]["payload_sha256"]),
        semantic_review_ledger_payload_sha256=str(manifest["semantic_review_ledger"]["payload_sha256"]),
        edges=tuple(admitted_edges),
    )
    return ExplanationAdmissionResult(AdmissionStatus.PASS, (), admitted)
