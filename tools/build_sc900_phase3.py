from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ingestion.importer import apply_review_decision, compile_question_bank, import_jsonl, promotion_counts
from ingestion.models import load_taxonomy, normalize_text
from tools.build_sc900_phase2 import (
    DEFAULT_BANK,
    PHASE2_STORE,
    STORE_FILES,
    _answer_key,
    _correct_answer_text,
    _UnionFind,
    review_content_sha256,
)
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS
from tools.validate_sc900_phase2 import validate_question_source_links
from tools.validate_sc900_phase3 import (
    EXPECTED_BLUEPRINT_LEAF_COUNT,
    EXPECTED_PHASE3_DOMAIN_COUNTS,
    EXPECTED_PHASE3_OBJECTIVE_COUNTS,
    validate_phase3_source_inventory,
)

ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = ROOT / "content" / "sc900" / "phase1"
PHASE1_BATCHES = PHASE1_ROOT / "batches"
PHASE1_REVIEWS = PHASE1_ROOT / "reviews"
PHASE1_STORE = PHASE1_ROOT / "store"
PHASE2_ROOT = ROOT / "content" / "sc900" / "phase2"
PHASE2_BATCHES = PHASE2_ROOT / "batches"
PHASE2_REVIEWS = PHASE2_ROOT / "reviews"
PHASE2_SEMANTIC_AUDIT = PHASE2_ROOT / "semantic_family_audit.json"
PHASE2_BUILD_RECEIPT = PHASE2_ROOT / "phase2_build_receipt.json"
PHASE3_ROOT = ROOT / "content" / "sc900" / "phase3"
PHASE3_BATCHES = PHASE3_ROOT / "batches"
PHASE3_REVIEWS = PHASE3_ROOT / "reviews"
PHASE3_STORE = PHASE3_ROOT / "store"
PHASE3_COMPILED = PHASE3_ROOT / "compiled" / "sc900_phase3_reviewed_bank.json"
PHASE3_SOURCE_INVENTORY = PHASE3_ROOT / "source_inventory.json"
SEMANTIC_AUDIT_PATH = PHASE3_ROOT / "semantic_family_audit.json"
BUILD_RECEIPT_PATH = PHASE3_ROOT / "phase3_build_receipt.json"
ACCEPTANCE_REPORT_PATH = PHASE3_ROOT / "phase3_acceptance_report.json"

WORK_ID = "SC900-BANK-PHASE3-001"
BUILD_RECEIPT_VERSION = "sc900-phase3-build-receipt/v1"
BUILD_EPOCH = "phase3-task5-deterministic-build"
BUILDER_IDENTITY = "tools.build_sc900_phase3"
BUILDER_VERSION = "sc900-phase3-task5/v1"
DETERMINISTIC_IMPORT_AT = "2026-09-11T18:00:00+00:00"
EXPECTED_SEMANTIC_AUDIT_SHA256 = "e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701"
EXPECTED_PHASE3_IDS = [f"sc900_p3_q{index:03d}" for index in range(1, 101)]
EXPECTED_SEMANTIC_FAMILY_COUNT = 27
EXPECTED_MERGE_OVERRIDE_COUNT = 158
EXPECTED_SPLIT_OVERRIDE_COUNT = 0
EXPECTED_UNRESOLVED_FAMILY_COUNT = 0
GATE2_STATUS = "GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE"
REVIEW_HASH_ALGORITHM = "sha256(canonical reviewed question content excluding semantic_family_id)"
CUSTODY_TRANSITIONS = [
    "PRIMARY_AUTHORED_CONTENT",
    "IMPORTED_PENDING",
    "REVIEW_MATCH",
    "EXPLICIT_APPROVAL",
    "SEMANTIC_AUDIT_APPLICATION",
    "CUMULATIVE_STORE",
    "COMPILED_CANDIDATE_BANK",
    "ACCEPTANCE_REPORT",
    "BUILD_RECEIPT",
]
AUDIT_VERSION = "sc900-semantic-family-audit/v2"
AUDIT_EPOCH = "phase3-task4-cumulative-200"
REVIEWER = "cursor-grok-4.6-cumulative-adversarial-semantic-audit"
REVIEWED_AT = "2026-09-11T18:00:00Z"
REVIEW_METHOD = (
    "cumulative adversarial semantic-family audit of Phase 1+2+3 accepted questions; "
    "prior family labels treated as hypotheses; fail closed on material transfer doubt"
)
EXPECTED_CUMULATIVE_COUNT = 200
UNRESOLVED_FAMILY_STATES = {"unresolved", "unknown", "disputed", "needs_review"}
RESOLVED_DECISION_TYPES = {"retained", "merged", "split"}
DECISION_TYPES = {"retained", "merged", "split", "unresolved"}
PROBE_ELIGIBLE = "eligible"

REQUIRED_TRANSFER_EDGES = (frozenset({"sc900_p1_q037", "sc900_p2_q033"}),)

CROSS_LEAF_FAMILY_GROUPS: dict[str, frozenset[str]] = {
    "sentinel_siem_soar_automation": frozenset({"siem_and_soar", "sentinel_threat_detection_mitigation"}),
    "defender_for_cloud_cspm_cwp": frozenset(
        {
            "microsoft_defender_for_cloud",
            "cloud_security_posture_management",
            "cloud_workload_protection",
            "security_policies_standards_recommendations",
        }
    ),
    "azure_nsg_firewall_waf_ddos": frozenset(
        {
            "network_security_groups",
            "azure_firewall",
            "azure_web_application_firewall",
            "azure_ddos_protection",
        }
    ),
    "purview_audit_ediscovery_insider_risk": frozenset({"audit", "ediscovery", "insider_risk_management"}),
    "service_trust_privacy_compliance_manager": frozenset(
        {
            "service_trust_portal_offerings",
            "microsoft_privacy_principles",
            "compliance_manager",
            "compliance_score",
        }
    ),
    "entra_hybrid_identity_and_ad": frozenset(
        {
            "entra_id_overview",
            "directory_services_active_directory",
            "hybrid_identity",
        }
    ),
    "conditional_access_and_identity_protection": frozenset({"conditional_access", "entra_id_protection"}),
    "entra_id_governance_and_access_reviews": frozenset({"entra_id_governance", "access_reviews"}),
    "defender_xdr_workload_suite": frozenset(
        {
            "defender_xdr_services",
            "defender_for_endpoint",
            "defender_for_identity",
            "defender_for_office_365",
            "defender_for_cloud_apps",
            "defender_portal",
            "defender_vulnerability_management",
            "defender_threat_intelligence",
        }
    ),
    "purview_information_protection_lifecycle": frozenset(
        {
            "data_classification",
            "sensitivity_labels_and_policies",
            "retention_policies_labels",
            "records_management",
            "data_loss_prevention",
            "content_and_activity_explorer",
        }
    ),
    "authentication_vs_authorization": frozenset({"authentication", "authorization"}),
    "zero_trust_and_identity_perimeter": frozenset({"zero_trust_model", "identity_primary_security_perimeter"}),
    "federation_and_identity_providers": frozenset({"federation", "identity_providers"}),
}

FAMILY_RATIONALES: dict[str, str] = {
    "sentinel_siem_soar_automation": (
        "SIEM/SOAR definitions, Sentinel platform identification, and Sentinel "
        "collect/detect/investigate/automate capabilities materially transfer, including "
        "the inherited SOAR playbook edge and the shared Microsoft Sentinel answer."
    ),
    "defender_for_cloud_cspm_cwp": (
        "Defender for Cloud is taught as the product that combines CSPM and CWP; posture, "
        "workload-protection, secure-score, and recommendation items therefore leak one another."
    ),
    "azure_nsg_firewall_waf_ddos": (
        "NSG, Azure Firewall, WAF, and DDoS items are linked by explicit layer-discrimination "
        "stems; knowing one control's layer/purpose substantially narrows the sibling contrast."
    ),
    "purview_audit_ediscovery_insider_risk": (
        "Audit, eDiscovery, and Insider Risk Management are coupled by product-discrimination "
        "items whose correct answers restate the sibling propositions."
    ),
    "service_trust_privacy_compliance_manager": (
        "SC-900 pairs Service Trust Portal with Microsoft privacy principles, and an explicit "
        "STP-versus-Compliance Manager item plus Compliance Manager score items share that "
        "trust/compliance documentation proposition."
    ),
    "entra_hybrid_identity_and_ad": (
        "Entra ID, AD DS, and hybrid identity items mutually reveal the cloud/on-premises "
        "directory relationship, including Entra Connect and password-hash sync."
    ),
    "conditional_access_and_identity_protection": (
        "Conditional Access signal/policy items and Entra ID Protection risk-detection items "
        "share the risk-signal-to-access-decision mapping."
    ),
    "entra_id_governance_and_access_reviews": (
        "Lifecycle Workflows, entitlement management, and access-review recertification are "
        "taught as complementary Entra ID Governance access-lifecycle controls, including an "
        "explicit Lifecycle Workflows versus access-reviews contrast."
    ),
    "defender_xdr_workload_suite": (
        "XDR suite-composition items name the workload Defender services; portal, "
        "vulnerability-management, and threat-intelligence items are investigation/posture "
        "faces of the same Defender XDR mapping."
    ),
    "purview_information_protection_lifecycle": (
        "Classification, sensitivity labels, retention/records, DLP, and Content/Activity "
        "explorer are taught as one information-protection workflow; distinction and "
        "before-labels/DLP items leak across those leaves."
    ),
    "authentication_vs_authorization": (
        "Authentication and authorization items are two sides of the same verify-then-permit "
        "distinction and name each other in stems and explanations."
    ),
    "zero_trust_and_identity_perimeter": (
        "Zero Trust verify-explicitly/least-privilege items and identity-as-primary-perimeter "
        "items teach the same rejection of implicit network trust."
    ),
    "federation_and_identity_providers": (
        "Federation trust items depend on the identity-provider role of authenticating a home "
        "identity for a relying party."
    ),
}

EXPLICIT_TRANSFER_EDGES: dict[frozenset[str], dict[str, str]] = {
    frozenset({"sc900_p1_q037", "sc900_p2_q033"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "SOAR automation/playbook exposure materially transfers across the SIEM/SOAR and Sentinel mitigation leaves.",
    },
    frozenset({"sc900_p1_q027", "sc900_p3_q008"}): {
        "edge_class": "shared_rationale",
        "rationale": "Both identify Microsoft Sentinel as the cloud-native SIEM and SOAR service.",
    },
    frozenset({"sc900_p1_q007", "sc900_p1_q016"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Defender for Cloud is defined as CSPM plus workload protection, which is the CSPM proposition.",
    },
    frozenset({"sc900_p2_q023", "sc900_p1_q015"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Azure Firewall versus NSG discrimination restates the NSG allow/deny subnet-or-NIC proposition.",
    },
    frozenset({"sc900_p3_q095", "sc900_p1_q044"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "NSG versus WAF discrimination restates WAF's HTTP application-layer role.",
    },
    frozenset({"sc900_p3_q015", "sc900_p1_q035"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "DDoS versus WAF discrimination restates DDoS Protection's volumetric network-layer role.",
    },
    frozenset({"sc900_p3_q050", "sc900_p1_q040"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "eDiscovery versus Audit discrimination restates Audit's searchable activity-record proposition.",
    },
    frozenset({"sc900_p3_q099", "sc900_p1_q050"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Audit versus Insider Risk Management discrimination restates the insider-risk internal-activity proposition.",
    },
    frozenset({"sc900_p3_q039", "sc900_p1_q019"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "STP versus Compliance Manager discrimination restates Compliance Manager's customer-posture role.",
    },
    frozenset({"sc900_p1_q039", "sc900_p1_q009"}): {
        "edge_class": "source_sibling_transfer",
        "rationale": "Privacy principles are taught as the companion topic to the Service Trust Portal.",
    },
    frozenset({"sc900_p3_q043", "sc900_p2_q006"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Entra ID versus AD DS discrimination restates the directory-service identity-store proposition.",
    },
    frozenset({"sc900_p3_q082", "sc900_p1_q014"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "ID Protection risk signals are the identity-risk input Conditional Access is taught to evaluate.",
    },
    frozenset({"sc900_p3_q004", "sc900_p1_q005"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Lifecycle Workflows are distinguished from access reviews, leaking the recertification proposition.",
    },
    frozenset({"sc900_p3_q016", "sc900_p1_q008"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Defender XDR suite composition names Defender for Endpoint as the endpoint workload service.",
    },
    frozenset({"sc900_p3_q090", "sc900_p1_q020"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Retention versus sensitivity-label discrimination restates sensitivity-label classification/protection.",
    },
    frozenset({"sc900_p1_q002", "sc900_p1_q021"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Authentication-then-authorization stems are two sides of the same identity-control distinction.",
    },
    frozenset({"sc900_p3_q001", "sc900_p1_q011"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Identity-as-perimeter and Zero Trust both reject implicit trust based on network location.",
    },
    frozenset({"sc900_p3_q081", "sc900_p2_q005"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Federation is taught as using a home identity provider to vouch for a user to a relying party.",
    },
    frozenset({"sc900_p3_q019", "sc900_p1_q010"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Classification-before-DLP workflow items leak the DLP sensitive-sharing proposition.",
    },
    frozenset({"sc900_p3_q088", "sc900_p1_q047"}): {
        "edge_class": "cross_leaf_transfer",
        "rationale": "Vulnerability Management versus incident-response-console discrimination points at the Defender portal/XDR operations experience.",
    },
}

LEAF_BY_GROUP = {leaf: family_id for family_id, leaves in CROSS_LEAF_FAMILY_GROUPS.items() for leaf in leaves}


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(context)
    return payload


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def sha256_canonical_file(path: Path) -> str:
    """SHA-256 of file bytes with CRLF/CR normalized to LF."""
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _rewrite_json_canonical(path: Path) -> None:
    _write_json(path, _load_json(path, []))


def _write_bytes_lf(path: Path) -> None:
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl_dir(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for batch_path in sorted(path.glob("*.jsonl")):
        for line in batch_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"non-object row in {batch_path}")
            rows.append(payload)
    return rows


def _phase2_prior_families() -> dict[str, str]:
    payload = _load_json(PHASE2_SEMANTIC_AUDIT, {})
    decisions = payload.get("decisions", []) if isinstance(payload, Mapping) else []
    result: dict[str, str] = {}
    for row in decisions:
        if not isinstance(row, Mapping):
            continue
        question_id = normalize_text(row.get("question_id"))
        family_id = normalize_text(row.get("semantic_family_id"))
        if question_id and family_id:
            result[question_id] = family_id
    return result


def _blueprint_leaf(record: Mapping[str, Any]) -> str:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    return normalize_text(metadata.get("blueprint_leaf_id"))


def _authored_family(record: Mapping[str, Any]) -> str:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    return normalize_text(metadata.get("semantic_family_id"))


def _probe_suitability(record: Mapping[str, Any]) -> str:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    return normalize_text(metadata.get("future_probe_suitability")) or "needs_review"


def load_cumulative_approved_questions() -> list[dict[str, Any]]:
    rows = _load_jsonl_dir(PHASE1_BATCHES) + _load_jsonl_dir(PHASE2_BATCHES) + _load_jsonl_dir(PHASE3_BATCHES)
    ids = [normalize_text(row.get("id")) for row in rows]
    if len(ids) != EXPECTED_CUMULATIVE_COUNT or len(set(ids)) != EXPECTED_CUMULATIVE_COUNT:
        raise ValueError(
            f"cumulative Task-4 input must be exactly {EXPECTED_CUMULATIVE_COUNT} unique questions, got {len(ids)}"
        )
    return sorted(rows, key=lambda row: normalize_text(row.get("id")))


def load_phase3_semantic_family_audit() -> dict[str, Any]:
    payload = _load_json(SEMANTIC_AUDIT_PATH, {})
    if not isinstance(payload, dict):
        raise ValueError("semantic_family_audit.json must be an object")
    return payload


def _prior_family(record: Mapping[str, Any], phase2_priors: Mapping[str, str]) -> str:
    question_id = normalize_text(record.get("id"))
    return phase2_priors.get(question_id) or _authored_family(record)


def _canonical_family(leaves: Sequence[str]) -> str:
    unique_leaves = [leaf for leaf in sorted(set(leaves)) if leaf]
    group_ids = sorted({LEAF_BY_GROUP[leaf] for leaf in unique_leaves if leaf in LEAF_BY_GROUP})
    if len(group_ids) == 1:
        return group_ids[0]
    if len(group_ids) > 1:
        raise ValueError(f"component mixed cross-leaf groups {group_ids} for leaves {unique_leaves}")
    if len(unique_leaves) == 1:
        return unique_leaves[0]
    return unique_leaves[0] if unique_leaves else "semantic_family_unresolved"


def _same_leaf_rationale(family_id: str) -> str:
    return (
        f"Same-leaf items for {family_id} test the same product/capability proposition or a "
        "scenario variant of it; different wording is not evidence of independence."
    )


def _family_rationale(family_id: str) -> str:
    return FAMILY_RATIONALES.get(family_id, _same_leaf_rationale(family_id))


def _decision_type(prior: str, canonical: str, family_state: str) -> str:
    if family_state in UNRESOLVED_FAMILY_STATES:
        return "unresolved"
    if prior == canonical:
        return "retained"
    return "merged"


def compute_phase3_semantic_family_audit(
    questions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    qids = [normalize_text(row.get("id")) for row in questions]
    if len(qids) != len(set(qids)) or any(not qid for qid in qids):
        raise ValueError("semantic audit requires unique non-empty question IDs")
    by_id = {normalize_text(row["id"]): row for row in questions}
    phase2_priors = _phase2_prior_families()
    uf = _UnionFind(qids)

    by_leaf: dict[str, list[str]] = defaultdict(list)
    for row in questions:
        qid = normalize_text(row["id"])
        leaf = _blueprint_leaf(row)
        if leaf:
            by_leaf[leaf].append(qid)

    for members in by_leaf.values():
        for qid in members[1:]:
            uf.union(members[0], qid)

    for family_id, leaves in CROSS_LEAF_FAMILY_GROUPS.items():
        group_members: list[str] = []
        for leaf in sorted(leaves):
            group_members.extend(by_leaf.get(leaf, []))
        if group_members:
            for qid in group_members[1:]:
                uf.union(group_members[0], qid)

    for edge in EXPLICIT_TRANSFER_EDGES:
        members = sorted(edge)
        if all(member in by_id for member in members):
            uf.union(members[0], members[1])

    components: dict[str, list[str]] = defaultdict(list)
    for qid in qids:
        components[uf.find(qid)].append(qid)

    families: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for members in sorted((sorted(values) for values in components.values()), key=lambda values: values[0]):
        rows = [by_id[qid] for qid in members]
        leaves = sorted({_blueprint_leaf(row) for row in rows if _blueprint_leaf(row)})
        prior_ids = sorted({_prior_family(row, phase2_priors) for row in rows if _prior_family(row, phase2_priors)})
        canonical = _canonical_family(leaves)
        family_state = "resolved" if canonical != "semantic_family_unresolved" else "unresolved"
        decision_type = (
            "unresolved" if family_state == "unresolved" else ("retained" if prior_ids == [canonical] else "merged")
        )
        evidence_class = []
        if len(leaves) == 1:
            evidence_class.append("same_leaf_transfer")
        else:
            evidence_class.append("cross_leaf_transfer")
        if canonical in FAMILY_RATIONALES:
            evidence_class.append("explicit_manual_transfer")
        evidence_class = sorted(set(evidence_class))
        families.append(
            {
                "semantic_family_id": canonical,
                "family_state": family_state,
                "members": members,
                "prior_family_ids": prior_ids,
                "decision_type": decision_type,
                "rationale": _family_rationale(canonical),
                "evidence_class": evidence_class,
                "blueprint_leaf_ids": leaves,
            }
        )
        for row in rows:
            qid = normalize_text(row["id"])
            prior = _prior_family(row, phase2_priors)
            item_state = family_state
            item_type = _decision_type(prior, canonical, item_state)
            probe = _probe_suitability(row)
            if item_state in UNRESOLVED_FAMILY_STATES and probe == PROBE_ELIGIBLE:
                probe = "needs_review"
            decisions.append(
                {
                    "question_id": qid,
                    "semantic_family_id": canonical,
                    "prior_semantic_family_id": prior,
                    "family_state": item_state,
                    "decision_type": item_type,
                    "rationale": _family_rationale(canonical),
                    "evidence_class": evidence_class,
                    "relationship_evidence": [
                        {
                            "edge_class": "same_leaf" if len(leaves) == 1 else "cross_leaf_transfer",
                            "members": members,
                        }
                    ],
                    "component_members": members,
                    "blueprint_leaf_id": _blueprint_leaf(row),
                    "blueprint_leaf_ids": leaves,
                    "correct_answer_text": _correct_answer_text(row),
                    "reviewer": REVIEWER,
                    "review_method": REVIEW_METHOD,
                    "reviewed_at": REVIEWED_AT,
                    "future_probe_suitability": probe,
                    "probe_suitability_consequence": (
                        "unresolved family cannot remain independently PROBE-eligible"
                        if item_state in UNRESOLVED_FAMILY_STATES
                        else "family consolidation changes co-family leakage; TRAIN/PROBE partition remains Task 6"
                    ),
                }
            )

    decisions.sort(key=lambda row: row["question_id"])
    families.sort(key=lambda row: row["semantic_family_id"])
    transfer_edges = []
    for edge, meta in EXPLICIT_TRANSFER_EDGES.items():
        members = sorted(edge)
        if not all(member in by_id for member in members):
            continue
        transfer_edges.append(
            {
                "left": members[0],
                "right": members[1],
                "edge_class": meta["edge_class"],
                "rationale": meta["rationale"],
                "disposition": "merged",
                "semantic_family_id": next(
                    row["semantic_family_id"] for row in decisions if row["question_id"] == members[0]
                ),
            }
        )
    transfer_edges.sort(key=lambda row: (row["left"], row["right"]))
    question_ids = sorted(qids)
    unresolved_family_ids = sorted(
        {row["semantic_family_id"] for row in decisions if row["family_state"] in UNRESOLVED_FAMILY_STATES}
    )
    return {
        "work_id": WORK_ID,
        "audit_version": AUDIT_VERSION,
        "audit_epoch": AUDIT_EPOCH,
        "reviewer": REVIEWER,
        "reviewed_at": REVIEWED_AT,
        "review_method": REVIEW_METHOD,
        "question_count": len(decisions),
        "question_ids": question_ids,
        "family_count": len({row["semantic_family_id"] for row in decisions}),
        "merge_override_count": sum(row["decision_type"] == "merged" for row in decisions),
        "split_override_count": sum(row["decision_type"] == "split" for row in decisions),
        "unresolved_family_count": len(unresolved_family_ids),
        "explicit_transfer_edge_count": len(transfer_edges),
        "rule": {
            "same_blueprint_leaf": "merge_unless_explicit_independence_adjudication",
            "same_normalized_correct_answer": "merge_unless_explicit_independence_adjudication",
            "unknown_or_disputed": "fail_closed",
            "explicit_cross_leaf_transfer_edges": [sorted(edge) for edge in REQUIRED_TRANSFER_EDGES],
        },
        "transfer_edges": transfer_edges,
        "independence_adjudications": [],
        "families": families,
        "decisions": decisions,
    }


def write_phase3_semantic_family_audit(audit: Mapping[str, Any] | None = None) -> dict[str, Any]:
    questions = load_cumulative_approved_questions()
    payload = dict(audit) if audit is not None else compute_phase3_semantic_family_audit(questions)
    errors = validate_phase3_semantic_audit(questions, payload)
    if errors:
        raise ValueError(f"semantic audit failed validation: {errors}")
    _write_json(SEMANTIC_AUDIT_PATH, payload)
    return dict(payload)


def _adjudicated_pairs(audit: Mapping[str, Any]) -> set[frozenset[str]]:
    pairs: set[frozenset[str]] = set()
    for raw in audit.get("independence_adjudications", []):
        if not isinstance(raw, Mapping):
            continue
        ids = [normalize_text(value) for value in raw.get("question_ids", []) if normalize_text(value)]
        if len(ids) >= 2:
            first = ids[0]
            for other in ids[1:]:
                pairs.add(frozenset({first, other}))
    return pairs


def _accounted_transfer_pairs(audit: Mapping[str, Any], family_of: Mapping[str, str]) -> set[frozenset[str]]:
    accounted: set[frozenset[str]] = set()
    for raw in audit.get("transfer_edges", []):
        if not isinstance(raw, Mapping):
            continue
        left = normalize_text(raw.get("left"))
        right = normalize_text(raw.get("right"))
        disposition = normalize_text(raw.get("disposition"))
        if left and right and disposition:
            accounted.add(frozenset({left, right}))
    for left, right_family in family_of.items():
        for right, family_id in family_of.items():
            if left < right and family_id and family_id == right_family:
                accounted.add(frozenset({left, right}))
    return accounted


def validate_phase3_semantic_audit(
    questions: Sequence[Mapping[str, Any]],
    audit: Mapping[str, Any],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    question_ids = [normalize_text(row.get("id")) for row in questions]
    question_id_set = {qid for qid in question_ids if qid}
    raw_decisions = audit.get("decisions", [])
    if not isinstance(raw_decisions, list):
        return [_error("INVALID_AUDIT_DECISIONS", "audit decisions must be an array")]

    seen: dict[str, dict[str, Any]] = {}
    families_of: dict[str, str] = {}
    for raw in raw_decisions:
        if not isinstance(raw, Mapping):
            errors.append(_error("MALFORMED_AUDIT_DECISION", "audit decision must be an object"))
            continue
        question_id = normalize_text(raw.get("question_id"))
        family_id = normalize_text(raw.get("semantic_family_id"))
        family_state = normalize_text(raw.get("family_state")).lower()
        decision_type = normalize_text(raw.get("decision_type")).lower()
        rationale = normalize_text(raw.get("rationale"))
        reviewer = normalize_text(raw.get("reviewer"))
        review_method = normalize_text(raw.get("review_method"))
        reviewed_at = normalize_text(raw.get("reviewed_at"))
        probe = normalize_text(raw.get("future_probe_suitability"))

        if not question_id:
            errors.append(_error("MISSING_AUDIT_QUESTION_ID", "audit decision is missing question_id"))
            continue
        if question_id not in question_id_set:
            errors.append(
                _error(
                    "UNKNOWN_AUDIT_ID",
                    "audit contains a question ID that is not in the cumulative approved set",
                    question_id=question_id,
                )
            )
        if question_id in seen:
            errors.append(
                _error(
                    "DUPLICATE_AUDIT_DECISION",
                    "each question may have exactly one audit decision",
                    question_id=question_id,
                )
            )
            prior_family = normalize_text(seen[question_id].get("semantic_family_id"))
            if family_id and prior_family and family_id != prior_family:
                errors.append(
                    _error(
                        "CONFLICTING_FAMILY_ASSIGNMENT",
                        "the same question received contradictory semantic-family identities",
                        question_id=question_id,
                        families=sorted({prior_family, family_id}),
                    )
                )
        else:
            seen[question_id] = dict(raw)
            families_of[question_id] = family_id

        if not family_id:
            errors.append(
                _error(
                    "MISSING_SEMANTIC_FAMILY_ID",
                    "canonical semantic_family_id is required",
                    question_id=question_id,
                )
            )
        if not rationale:
            errors.append(
                _error(
                    "MISSING_FAMILY_RATIONALE",
                    "each family decision requires an audit rationale",
                    question_id=question_id,
                )
            )
        if not reviewer or not review_method or not reviewed_at:
            errors.append(
                _error(
                    "MISSING_DECISION_PROVENANCE",
                    "each decision requires reviewer, review_method, and reviewed_at",
                    question_id=question_id,
                )
            )
        if family_state in UNRESOLVED_FAMILY_STATES and decision_type in RESOLVED_DECISION_TYPES:
            errors.append(
                _error(
                    "UNRESOLVED_FAMILY_TREATED_AS_RESOLVED",
                    "unresolved or disputed family state cannot be recorded as a resolved decision",
                    question_id=question_id,
                    family_state=family_state,
                    decision_type=decision_type,
                )
            )
        if family_state in UNRESOLVED_FAMILY_STATES and probe == PROBE_ELIGIBLE:
            errors.append(
                _error(
                    "UNRESOLVED_FAMILY_PROBE_ELIGIBLE",
                    "unresolved or disputed families must not remain independently PROBE-eligible",
                    question_id=question_id,
                    family_state=family_state,
                )
            )
        if decision_type and decision_type not in DECISION_TYPES:
            errors.append(
                _error(
                    "INVALID_DECISION_TYPE",
                    "decision_type must be retained, merged, split, or unresolved",
                    question_id=question_id,
                    decision_type=decision_type,
                )
            )

        members = raw.get("component_members")
        if isinstance(members, list):
            member_ids = [normalize_text(value) for value in members if normalize_text(value)]
            member_families = {families_of.get(member_id) or family_id for member_id in member_ids}
            # Defer full member-family comparison until all decisions are indexed.

    missing = sorted(question_id_set - set(seen))
    for question_id in missing:
        errors.append(
            _error(
                "MISSING_AUDIT_DECISION",
                "every cumulative approved question must have an audit decision",
                question_id=question_id,
            )
        )

    reported_count = audit.get("question_count")
    if (
        reported_count != EXPECTED_CUMULATIVE_COUNT
        or len(question_id_set) != EXPECTED_CUMULATIVE_COUNT
        or len(questions) != EXPECTED_CUMULATIVE_COUNT
    ):
        errors.append(
            _error(
                "AUDIT_COUNT_MISMATCH",
                "semantic audit must cover exactly 200 cumulative questions",
                expected=EXPECTED_CUMULATIVE_COUNT,
                reported=reported_count,
                question_ids=len(question_id_set),
            )
        )

    family_of: dict[str, str] = {}
    members_by_id: dict[str, list[str]] = {}
    for question_id, row in seen.items():
        family_of[question_id] = normalize_text(row.get("semantic_family_id"))
        members = row.get("component_members")
        if isinstance(members, list):
            members_by_id[question_id] = [normalize_text(value) for value in members if normalize_text(value)]

    for question_id, members in members_by_id.items():
        family_ids = {family_of.get(member) for member in members if member in family_of}
        family_ids.discard("")
        if len(family_ids) > 1:
            errors.append(
                _error(
                    "CONTRADICTORY_FAMILY_IDENTITY",
                    "the same explicit semantic family was split into contradictory identities",
                    question_id=question_id,
                    families=sorted(family_ids),
                    members=members,
                )
            )

    by_id = {normalize_text(row.get("id")): row for row in questions}
    independence_pairs = _adjudicated_pairs(audit)
    by_leaf: dict[str, list[str]] = defaultdict(list)
    by_answer: dict[str, list[str]] = defaultdict(list)
    for row in questions:
        qid = normalize_text(row.get("id"))
        leaf = _blueprint_leaf(row)
        answer = _answer_key(row)
        if leaf:
            by_leaf[leaf].append(qid)
        if answer:
            by_answer[answer].append(qid)

    def _high_risk(members: Sequence[str], reason: str) -> None:
        unique = [qid for qid in members if qid]
        for index, left in enumerate(unique):
            for right in unique[index + 1 :]:
                if family_of.get(left) and family_of.get(right) and family_of[left] != family_of[right]:
                    pair = frozenset({left, right})
                    if pair not in independence_pairs:
                        errors.append(
                            _error(
                                "HIGH_RISK_PAIR_UNADJUDICATED",
                                "same-leaf or shared-answer pair treated as independent without explicit adjudication",
                                left=left,
                                right=right,
                                reason=reason,
                            )
                        )

    for leaf, members in by_leaf.items():
        _high_risk(members, f"same_blueprint_leaf:{leaf}")
    for answer, members in by_answer.items():
        if len(members) > 1:
            _high_risk(members, f"shared_correct_answer:{answer}")

    accounted = _accounted_transfer_pairs(audit, family_of)
    present_ids = set(family_of) | question_id_set
    for edge in REQUIRED_TRANSFER_EDGES:
        members = sorted(edge)
        if not all(member in present_ids for member in members):
            continue
        if frozenset(members) not in accounted:
            errors.append(
                _error(
                    "TRANSFER_EDGE_UNACCOUNTED",
                    "a known material transfer edge was left unaccounted for",
                    left=members[0],
                    right=members[1],
                )
            )

    reported_family_count = audit.get("family_count")
    actual_family_count = len({family_id for family_id in family_of.values() if family_id})
    if reported_family_count is not None and reported_family_count != actual_family_count:
        errors.append(
            _error(
                "AUDIT_FAMILY_COUNT_MISMATCH",
                "reported family_count does not match unique canonical family IDs",
                expected=actual_family_count,
                actual=reported_family_count,
            )
        )
    return errors


def posix_repo_path(path: Path) -> str:
    relative = path.resolve().relative_to(ROOT).as_posix()
    if "\\" in relative:
        raise ValueError("NONDETERMINISTIC_PATH")
    return relative


def _hash_map(paths: Sequence[Path]) -> dict[str, str]:
    return {posix_repo_path(path): sha256_canonical_file(path) for path in paths}


def _load_review_receipts(reviews_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(reviews_dir.glob("*.json")):
        payload = _load_json(path, {})
        rows = payload.get("reviews", []) if isinstance(payload, Mapping) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            question_id = normalize_text(row.get("question_id"))
            if not question_id:
                continue
            if question_id in result:
                raise ValueError(f"duplicate review receipt for {question_id} in {posix_repo_path(path)}")
            result[question_id] = row
    return result


def load_phase3_records() -> list[dict[str, Any]]:
    return _load_jsonl_dir(PHASE3_BATCHES)


def load_phase3_reviews() -> dict[str, dict[str, Any]]:
    return _load_review_receipts(PHASE3_REVIEWS)


def pending_before_approval_errors(
    questions: Sequence[Mapping[str, Any]],
    phase3_ids: Sequence[str],
    approved_predecessor_count: int = 100,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    phase3_id_set = {normalize_text(question_id) for question_id in phase3_ids}
    imported = [row for row in questions if normalize_text(row.get("id")) in phase3_id_set]
    predecessors = [row for row in questions if normalize_text(row.get("id")) not in phase3_id_set]
    imported_counts = promotion_counts(imported)
    predecessor_counts = promotion_counts(predecessors)
    bypassed = [
        normalize_text(row.get("id"))
        for row in imported
        if normalize_text(row.get("promotion_status")).lower() != "pending"
    ]
    if bypassed or imported_counts["approved"] != 0:
        errors.append(
            _error(
                "IMPORT_BYPASSES_PENDING",
                "Phase-3 authored records must enter the store as pending before review promotion",
                approved_ids=bypassed,
                imported_counts=imported_counts,
            )
        )
    if imported_counts["pending"] != len(phase3_id_set) or len(imported) != len(phase3_id_set):
        errors.append(
            _error(
                "PHASE3_PENDING_IMPORT_COUNT_MISMATCH",
                "Phase-3 pending import count must equal the frozen 100-question ID set",
                expected=len(phase3_id_set),
                actual=imported_counts["pending"],
            )
        )
    if predecessor_counts["approved"] != approved_predecessor_count:
        errors.append(
            _error(
                "PREDECESSOR_APPROVED_COUNT_MISMATCH",
                "Phase-3 import must start from the accepted 100 approved predecessor questions",
                expected=approved_predecessor_count,
                actual=predecessor_counts["approved"],
            )
        )
    return errors


def phase3_review_custody_errors(
    records: Sequence[Mapping[str, Any]],
    reviews: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    seen_ids: list[str] = []
    for record in records:
        question_id = normalize_text(record.get("id"))
        seen_ids.append(question_id)
        receipt = reviews.get(question_id)
        if receipt is None:
            errors.append(
                _error(
                    "MISSING_REVIEW_RECEIPT",
                    "Phase-3 approval requires a matching content-bound review receipt",
                    question_id=question_id,
                )
            )
            continue
        if normalize_text(receipt.get("disposition")).lower() != "approved":
            errors.append(
                _error(
                    "REVIEW_DISPOSITION_MISMATCH",
                    "Phase-3 promotion requires an approved review disposition",
                    question_id=question_id,
                )
            )
        failed_checks = [field for field in REVIEW_CHECK_FIELDS if receipt.get(field) is not True]
        if failed_checks:
            errors.append(
                _error(
                    "REVIEW_RECEIPT_INCOMPLETE",
                    "review receipt is missing required affirmative checks",
                    question_id=question_id,
                    fields=failed_checks,
                )
            )
        expected_hash = review_content_sha256(record)
        actual_hash = normalize_text(receipt.get("reviewed_content_sha256")).lower()
        if actual_hash != expected_hash:
            errors.append(
                _error(
                    "STALE_REVIEW_HASH",
                    "Phase-3 review receipt is not bound to the exact reviewed question content",
                    question_id=question_id,
                    expected=expected_hash,
                    actual=actual_hash or "<missing>",
                )
            )
        if not normalize_text(receipt.get("reviewer")) or not normalize_text(receipt.get("reviewed_at")):
            errors.append(
                _error(
                    "REVIEW_CUSTODY_INCOMPLETE",
                    "review receipt must identify reviewer and reviewed_at",
                    question_id=question_id,
                )
            )
    extra = sorted(set(reviews) - set(seen_ids))
    if extra:
        errors.append(
            _error(
                "UNKNOWN_REVIEW_RECEIPT",
                "review receipts exist for question IDs that were not authored in Phase 3",
                question_ids=extra,
            )
        )
    return errors


def apply_task4_semantic_audit(questions: Sequence[dict[str, Any]], audit: Mapping[str, Any]) -> None:
    decisions = {
        normalize_text(row.get("question_id")): row
        for row in audit.get("decisions", [])
        if isinstance(row, Mapping) and normalize_text(row.get("question_id"))
    }
    for record in questions:
        question_id = normalize_text(record.get("id"))
        decision = decisions.get(question_id)
        if decision is None:
            continue
        metadata = dict(record.get("metadata") or {})
        prior = normalize_text(decision.get("prior_semantic_family_id")) or normalize_text(
            metadata.get("semantic_family_id")
        )
        metadata["prior_semantic_family_id"] = prior
        metadata["semantic_family_id"] = normalize_text(decision.get("semantic_family_id"))
        metadata["semantic_audit_version"] = normalize_text(audit.get("audit_version")) or AUDIT_VERSION
        metadata["semantic_audit_epoch"] = normalize_text(audit.get("audit_epoch")) or AUDIT_EPOCH
        metadata["semantic_decision_type"] = normalize_text(decision.get("decision_type"))
        probe = normalize_text(decision.get("future_probe_suitability"))
        if probe:
            metadata["future_probe_suitability"] = probe
        record["metadata"] = metadata


def store_semantic_application_errors(
    questions: Sequence[Mapping[str, Any]],
    audit: Mapping[str, Any],
    expected_family_count: int = EXPECTED_SEMANTIC_FAMILY_COUNT,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    approved = [
        row
        for row in questions
        if normalize_text(row.get("promotion_status")).lower() == "approved" or row.get("promotion_status") is None
    ]
    approved_ids = [normalize_text(row.get("id")) for row in approved]
    decisions: dict[str, Mapping[str, Any]] = {}
    for raw in audit.get("decisions", []):
        if not isinstance(raw, Mapping):
            continue
        question_id = normalize_text(raw.get("question_id"))
        if not question_id:
            continue
        if question_id in decisions:
            errors.append(
                _error(
                    "DUPLICATE_AUDIT_DECISION",
                    "semantic audit contains a duplicate question decision",
                    question_id=question_id,
                )
            )
            continue
        decisions[question_id] = raw
    missing = sorted(set(approved_ids) - set(decisions))
    unknown = sorted(set(decisions) - set(approved_ids))
    if missing:
        errors.append(
            _error(
                "MISSING_AUDIT_DECISION",
                "an approved question has no accepted Task-4 semantic decision",
                question_ids=missing,
            )
        )
    if unknown:
        errors.append(
            _error(
                "UNKNOWN_AUDIT_ID",
                "semantic audit contains a decision for an unknown question ID",
                question_ids=unknown,
            )
        )
    families: set[str] = set()
    for record in approved:
        question_id = normalize_text(record.get("id"))
        decision = decisions.get(question_id)
        if decision is None:
            continue
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        actual_family = normalize_text(metadata.get("semantic_family_id"))
        expected_family = normalize_text(decision.get("semantic_family_id"))
        families.add(actual_family)
        if not expected_family or actual_family != expected_family:
            errors.append(
                _error(
                    "SEMANTIC_AUDIT_STORE_MISMATCH",
                    "canonical store family does not match accepted Task-4 authority",
                    question_id=question_id,
                    expected=expected_family,
                    actual=actual_family,
                )
            )
        family_state = normalize_text(decision.get("family_state")).lower()
        if family_state in UNRESOLVED_FAMILY_STATES:
            errors.append(
                _error(
                    "UNRESOLVED_FAMILY_REMAINING",
                    "Task-4 unresolved family remained after semantic-audit application",
                    question_id=question_id,
                    family_state=family_state,
                )
            )
    actual_family_count = len({family for family in families if family})
    reported_family_count = audit.get("family_count")
    if actual_family_count != expected_family_count or reported_family_count != expected_family_count:
        errors.append(
            _error(
                "SEMANTIC_FAMILY_COUNT_MISMATCH",
                "applied semantic-family count does not match the accepted 27-family structure",
                expected=expected_family_count,
                actual=actual_family_count,
                reported=reported_family_count,
            )
        )
    return errors


def _copy_phase2_store(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in STORE_FILES:
        source = PHASE2_STORE / name
        if source.exists():
            shutil.copy2(source, destination / name)
        else:
            _write_json(destination / name, [])


def _normalize_generated_custody(
    store_dir: Path,
    phase3_ids: set[str],
    reviews: Mapping[str, Mapping[str, Any]],
) -> None:
    questions = _load_json(store_dir / "questions.json", [])
    for row in questions:
        if normalize_text(row.get("id")) in phase3_ids:
            provenance = dict(row.get("provenance") or {})
            provenance["imported_at"] = DETERMINISTIC_IMPORT_AT
            provenance["phase"] = "phase3"
            row["provenance"] = provenance
            metadata = dict(row.get("metadata") or {})
            metadata["phase"] = "phase3"
            row["metadata"] = metadata
    _write_json(store_dir / "questions.json", questions)

    decisions = _load_json(store_dir / "review_decisions.json", [])
    for row in decisions:
        question_id = normalize_text(row.get("id"))
        if question_id not in phase3_ids:
            continue
        decision = normalize_text(row.get("decision")).lower()
        if decision == "pending":
            row["actor"] = "import"
            row["decided_at"] = DETERMINISTIC_IMPORT_AT
        elif decision == "approved":
            receipt = reviews[question_id]
            row["actor"] = normalize_text(receipt.get("reviewer")) or "phase3-reviewer"
            row["decided_at"] = normalize_text(receipt.get("reviewed_at")) or DETERMINISTIC_IMPORT_AT
    _write_json(store_dir / "review_decisions.json", decisions)


def _count_by(questions: Sequence[Mapping[str, Any]], field: str, expected: Mapping[str, int]) -> dict[str, int]:
    counts = Counter(normalize_text(row.get(field)) for row in questions)
    return {key: int(counts.get(key, 0)) for key in expected}


def _distinct_leaves(questions: Sequence[Mapping[str, Any]]) -> set[str]:
    leaves: set[str] = set()
    for row in questions:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
        leaf = normalize_text(metadata.get("blueprint_leaf_id"))
        if leaf:
            leaves.add(leaf)
    return leaves


def _fail_closed(errors: Sequence[Mapping[str, Any]], *, code: str = "BUILD_FAILED") -> None:
    if errors:
        raise ValueError(json.dumps({"code": code, "errors": list(errors)}, sort_keys=True))


def _verify_predecessor_store() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    questions_path = PHASE2_STORE / "questions.json"
    if not questions_path.exists():
        errors.append(_error("PHASE2_STORE_MISSING", "accepted Phase-2 questions store is missing"))
        return errors
    questions = _load_json(questions_path, [])
    counts = promotion_counts(questions)
    if counts != {"approved": 100, "pending": 0, "withheld": 0}:
        errors.append(
            _error(
                "PHASE2_STORE_NOT_TERMINAL",
                "accepted Phase-2 store must contain exactly 100 approved questions",
                actual=counts,
            )
        )
    return errors


def build_phase3(work_dir: Path) -> dict[str, Any]:
    taxonomy = load_taxonomy()
    phase3_records = load_phase3_records()
    phase3_ids = [normalize_text(row.get("id")) for row in phase3_records]
    if sorted(phase3_ids) != EXPECTED_PHASE3_IDS or len(phase3_ids) != len(set(phase3_ids)):
        raise ValueError("Phase 3 requires exactly sc900_p3_q001 through sc900_p3_q100")

    reviews = load_phase3_reviews()
    review_errors = phase3_review_custody_errors(phase3_records, reviews)
    _fail_closed(review_errors, code="REVIEW_CUSTODY_FAILED")

    actual_audit_hash = sha256_canonical_file(SEMANTIC_AUDIT_PATH)
    if actual_audit_hash != EXPECTED_SEMANTIC_AUDIT_SHA256:
        raise ValueError(
            f"semantic audit hash mismatch expected={EXPECTED_SEMANTIC_AUDIT_SHA256} actual={actual_audit_hash}"
        )
    audit = load_phase3_semantic_family_audit()
    authored_cumulative = load_cumulative_approved_questions()
    audit_structure_errors = validate_phase3_semantic_audit(authored_cumulative, audit)
    _fail_closed(audit_structure_errors, code="SEMANTIC_AUDIT_INVALID")
    if (
        audit.get("family_count") != EXPECTED_SEMANTIC_FAMILY_COUNT
        or audit.get("merge_override_count") != EXPECTED_MERGE_OVERRIDE_COUNT
        or audit.get("split_override_count") != EXPECTED_SPLIT_OVERRIDE_COUNT
        or audit.get("unresolved_family_count") != EXPECTED_UNRESOLVED_FAMILY_COUNT
    ):
        raise ValueError("accepted Task-4 semantic structure is not intact")

    predecessor_errors = _verify_predecessor_store()
    _fail_closed(predecessor_errors, code="PREDECESSOR_STORE_DRIFT")

    default_bank_sha256 = sha256_canonical_file(DEFAULT_BANK)
    store_dir = work_dir / "store"
    compiled_path = work_dir / "compiled.json"
    _copy_phase2_store(store_dir)

    predecessor_questions = _load_json(store_dir / "questions.json", [])
    predecessor_counts = promotion_counts(predecessor_questions)
    if predecessor_counts != {"approved": 100, "pending": 0, "withheld": 0}:
        raise ValueError(f"Phase-2 predecessor store is not terminal approved: {predecessor_counts}")

    import_reports: list[dict[str, Any]] = []
    for batch in sorted(PHASE3_BATCHES.glob("*.jsonl")):
        report = import_jsonl(batch, store_dir, taxonomy)
        import_reports.append(report)
        if report["accepted"] != 10 or report["rejected"] or report["skipped"] or report["review"]:
            raise ValueError(f"Phase-3 import failed closed for {batch.name}: {report}")
    for report, batch in zip(import_reports, sorted(PHASE3_BATCHES.glob("*.jsonl")), strict=True):
        report["batch_fingerprint"] = sha256_canonical_file(batch)

    preapproval_questions = _load_json(store_dir / "questions.json", [])
    pending_errors = pending_before_approval_errors(preapproval_questions, EXPECTED_PHASE3_IDS)
    _fail_closed(pending_errors, code="IMPORT_BYPASSES_PENDING")
    counts_before = promotion_counts(preapproval_questions)
    phase3_before = [row for row in preapproval_questions if normalize_text(row.get("id")) in set(EXPECTED_PHASE3_IDS)]
    phase3_approved_before_review = promotion_counts(phase3_before)["approved"]
    pending_ledger = _load_json(store_dir / "review_decisions.json", [])
    pending_ids = {
        normalize_text(row.get("id"))
        for row in pending_ledger
        if normalize_text(row.get("decision")).lower() == "pending"
    }
    if not set(EXPECTED_PHASE3_IDS).issubset(pending_ids):
        raise ValueError("import-pending ledger is missing one or more Phase-3 IDs")

    for question_id in EXPECTED_PHASE3_IDS:
        receipt = reviews[question_id]
        apply_review_decision(
            store_dir,
            question_id,
            "approved",
            actor=normalize_text(receipt.get("reviewer")),
        )

    _normalize_generated_custody(store_dir, set(EXPECTED_PHASE3_IDS), reviews)
    questions = _load_json(store_dir / "questions.json", [])
    counts_after = promotion_counts(questions)
    phase3_after = [row for row in questions if normalize_text(row.get("id")) in set(EXPECTED_PHASE3_IDS)]
    phase3_after_counts = promotion_counts(phase3_after)
    if counts_after != {"approved": 200, "pending": 0, "withheld": 0}:
        raise ValueError(f"post-review promotion counts invalid: {counts_after}")
    if phase3_after_counts != {"approved": 100, "pending": 0, "withheld": 0}:
        raise ValueError(f"Phase-3 post-review counts invalid: {phase3_after_counts}")

    apply_task4_semantic_audit(questions, audit)
    semantic_errors = store_semantic_application_errors(
        questions,
        audit,
        expected_family_count=EXPECTED_SEMANTIC_FAMILY_COUNT,
    )
    _fail_closed(semantic_errors, code="SEMANTIC_AUDIT_APPLICATION_FAILED")
    _write_json(store_dir / "questions.json", questions)

    compile_result = compile_question_bank(store_dir, compiled_path)
    if compile_result["compiled"] != 200:
        raise ValueError(f"compiled count invalid: {compile_result}")
    for name in STORE_FILES:
        _rewrite_json_canonical(store_dir / name)
    _write_bytes_lf(compiled_path)

    inventory = _load_json(PHASE3_SOURCE_INVENTORY, {})
    source_errors = validate_phase3_source_inventory(inventory, taxonomy)
    source_errors.extend(validate_question_source_links(phase3_after, inventory))
    _fail_closed(source_errors, code="SOURCE_CUSTODY_FAILED")

    approved = [row for row in questions if normalize_text(row.get("promotion_status")).lower() == "approved"]
    domain_counts = _count_by(approved, "domain", EXPECTED_PHASE3_DOMAIN_COUNTS)
    objective_counts = _count_by(approved, "objective", EXPECTED_PHASE3_OBJECTIVE_COUNTS)
    distinct_leaves = _distinct_leaves(approved)
    if domain_counts != dict(EXPECTED_PHASE3_DOMAIN_COUNTS):
        raise ValueError(f"domain allocation mismatch: {domain_counts}")
    if objective_counts != dict(EXPECTED_PHASE3_OBJECTIVE_COUNTS):
        raise ValueError(f"objective allocation mismatch: {objective_counts}")
    if len(distinct_leaves) != EXPECTED_BLUEPRINT_LEAF_COUNT:
        raise ValueError(f"leaf coverage mismatch: {len(distinct_leaves)}")
    if sha256_canonical_file(DEFAULT_BANK) != default_bank_sha256:
        raise ValueError("default launch bank changed during Phase-3 build")

    families = {
        normalize_text((row.get("metadata") or {}).get("semantic_family_id"))
        for row in approved
        if isinstance(row.get("metadata"), Mapping)
    }
    custody = {
        "transitions": list(CUSTODY_TRANSITIONS),
        "review_hash_algorithm": REVIEW_HASH_ALGORITHM,
        "import_pending_ledger_complete": True,
        "phase3_authored_count": 100,
        "phase3_imported_pending_count_before_review": promotion_counts(phase3_before)["pending"],
        "phase3_approved_before_review_application": phase3_approved_before_review,
        "phase3_review_receipts_applied": len(EXPECTED_PHASE3_IDS),
        "phase3_approved_after_review": phase3_after_counts["approved"],
        "phase3_pending_after_review": phase3_after_counts["pending"],
        "phase3_withheld_after_review": phase3_after_counts["withheld"],
        "cumulative_counts_before_review": counts_before,
        "cumulative_counts_after_review": counts_after,
        "semantic_family_audit_reviewed_by": normalize_text(audit.get("reviewer")) or REVIEWER,
        "semantic_family_audit_reviewed_at": normalize_text(audit.get("reviewed_at")) or REVIEWED_AT,
    }
    receipt = {
        "build_receipt_version": BUILD_RECEIPT_VERSION,
        "work_id": WORK_ID,
        "build_epoch": BUILD_EPOCH,
        "builder": BUILDER_IDENTITY,
        "builder_version": BUILDER_VERSION,
        "status": "REPRODUCIBLE",
        "phase3_authored_count": 100,
        "phase3_imported_pending_count_before_review": custody["phase3_imported_pending_count_before_review"],
        "phase3_approved_before_review_application": phase3_approved_before_review,
        "phase3_review_receipts_applied": 100,
        "phase3_approved_after_review": phase3_after_counts["approved"],
        "phase3_pending_after_review": phase3_after_counts["pending"],
        "phase3_withheld_after_review": phase3_after_counts["withheld"],
        "approved_count": counts_after["approved"],
        "pending_count": counts_after["pending"],
        "withheld_count": counts_after["withheld"],
        "compiled_count": compile_result["compiled"],
        "phase3_ids": list(EXPECTED_PHASE3_IDS),
        "domain_counts": domain_counts,
        "objective_counts": objective_counts,
        "distinct_leaf_count": len(distinct_leaves),
        "semantic_family_count": len(families),
        "semantic_merge_override_count": audit.get("merge_override_count"),
        "semantic_split_override_count": audit.get("split_override_count"),
        "semantic_unresolved_family_count": audit.get("unresolved_family_count"),
        "cand01_gate2_status": GATE2_STATUS,
        "implementation_authorized": False,
        "phase_3_structurally_accepted": False,
        "task_6_required": True,
        "build_errors": [],
        "inputs": {
            "phase1_batches": _hash_map(sorted(PHASE1_BATCHES.glob("*.jsonl"))),
            "phase1_reviews": _hash_map(sorted(PHASE1_REVIEWS.glob("*.json"))),
            "phase1_questions_sha256": sha256_canonical_file(PHASE1_STORE / "questions.json"),
            "phase2_batches": _hash_map(sorted(PHASE2_BATCHES.glob("*.jsonl"))),
            "phase2_reviews": _hash_map(sorted(PHASE2_REVIEWS.glob("*.json"))),
            "phase2_questions_sha256": sha256_canonical_file(PHASE2_STORE / "questions.json"),
            "phase2_semantic_audit_sha256": sha256_canonical_file(PHASE2_SEMANTIC_AUDIT),
            "phase2_build_receipt_sha256": sha256_canonical_file(PHASE2_BUILD_RECEIPT),
            "batches": _hash_map(sorted(PHASE3_BATCHES.glob("*.jsonl"))),
            "reviews": _hash_map(sorted(PHASE3_REVIEWS.glob("*.json"))),
            "source_inventory_sha256": sha256_canonical_file(PHASE3_SOURCE_INVENTORY),
            "semantic_audit_sha256": actual_audit_hash,
            "semantic_audit_expected_sha256": EXPECTED_SEMANTIC_AUDIT_SHA256,
        },
        "outputs": {
            "store": {name: sha256_canonical_file(store_dir / name) for name in STORE_FILES},
            "compiled_sha256": sha256_canonical_file(compiled_path),
            "default_launch_bank_sha256": default_bank_sha256,
        },
        "import_reports": import_reports,
        "custody": custody,
    }
    acceptance_report = {
        "task": 5,
        "task_status": "TASK_5_DETERMINISTIC_BUILD_ACCEPTED",
        "approved_count": 200,
        "compiled_count": 200,
        "phase3_new_count": 100,
        "pending_count": 0,
        "withheld_count": 0,
        "domain_counts": domain_counts,
        "objective_counts": objective_counts,
        "distinct_leaf_count": len(distinct_leaves),
        "semantic_family_count": len(families),
        "semantic_merge_override_count": audit.get("merge_override_count"),
        "semantic_split_override_count": audit.get("split_override_count"),
        "semantic_unresolved_family_count": audit.get("unresolved_family_count"),
        "source_inventory_errors": [],
        "review_custody_errors": [],
        "semantic_audit_errors": [],
        "build_errors": [],
        "reproducibility": "REPRODUCIBLE",
        "default_bank_unchanged": True,
        "cand01_gate2_status": GATE2_STATUS,
        "implementation_authorized": False,
        "task_6_required": True,
        "phase_3_structurally_accepted": False,
        "compiled_sha256": sha256_canonical_file(compiled_path),
        "default_launch_bank_sha256": default_bank_sha256,
        "semantic_audit_sha256": actual_audit_hash,
        "work_id": WORK_ID,
        "build_epoch": BUILD_EPOCH,
    }
    return {
        "store_dir": store_dir,
        "compiled_path": compiled_path,
        "receipt": receipt,
        "acceptance_report": acceptance_report,
    }


def write_committed_phase3_build(build: Mapping[str, Any]) -> None:
    PHASE3_STORE.mkdir(parents=True, exist_ok=True)
    for name in STORE_FILES:
        shutil.copy2(Path(build["store_dir"]) / name, PHASE3_STORE / name)
    PHASE3_COMPILED.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(build["compiled_path"]), PHASE3_COMPILED)
    _write_json(BUILD_RECEIPT_PATH, build["receipt"])
    _write_json(ACCEPTANCE_REPORT_PATH, build["acceptance_report"])


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def verify_committed_phase3_build() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="sc900-phase3-verify-") as temp_dir:
        build = build_phase3(Path(temp_dir))
        for name in STORE_FILES:
            expected = Path(build["store_dir"]) / name
            actual = PHASE3_STORE / name
            if not actual.exists() or _canonical_bytes(actual) != _canonical_bytes(expected):
                errors.append(
                    _error("STORE_ARTIFACT_DRIFT", "store artifact differs from independent rebuild", file=name)
                )
        if not PHASE3_COMPILED.exists() or _canonical_bytes(PHASE3_COMPILED) != _canonical_bytes(
            Path(build["compiled_path"])
        ):
            errors.append(_error("COMPILED_BANK_DRIFT", "compiled candidate bank differs from independent rebuild"))
        committed_receipt = _load_json(BUILD_RECEIPT_PATH, {})
        if committed_receipt != build["receipt"]:
            errors.append(_error("BUILD_RECEIPT_DRIFT", "build receipt differs from independent rebuild"))
        committed_acceptance = _load_json(ACCEPTANCE_REPORT_PATH, {})
        if committed_acceptance != build["acceptance_report"]:
            errors.append(_error("ACCEPTANCE_REPORT_DRIFT", "acceptance report differs from independent rebuild"))
    return errors


def _run_semantic_audit_cli(write: bool) -> int:
    questions = load_cumulative_approved_questions()
    computed = compute_phase3_semantic_family_audit(questions)
    if write:
        write_phase3_semantic_family_audit(computed)
        print(
            json.dumps(
                {
                    "status": "WRITTEN",
                    "path": posix_repo_path(SEMANTIC_AUDIT_PATH),
                    "question_count": computed["question_count"],
                    "family_count": computed["family_count"],
                    "merge_override_count": computed["merge_override_count"],
                    "split_override_count": computed["split_override_count"],
                    "unresolved_family_count": computed["unresolved_family_count"],
                    "explicit_transfer_edge_count": computed["explicit_transfer_edge_count"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    committed = load_phase3_semantic_family_audit()
    errors = validate_phase3_semantic_audit(questions, committed)
    if committed != computed:
        errors.append(_error("AUDIT_NOT_REPRODUCIBLE", "committed audit differs from recomputed audit"))
    if errors:
        print(json.dumps({"status": "DRIFT", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "REPRODUCIBLE",
                "question_count": computed["question_count"],
                "family_count": computed["family_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SC-900 Phase 3 semantic-audit helper and deterministic Task-5 builder."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-semantic-audit", action="store_true")
    mode.add_argument("--verify-semantic-audit", action="store_true")
    mode.add_argument("--write", action="store_true", help="Write deterministic cumulative Phase-3 build artifacts.")
    mode.add_argument(
        "--verify-committed",
        action="store_true",
        help="Rebuild independently and compare with committed Task-5 artifacts.",
    )
    args = parser.parse_args()
    if args.write_semantic_audit or args.verify_semantic_audit:
        return _run_semantic_audit_cli(write=bool(args.write_semantic_audit))
    if args.write:
        with tempfile.TemporaryDirectory(prefix="sc900-phase3-build-") as temp_dir:
            build = build_phase3(Path(temp_dir))
            write_committed_phase3_build(build)
            print(json.dumps(build["receipt"], indent=2, sort_keys=True))
            return 0
    errors = verify_committed_phase3_build()
    if errors:
        print(json.dumps({"status": "DRIFT", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(json.dumps({"status": "REPRODUCIBLE"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
