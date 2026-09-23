from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from content_fingerprint_bridge import (
    FingerprintBridgeError,
    RuntimeBoundRevision,
    bind_admitted_revision,
    history_event_matches_runtime_bound_revision,
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
from question_identity import (
    canonical_question_id,
    question_content_fingerprint,
    register_progress_identity_bank,
    registered_progress_identity_bank,
)

AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {
    "manifests/sc900_answer_length_rebalance_t1.json": (
        "d10a1999452192a9a55401711db0c1cc7de2e0fa6bdf3711c3f4fbbb3a54a887"
    ),
    "manifests/sc900_answer_length_rebalance_t2.json": (
        "646ad8ba5a7ccb0ae7f369b019b482fcd3212495ff0ce893aaecf0ceb5237cbe"
    ),
    "manifests/sc900_answer_length_rebalance_t3.json": (
        "4b9eab410da68bd348b4ae40946cf54a45b1da98bf04d68baaf6a57e3de15338"
    ),
    "manifests/sc900_answer_length_rebalance_t4.json": (
        "83482105c1cb820292e14524b268ae8660e9ba9c493c055e920d22579b1639cb"
    ),
    "manifests/sc900_answer_length_rebalance_t5.json": (
        "654757b22e91e3d47754095035f7c260f8b0f0b6843ca9c122d443041108eac8"
    ),
    "manifests/sc900_content_correction_001.json": ("5d32c7c9b24192e6911a943fb8f9538369aad0331a6927fdbf5e95a81234c0f1"),
    "manifests/sc900_explanation_tranche_1.json": ("55d362a20007054b8fe23d1bd2003ba8dc4880beb1777724ec4aad29a93ed686"),
    "manifests/sc900_explanation_q118_repair_001.json": (
        "c938805a9c73e3d73047fa7518fa9adfc7ff23c7baa9769387a30a7b0a8e9730"
    ),
    "manifests/sc900_explanation_final_454_repair.json": (
        "f0414c09455bd280358b984d3f8487690d6c9d77f1a6795dfd234cb83bcd4ae2"
    ),
    "manifests/sc900_final_two_question_content_correction.json": (
        "3e62c4a195d2fe8961b29d98694a184a6f4c2a2265da20602f4cd09819f51345"
    ),
}
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
        "sc900_bank_v8_explanation_final_454_repair.json",
        "sc900_bank_v8_final_content_correction_002.json",
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


@dataclass(frozen=True, slots=True)
class RegisteredContentLineage:
    bank_filenames: tuple[str, ...]
    revisions: tuple[RuntimeBoundRevision, ...]


_CACHED_PRODUCTION_LINEAGE_KEY: tuple[tuple[str, str], ...] | None = None
_CACHED_PRODUCTION_LINEAGE: RegisteredContentLineage | None = None


def _read_pinned_manifest(
    relative_path: str,
    expected_hash: str,
    root: Path,
) -> dict[str, Any] | AdmissionResult:
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
    if not isinstance(payload, dict) or canonical_manifest_sha256(payload) != expected_hash:
        return _fail(RevisionFailureReason.REGISTRY_HASH_MISMATCH)
    return payload


def reconstruct_registered_lineage(
    *,
    evidence_root: Path | None = None,
    review_root: Path | None = None,
    registry: Mapping[str, str] | None = None,
    bank_dir: Path | None = None,
) -> RegisteredContentLineage | AdmissionResult | None:
    global _CACHED_PRODUCTION_LINEAGE, _CACHED_PRODUCTION_LINEAGE_KEY
    pinned = AUTHORIZED_CONTENT_REVISION_MANIFESTS if registry is None else registry
    if not pinned:
        return None
    cache_key = tuple(sorted((str(path), str(digest)) for path, digest in pinned.items())) if registry is None else None
    if cache_key is not None and cache_key == _CACHED_PRODUCTION_LINEAGE_KEY and _CACHED_PRODUCTION_LINEAGE is not None:
        return _CACHED_PRODUCTION_LINEAGE
    root = Path(evidence_root) if evidence_root is not None else CONTENT_REVISION_EVIDENCE_ROOT
    reviews = Path(review_root) if review_root is not None else root / "reviews"
    banks = Path(bank_dir) if bank_dir is not None else root.parent
    by_source: dict[str, tuple[str, str, str]] = {}
    targets: set[str] = set()
    for relative_path, expected_hash in pinned.items():
        loaded = _read_pinned_manifest(str(relative_path), str(expected_hash), root)
        if isinstance(loaded, AdmissionResult):
            return loaded
        source_binding = loaded.get("source_bank")
        target_binding = loaded.get("target_bank")
        if not isinstance(source_binding, Mapping) or not isinstance(target_binding, Mapping):
            return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
        source_name = str(source_binding.get("filename") or "")
        target_name = str(target_binding.get("filename") or "")
        if not source_name or not target_name or source_name == target_name:
            return _fail(RevisionFailureReason.SCHEMA_UNSUPPORTED)
        if source_name in by_source or target_name in targets:
            return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
        by_source[source_name] = (target_name, str(relative_path), str(expected_hash))
        targets.add(target_name)
    starts = [name for name in by_source if name not in targets]
    if len(starts) != 1:
        return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
    ordered: list[tuple[str, str, str]] = []
    bank_filenames = [starts[0]]
    current = starts[0]
    seen: set[str] = set()
    while current in by_source:
        if current in seen:
            return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
        seen.add(current)
        target_name, relative_path, expected_hash = by_source[current]
        ordered.append((target_name, relative_path, expected_hash))
        bank_filenames.append(target_name)
        current = target_name
    if len(ordered) != len(pinned) or len(bank_filenames) != len(set(bank_filenames)):
        return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
    revisions: list[RuntimeBoundRevision] = []
    for target_name, relative_path, expected_hash in ordered:
        result = resolve_registered_revision_for_target(
            banks / target_name,
            evidence_root=root,
            review_root=reviews,
            registry={relative_path: expected_hash},
        )
        bound = runtime_bound_revision_for_admission(result)
        if bound is None or getattr(result, "status", None) != AdmissionStatus.PASS:
            if isinstance(result, AdmissionResult):
                return result
            return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
        if bound.source_bank_filename != bank_filenames[len(revisions)] or bound.target_bank_filename != target_name:
            return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
        revisions.append(bound)
    for index in range(1, len(revisions)):
        if revisions[index].source_node.bank_node_id != revisions[index - 1].target_node.bank_node_id:
            return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
        if revisions[index].bridge_sha256 != revisions[0].bridge_sha256:
            return _fail(RevisionFailureReason.LINEAGE_CONFLICT)
    lineage = RegisteredContentLineage(tuple(bank_filenames), tuple(revisions))
    if cache_key is not None:
        _CACHED_PRODUCTION_LINEAGE_KEY = cache_key
        _CACHED_PRODUCTION_LINEAGE = lineage
    return lineage


def history_event_matches_registered_lineage(
    event: Mapping[str, Any] | None,
    question: Mapping[str, Any] | None,
    revisions: Sequence[RuntimeBoundRevision],
) -> bool:
    if not revisions:
        return False
    if len(revisions) == 1:
        return history_event_matches_runtime_bound_revision(event, question, revisions[0])
    if not isinstance(event, Mapping) or not isinstance(question, Mapping):
        return False
    qid = canonical_question_id(question)
    event_qid = str(event.get("question_id") or event.get("canonical_question_id") or "").strip()
    if not qid or event_qid != qid:
        return False
    event_fp = str(event.get("question_content_fingerprint") or "").strip()
    if not event_fp:
        return False
    current_fp = question_content_fingerprint(question)
    if event_fp == current_fp:
        return True
    nodes = [revisions[0].source_node, *[revision.target_node for revision in revisions]]
    if current_fp != nodes[-1].runtime_by_question.get(qid):
        return False
    matching = [
        index
        for index, node in enumerate(nodes)
        if event_fp in {node.artifact_by_question.get(qid), node.runtime_by_question.get(qid)}
    ]
    if not matching:
        return False
    start = min(matching)
    for hop_index in range(start, len(revisions)):
        revision = revisions[hop_index]
        source_artifact = revision.source_node.artifact_by_question.get(qid)
        target_artifact = revision.target_node.artifact_by_question.get(qid)
        if source_artifact == target_artifact:
            continue
        raw_edge = revision.artifact_edge(qid)
        if raw_edge is None or not revision.admitted.permits_fingerprint_transition(
            qid,
            str(raw_edge.from_content_fingerprint),
            str(raw_edge.to_content_fingerprint),
        ):
            return False
    return True


def history_events_for_registered_lineage(
    history_map: Mapping[str, list[Mapping[str, Any]]],
    question: Mapping[str, Any] | None,
    revisions: Sequence[RuntimeBoundRevision],
) -> list[Mapping[str, Any]]:
    qid = canonical_question_id(question)
    if not qid:
        return []
    return [
        event
        for event in history_map.get(qid, [])
        if history_event_matches_registered_lineage(event, question, revisions)
    ]
