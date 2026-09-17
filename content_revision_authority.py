from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint


class AdmissionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class RevisionFailureReason(StrEnum):
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    MISSING_FIELD = "MISSING_FIELD"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    MANIFEST_HASH_MISMATCH = "MANIFEST_HASH_MISMATCH"
    SOURCE_BANK_FILE_HASH_MISMATCH = "SOURCE_BANK_FILE_HASH_MISMATCH"
    TARGET_BANK_FILE_HASH_MISMATCH = "TARGET_BANK_FILE_HASH_MISMATCH"
    SOURCE_BANK_FINGERPRINT_MISMATCH = "SOURCE_BANK_FINGERPRINT_MISMATCH"
    TARGET_BANK_FINGERPRINT_MISMATCH = "TARGET_BANK_FINGERPRINT_MISMATCH"
    QUESTION_COUNT_MISMATCH = "QUESTION_COUNT_MISMATCH"
    QUESTION_ID_SET_MISMATCH = "QUESTION_ID_SET_MISMATCH"
    DUPLICATE_QUESTION_ID = "DUPLICATE_QUESTION_ID"
    UNDECLARED_CONTENT_CHANGE = "UNDECLARED_CONTENT_CHANGE"
    EXTRA_EQUIVALENCE_EDGE = "EXTRA_EQUIVALENCE_EDGE"
    DUPLICATE_EQUIVALENCE_EDGE = "DUPLICATE_EQUIVALENCE_EDGE"
    FROM_FINGERPRINT_MISMATCH = "FROM_FINGERPRINT_MISMATCH"
    TO_FINGERPRINT_MISMATCH = "TO_FINGERPRINT_MISMATCH"
    CORRECT_KEY_CHANGED = "CORRECT_KEY_CHANGED"
    CHOICE_LABEL_SET_CHANGED = "CHOICE_LABEL_SET_CHANGED"
    CHOICE_LETTER_MAPPING_CHANGED = "CHOICE_LETTER_MAPPING_CHANGED"
    PROMPT_CHANGED = "PROMPT_CHANGED"
    OBJECTIVE_CHANGED = "OBJECTIVE_CHANGED"
    DOMAIN_CHANGED = "DOMAIN_CHANGED"
    TOPICS_CHANGED = "TOPICS_CHANGED"
    TIER_CHANGED = "TIER_CHANGED"
    EXAM_ELIGIBILITY_CHANGED = "EXAM_ELIGIBILITY_CHANGED"
    QUESTION_TYPE_CHANGED = "QUESTION_TYPE_CHANGED"
    NONPERMITTED_FIELD_CHANGED = "NONPERMITTED_FIELD_CHANGED"
    SEMANTIC_REVIEW_MISSING = "SEMANTIC_REVIEW_MISSING"
    SEMANTIC_REVIEW_HASH_MISMATCH = "SEMANTIC_REVIEW_HASH_MISMATCH"
    SEMANTIC_EQUIVALENCE_NOT_APPROVED = "SEMANTIC_EQUIVALENCE_NOT_APPROVED"
    CHOICE_SEMANTICS_CHANGED = "CHOICE_SEMANTICS_CHANGED"
    AUTHORITY_EVIDENCE_MISSING = "AUTHORITY_EVIDENCE_MISSING"
    UNREGISTERED_MANIFEST = "UNREGISTERED_MANIFEST"
    REGISTRY_HASH_MISMATCH = "REGISTRY_HASH_MISMATCH"
    LINEAGE_INCOMPLETE = "LINEAGE_INCOMPLETE"
    LINEAGE_CONFLICT = "LINEAGE_CONFLICT"


class ContentRevisionManifestError(ValueError):
    def __init__(self, reason: RevisionFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason.value if not detail else f"{reason.value}: {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RevisionEdge:
    question_id: str
    from_content_fingerprint: str
    to_content_fingerprint: str
    review_artifact: str
    review_artifact_sha256: str


@dataclass(frozen=True, slots=True)
class AdmittedRevision:
    manifest_sha256: str
    source_bank_filename: str
    source_bank_file_sha256: str
    source_bank_content_fingerprint: str
    target_bank_filename: str
    target_bank_file_sha256: str
    target_bank_content_fingerprint: str
    edges: tuple[RevisionEdge, ...]

    def permits_fingerprint_transition(self, question_id: str, from_fp: str, to_fp: str) -> bool:
        return any(
            edge.question_id == question_id
            and edge.from_content_fingerprint == from_fp
            and edge.to_content_fingerprint == to_fp
            for edge in self.edges
        )


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    status: AdmissionStatus
    reasons: tuple[RevisionFailureReason, ...]
    admitted: AdmittedRevision | None


def _reject_duplicate_object_keys(pairs: list[tuple[Any, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        name = str(key)
        if name in seen:
            raise ContentRevisionManifestError(RevisionFailureReason.DUPLICATE_JSON_KEY, name)
        seen.add(name)
        payload[name] = value
    return payload


def parse_json_duplicate_safe(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw, object_pairs_hook=_reject_duplicate_object_keys)
    except ContentRevisionManifestError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ContentRevisionManifestError(RevisionFailureReason.SCHEMA_UNSUPPORTED, str(exc)) from exc
    if not isinstance(parsed, dict):
        raise ContentRevisionManifestError(RevisionFailureReason.SCHEMA_UNSUPPORTED, "top-level object required")
    return parsed


def canonical_manifest_sha256(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "payload_sha256"}
    serialized = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


REQUIRED_QUESTION_COUNT = 454
CHOICE_LABELS = ("A", "B", "C", "D")
MANIFEST_KIND = "sc900_content_revision_equivalence"
CONTINUITY_POLICY = "FULL_CONTINUITY"
PERMITTED_CHANGE_CLASS = "WORDING_ONLY_LENGTH_REBALANCE"
MS_LEARN_PREFIX = "https://learn.microsoft.com/"
REVIEW_STATUS_APPROVED = "APPROVED"
REVIEW_DISPOSITION_APPROVED = "APPROVED_FOR_FULL_CONTINUITY"
SEMANTIC_EQUIVALENT = "EQUIVALENT"
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_MANIFEST_FIELDS = (
    "schema_version",
    "manifest_kind",
    "work_id",
    "continuity_policy",
    "source_bank",
    "target_bank",
    "permitted_change_class",
    "edges",
    "payload_sha256",
)
_BANK_BINDING_FIELDS = ("filename", "file_sha256", "content_fingerprint", "question_count")
_EDGE_FIELDS = (
    "question_id",
    "from_content_fingerprint",
    "to_content_fingerprint",
    "correct_key_unchanged",
    "choice_letter_mapping_unchanged",
    "prompt_unchanged",
    "objective_unchanged",
    "tier_unchanged",
    "exam_eligibility_unchanged",
    "choice_semantics",
    "review_status",
    "review_artifact",
    "review_artifact_sha256",
    "authority_refs",
)
_REVIEW_FIELDS = (
    "question_id",
    "from_content_fingerprint",
    "to_content_fingerprint",
    "before",
    "after",
    "semantic_review",
    "correct_key_before",
    "correct_key_after",
    "authority_refs",
    "disposition",
)
_EDGE_BOOL_FIELDS = (
    "correct_key_unchanged",
    "choice_letter_mapping_unchanged",
    "prompt_unchanged",
    "objective_unchanged",
    "tier_unchanged",
    "exam_eligibility_unchanged",
)
_SPECIFIC_QUESTION_REASONS = {
    "prompt": RevisionFailureReason.PROMPT_CHANGED,
    "question_type": RevisionFailureReason.QUESTION_TYPE_CHANGED,
    "objective_code": RevisionFailureReason.OBJECTIVE_CHANGED,
    "domain": RevisionFailureReason.DOMAIN_CHANGED,
    "topics": RevisionFailureReason.TOPICS_CHANGED,
    "exam_calibration_tier": RevisionFailureReason.TIER_CHANGED,
    "exam_simulation_eligible": RevisionFailureReason.EXAM_ELIGIBILITY_CHANGED,
}
_PAIR_SKIP_FIELDS = {"choices", "correct", *_SPECIFIC_QUESTION_REASONS}


def _fail(*reasons: RevisionFailureReason) -> AdmissionResult:
    return AdmissionResult(AdmissionStatus.FAIL, reasons, None)


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


def _unknown_or_missing(payload: Mapping[str, Any], required: Sequence[str]) -> RevisionFailureReason | None:
    required_set = set(required)
    for key in payload:
        if key not in required_set:
            return RevisionFailureReason.UNKNOWN_FIELD
    for key in required:
        if key not in payload:
            return RevisionFailureReason.MISSING_FIELD
    return None


def _exact_ad_string_mapping(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value.keys()) != set(CHOICE_LABELS):
        return False
    return all(isinstance(value[letter], str) for letter in CHOICE_LABELS)


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _validate_bank_binding(payload: Any) -> RevisionFailureReason | None:
    if not isinstance(payload, Mapping):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    shape = _unknown_or_missing(payload, _BANK_BINDING_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["filename"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["file_sha256"]) or not _is_hex64(payload["content_fingerprint"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_int(payload["question_count"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_edge(payload: Any) -> RevisionFailureReason | None:
    if not isinstance(payload, Mapping):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    shape = _unknown_or_missing(payload, _EDGE_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["question_id"]) or not _nonempty_str(payload["review_artifact"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["from_content_fingerprint"]) or not _is_hex64(payload["to_content_fingerprint"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["review_artifact_sha256"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    for field in _EDGE_BOOL_FIELDS:
        if not isinstance(payload[field], bool):
            return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _exact_ad_string_mapping(payload["choice_semantics"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _nonempty_str(payload["review_status"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["authority_refs"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_review(payload: Mapping[str, Any]) -> RevisionFailureReason | None:
    shape = _unknown_or_missing(payload, _REVIEW_FIELDS)
    if shape is not None:
        return shape
    if not _nonempty_str(payload["question_id"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(payload["from_content_fingerprint"]) or not _is_hex64(payload["to_content_fingerprint"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _exact_ad_string_mapping(payload["before"]) or not _exact_ad_string_mapping(payload["after"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _exact_ad_string_mapping(payload["semantic_review"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["correct_key_before"]) or not _string_list(payload["correct_key_after"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _string_list(payload["authority_refs"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _nonempty_str(payload["disposition"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    return None


def _validate_manifest_schema(manifest: Mapping[str, Any]) -> RevisionFailureReason | None:
    shape = _unknown_or_missing(manifest, _MANIFEST_FIELDS)
    if shape is not None:
        return shape
    if not _is_int(manifest["schema_version"]) or not _nonempty_str(manifest["work_id"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not isinstance(manifest["manifest_kind"], str) or not isinstance(manifest["continuity_policy"], str):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not isinstance(manifest["permitted_change_class"], str):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if not _is_hex64(manifest["payload_sha256"]):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if manifest["schema_version"] != 1 or manifest["manifest_kind"] != MANIFEST_KIND:
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if manifest["continuity_policy"] != CONTINUITY_POLICY:
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    if manifest["permitted_change_class"] != PERMITTED_CHANGE_CLASS:
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    source_reason = _validate_bank_binding(manifest["source_bank"])
    if source_reason is not None:
        return source_reason
    target_reason = _validate_bank_binding(manifest["target_bank"])
    if target_reason is not None:
        return target_reason
    edges = manifest["edges"]
    if not isinstance(edges, list):
        return RevisionFailureReason.SCHEMA_UNSUPPORTED
    for edge in edges:
        edge_reason = _validate_edge(edge)
        if edge_reason is not None:
            return edge_reason
    return None


def contained_relative_path(path_value: str, root: Path) -> bool:
    if not _nonempty_str(path_value):
        return False
    candidate = Path(path_value.strip())
    if candidate.is_absolute() or candidate.drive:
        return False
    if any(part == ".." for part in candidate.parts):
        return False
    try:
        resolved_root = root.resolve()
        resolved = (resolved_root / candidate).resolve()
        resolved.relative_to(resolved_root)
    except (OSError, ValueError):
        return False
    return True


def _read_authority_object(
    path: Path, missing_reason: RevisionFailureReason
) -> tuple[dict[str, Any] | None, AdmissionResult | None]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None, _fail(missing_reason)
    try:
        payload = parse_json_duplicate_safe(raw)
    except ContentRevisionManifestError as exc:
        return None, _fail(exc.reason)
    return payload, None


def _index_questions(questions: Sequence[Any]) -> tuple[dict[str, Mapping[str, Any]], RevisionFailureReason | None]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        if not isinstance(question, Mapping):
            return {}, RevisionFailureReason.SCHEMA_UNSUPPORTED
        question_id = canonical_question_id(question)
        if not question_id:
            return {}, RevisionFailureReason.QUESTION_ID_SET_MISMATCH
        if question_id in indexed:
            return {}, RevisionFailureReason.DUPLICATE_QUESTION_ID
        indexed[question_id] = question
    return indexed, None


def _correct_key(question: Mapping[str, Any]) -> tuple[str, ...] | None:
    correct = question.get("correct")
    if isinstance(correct, str):
        correct = [correct]
    if not isinstance(correct, list):
        return None
    return tuple(sorted(str(item) for item in correct))


def _choice_labels(question: Mapping[str, Any]) -> set[str] | None:
    choices = question.get("choices")
    if not isinstance(choices, Mapping):
        return None
    return {str(key) for key in choices}


def _keyed_choice_texts(question: Mapping[str, Any]) -> dict[str, str] | None:
    choices = question.get("choices")
    if not isinstance(choices, Mapping) or set(choices.keys()) != set(CHOICE_LABELS):
        return None
    return {letter: str(choices[letter]) for letter in CHOICE_LABELS}


def _letter_mapping_changed(source: Mapping[str, str], target: Mapping[str, str]) -> bool:
    if source == target:
        return False
    source_letters_by_text: dict[str, set[str]] = {}
    for letter, text in source.items():
        source_letters_by_text.setdefault(text, set()).add(letter)
    for letter, text in target.items():
        source_letters = source_letters_by_text.get(text)
        if source_letters is not None and letter not in source_letters:
            return True
    return False


def _pair_invariant_reason(source: Mapping[str, Any], target: Mapping[str, Any]) -> RevisionFailureReason | None:
    if _correct_key(source) != _correct_key(target):
        return RevisionFailureReason.CORRECT_KEY_CHANGED
    source_labels = _choice_labels(source)
    target_labels = _choice_labels(target)
    if (
        source_labels is None
        or target_labels is None
        or source_labels != target_labels
        or source_labels != set(CHOICE_LABELS)
    ):
        return RevisionFailureReason.CHOICE_LABEL_SET_CHANGED
    for field, reason in _SPECIFIC_QUESTION_REASONS.items():
        if _canonical_json(source.get(field)) != _canonical_json(target.get(field)):
            return reason
    source_choices = _keyed_choice_texts(source)
    target_choices = _keyed_choice_texts(target)
    if source_choices is None or target_choices is None or _letter_mapping_changed(source_choices, target_choices):
        return RevisionFailureReason.CHOICE_LETTER_MAPPING_CHANGED
    keys = set(source.keys()) | set(target.keys())
    for key in sorted(keys):
        if key in _PAIR_SKIP_FIELDS:
            continue
        if _canonical_json(source.get(key)) != _canonical_json(target.get(key)):
            return RevisionFailureReason.NONPERMITTED_FIELD_CHANGED
    return None


def _microsoft_learn_refs(refs: Sequence[Any]) -> bool:
    if not refs:
        return False
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip().startswith(MS_LEARN_PREFIX):
            return False
    return True


def admit_content_revision(
    manifest: Mapping[str, Any],
    *,
    source_questions: Sequence[Mapping[str, Any]],
    target_questions: Sequence[Mapping[str, Any]],
    source_bank_path: Path,
    target_bank_path: Path,
    review_root: Path,
) -> AdmissionResult:
    del source_questions, target_questions
    if not isinstance(manifest, Mapping):
        return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
    schema_reason = _validate_manifest_schema(manifest)
    if schema_reason is not None:
        return _fail(schema_reason)
    expected_hash = canonical_manifest_sha256(manifest)
    if expected_hash != str(manifest["payload_sha256"]):
        return _fail(RevisionFailureReason.MANIFEST_HASH_MISMATCH)
    edges = list(manifest["edges"])
    for edge in edges:
        if not contained_relative_path(str(edge["review_artifact"]), review_root):
            return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
    source_bank, source_error = _read_authority_object(
        source_bank_path, RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH
    )
    if source_error is not None:
        return source_error
    target_bank, target_error = _read_authority_object(
        target_bank_path, RevisionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH
    )
    if target_error is not None:
        return target_error
    assert source_bank is not None and target_bank is not None
    source_bank_questions = source_bank.get("questions")
    target_bank_questions = target_bank.get("questions")
    if not isinstance(source_bank_questions, list) or not isinstance(target_bank_questions, list):
        return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
    try:
        source_file_hash = sha256_file(source_bank_path)
        target_file_hash = sha256_file(target_bank_path)
    except OSError:
        return _fail(RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if source_file_hash != manifest["source_bank"]["file_sha256"]:
        return _fail(RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
    if target_file_hash != manifest["target_bank"]["file_sha256"]:
        return _fail(RevisionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
    if (
        len(source_bank_questions) != REQUIRED_QUESTION_COUNT
        or len(target_bank_questions) != REQUIRED_QUESTION_COUNT
        or manifest["source_bank"]["question_count"] != REQUIRED_QUESTION_COUNT
        or manifest["target_bank"]["question_count"] != REQUIRED_QUESTION_COUNT
    ):
        return _fail(RevisionFailureReason.QUESTION_COUNT_MISMATCH)
    source_index, source_id_reason = _index_questions(source_bank_questions)
    if source_id_reason is not None:
        return _fail(source_id_reason)
    target_index, target_id_reason = _index_questions(target_bank_questions)
    if target_id_reason is not None:
        return _fail(target_id_reason)
    if set(source_index) != set(target_index):
        return _fail(RevisionFailureReason.QUESTION_ID_SET_MISMATCH)
    source_meta = {key: value for key, value in source_bank.items() if key != "questions"}
    target_meta = {key: value for key, value in target_bank.items() if key != "questions"}
    if _canonical_json(source_meta) != _canonical_json(target_meta):
        return _fail(RevisionFailureReason.NONPERMITTED_FIELD_CHANGED)
    for question_id in sorted(source_index):
        pair_reason = _pair_invariant_reason(source_index[question_id], target_index[question_id])
        if pair_reason is not None:
            return _fail(pair_reason)
    source_fp = bank_content_fingerprint(source_bank_questions)
    target_fp = bank_content_fingerprint(target_bank_questions)
    if source_fp != manifest["source_bank"]["content_fingerprint"]:
        return _fail(RevisionFailureReason.SOURCE_BANK_FINGERPRINT_MISMATCH)
    if target_fp != manifest["target_bank"]["content_fingerprint"]:
        return _fail(RevisionFailureReason.TARGET_BANK_FINGERPRINT_MISMATCH)
    actual_changed: set[str] = set()
    source_question_fps: dict[str, str] = {}
    target_question_fps: dict[str, str] = {}
    for question_id in source_index:
        source_question_fps[question_id] = question_content_fingerprint(source_index[question_id])
        target_question_fps[question_id] = question_content_fingerprint(target_index[question_id])
        if source_question_fps[question_id] != target_question_fps[question_id]:
            actual_changed.add(question_id)
    seen_edge_ids: set[str] = set()
    for edge in edges:
        question_id = str(edge["question_id"])
        if question_id in seen_edge_ids:
            return _fail(RevisionFailureReason.DUPLICATE_EQUIVALENCE_EDGE)
        seen_edge_ids.add(question_id)
    if actual_changed - seen_edge_ids:
        return _fail(RevisionFailureReason.UNDECLARED_CONTENT_CHANGE)
    if seen_edge_ids - actual_changed:
        return _fail(RevisionFailureReason.EXTRA_EQUIVALENCE_EDGE)
    admitted_edges: list[RevisionEdge] = []
    for edge in edges:
        question_id = str(edge["question_id"])
        if question_id not in source_index:
            return _fail(RevisionFailureReason.QUESTION_ID_SET_MISMATCH)
        if source_question_fps[question_id] != edge["from_content_fingerprint"]:
            return _fail(RevisionFailureReason.FROM_FINGERPRINT_MISMATCH)
        if target_question_fps[question_id] != edge["to_content_fingerprint"]:
            return _fail(RevisionFailureReason.TO_FINGERPRINT_MISMATCH)
        review_path = review_root / str(edge["review_artifact"])
        review_payload, review_error = _read_authority_object(
            review_path, RevisionFailureReason.SEMANTIC_REVIEW_MISSING
        )
        if review_error is not None:
            return review_error
        assert review_payload is not None
        try:
            review_hash = sha256_file(review_path)
        except OSError:
            return _fail(RevisionFailureReason.SEMANTIC_REVIEW_MISSING)
        if review_hash != edge["review_artifact_sha256"]:
            return _fail(RevisionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH)
        review_schema = _validate_review(review_payload)
        if review_schema is not None:
            return _fail(review_schema)
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        if (
            review_payload["question_id"] != question_id
            or review_payload["from_content_fingerprint"] != edge["from_content_fingerprint"]
            or review_payload["to_content_fingerprint"] != edge["to_content_fingerprint"]
        ):
            return _fail(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED)
        if _canonical_json(review_payload["before"]) != _canonical_json(_keyed_choice_texts(source_question)):
            return _fail(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED)
        if _canonical_json(review_payload["after"]) != _canonical_json(_keyed_choice_texts(target_question)):
            return _fail(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED)
        if tuple(review_payload["correct_key_before"]) != _correct_key(source_question):
            return _fail(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED)
        if tuple(review_payload["correct_key_after"]) != _correct_key(target_question):
            return _fail(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED)
        edge_semantics = edge["choice_semantics"]
        review_semantics = review_payload["semantic_review"]
        for letter in CHOICE_LABELS:
            if edge_semantics[letter] != SEMANTIC_EQUIVALENT or review_semantics[letter] != SEMANTIC_EQUIVALENT:
                return _fail(RevisionFailureReason.CHOICE_SEMANTICS_CHANGED)
        if (
            edge["review_status"] != REVIEW_STATUS_APPROVED
            or review_payload["disposition"] != REVIEW_DISPOSITION_APPROVED
        ):
            return _fail(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED)
        if not _microsoft_learn_refs(edge["authority_refs"]) or not _microsoft_learn_refs(
            review_payload["authority_refs"]
        ):
            return _fail(RevisionFailureReason.AUTHORITY_EVIDENCE_MISSING)
        admitted_edges.append(
            RevisionEdge(
                question_id=question_id,
                from_content_fingerprint=str(edge["from_content_fingerprint"]),
                to_content_fingerprint=str(edge["to_content_fingerprint"]),
                review_artifact=str(edge["review_artifact"]),
                review_artifact_sha256=str(edge["review_artifact_sha256"]),
            )
        )
    admitted = AdmittedRevision(
        manifest_sha256=expected_hash,
        source_bank_filename=str(manifest["source_bank"]["filename"]),
        source_bank_file_sha256=str(manifest["source_bank"]["file_sha256"]),
        source_bank_content_fingerprint=str(manifest["source_bank"]["content_fingerprint"]),
        target_bank_filename=str(manifest["target_bank"]["filename"]),
        target_bank_file_sha256=str(manifest["target_bank"]["file_sha256"]),
        target_bank_content_fingerprint=str(manifest["target_bank"]["content_fingerprint"]),
        edges=tuple(admitted_edges),
    )
    return AdmissionResult(AdmissionStatus.PASS, (), admitted)


def approved_lineage(
    revisions: Sequence[AdmittedRevision],
    question_id: str,
    from_fingerprint: str,
    to_fingerprint: str,
) -> tuple[RevisionEdge, ...] | None:
    if from_fingerprint == to_fingerprint:
        return ()
    index: dict[str, list[RevisionEdge]] = {}
    for revision in revisions:
        for edge in revision.edges:
            if edge.question_id != question_id:
                continue
            index.setdefault(edge.from_content_fingerprint, []).append(edge)
    chain: list[RevisionEdge] = []
    visited = {from_fingerprint}
    current = from_fingerprint
    while current != to_fingerprint:
        options = index.get(current, [])
        if not options:
            return None
        destinations = {edge.to_content_fingerprint for edge in options}
        if len(destinations) != 1:
            raise ContentRevisionManifestError(RevisionFailureReason.LINEAGE_CONFLICT, question_id)
        edge = options[0]
        if edge.to_content_fingerprint in visited:
            raise ContentRevisionManifestError(RevisionFailureReason.LINEAGE_CONFLICT, question_id)
        visited.add(edge.to_content_fingerprint)
        chain.append(edge)
        current = edge.to_content_fingerprint
    return tuple(chain)
