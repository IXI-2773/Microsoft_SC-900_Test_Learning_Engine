from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionResult,
    AdmissionStatus,
    ContentRevisionManifestError,
    RevisionFailureReason,
    admit_content_revision,
    canonical_manifest_sha256,
    contained_relative_path,
    parse_json_duplicate_safe,
)
from question_bank import load_bank
from question_identity import register_progress_identity_bank, registered_progress_identity_bank

AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {}
CONTENT_REVISION_EVIDENCE_ROOT = Path(__file__).resolve().parent / "content_revision_evidence"


def _fail(reason: RevisionFailureReason) -> AdmissionResult:
    return AdmissionResult(AdmissionStatus.FAIL, (reason,), None)


def resolve_registered_revision_for_target(
    target_bank_path: Path,
    *,
    evidence_root: Path | None = None,
    review_root: Path | None = None,
    registry: Mapping[str, str] | None = None,
) -> AdmissionResult | None:
    pinned = AUTHORIZED_CONTENT_REVISION_MANIFESTS if registry is None else registry
    if not pinned:
        return None
    root = Path(evidence_root) if evidence_root is not None else CONTENT_REVISION_EVIDENCE_ROOT
    reviews = Path(review_root) if review_root is not None else root / "reviews"
    target_name = Path(target_bank_path).name
    matches: list[tuple[str, dict[str, Any]]] = []
    for relative_path, expected_hash in pinned.items():
        if not contained_relative_path(relative_path, root):
            return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
        manifest_path = root / relative_path
        try:
            raw = manifest_path.read_text(encoding="utf-8")
        except OSError:
            return _fail(RevisionFailureReason.REGISTRY_HASH_MISMATCH)
        try:
            payload = parse_json_duplicate_safe(raw)
        except ContentRevisionManifestError as exc:
            if exc.reason == RevisionFailureReason.DUPLICATE_JSON_KEY:
                return _fail(RevisionFailureReason.DUPLICATE_JSON_KEY)
            return _fail(RevisionFailureReason.REGISTRY_HASH_MISMATCH)
        except Exception:
            return _fail(RevisionFailureReason.REGISTRY_HASH_MISMATCH)
        if canonical_manifest_sha256(payload) != expected_hash:
            return _fail(RevisionFailureReason.REGISTRY_HASH_MISMATCH)
        target_binding = payload.get("target_bank")
        if not isinstance(target_binding, Mapping):
            return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
        if str(target_binding.get("filename") or "") != target_name:
            continue
        matches.append((relative_path, payload))
    if not matches:
        return None
    if len(matches) > 1:
        return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
    _relative_path, manifest = matches[0]
    source_binding = manifest.get("source_bank")
    if not isinstance(source_binding, Mapping):
        return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
    source_name = str(source_binding.get("filename") or "")
    if not source_name or source_name == target_name:
        return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
    source_bank_path = Path(target_bank_path).parent / source_name
    prior_questions = registered_progress_identity_bank()
    target_questions: tuple[Any, ...] = ()
    try:
        try:
            target_data = load_bank(Path(target_bank_path))
        except Exception:
            return _fail(RevisionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH)
        target_questions = tuple(target_data["questions"])
        try:
            source_data = load_bank(source_bank_path)
        except Exception:
            return _fail(RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH)
        return admit_content_revision(
            manifest,
            source_questions=source_data["questions"],
            target_questions=target_data["questions"],
            source_bank_path=source_bank_path,
            target_bank_path=Path(target_bank_path),
            review_root=reviews,
        )
    finally:
        restore = target_questions or prior_questions
        if restore:
            register_progress_identity_bank(restore)
