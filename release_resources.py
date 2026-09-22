from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cert_config import QUESTION_BANK_FILENAME
from content_fingerprint_bridge import DEFAULT_BRIDGE_PATH, FROZEN_BANK_FILENAMES
from content_revision_authority import parse_json_duplicate_safe
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS, CONTENT_REVISION_EVIDENCE_ROOT

ROOT = Path(__file__).resolve().parent
_BASE_RUNTIME_RESOURCES = (
    Path("cert_profile_sc900.json"),
    Path(QUESTION_BANK_FILENAME),
    Path("sc900_bank_v8_baseline.json"),
    Path("config/certifications/sc900-2026.json"),
)


def governed_binding_relative_path(binding: Mapping[str, Any], subdir: str) -> Path:
    filename = str(binding.get("filename") or "").strip()
    relative = Path(filename)
    if not filename or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Ungoverned artifact binding: {filename!r}")
    if relative.parts and relative.parts[0] == "content_revision_evidence":
        return relative
    return Path("content_revision_evidence") / subdir / relative


def _remember(order: list[Path], consumers: dict[str, set[str]], relative: Path, consumer: str) -> None:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Ungoverned packaged resource: {relative}")
    key = relative.as_posix()
    if not (ROOT / relative).is_file():
        raise FileNotFoundError(f"Required lineage resource is missing: {ROOT / relative}")
    consumers.setdefault(key, set()).add(consumer)
    if key not in {path.as_posix() for path in order}:
        order.append(relative)


def _review_artifacts(payload: Mapping[str, Any]) -> list[str]:
    edges = payload.get("edges")
    if not isinstance(edges, list):
        return []
    artifacts: list[str] = []
    for edge in edges:
        if not isinstance(edge, Mapping):
            raise ValueError("Lineage manifest edge is not an object")
        artifact = str(edge.get("review_artifact") or "").strip()
        if not artifact:
            raise ValueError("Lineage manifest edge is missing review_artifact")
        artifacts.append(artifact)
    return artifacts


def _lineage_closure() -> tuple[tuple[Path, ...], dict[str, set[str]]]:
    order: list[Path] = []
    consumers: dict[str, set[str]] = {}
    evidence_root = CONTENT_REVISION_EVIDENCE_ROOT
    for filename in FROZEN_BANK_FILENAMES:
        _remember(order, consumers, Path(filename), "fingerprint_bridge_bank")
    bridge = Path(DEFAULT_BRIDGE_PATH.resolve().relative_to(ROOT.resolve()).as_posix())
    _remember(order, consumers, bridge, "fingerprint_bridge")
    for relative_manifest in AUTHORIZED_CONTENT_REVISION_MANIFESTS:
        manifest_path = Path("content_revision_evidence") / relative_manifest
        _remember(order, consumers, manifest_path, "pinned_manifest")
        payload = parse_json_duplicate_safe((evidence_root / relative_manifest).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Lineage manifest is not an object: {manifest_path}")
        for bank_key in ("source_bank", "target_bank"):
            binding = payload.get(bank_key)
            if not isinstance(binding, Mapping):
                raise ValueError(f"Lineage manifest is missing {bank_key}: {manifest_path}")
            filename = str(binding.get("filename") or "").strip()
            if not filename:
                raise ValueError(f"Lineage manifest bank filename is empty: {manifest_path}")
            _remember(order, consumers, Path(filename), f"manifest_{bank_key}")
        binding_consumers = (
            ("correction_spec", "specs", "correction_spec"),
            ("currentness_record", "currentness", "correction_currentness"),
            ("revision_spec", "specs", "explanation_spec"),
            ("semantic_review_ledger", "reviews", "explanation_review_ledger"),
        )
        for field, subdir, consumer in binding_consumers:
            if field not in payload:
                continue
            binding = payload.get(field)
            if not isinstance(binding, Mapping):
                raise ValueError(f"{field} binding is invalid: {manifest_path}")
            _remember(order, consumers, governed_binding_relative_path(binding, subdir), consumer)
        kind = str(payload.get("manifest_kind") or "")
        if "explanation" not in kind:
            consumer = "correction_review" if "correction" in kind else "equivalence_review"
            for artifact in _review_artifacts(payload):
                _remember(order, consumers, Path("content_revision_evidence") / "reviews" / artifact, consumer)
    return tuple(order), consumers


_LINEAGE_RESOURCES, _LINEAGE_CONSUMERS = _lineage_closure()


def packaged_lineage_resource_closure() -> tuple[Path, ...]:
    """Return the exact files reconstruct_registered_lineage() must read."""
    return _LINEAGE_RESOURCES


def packaged_lineage_closure_records() -> tuple[dict[str, str], ...]:
    records: list[dict[str, str]] = []
    for resource in _LINEAGE_RESOURCES:
        key = resource.as_posix()
        digest = hashlib.sha256((ROOT / resource).read_bytes()).hexdigest()
        records.append(
            {
                "path": key,
                "sha256": digest,
                "consumer": ",".join(sorted(_LINEAGE_CONSUMERS[key])),
                "packaged_relative_path": key,
            }
        )
    return tuple(records)


def _required_runtime_resources() -> tuple[Path, ...]:
    order: list[Path] = []
    seen: set[str] = set()
    for resource in (*_BASE_RUNTIME_RESOURCES, *_LINEAGE_RESOURCES):
        key = resource.as_posix()
        if key in seen:
            continue
        if not (ROOT / resource).is_file():
            raise FileNotFoundError(f"Required runtime resource is missing: {ROOT / resource}")
        seen.add(key)
        order.append(resource)
    return tuple(order)


REQUIRED_RUNTIME_RESOURCES = _required_runtime_resources()


def pyinstaller_resource_args(separator: str) -> list[str]:
    args: list[str] = []
    for resource in REQUIRED_RUNTIME_RESOURCES:
        source = ROOT / resource
        if not source.is_file():
            raise FileNotFoundError(f"Required runtime resource is missing: {source}")
        destination = resource.parent.as_posix() if resource.parent != Path(".") else "."
        args.extend(["--add-data", f"{source}{separator}{destination}"])
    return args
