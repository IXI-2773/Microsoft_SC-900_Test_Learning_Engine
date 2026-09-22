from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from content_fingerprint_bridge import (
    FingerprintBridgeError,
    RuntimeBoundRevision,
    bind_admitted_revision,
    verify_bridge_artifact,
)
from content_revision_authority import (
    MANIFEST_KIND as EQUIVALENCE_MANIFEST_KIND,
)
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
from content_revision_correction_authority import (
    MANIFEST_KIND as CORRECTION_MANIFEST_KIND,
)
from content_revision_correction_authority import (
    admit_content_correction,
)
from content_revision_explanation_authority import (
    MANIFEST_KIND as EXPLANATION_MANIFEST_KIND,
)
from content_revision_explanation_authority import (
    admit_explanation_revision,
)
from question_bank import load_bank
from question_identity import register_progress_identity_bank, registered_progress_identity_bank

AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {}
CONTENT_REVISION_EVIDENCE_ROOT = Path(__file__).resolve().parent / "content_revision_evidence"
FROZEN_BRIDGE_BANKS = frozenset(
    {
        "sc900_bank_v8_final.json",
        "sc900_bank_v8_length_rebalanced_t1.json",
        "sc900_bank_v8_length_rebalanced_t2.json",
        "sc900_bank_v8_length_rebalanced_t3.json",
        "sc900_bank_v8_length_rebalanced_t4.json",
        "sc900_bank_v8_length_rebalanced_t5.json",
        "sc900_bank_v8_content_correction_001.json",
        "sc900_bank_v8_explanation_tranche_1.json",
        "sc900_bank_v8_explanation_q118_repair.json",
    }
)


@dataclass(frozen=True, slots=True)
class RuntimeBoundAdmissionResult:
    status: Any
    reasons: tuple[Any, ...]
    admitted: Any
    runtime_bound: RuntimeBoundRevision | None


def runtime_bound_revision_for_admission(result: Any) -> RuntimeBoundRevision | None:
    return result.runtime_bound if isinstance(result, RuntimeBoundAdmissionResult) else None


def _bind_runtime_identity(result: Any) -> Any:
    admitted = getattr(result, "admitted", None)
    if getattr(result, "status", None) != AdmissionStatus.PASS or admitted is None:
        return result
    try:
        bridge = verify_bridge_artifact()
        bound = bind_admitted_revision(admitted, bridge)
    except (FingerprintBridgeError, OSError, ValueError, KeyError):
        return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
    return RuntimeBoundAdmissionResult(result.status, tuple(result.reasons), admitted, bound)


def _fail(reason: RevisionFailureReason) -> AdmissionResult:
    return AdmissionResult(AdmissionStatus.FAIL, (reason,), None)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = parse_json_duplicate_safe(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _artifact_path(root: Path, binding: Any, subdir: str) -> Path | None:
    if not isinstance(binding, Mapping):
        return None
    filename = str(binding.get("filename") or "").strip()
    if not filename:
        return None
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    repo_root = root.parent
    if relative.parts and relative.parts[0] == "content_revision_evidence":
        candidate = repo_root / relative
    else:
        candidate = root / subdir / relative
    try:
        candidate.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    return candidate


def resolve_registered_revision_for_target(
    target_bank_path: Path,
    *,
    evidence_root: Path | None = None,
    review_root: Path | None = None,
    registry: Mapping[str, str] | None = None,
) -> Any:
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

        manifest_kind = str(manifest.get("manifest_kind") or "")
        result: Any
        if manifest_kind == EQUIVALENCE_MANIFEST_KIND:
            result = admit_content_revision(
                manifest,
                source_questions=source_data["questions"],
                target_questions=target_data["questions"],
                source_bank_path=source_bank_path,
                target_bank_path=Path(target_bank_path),
                review_root=reviews,
            )
            if source_name in FROZEN_BRIDGE_BANKS and target_name in FROZEN_BRIDGE_BANKS:
                return _bind_runtime_identity(result)
            return result

        if manifest_kind == CORRECTION_MANIFEST_KIND:
            spec_path = _artifact_path(root, manifest.get("correction_spec"), "specs")
            currentness_path = _artifact_path(root, manifest.get("currentness_record"), "currentness")
            if spec_path is None or currentness_path is None:
                return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
            spec = _read_json_object(spec_path)
            currentness = _read_json_object(currentness_path)
            if spec is None or currentness is None:
                return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
            result = admit_content_correction(
                manifest,
                spec=spec,
                currentness_record=currentness,
                source_bank_path=source_bank_path,
                target_bank_path=Path(target_bank_path),
                spec_path=spec_path,
                currentness_path=currentness_path,
                review_root=reviews,
            )
            if source_name in FROZEN_BRIDGE_BANKS and target_name in FROZEN_BRIDGE_BANKS:
                return _bind_runtime_identity(result)
            return result

        if manifest_kind == EXPLANATION_MANIFEST_KIND:
            spec_path = _artifact_path(root, manifest.get("revision_spec"), "specs")
            ledger_path = _artifact_path(root, manifest.get("semantic_review_ledger"), "reviews")
            if spec_path is None or ledger_path is None:
                return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
            result = admit_explanation_revision(
                manifest,
                source_bank_path=source_bank_path,
                target_bank_path=Path(target_bank_path),
                spec_path=spec_path,
                ledger_path=ledger_path,
            )
            if source_name in FROZEN_BRIDGE_BANKS and target_name in FROZEN_BRIDGE_BANKS:
                return _bind_runtime_identity(result)
            return result

        return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
    finally:
        restore = target_questions or prior_questions
        if restore:
            register_progress_identity_bank(restore)
