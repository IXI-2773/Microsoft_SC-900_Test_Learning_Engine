from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


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
