from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from fingerprint_identity import (
    ARTIFACT_FINGERPRINT_DOMAIN,
    ARTIFACT_PROJECTION_VERSION,
    FINGERPRINT_SCHEMA_VERSION,
    RUNTIME_FINGERPRINT_DOMAIN,
    RUNTIME_LOADER_CONTRACT_VERSION,
)
from question_bank import load_bank
from question_identity import (
    bank_content_fingerprint,
    canonical_question_id,
    question_content_fingerprint,
    question_content_projection,
    register_progress_identity_bank,
    registered_progress_identity_bank,
)

BRIDGE_FORMAT_VERSION = 1
BRIDGE_GENERATOR_VERSION = 1
DEFAULT_BRIDGE_PATH = (
    Path(__file__).resolve().parent
    / "content_revision_evidence"
    / "fingerprint_bridges"
    / "sc900_content_fingerprint_bridge_v1.json"
)
FROZEN_BANK_FILENAMES = (
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
)


class BridgeFailureReason(StrEnum):
    UNKNOWN_BANK_NODE = "UNKNOWN_BANK_NODE"
    UNKNOWN_QUESTION_ID = "UNKNOWN_QUESTION_ID"
    UNKNOWN_DOMAIN = "UNKNOWN_DOMAIN"
    UNKNOWN_SCHEMA_VERSION = "UNKNOWN_SCHEMA_VERSION"
    WRONG_DOMAIN_FINGERPRINT = "WRONG_DOMAIN_FINGERPRINT"
    MAPPING_COLLISION = "MAPPING_COLLISION"
    TAMPERED_MAPPING = "TAMPERED_MAPPING"
    INCOMPLETE_NODE_MAPPING = "INCOMPLETE_NODE_MAPPING"
    BANK_HASH_DRIFT = "BANK_HASH_DRIFT"
    QUESTION_COUNT_DRIFT = "QUESTION_COUNT_DRIFT"
    UNREVIEWED_NORMALIZATION_DELTA = "UNREVIEWED_NORMALIZATION_DELTA"


class FingerprintBridgeError(ValueError):
    def __init__(self, reason: BridgeFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason.value if not detail else f"{reason.value}: {detail}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_bridge_sha256(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "payload_sha256"}
    return _sha256_json(body)


def _raw_questions(path: Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise FingerprintBridgeError(BridgeFailureReason.BANK_HASH_DRIFT, path.name)
    questions = data["questions"]
    if not all(isinstance(row, dict) for row in questions):
        raise FingerprintBridgeError(BridgeFailureReason.BANK_HASH_DRIFT, path.name)
    return [dict(row) for row in questions]


def _runtime_questions_isolated(path: Path) -> list[dict[str, Any]]:
    prior = registered_progress_identity_bank()
    try:
        data = load_bank(Path(path))
        return [dict(row) for row in data["questions"]]
    finally:
        register_progress_identity_bank(prior)


def _verify_reviewed_projection_delta(raw: Mapping[str, Any], runtime: Mapping[str, Any]) -> None:
    raw_projection = question_content_projection(raw)
    runtime_projection = question_content_projection(runtime)
    expected = json.loads(json.dumps(raw_projection))
    if "subtitle" not in expected:
        expected["subtitle"] = ""
    if "study_focus" not in expected:
        expected["study_focus"] = ""
    if runtime_projection != expected:
        qid = canonical_question_id(raw) or canonical_question_id(runtime)
        raise FingerprintBridgeError(
            BridgeFailureReason.UNREVIEWED_NORMALIZATION_DELTA,
            qid,
        )


def _node_binding(
    *,
    bank_filename: str,
    raw_file_sha256: str,
    question_count: int,
    artifact_bank_fingerprint: str,
    runtime_bank_fingerprint: str,
    question_triple_digest: str,
) -> dict[str, Any]:
    return {
        "bank_filename": bank_filename,
        "raw_file_sha256": raw_file_sha256,
        "question_count": int(question_count),
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "artifact_domain": ARTIFACT_FINGERPRINT_DOMAIN,
        "artifact_projection_version": ARTIFACT_PROJECTION_VERSION,
        "artifact_bank_fingerprint": artifact_bank_fingerprint,
        "runtime_domain": RUNTIME_FINGERPRINT_DOMAIN,
        "runtime_loader_contract_version": RUNTIME_LOADER_CONTRACT_VERSION,
        "runtime_bank_fingerprint": runtime_bank_fingerprint,
        "question_triple_digest": question_triple_digest,
    }


def build_bank_node(path: Path) -> dict[str, Any]:
    path = Path(path)
    raw_questions = _raw_questions(path)
    runtime_questions = _runtime_questions_isolated(path)
    if len(raw_questions) != len(runtime_questions):
        raise FingerprintBridgeError(BridgeFailureReason.QUESTION_COUNT_DRIFT, path.name)
    raw_by_id = {canonical_question_id(row): row for row in raw_questions}
    runtime_by_id = {canonical_question_id(row): row for row in runtime_questions}
    if not raw_by_id or set(raw_by_id) != set(runtime_by_id) or len(raw_by_id) != len(raw_questions):
        raise FingerprintBridgeError(BridgeFailureReason.INCOMPLETE_NODE_MAPPING, path.name)

    triples: list[dict[str, str]] = []
    for qid in sorted(raw_by_id):
        raw = raw_by_id[qid]
        runtime = runtime_by_id[qid]
        _verify_reviewed_projection_delta(raw, runtime)
        triples.append(
            {
                "question_id": qid,
                "artifact_fingerprint": question_content_fingerprint(raw),
                "runtime_fingerprint": question_content_fingerprint(runtime),
            }
        )
    triple_digest = _sha256_json(triples)
    binding = _node_binding(
        bank_filename=path.name,
        raw_file_sha256=_sha256_file(path),
        question_count=len(raw_questions),
        artifact_bank_fingerprint=bank_content_fingerprint(raw_questions),
        runtime_bank_fingerprint=bank_content_fingerprint(runtime_questions),
        question_triple_digest=triple_digest,
    )
    bank_node_id = _sha256_json(binding)
    return {
        **binding,
        "bank_node_id": bank_node_id,
        "questions": triples,
    }


def build_bridge_payload(
    repo_root: Path,
    bank_filenames: Sequence[str] = FROZEN_BANK_FILENAMES,
) -> dict[str, Any]:
    root = Path(repo_root)
    nodes = [build_bank_node(root / filename) for filename in bank_filenames]
    if len(nodes) != len(set(str(node["bank_node_id"]) for node in nodes)):
        raise FingerprintBridgeError(BridgeFailureReason.MAPPING_COLLISION, "bank_node_id")
    payload: dict[str, Any] = {
        "bridge_format_version": BRIDGE_FORMAT_VERSION,
        "generator_version": BRIDGE_GENERATOR_VERSION,
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "artifact_domain": ARTIFACT_FINGERPRINT_DOMAIN,
        "runtime_domain": RUNTIME_FINGERPRINT_DOMAIN,
        "nodes": nodes,
    }
    payload["payload_sha256"] = canonical_bridge_sha256(payload)
    FingerprintBridge.from_payload(payload)
    return payload


@dataclass(frozen=True, slots=True)
class BankFingerprintNode:
    bank_node_id: str
    bank_filename: str
    raw_file_sha256: str
    question_count: int
    artifact_bank_fingerprint: str
    runtime_bank_fingerprint: str
    artifact_by_question: Mapping[str, str]
    runtime_by_question: Mapping[str, str]
    question_triple_digest: str


@dataclass(frozen=True, slots=True)
class RuntimeBoundEdge:
    question_id: str
    from_content_fingerprint: str
    to_content_fingerprint: str


@dataclass(frozen=True, slots=True)
class RuntimeBoundRevision:
    admitted: Any
    source_node: BankFingerprintNode
    target_node: BankFingerprintNode
    bridge_sha256: str

    def __getattr__(self, name: str) -> Any:
        return getattr(self.admitted, name)

    @property
    def source_bank_content_fingerprint(self) -> str:
        return self.source_node.runtime_bank_fingerprint

    @property
    def target_bank_content_fingerprint(self) -> str:
        return self.target_node.runtime_bank_fingerprint

    @property
    def source_bank_filename(self) -> str:
        return str(self.admitted.source_bank_filename)

    @property
    def target_bank_filename(self) -> str:
        return str(self.admitted.target_bank_filename)

    @property
    def manifest_sha256(self) -> str:
        return str(self.admitted.manifest_sha256)

    @property
    def edges(self) -> tuple[RuntimeBoundEdge, ...]:
        return tuple(
            RuntimeBoundEdge(
                question_id=str(edge.question_id),
                from_content_fingerprint=self.runtime_source_question_fingerprint(str(edge.question_id)),
                to_content_fingerprint=self.runtime_target_question_fingerprint(str(edge.question_id)),
            )
            for edge in self.admitted.edges
        )

    @property
    def artifact_edges(self) -> tuple[Any, ...]:
        return tuple(self.admitted.edges)

    def artifact_edge(self, question_id: str) -> Any | None:
        qid = str(question_id)
        return next((edge for edge in self.admitted.edges if str(edge.question_id) == qid), None)

    def permits_fingerprint_transition(self, question_id: str, from_fp: str, to_fp: str) -> bool:
        qid = str(question_id)
        if str(from_fp) != self.runtime_source_question_fingerprint(qid) or str(
            to_fp
        ) != self.runtime_target_question_fingerprint(qid):
            return False
        raw = self.artifact_edge(qid)
        if raw is None:
            return False
        return bool(
            self.admitted.permits_fingerprint_transition(
                qid,
                str(raw.from_content_fingerprint),
                str(raw.to_content_fingerprint),
            )
        )

    def artifact_source_question_fingerprint(self, question_id: str) -> str:
        return self.source_node.artifact_by_question[str(question_id)]

    def artifact_target_question_fingerprint(self, question_id: str) -> str:
        return self.target_node.artifact_by_question[str(question_id)]

    def runtime_source_question_fingerprint(self, question_id: str) -> str:
        return self.source_node.runtime_by_question[str(question_id)]

    def runtime_target_question_fingerprint(self, question_id: str) -> str:
        return self.target_node.runtime_by_question[str(question_id)]


@dataclass(frozen=True, slots=True)
class FingerprintBridge:
    payload_sha256: str
    nodes: tuple[BankFingerprintNode, ...]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> FingerprintBridge:
        if int(payload.get("bridge_format_version") or 0) != BRIDGE_FORMAT_VERSION:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_SCHEMA_VERSION, "bridge format")
        if int(payload.get("fingerprint_schema_version") or 0) != FINGERPRINT_SCHEMA_VERSION:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_SCHEMA_VERSION, "fingerprint schema")
        if str(payload.get("artifact_domain") or "") != ARTIFACT_FINGERPRINT_DOMAIN:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_DOMAIN, "artifact")
        if str(payload.get("runtime_domain") or "") != RUNTIME_FINGERPRINT_DOMAIN:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_DOMAIN, "runtime")
        expected_sha = canonical_bridge_sha256(payload)
        if str(payload.get("payload_sha256") or "") != expected_sha:
            raise FingerprintBridgeError(BridgeFailureReason.TAMPERED_MAPPING, "payload_sha256")
        raw_nodes = payload.get("nodes")
        if not isinstance(raw_nodes, list):
            raise FingerprintBridgeError(BridgeFailureReason.INCOMPLETE_NODE_MAPPING, "nodes")

        nodes: list[BankFingerprintNode] = []
        node_ids: set[str] = set()
        question_keys: set[tuple[str, str, str, str]] = set()
        for raw_node in raw_nodes:
            if not isinstance(raw_node, Mapping):
                raise FingerprintBridgeError(BridgeFailureReason.INCOMPLETE_NODE_MAPPING, "node")
            bank_node_id = str(raw_node.get("bank_node_id") or "")
            binding = _node_binding(
                bank_filename=str(raw_node.get("bank_filename") or ""),
                raw_file_sha256=str(raw_node.get("raw_file_sha256") or ""),
                question_count=int(raw_node.get("question_count") or 0),
                artifact_bank_fingerprint=str(raw_node.get("artifact_bank_fingerprint") or ""),
                runtime_bank_fingerprint=str(raw_node.get("runtime_bank_fingerprint") or ""),
                question_triple_digest=str(raw_node.get("question_triple_digest") or ""),
            )
            if bank_node_id != _sha256_json(binding) or bank_node_id in node_ids:
                raise FingerprintBridgeError(BridgeFailureReason.MAPPING_COLLISION, bank_node_id)
            node_ids.add(bank_node_id)
            rows = raw_node.get("questions")
            if not isinstance(rows, list) or len(rows) != binding["question_count"]:
                raise FingerprintBridgeError(BridgeFailureReason.INCOMPLETE_NODE_MAPPING, binding["bank_filename"])
            artifact: dict[str, str] = {}
            runtime: dict[str, str] = {}
            canonical_rows: list[dict[str, str]] = []
            for row in rows:
                if not isinstance(row, Mapping):
                    raise FingerprintBridgeError(BridgeFailureReason.INCOMPLETE_NODE_MAPPING, bank_node_id)
                qid = str(row.get("question_id") or "")
                afp = str(row.get("artifact_fingerprint") or "")
                rfp = str(row.get("runtime_fingerprint") or "")
                if not qid or len(afp) != 64 or len(rfp) != 64 or qid in artifact:
                    raise FingerprintBridgeError(BridgeFailureReason.MAPPING_COLLISION, qid)
                for domain, fp in ((ARTIFACT_FINGERPRINT_DOMAIN, afp), (RUNTIME_FINGERPRINT_DOMAIN, rfp)):
                    key = (bank_node_id, qid, domain, fp)
                    if key in question_keys:
                        raise FingerprintBridgeError(BridgeFailureReason.MAPPING_COLLISION, qid)
                    question_keys.add(key)
                artifact[qid] = afp
                runtime[qid] = rfp
                canonical_rows.append({"question_id": qid, "artifact_fingerprint": afp, "runtime_fingerprint": rfp})
            canonical_rows.sort(key=lambda item: item["question_id"])
            if _sha256_json(canonical_rows) != binding["question_triple_digest"]:
                raise FingerprintBridgeError(BridgeFailureReason.TAMPERED_MAPPING, "question_triple_digest")
            nodes.append(
                BankFingerprintNode(
                    bank_node_id=bank_node_id,
                    bank_filename=binding["bank_filename"],
                    raw_file_sha256=binding["raw_file_sha256"],
                    question_count=binding["question_count"],
                    artifact_bank_fingerprint=binding["artifact_bank_fingerprint"],
                    runtime_bank_fingerprint=binding["runtime_bank_fingerprint"],
                    artifact_by_question=artifact,
                    runtime_by_question=runtime,
                    question_triple_digest=binding["question_triple_digest"],
                )
            )
        return cls(expected_sha, tuple(nodes))

    def node_for_filename(self, filename: str) -> BankFingerprintNode:
        matches = [node for node in self.nodes if node.bank_filename == str(filename)]
        if len(matches) != 1:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_BANK_NODE, str(filename))
        return matches[0]

    def node_for_runtime_bank_fingerprint(self, fingerprint: str) -> BankFingerprintNode:
        matches = [node for node in self.nodes if node.runtime_bank_fingerprint == str(fingerprint)]
        if len(matches) != 1:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_BANK_NODE, str(fingerprint))
        return matches[0]

    def node_for_artifact_bank_fingerprint(self, fingerprint: str) -> BankFingerprintNode:
        matches = [node for node in self.nodes if node.artifact_bank_fingerprint == str(fingerprint)]
        if len(matches) != 1:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_BANK_NODE, str(fingerprint))
        return matches[0]

    def translate_bank(self, bank_node_id: str, source_domain: str, source_fingerprint: str) -> str:
        node = next((item for item in self.nodes if item.bank_node_id == bank_node_id), None)
        if node is None:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_BANK_NODE, bank_node_id)
        if source_domain == ARTIFACT_FINGERPRINT_DOMAIN:
            if source_fingerprint != node.artifact_bank_fingerprint:
                raise FingerprintBridgeError(BridgeFailureReason.WRONG_DOMAIN_FINGERPRINT, source_fingerprint)
            return node.runtime_bank_fingerprint
        if source_domain == RUNTIME_FINGERPRINT_DOMAIN:
            if source_fingerprint != node.runtime_bank_fingerprint:
                raise FingerprintBridgeError(BridgeFailureReason.WRONG_DOMAIN_FINGERPRINT, source_fingerprint)
            return node.artifact_bank_fingerprint
        raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_DOMAIN, source_domain)

    def translate_question(
        self,
        bank_node_id: str,
        question_id: str,
        source_domain: str,
        source_fingerprint: str,
    ) -> str:
        node = next((item for item in self.nodes if item.bank_node_id == bank_node_id), None)
        if node is None:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_BANK_NODE, bank_node_id)
        qid = str(question_id)
        if qid not in node.artifact_by_question:
            raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_QUESTION_ID, qid)
        if source_domain == ARTIFACT_FINGERPRINT_DOMAIN:
            if source_fingerprint != node.artifact_by_question[qid]:
                raise FingerprintBridgeError(BridgeFailureReason.WRONG_DOMAIN_FINGERPRINT, qid)
            return node.runtime_by_question[qid]
        if source_domain == RUNTIME_FINGERPRINT_DOMAIN:
            if source_fingerprint != node.runtime_by_question[qid]:
                raise FingerprintBridgeError(BridgeFailureReason.WRONG_DOMAIN_FINGERPRINT, qid)
            return node.artifact_by_question[qid]
        raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_DOMAIN, source_domain)


def load_bridge(path: Path = DEFAULT_BRIDGE_PATH) -> FingerprintBridge:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FingerprintBridgeError(BridgeFailureReason.TAMPERED_MAPPING, "top-level")
    return FingerprintBridge.from_payload(payload)


def verify_bridge_artifact(
    path: Path = DEFAULT_BRIDGE_PATH,
    *,
    repo_root: Path | None = None,
) -> FingerprintBridge:
    path = Path(path)
    bridge = load_bridge(path)
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent
    regenerated = build_bridge_payload(root, tuple(node.bank_filename for node in bridge.nodes))
    if canonical_bridge_sha256(regenerated) != bridge.payload_sha256:
        raise FingerprintBridgeError(BridgeFailureReason.TAMPERED_MAPPING, "regeneration mismatch")
    return bridge


def bind_admitted_revision(admitted: Any, bridge: FingerprintBridge) -> RuntimeBoundRevision:
    try:
        source = bridge.node_for_filename(str(admitted.source_bank_filename))
        target = bridge.node_for_filename(str(admitted.target_bank_filename))
    except AttributeError as exc:
        raise FingerprintBridgeError(BridgeFailureReason.UNKNOWN_BANK_NODE, "revision binding") from exc
    if source.raw_file_sha256 != str(admitted.source_bank_file_sha256):
        raise FingerprintBridgeError(BridgeFailureReason.BANK_HASH_DRIFT, source.bank_filename)
    if target.raw_file_sha256 != str(admitted.target_bank_file_sha256):
        raise FingerprintBridgeError(BridgeFailureReason.BANK_HASH_DRIFT, target.bank_filename)
    if source.artifact_bank_fingerprint != str(admitted.source_bank_content_fingerprint):
        raise FingerprintBridgeError(BridgeFailureReason.WRONG_DOMAIN_FINGERPRINT, source.bank_filename)
    if target.artifact_bank_fingerprint != str(admitted.target_bank_content_fingerprint):
        raise FingerprintBridgeError(BridgeFailureReason.WRONG_DOMAIN_FINGERPRINT, target.bank_filename)
    for edge in tuple(admitted.edges):
        qid = str(edge.question_id)
        if source.artifact_by_question.get(qid) != str(
            edge.from_content_fingerprint
        ) or target.artifact_by_question.get(qid) != str(edge.to_content_fingerprint):
            raise FingerprintBridgeError(BridgeFailureReason.TAMPERED_MAPPING, qid)
    return RuntimeBoundRevision(admitted, source, target, bridge.payload_sha256)


def unwrap_revision(revision: Any) -> Any:
    return revision.admitted if isinstance(revision, RuntimeBoundRevision) else revision


def bound_migration_id(base_migration_id: str, revision: Any) -> str:
    if not isinstance(revision, RuntimeBoundRevision):
        return str(base_migration_id)
    return _sha256_json(
        {
            "base_migration_id": str(base_migration_id),
            "manifest_sha256": revision.manifest_sha256,
            "bridge_sha256": revision.bridge_sha256,
            "source_bank_node_id": revision.source_node.bank_node_id,
            "target_bank_node_id": revision.target_node.bank_node_id,
            "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
            "source_domain": RUNTIME_FINGERPRINT_DOMAIN,
            "target_domain": RUNTIME_FINGERPRINT_DOMAIN,
        }
    )


def runtime_bank_node_id_for_fingerprint(
    fingerprint: str,
    *,
    bridge_path: Path = DEFAULT_BRIDGE_PATH,
) -> str:
    bridge = load_bridge(bridge_path)
    return bridge.node_for_runtime_bank_fingerprint(str(fingerprint)).bank_node_id


def history_event_matches_runtime_bound_revision(
    event: Mapping[str, Any] | None,
    question: Mapping[str, Any] | None,
    revision: RuntimeBoundRevision,
) -> bool:
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
    source_runtime = revision.source_node.runtime_by_question.get(qid)
    target_runtime = revision.target_node.runtime_by_question.get(qid)
    source_artifact = revision.source_node.artifact_by_question.get(qid)
    target_artifact = revision.target_node.artifact_by_question.get(qid)
    if current_fp != target_runtime:
        return False
    if event_fp == target_artifact:
        return True
    raw_edge = revision.artifact_edge(qid)
    if raw_edge is None:
        return event_fp in {source_runtime, source_artifact} and source_runtime == target_runtime
    if event_fp not in {source_runtime, source_artifact}:
        return False
    return bool(
        revision.admitted.permits_fingerprint_transition(
            qid,
            str(raw_edge.from_content_fingerprint),
            str(raw_edge.to_content_fingerprint),
        )
    )


def history_events_for_runtime_bound_revision(
    history_map: Mapping[str, list[Mapping[str, Any]]],
    question: Mapping[str, Any] | None,
    revision: RuntimeBoundRevision,
) -> list[Mapping[str, Any]]:
    qid = canonical_question_id(question)
    if not qid:
        return []
    return [
        event
        for event in history_map.get(qid, [])
        if history_event_matches_runtime_bound_revision(event, question, revision)
    ]
