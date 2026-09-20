from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import AdmissionStatus, canonical_manifest_sha256, sha256_file
from content_revision_correction_authority import (
    CHOICE_LABELS,
    CONTINUITY_POLICY,
    CURRENTNESS_REQUIREMENTS,
    EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256,
    EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256,
    EXPECTED_SOURCE_BANK_SHA256,
    EXPECTED_SOURCE_CONTENT_FINGERPRINT,
    EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256,
    MANIFEST_KIND,
    PERMITTED_CHANGE_CLASS,
    PROMPT_CHANGED_IDS,
    Q219_PRIOR_CURRENTNESS_WORK_ID,
    Q219_REPLACEMENT_WORK_ID,
    Q219_TESTED_DECISION,
    REQUIRED_QUESTION_COUNT,
    REVIEW_DISPOSITION_APPROVED,
    REVIEW_STATUS_APPROVED,
    SCHEMA_VERSION,
    SOURCE_BANK_FILENAME,
    SOURCE_VALIDATION_WORK_ID,
    TARGET_BANK_FILENAME,
    TARGET_IDS,
    WORK_ID,
    CorrectionFailureReason,
    admit_content_correction,
)
from package_b_canonical_json import write_canonical_package_b_json
from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint

REVIEW_DIRECTORY = "SC900-SEPARATE-CONTENT-CORRECTION-001"
CORRECTION_SPEC_RELATIVE_PATH = "content_revision_evidence/specs/sc900_content_correction_001.json"
CURRENTNESS_RECORD_RELATIVE_PATH = "content_revision_evidence/currentness/sc900_content_correction_001.json"
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_content_correction_001.json"
T5_MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t5.json"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
CURRENTNESS_CHECKED_AT = "2026-09-20T17:58:24Z"
Q118_Q269_CHECKED_AT = "2026-09-20T17:32:35Z"
FINAL_STATUSES = {
    "sc900_mlc_q064": "REVISED_SAFE",
    "sc900_mlc_q118": "VALIDATED_SAFE",
    "sc900_mlc_q150": "REVISED_SAFE",
    "sc900_mlc_q198": "VALIDATED_SAFE",
    "sc900_mlc_q219": "Q219_REPLACEMENT_FROZEN_NINE_QUESTION_SEMANTIC_INPUT_READY",
    "sc900_mlc_q226": "REVISED_SAFE",
    "sc900_mlc_q242": "VALIDATED_SAFE",
    "sc900_mlc_q249": "VALIDATED_SAFE",
    "sc900_mlc_q269": "VALIDATED_SAFE",
}
CURRENTNESS_CLASS = {
    "sc900_mlc_q064": "MODERATE",
    "sc900_mlc_q118": "MODERATE",
    "sc900_mlc_q150": "LOW",
    "sc900_mlc_q198": "MODERATE",
    "sc900_mlc_q219": "HIGH",
    "sc900_mlc_q226": "LOW",
    "sc900_mlc_q242": "MODERATE",
    "sc900_mlc_q249": "LOW",
    "sc900_mlc_q269": "MODERATE",
}
CURRENTNESS_AUTHORITY = {
    "sc900_mlc_q118": [
        "https://learn.microsoft.com/en-us/defender-vulnerability-management/defender-vulnerability-management",
        "https://learn.microsoft.com/en-us/defender-vulnerability-management/defender-vulnerability-management-capabilities",
    ],
    "sc900_mlc_q219": [
        "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900",
        "https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-sync-whatis",
        "https://learn.microsoft.com/en-us/training/modules/explore-basic-services-identity-types/4-describe-concept-of-hybrid-identity",
    ],
    "sc900_mlc_q269": [
        "https://learn.microsoft.com/en-us/azure/sentinel/automate-incident-handling-with-automation-rules",
        "https://learn.microsoft.com/en-us/azure/sentinel/automation/run-playbooks",
        "https://learn.microsoft.com/en-us/defender-xdr/automatic-attack-disruption",
    ],
}
SEMANTIC_TARGETS = {
    "sc900_mlc_q064": {
        "prompt": "A policy must require MFA for selected administrator roles and allow administrators to choose exactly which built-in roles are targeted. Which Microsoft Entra feature supports that scoping?",
        "choices": {
            "A": "Conditional Access targeting directory roles",
            "B": "Self-service password reset",
            "C": "Microsoft Entra Password Protection",
            "D": "Security defaults",
        },
        "explanation": "Conditional Access assignments can target directory roles, and Conditional Access grant controls can require multifactor authentication. Security defaults provides broad preconfigured MFA protections but does not let administrators customize exactly which administrator roles are targeted. Self-service password reset and Password Protection serve different functions.",
    },
    "sc900_mlc_q118": {
        "prompt": "Leadership wants a prioritized list of exposed software weaknesses on endpoints, not a SIEM correlation timeline. Which capability fits?",
        "choices": {
            "A": "Microsoft Sentinel hunting",
            "B": "Microsoft Defender for Identity",
            "C": "Microsoft Defender for Office 365",
            "D": "Microsoft Defender Vulnerability Management",
        },
        "explanation": "Microsoft Defender Vulnerability Management is the vulnerability-management capability for discovering, assessing, prioritizing, and tracking remediation of endpoint weaknesses. Defender for Endpoint Plan 2 already includes core Defender Vulnerability Management capabilities such as vulnerability assessment and risk-based prioritization, so Defender for Endpoint should not be used as a competing distractor for this generic requirement.",
    },
    "sc900_mlc_q150": {
        "prompt": "Business users should request a governed bundle of application access that can require approval. Which Microsoft Entra ID Governance feature provides that requestable bundle?",
        "choices": {
            "A": "Access reviews",
            "B": "An access package in Microsoft Entra entitlement management",
            "C": "Lifecycle Workflows",
            "D": "Privileged Identity Management",
        },
        "explanation": "An access package is the requestable bundle of resource roles and access policies within Microsoft Entra entitlement management. Entitlement management is the broader capability; access reviews, lifecycle workflows, and Privileged Identity Management address different governance tasks.",
    },
    "sc900_mlc_q198": {
        "prompt": "Security wants to correlate user-behavior signals, assign risk, and investigate whether departing employees are engaging in unusual exfiltration activity. Which Microsoft Purview solution is designed for that risk-investigation workflow?",
        "choices": {
            "A": "Data Loss Prevention",
            "B": "eDiscovery",
            "C": "Insider Risk Management",
            "D": "Communication Compliance",
        },
        "explanation": "Insider Risk Management correlates user activity and other risk indicators to identify and investigate potentially risky behavior, including unusual exfiltration by departing users. Data Loss Prevention focuses on sensitive-content policy detection and enforcement, such as restricting or blocking transfers. Because the stem asks for risk correlation and investigation rather than preventive content enforcement, Insider Risk Management is the intended answer.",
    },
    "sc900_mlc_q219": {
        "prompt": "An organization's existing hybrid identity deployment uses Microsoft's earlier on-premises synchronization application to synchronize on-premises Active Directory users and groups with Microsoft Entra ID. Which tool is it using?",
        "choices": {
            "A": "Microsoft Entra Cloud Sync",
            "B": "Pass-through authentication",
            "C": "Active Directory Federation Services (AD FS)",
            "D": "Microsoft Entra Connect Sync",
        },
        "explanation": "Hybrid identity uses provisioning and synchronization to connect on-premises identity with Microsoft Entra ID. Microsoft currently recommends Cloud Sync for new deployments and describes Microsoft Entra Connect Sync as the earlier on-premises synchronization tool that Cloud Sync is replacing. Pass-through authentication and AD FS are authentication or federation approaches, not the earlier synchronization application described in the question.",
    },
    "sc900_mlc_q226": {
        "prompt": "A cloud operator needs to start and stop virtual machines in a subscription but should not manage users in Microsoft Entra ID. Which access model fits?",
        "choices": {
            "A": "Global Administrator, because Azure VM power-state is a directory setting",
            "B": "Microsoft Entra RBAC for directory resources such as users and groups",
            "C": "Privileged Identity Management",
            "D": "Azure RBAC at the subscription or resource-group scope, not a Microsoft Entra directory role",
        },
        "explanation": "Azure RBAC authorizes actions on Azure resources and can be scoped to a subscription, resource group, or individual resource. Microsoft Entra roles authorize administration of Microsoft Entra resources such as users, groups, and applications. Privileged Identity Management can govern activation of eligible roles, but it does not replace the underlying Azure RBAC permission.",
    },
    "sc900_mlc_q242": {
        "prompt": "An administrator wants to scope a Conditional Access policy by operating-system platform, such as including Android and iOS but excluding Windows, without making any claim about device management or compliance. Which condition is designed for that purpose?",
        "choices": {
            "A": "Sign-in risk",
            "B": "Named locations",
            "C": "Device platforms",
            "D": "Require device to be marked as compliant",
        },
        "explanation": "The Device platforms condition scopes a Conditional Access policy by operating-system platform. It does not prove that a device is managed or compliant. Compliance is a separate device state enforced with the Require device to be marked as compliant grant control. Device management or enrollment state is also separate; filter for devices can target registered-device attributes, including compliance and MDM-related properties, when finer device targeting is needed.",
    },
    "sc900_mlc_q249": {
        "prompt": "A payment workload must not share the same private address space as a general development environment. Which Azure construct provides that isolation?",
        "choices": {
            "A": "Separate subnets within the same virtual network",
            "B": "Network security groups applied to the subnets",
            "C": "Azure Firewall filtering traffic between the environments",
            "D": "Separate virtual networks with non-overlapping private address spaces",
        },
        "explanation": "A subnet uses an address range from its virtual network's address space. Separate subnets can segment traffic, but they do not create separate VNet address spaces. If the workloads must not share the same private address space, use separate virtual networks with non-overlapping address spaces.",
    },
    "sc900_mlc_q269": {
        "prompt": "Microsoft Defender XDR can use automatic attack disruption to contain an in-progress attack. How does this differ from Microsoft Sentinel SOAR automation?",
        "choices": {
            "A": "Defender XDR has built-in automatic attack disruption; Sentinel can automatically run administrator-configured playbooks through automation rules",
            "B": "Sentinel playbooks can run only when an analyst starts them manually",
            "C": "Defender XDR attack disruption requires a Sentinel playbook before it can contain assets",
            "D": "Sentinel automation rules provide the same built-in attack-disruption logic as Defender XDR without configured actions",
        },
        "explanation": "Automatic attack disruption in Defender XDR is built in and uses high-confidence cross-workload incident signals to automatically contain compromised assets during an attack. Microsoft Sentinel automation rules can also run configured playbooks automatically. Playbooks may also be run manually, so manual execution is not the distinguishing feature.",
    },
}


class ContentCorrectionBuildError(ValueError):
    def __init__(self, reason: CorrectionFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason.value if not detail else f"{reason.value}: {detail}"
        super().__init__(message)


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SCHEMA_UNSUPPORTED, f"{label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContentCorrectionBuildError(CorrectionFailureReason.SCHEMA_UNSUPPORTED, f"{label} must be an object")
    return payload


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def _index_questions(questions: list[Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for question in questions:
        if not isinstance(question, dict):
            raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID)
        question_id = canonical_question_id(question)
        if not question_id:
            raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID)
        if question_id in indexed:
            raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID, question_id)
        indexed[question_id] = question
    return indexed


def build_currentness_record() -> dict[str, Any]:
    record = {
        "checked_at": CURRENTNESS_CHECKED_AT,
        "overall_status": "PASS",
        "payload_sha256": "",
        "q219_prior_device_sync_failure_provenance": True,
        "q219_prior_failure_work_id": Q219_PRIOR_CURRENTNESS_WORK_ID,
        "q219_replacement_pass_provenance": True,
        "q219_replacement_work_id": Q219_REPLACEMENT_WORK_ID,
        "schema_version": 1,
        "source_bank": SOURCE_BANK_FILENAME,
        "source_bank_content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
        "source_bank_raw_sha256": EXPECTED_SOURCE_BANK_SHA256,
        "targets": [
            {
                "authority_refs": list(CURRENTNESS_AUTHORITY["sc900_mlc_q118"]),
                "checked_at": Q118_Q269_CHECKED_AT,
                "material_change_detected": False,
                "notes": "Currentness PASS is reused from SC900-SEPARATE-CONTENT-CORRECTION-001-Q219-PRE-IMPLEMENTATION-CURRENTNESS-REVALIDATION-001. No dedicated historical q118 currentness work ID exists.",
                "prior_currentness_work_id": Q219_PRIOR_CURRENTNESS_WORK_ID,
                "question_id": "sc900_mlc_q118",
                "status": "PASS",
                "superseding_work_id_if_any": "",
            },
            {
                "authority_refs": list(CURRENTNESS_AUTHORITY["sc900_mlc_q219"]),
                "checked_at": CURRENTNESS_CHECKED_AT,
                "material_change_detected": False,
                "notes": "Prior device-sync/hybrid-join currentness FAIL is preserved from SC900-SEPARATE-CONTENT-CORRECTION-001-Q219-PRE-IMPLEMENTATION-CURRENTNESS-REVALIDATION-001. Replacement packet PASS is preserved from SC900-SEPARATE-CONTENT-CORRECTION-001-Q219-BOUNDED-REPLACEMENT-FREEZE-001. The superseded device-sync target is not implemented.",
                "prior_currentness_work_id": Q219_PRIOR_CURRENTNESS_WORK_ID,
                "question_id": "sc900_mlc_q219",
                "status": "PASS",
                "superseding_work_id_if_any": Q219_REPLACEMENT_WORK_ID,
            },
            {
                "authority_refs": list(CURRENTNESS_AUTHORITY["sc900_mlc_q269"]),
                "checked_at": Q118_Q269_CHECKED_AT,
                "material_change_detected": False,
                "notes": "Currentness PASS is reused from SC900-SEPARATE-CONTENT-CORRECTION-001-Q219-PRE-IMPLEMENTATION-CURRENTNESS-REVALIDATION-001. No dedicated historical q269 currentness work ID exists.",
                "prior_currentness_work_id": Q219_PRIOR_CURRENTNESS_WORK_ID,
                "question_id": "sc900_mlc_q269",
                "status": "PASS",
                "superseding_work_id_if_any": "",
            },
        ],
        "work_id": WORK_ID,
    }
    record["payload_sha256"] = canonical_manifest_sha256(record)
    if record["payload_sha256"] != EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256:
        raise ContentCorrectionBuildError(
            CorrectionFailureReason.CURRENTNESS_GATE_FAILED, str(record["payload_sha256"])
        )
    return record


def build_correction_spec(source_index: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    corrections: list[dict[str, Any]] = []
    for question_id in TARGET_IDS:
        source = source_index[question_id]
        target = SEMANTIC_TARGETS[question_id]
        if list(source.get("correct") or []) != list(
            {
                "sc900_mlc_q064": ["A"],
                "sc900_mlc_q118": ["D"],
                "sc900_mlc_q150": ["B"],
                "sc900_mlc_q198": ["C"],
                "sc900_mlc_q219": ["D"],
                "sc900_mlc_q226": ["D"],
                "sc900_mlc_q242": ["C"],
                "sc900_mlc_q249": ["D"],
                "sc900_mlc_q269": ["A"],
            }[question_id]
        ):
            raise ContentCorrectionBuildError(CorrectionFailureReason.CORRECT_KEY_CHANGED, question_id)
        if question_id == "sc900_mlc_q219" and source.get("tested_decision") != Q219_TESTED_DECISION:
            raise ContentCorrectionBuildError(CorrectionFailureReason.TESTED_DECISION_CHANGED, question_id)
        prompt_changed = source["prompt"] != target["prompt"]
        if prompt_changed != (question_id in PROMPT_CHANGED_IDS):
            raise ContentCorrectionBuildError(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE, question_id)
        target_choice_explanations = {letter: target["explanation"] for letter in CHOICE_LABELS}
        authorized = ["choice_explanations", "choices", "general_explanation"]
        if prompt_changed:
            authorized.append("prompt")
        authorized = sorted(authorized)
        source_values = {
            "choice_explanations": copy.deepcopy(source["choice_explanations"]),
            "choices": copy.deepcopy(source["choices"]),
            "general_explanation": source["general_explanation"],
        }
        target_values = {
            "choice_explanations": target_choice_explanations,
            "choices": copy.deepcopy(target["choices"]),
            "general_explanation": target["explanation"],
        }
        if prompt_changed:
            source_values["prompt"] = source["prompt"]
            target_values["prompt"] = target["prompt"]
        source_refs = [
            ref for ref in source.get("references") or [] if str(ref).startswith("https://learn.microsoft.com/")
        ]
        if not source_refs:
            raise ContentCorrectionBuildError(CorrectionFailureReason.AUTHORITY_EVIDENCE_MISSING, question_id)
        authority_refs = sorted(set(source_refs) | set(CURRENTNESS_AUTHORITY.get(question_id, [])))
        semantic_work = Q219_REPLACEMENT_WORK_ID if question_id == "sc900_mlc_q219" else SOURCE_VALIDATION_WORK_ID
        corrections.append(
            {
                "authority_refs": authority_refs,
                "authorized_changed_fields": authorized,
                "correct_key": list(source["correct"]),
                "currentness_class": CURRENTNESS_CLASS[question_id],
                "final_validation_status": FINAL_STATUSES[question_id],
                "objective_code": source["objective_code"],
                "question_id": question_id,
                "semantic_validation_work_id": semantic_work,
                "source_values": source_values,
                "target_values": target_values,
            }
        )
    spec = {
        "corrections": corrections,
        "currentness_requirements": copy.deepcopy(CURRENTNESS_REQUIREMENTS),
        "payload_sha256": "",
        "question_count": REQUIRED_QUESTION_COUNT,
        "schema_version": SCHEMA_VERSION,
        "source_bank": SOURCE_BANK_FILENAME,
        "source_bank_content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
        "source_bank_raw_sha256": EXPECTED_SOURCE_BANK_SHA256,
        "source_manifest_payload_sha256": EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256,
        "source_validation_work_id": SOURCE_VALIDATION_WORK_ID,
        "superseding_validation_work_ids": [Q219_REPLACEMENT_WORK_ID],
        "target_ids": list(TARGET_IDS),
        "work_id": WORK_ID,
    }
    spec["payload_sha256"] = canonical_manifest_sha256(spec)
    if spec["payload_sha256"] != EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256:
        raise ContentCorrectionBuildError(
            CorrectionFailureReason.CORRECTION_SPEC_HASH_MISMATCH, str(spec["payload_sha256"])
        )
    return spec


def apply_corrections(source_payload: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    candidate = copy.deepcopy(dict(source_payload))
    questions = candidate["questions"]
    index = _index_questions(questions)
    by_id = {str(entry["question_id"]): entry for entry in spec["corrections"]}
    for question_id, entry in by_id.items():
        question = index[question_id]
        target_values = entry["target_values"]
        for field in entry["authorized_changed_fields"]:
            question[field] = copy.deepcopy(target_values[field])
    return candidate


def build_sc900_content_correction_001(
    source_bank_path: Path,
    candidate_bank_path: Path,
    spec_path: Path,
    currentness_path: Path,
    review_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    source_bank_path = Path(source_bank_path)
    candidate_bank_path = Path(candidate_bank_path)
    spec_path = Path(spec_path)
    currentness_path = Path(currentness_path)
    review_root = Path(review_root)
    manifest_path = Path(manifest_path)
    if source_bank_path.name != SOURCE_BANK_FILENAME:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID, source_bank_path.name)
    if candidate_bank_path.name != TARGET_BANK_FILENAME:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SCHEMA_UNSUPPORTED, candidate_bank_path.name)
    if candidate_bank_path.name == PRODUCTION_BANK_FILENAME or source_bank_path.name == candidate_bank_path.name:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SCHEMA_UNSUPPORTED, "production bank collision")
    if any(
        _same_path(source_bank_path, path) for path in (candidate_bank_path, spec_path, currentness_path, manifest_path)
    ):
        raise ContentCorrectionBuildError(CorrectionFailureReason.SCHEMA_UNSUPPORTED, "source overwrite")
    source_bytes_before = source_bank_path.read_bytes()
    source_hash = sha256_file(source_bank_path)
    if source_hash != EXPECTED_SOURCE_BANK_SHA256:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH, source_hash)
    source_payload = _load_json_object(source_bank_path, "source bank")
    source_questions = source_payload.get("questions")
    if not isinstance(source_questions, list) or len(source_questions) != REQUIRED_QUESTION_COUNT:
        raise ContentCorrectionBuildError(CorrectionFailureReason.QUESTION_COUNT_MISMATCH)
    source_ids = [canonical_question_id(question) for question in source_questions]
    if len(set(source_ids)) != REQUIRED_QUESTION_COUNT:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID)
    source_fp = bank_content_fingerprint(source_questions)
    if source_fp != EXPECTED_SOURCE_CONTENT_FINGERPRINT:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_CONTENT_FINGERPRINT_MISMATCH, source_fp)
    source_index = _index_questions(source_questions)
    for question_id in TARGET_IDS:
        if question_id not in source_index:
            raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID, question_id)
    t5_manifest_path = source_bank_path.parent / T5_MANIFEST_RELATIVE_PATH
    if t5_manifest_path.is_file():
        t5_manifest = _load_json_object(t5_manifest_path, "t5 manifest")
        if canonical_manifest_sha256(t5_manifest) != EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256:
            raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_IDENTITY_INVALID, "t5 manifest")
    currentness = build_currentness_record()
    spec = build_correction_spec(source_index)
    candidate_payload = apply_corrections(source_payload, spec)
    target_questions = candidate_payload["questions"]
    target_ids = [canonical_question_id(question) for question in target_questions]
    if target_ids != source_ids:
        raise ContentCorrectionBuildError(CorrectionFailureReason.QUESTION_ORDER_MISMATCH)
    target_index = _index_questions(target_questions)
    changed = [
        question_id
        for question_id in source_ids
        if question_content_fingerprint(source_index[question_id])
        != question_content_fingerprint(target_index[question_id])
    ]
    if set(changed) != set(TARGET_IDS):
        raise ContentCorrectionBuildError(CorrectionFailureReason.UNDECLARED_CONTENT_CHANGE, ",".join(changed))
    if source_bank_path.read_bytes() != source_bytes_before:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH, "mutated source")
    write_canonical_package_b_json(spec_path, spec)
    write_canonical_package_b_json(currentness_path, currentness)
    write_canonical_package_b_json(candidate_bank_path, candidate_payload)
    receipt_hashes: dict[str, str] = {}
    edges: list[dict[str, Any]] = []
    spec_by_id = {str(entry["question_id"]): entry for entry in spec["corrections"]}
    for question_id in TARGET_IDS:
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        entry = spec_by_id[question_id]
        receipt = {
            "after": copy.deepcopy(entry["target_values"]),
            "authorized_changed_fields": list(entry["authorized_changed_fields"]),
            "authority_refs": list(entry["authority_refs"]),
            "before": copy.deepcopy(entry["source_values"]),
            "correction_spec_payload_sha256": spec["payload_sha256"],
            "correct_key_after": list(target_question["correct"]),
            "correct_key_before": list(source_question["correct"]),
            "disposition": REVIEW_DISPOSITION_APPROVED,
            "from_content_fingerprint": question_content_fingerprint(source_question),
            "objective_after": target_question["objective_code"],
            "objective_before": source_question["objective_code"],
            "question_id": question_id,
            "to_content_fingerprint": question_content_fingerprint(target_question),
        }
        relative_path = Path(REVIEW_DIRECTORY) / f"{question_id}.json"
        receipt_path = review_root / relative_path
        write_canonical_package_b_json(receipt_path, receipt)
        receipt_hashes[question_id] = sha256_file(receipt_path)
        edges.append(
            {
                "authority_refs": list(entry["authority_refs"]),
                "changed_fields": list(entry["authorized_changed_fields"]),
                "correct_key_unchanged": True,
                "domain_unchanged": True,
                "exam_eligibility_unchanged": True,
                "from_content_fingerprint": receipt["from_content_fingerprint"],
                "objective_unchanged": True,
                "question_id": question_id,
                "question_type_unchanged": True,
                "review_artifact": relative_path.as_posix(),
                "review_artifact_sha256": receipt_hashes[question_id],
                "review_status": REVIEW_STATUS_APPROVED,
                "tier_unchanged": True,
                "to_content_fingerprint": receipt["to_content_fingerprint"],
            }
        )
    manifest = {
        "continuity_policy": CONTINUITY_POLICY,
        "correction_spec": {
            "file_sha256": sha256_file(spec_path),
            "filename": spec_path.name,
            "payload_sha256": spec["payload_sha256"],
        },
        "currentness_record": {
            "file_sha256": sha256_file(currentness_path),
            "filename": currentness_path.name,
            "payload_sha256": currentness["payload_sha256"],
        },
        "edges": edges,
        "manifest_kind": MANIFEST_KIND,
        "payload_sha256": "",
        "permitted_change_class": PERMITTED_CHANGE_CLASS,
        "schema_version": SCHEMA_VERSION,
        "source_bank": {
            "content_fingerprint": source_fp,
            "file_sha256": source_hash,
            "filename": source_bank_path.name,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "target_bank": {
            "content_fingerprint": bank_content_fingerprint(target_questions),
            "file_sha256": sha256_file(candidate_bank_path),
            "filename": candidate_bank_path.name,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "work_id": WORK_ID,
    }
    manifest["payload_sha256"] = canonical_manifest_sha256(manifest)
    write_canonical_package_b_json(manifest_path, manifest)
    admission = admit_content_correction(
        manifest,
        spec=spec,
        currentness_record=currentness,
        source_bank_path=source_bank_path,
        target_bank_path=candidate_bank_path,
        spec_path=spec_path,
        currentness_path=currentness_path,
        review_root=review_root,
    )
    if admission.status != AdmissionStatus.PASS or admission.admitted is None:
        reasons = ", ".join(reason.value for reason in admission.reasons) or "unknown rejection"
        raise ContentCorrectionBuildError(CorrectionFailureReason.SCHEMA_UNSUPPORTED, reasons)
    if source_bank_path.read_bytes() != source_bytes_before:
        raise ContentCorrectionBuildError(CorrectionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH, "source mutated")
    return {
        "admission_status": admission.status.value,
        "changed_question_ids": list(TARGET_IDS),
        "currentness_payload_sha256": currentness["payload_sha256"],
        "manifest_sha256": manifest["payload_sha256"],
        "receipt_count": len(receipt_hashes),
        "source_bank_content_fingerprint": source_fp,
        "source_file_sha256": source_hash,
        "spec_payload_sha256": spec["payload_sha256"],
        "target_bank_content_fingerprint": admission.admitted.target_bank_content_fingerprint,
        "target_file_sha256": admission.admitted.target_bank_file_sha256,
    }


def default_repository_paths(root: Path) -> dict[str, Path]:
    root = Path(root)
    return {
        "source_bank": root / SOURCE_BANK_FILENAME,
        "candidate_bank": root / TARGET_BANK_FILENAME,
        "spec": root / CORRECTION_SPEC_RELATIVE_PATH,
        "currentness": root / CURRENTNESS_RECORD_RELATIVE_PATH,
        "review_root": root / "content_revision_evidence" / "reviews",
        "manifest": root / MANIFEST_RELATIVE_PATH,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the governed nine-question content-correction candidate.")
    parser.add_argument("--source-bank", type=Path)
    parser.add_argument("--candidate-bank", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--currentness", type=Path)
    parser.add_argument("--review-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    defaults = default_repository_paths(root)
    try:
        result = build_sc900_content_correction_001(
            args.source_bank or defaults["source_bank"],
            args.candidate_bank or defaults["candidate_bank"],
            args.spec or defaults["spec"],
            args.currentness or defaults["currentness"],
            args.review_root or defaults["review_root"],
            args.manifest or defaults["manifest"],
        )
    except ContentCorrectionBuildError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
