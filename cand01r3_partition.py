from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PHASE3_ROOT = ROOT / "content" / "sc900" / "phase3"
MANIFEST_PATH = PHASE3_ROOT / "train_probe_manifest.json"
STORE_PATH = PHASE3_ROOT / "store" / "questions.json"
AUDIT_PATH = PHASE3_ROOT / "semantic_family_audit.json"
COMPILED_PATH = PHASE3_ROOT / "compiled" / "sc900_phase3_reviewed_bank.json"

EXPECTED_SEMANTIC_AUDIT_SHA256 = "e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701"
EXPECTED_STORE_SHA256 = "2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c"
EXPECTED_COMPILED_SHA256 = "72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b"
EXPECTED_MANIFEST_SHA256 = "67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90"
PARTITION_EPOCH = "phase3-task6-train-probe-partition"
EXAM_ID = "SC-900"

INTENDED_USE_TRAINING = "TRAINING"
INTENDED_USE_MEASUREMENT = "MEASUREMENT"

ROLE_TRAIN = "TRAIN"
ROLE_PROBE = "PROBE"
ROLE_UNASSIGNED = "UNASSIGNED"
ROLE_NOT_ELIGIBLE = "NOT_ELIGIBLE"
VALID_ROLES = {ROLE_TRAIN, ROLE_PROBE, ROLE_UNASSIGNED}

APPROVED_STATUS = "approved"
RESOLVED_FAMILY = "resolved"
PROBE_ELIGIBLE = "eligible"


def sha256_file(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def canonical_question_id(question: Mapping[str, Any] | str | None) -> str:
    if isinstance(question, str):
        return question.strip()
    if not isinstance(question, Mapping):
        return ""
    for key in ("id", "question_id", "canonical_question_id"):
        value = str(question.get(key) or "").strip()
        if value:
            return value
    metadata = question.get("metadata")
    if isinstance(metadata, Mapping):
        value = str(metadata.get("question_id") or metadata.get("canonical_question_id") or "").strip()
        if value:
            return value
    return ""


@dataclass
class EligibilityDecision:
    role: str
    reason: str
    question_id: str = ""
    family_id: str = ""

    @property
    def eligible(self) -> bool:
        return self.role in {ROLE_TRAIN, ROLE_PROBE} and self.reason == "OK"


@dataclass
class RuntimeAuthority:
    valid: bool
    reason: str
    partition_epoch: str = PARTITION_EPOCH
    manifest_sha256: str = ""
    store_sha256: str = ""
    semantic_audit_sha256: str = ""
    compiled_sha256: str = ""
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    families: dict[str, dict[str, Any]] = field(default_factory=dict)
    transfer_edges: list[dict[str, Any]] = field(default_factory=list)
    probe_family_ids: tuple[str, ...] = ()
    train_family_ids: tuple[str, ...] = ()

    @property
    def train_count(self) -> int:
        return sum(1 for item in self.items.values() if item.get("role") == ROLE_TRAIN)

    @property
    def probe_count(self) -> int:
        return sum(1 for item in self.items.values() if item.get("role") == ROLE_PROBE)


def _invalid_authority(reason: str, **overrides: Any) -> RuntimeAuthority:
    return RuntimeAuthority(
        valid=False,
        reason=reason,
        partition_epoch=str(overrides.get("partition_epoch") or PARTITION_EPOCH),
        manifest_sha256=str(overrides.get("manifest_sha256") or ""),
        store_sha256=str(overrides.get("store_sha256") or ""),
        semantic_audit_sha256=str(overrides.get("semantic_audit_sha256") or ""),
        compiled_sha256=str(overrides.get("compiled_sha256") or ""),
        items=dict(overrides.get("items") or {}),
        families=dict(overrides.get("families") or {}),
        transfer_edges=list(overrides.get("transfer_edges") or []),
        probe_family_ids=tuple(overrides.get("probe_family_ids") or ()),
        train_family_ids=tuple(overrides.get("train_family_ids") or ()),
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_runtime_authority(
    *,
    manifest_path: Path | None = None,
    store_path: Path | None = None,
    audit_path: Path | None = None,
    compiled_path: Path | None = None,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_store_sha256: str = EXPECTED_STORE_SHA256,
    expected_semantic_audit_sha256: str = EXPECTED_SEMANTIC_AUDIT_SHA256,
    expected_compiled_sha256: str = EXPECTED_COMPILED_SHA256,
) -> RuntimeAuthority:
    manifest_file = Path(manifest_path or MANIFEST_PATH)
    store_file = Path(store_path or STORE_PATH)
    audit_file = Path(audit_path or AUDIT_PATH)
    compiled_file = Path(compiled_path or COMPILED_PATH)
    if not manifest_file.exists():
        return _invalid_authority("MISSING_MANIFEST")
    if not store_file.exists():
        return _invalid_authority("STORE_HASH_MISMATCH")
    if not audit_file.exists():
        return _invalid_authority("SEMANTIC_AUDIT_HASH_MISMATCH")
    try:
        manifest_sha = sha256_file(manifest_file)
        store_sha = sha256_file(store_file)
        audit_sha = sha256_file(audit_file)
        compiled_sha = sha256_file(compiled_file) if compiled_file.exists() else ""
    except OSError:
        return _invalid_authority("MISSING_MANIFEST")
    if manifest_sha != expected_manifest_sha256:
        return _invalid_authority(
            "MANIFEST_HASH_MISMATCH",
            manifest_sha256=manifest_sha,
            store_sha256=store_sha,
            semantic_audit_sha256=audit_sha,
        )
    if store_sha != expected_store_sha256:
        return _invalid_authority(
            "STORE_HASH_MISMATCH", manifest_sha256=manifest_sha, store_sha256=store_sha, semantic_audit_sha256=audit_sha
        )
    if audit_sha != expected_semantic_audit_sha256:
        return _invalid_authority(
            "SEMANTIC_AUDIT_HASH_MISMATCH",
            manifest_sha256=manifest_sha,
            store_sha256=store_sha,
            semantic_audit_sha256=audit_sha,
        )
    if compiled_file.exists() and compiled_sha != expected_compiled_sha256:
        return _invalid_authority(
            "STORE_HASH_MISMATCH",
            manifest_sha256=manifest_sha,
            store_sha256=store_sha,
            semantic_audit_sha256=audit_sha,
            compiled_sha256=compiled_sha,
        )
    try:
        manifest = _load_json(manifest_file)
        audit = _load_json(audit_file)
    except (OSError, json.JSONDecodeError):
        return _invalid_authority("MISSING_MANIFEST", manifest_sha256=manifest_sha)
    items: dict[str, dict[str, Any]] = {}
    for raw in manifest.get("items") or []:
        if not isinstance(raw, Mapping):
            continue
        question_id = str(raw.get("question_id") or "").strip()
        if not question_id:
            continue
        items[question_id] = {
            "question_id": question_id,
            "role": raw.get("role"),
            "semantic_family_id": str(raw.get("semantic_family_id") or "").strip(),
            "family_state": str(raw.get("family_state") or "").strip(),
            "promotion_status": str(raw.get("promotion_status") or "").strip(),
            "future_probe_suitability": str(raw.get("future_probe_suitability") or "").strip(),
        }
    families: dict[str, dict[str, Any]] = {}
    for raw in manifest.get("family_assignments") or []:
        if not isinstance(raw, Mapping):
            continue
        family_id = str(raw.get("semantic_family_id") or "").strip()
        if not family_id:
            continue
        families[family_id] = {
            "semantic_family_id": family_id,
            "role": raw.get("role"),
            "member_ids": [str(member) for member in raw.get("member_ids") or []],
            "family_state": str(raw.get("family_state") or "").strip(),
        }
    transfer_edges = [dict(edge) for edge in (audit.get("transfer_edges") or []) if isinstance(edge, Mapping)]
    train_families = tuple(sorted(family_id for family_id, row in families.items() if row.get("role") == ROLE_TRAIN))
    probe_families = tuple(sorted(family_id for family_id, row in families.items() if row.get("role") == ROLE_PROBE))
    return RuntimeAuthority(
        valid=True,
        reason="OK",
        partition_epoch=str(manifest.get("partition_epoch") or PARTITION_EPOCH),
        manifest_sha256=manifest_sha,
        store_sha256=store_sha,
        semantic_audit_sha256=audit_sha,
        compiled_sha256=compiled_sha,
        items=items,
        families=families,
        transfer_edges=transfer_edges,
        probe_family_ids=probe_families,
        train_family_ids=train_families,
    )


def _role_reason(raw_role: Any) -> tuple[str | None, str | None]:
    if raw_role is None or raw_role == "":
        return None, "MALFORMED_ROLE"
    if not isinstance(raw_role, str):
        return None, "MALFORMED_ROLE"
    role = raw_role.strip()
    if not role:
        return None, "MALFORMED_ROLE"
    if role == "MISSING_ROLE":
        return None, "UNKNOWN_ROLE"
    if role not in VALID_ROLES:
        return None, "UNKNOWN_ROLE"
    return role, None


def _family_has_role(authority: RuntimeAuthority, family_id: str, role: str) -> bool:
    family = authority.families.get(family_id) or {}
    for member_id in family.get("member_ids") or []:
        item = authority.items.get(str(member_id)) or {}
        if item.get("role") == role:
            return True
    return False


def _transfer_conflict(question_id: str, family_id: str, authority: RuntimeAuthority) -> bool:
    family_role = (authority.families.get(family_id) or {}).get("role")
    item_role = (authority.items.get(question_id) or {}).get("role")
    connected_ids = {question_id}
    for edge in authority.transfer_edges:
        left = str(edge.get("left") or "").strip()
        right = str(edge.get("right") or "").strip()
        if question_id in {left, right}:
            connected_ids.add(left)
            connected_ids.add(right)
        if family_id and str(edge.get("semantic_family_id") or "") == family_id:
            connected_ids.add(left)
            connected_ids.add(right)
    roles = {(authority.items.get(member_id) or {}).get("role") for member_id in connected_ids if member_id}
    if ROLE_TRAIN in roles and ROLE_PROBE in roles:
        return True
    if family_role in {ROLE_TRAIN, ROLE_PROBE} and item_role in {ROLE_TRAIN, ROLE_PROBE} and family_role != item_role:
        return True
    return False


def partition_eligibility(
    question: Mapping[str, Any] | str,
    intended_use: str,
    runtime_authority: RuntimeAuthority | None,
) -> EligibilityDecision:
    if runtime_authority is None or not runtime_authority.valid:
        reason = getattr(runtime_authority, "reason", None) or "MISSING_MANIFEST"
        return EligibilityDecision(role=ROLE_NOT_ELIGIBLE, reason=reason, question_id=canonical_question_id(question))
    question_id = canonical_question_id(question)
    if not question_id:
        return EligibilityDecision(role=ROLE_NOT_ELIGIBLE, reason="QUESTION_NOT_IN_MANIFEST")
    item = runtime_authority.items.get(question_id)
    if item is None:
        return EligibilityDecision(role=ROLE_NOT_ELIGIBLE, reason="QUESTION_NOT_IN_MANIFEST", question_id=question_id)
    role, role_reason = _role_reason(item.get("role"))
    if role_reason:
        return EligibilityDecision(role=ROLE_NOT_ELIGIBLE, reason=role_reason, question_id=question_id)
    if role == ROLE_UNASSIGNED:
        return EligibilityDecision(role=ROLE_NOT_ELIGIBLE, reason="UNASSIGNED", question_id=question_id)
    family_id = str(item.get("semantic_family_id") or "").strip()
    if not family_id:
        return EligibilityDecision(role=ROLE_NOT_ELIGIBLE, reason="UNKNOWN_FAMILY", question_id=question_id)
    family = runtime_authority.families.get(family_id)
    if family is None:
        return EligibilityDecision(
            role=ROLE_NOT_ELIGIBLE, reason="UNKNOWN_FAMILY", question_id=question_id, family_id=family_id
        )
    family_state = str(item.get("family_state") or family.get("family_state") or "").strip()
    if family_state != RESOLVED_FAMILY:
        return EligibilityDecision(
            role=ROLE_NOT_ELIGIBLE, reason="UNRESOLVED_FAMILY", question_id=question_id, family_id=family_id
        )
    if str(item.get("promotion_status") or "").strip() != APPROVED_STATUS:
        return EligibilityDecision(
            role=ROLE_NOT_ELIGIBLE, reason="UNAPPROVED_ITEM", question_id=question_id, family_id=family_id
        )
    if family.get("role") != role:
        return EligibilityDecision(
            role=ROLE_NOT_ELIGIBLE, reason="FAMILY_ROLE_INCONSISTENCY", question_id=question_id, family_id=family_id
        )
    if _transfer_conflict(question_id, family_id, runtime_authority):
        return EligibilityDecision(
            role=ROLE_NOT_ELIGIBLE, reason="TRANSFER_EDGE_CONFLICT", question_id=question_id, family_id=family_id
        )
    if intended_use == INTENDED_USE_TRAINING:
        if role != ROLE_TRAIN:
            return EligibilityDecision(
                role=ROLE_NOT_ELIGIBLE, reason=role or "NOT_ELIGIBLE", question_id=question_id, family_id=family_id
            )
        if _family_has_role(runtime_authority, family_id, ROLE_PROBE):
            return EligibilityDecision(
                role=ROLE_NOT_ELIGIBLE, reason="FAMILY_ROLE_INCONSISTENCY", question_id=question_id, family_id=family_id
            )
        return EligibilityDecision(role=ROLE_TRAIN, reason="OK", question_id=question_id, family_id=family_id)
    if intended_use == INTENDED_USE_MEASUREMENT:
        if role != ROLE_PROBE:
            return EligibilityDecision(
                role=ROLE_NOT_ELIGIBLE, reason=role or "NOT_ELIGIBLE", question_id=question_id, family_id=family_id
            )
        if str(item.get("future_probe_suitability") or "").strip() != PROBE_ELIGIBLE:
            return EligibilityDecision(
                role=ROLE_NOT_ELIGIBLE, reason="PROBE_INELIGIBLE", question_id=question_id, family_id=family_id
            )
        if _family_has_role(runtime_authority, family_id, ROLE_TRAIN):
            return EligibilityDecision(
                role=ROLE_NOT_ELIGIBLE, reason="FAMILY_ROLE_INCONSISTENCY", question_id=question_id, family_id=family_id
            )
        return EligibilityDecision(role=ROLE_PROBE, reason="OK", question_id=question_id, family_id=family_id)
    return EligibilityDecision(
        role=ROLE_NOT_ELIGIBLE, reason="UNKNOWN_ROLE", question_id=question_id, family_id=family_id
    )


def filter_questions(
    questions: Iterable[Mapping[str, Any]],
    intended_use: str,
    runtime_authority: RuntimeAuthority | None,
) -> list[Any]:
    eligible: list[Any] = []
    for question in questions:
        decision = partition_eligibility(question, intended_use, runtime_authority)
        if intended_use == INTENDED_USE_TRAINING and decision.role == ROLE_TRAIN:
            eligible.append(question)
        elif intended_use == INTENDED_USE_MEASUREMENT and decision.role == ROLE_PROBE:
            eligible.append(question)
    return eligible
