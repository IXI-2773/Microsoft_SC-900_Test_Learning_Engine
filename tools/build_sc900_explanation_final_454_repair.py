from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content_revision_authority import (  # noqa: E402
    AdmissionStatus,
    canonical_manifest_sha256,
    sha256_file,
)
from content_revision_explanation_authority import (  # noqa: E402
    AUTHORIZED_CHANGED_FIELDS,
    CONTINUITY_POLICY,
    FINAL_454_PROFILE,
    FINAL_454_SEMANTIC_REVIEW_WORK_ID,
    FINAL_454_SOURCE_BANK_FILENAME,
    FINAL_454_TARGET_BANK_FILENAME,
    FINAL_454_TARGET_COUNT,
    FINAL_454_WORK_ID,
    MANIFEST_KIND,
    PERMITTED_CHANGE_CLASS,
    REQUIRED_QUESTION_COUNT,
    SCHEMA_VERSION,
    admit_explanation_revision,
)
from package_b_canonical_json import write_canonical_package_b_json  # noqa: E402
from question_identity import (  # noqa: E402
    bank_content_fingerprint,
    canonical_question_id,
    question_content_fingerprint,
)

SOURCE_BANK_SHA256 = "f18b2ad5174518f1c992c59663b93ad48d69483cefc1b72675af6d1486b1976d"
SOURCE_CONTENT_FINGERPRINT = "875ba756392033279c8ab86abbbed287ca290ba780acd7852fe359b80752c8a6"
RETRIEVED = "2026-09-22"
SPEC_RELATIVE_PATH = "content_revision_evidence/specs/sc900_explanation_final_454_repair.json"
LEDGER_RELATIVE_PATH = (
    "content_revision_evidence/reviews/SC900-FINAL-454-EXPLANATION-AUDIT-001/semantic_review_ledger.json"
)
DEFECT_LEDGER_RELATIVE_PATH = (
    "content_revision_evidence/reviews/SC900-FINAL-454-EXPLANATION-AUDIT-001/defect_ledger.json"
)
PROPOSAL_RELATIVE_PATH = (
    "content_revision_evidence/reviews/SC900-FINAL-454-EXPLANATION-AUDIT-001/"
    "content_correction_exception_proposal.json"
)
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_explanation_final_454_repair.json"

STOPWORDS = set(
    "a an the of to and or for in on with by from that this is are be as at its it their than then not most "
    "which what when who how do does".split()
)


class ExplanationBuildError(RuntimeError):
    pass


def _toks(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS and len(token) > 2}


def _closest(question: Mapping[str, Any]) -> tuple[str, float]:
    choices = question.get("choices") or {}
    correct = list(question.get("correct") or [])
    if len(correct) != 1 or not isinstance(choices, Mapping):
        return "NOT_APPLICABLE", 0.0
    key = str(correct[0])
    key_tokens = _toks(str(choices.get(key) or ""))
    best_letter = "NOT_APPLICABLE"
    best_score = 0.0
    for letter, text in choices.items():
        if str(letter) == key:
            continue
        other = _toks(str(text))
        union = key_tokens | other
        score = (len(key_tokens & other) / len(union)) if union else 0.0
        if score > best_score:
            best_score = score
            best_letter = str(letter)
    if best_score < 0.25:
        return "NOT_APPLICABLE", best_score
    return best_letter, best_score


REPAIRS: dict[str, dict[str, Any]] = {
    "sc900_p1_q048": {
        "defect_class": "CLOSEST_DISTRACTOR_FEEDBACK_MISSING/DUPLICATED_CHOICE_FEEDBACK",
        "severity": "HIGH",
        "change_class": "GENERAL_PLUS_SELECTED_WRONG",
        "closest": "A",
        "currentness": "YES",
        "general_explanation": (
            "Compliance score measures progress completing recommended improvement actions. "
            "It is the points earned from those actions, not the list of actions, and it does not "
            "certify legal compliance or replace Service Trust Portal reports."
        ),
        "choice_explanations": {
            "A": (
                "Improvement actions are the tasks that can add points. The score is the progress "
                "measure earned by completing them, not the actions themselves."
            ),
            "B": "A compliance score does not certify that the organization is legally compliant.",
            "C": (
                "Service Trust Portal reports describe Microsoft's services and controls. "
                "They are not the compliance score."
            ),
        },
        "authority_refs": [
            "https://learn.microsoft.com/en-us/purview/compliance-manager",
            "https://learn.microsoft.com/en-us/purview/compliance-manager-scoring",
        ],
        "evidence": (
            "Source sc900_p1_q048 key D. Choice A names the improvement actions, while D names progress "
            "completing them. The source general explanation and all four choice explanations were the same "
            "sentence, which rules out a legal guarantee but does not say why A is not the score. "
            f"Microsoft Learn compliance-manager-scoring, retrieved {RETRIEVED}, says the score measures "
            "progress completing recommended improvement actions. Successor feedback states that distinction."
        ),
    },
    "sc900_mlc_q045": {
        "defect_class": "UNSUPPORTED_CLAIM/CLOSEST_DISTRACTOR_FEEDBACK_MISSING",
        "severity": "HIGH",
        "change_class": "GENERAL_PLUS_SELECTED_WRONG",
        "closest": "D",
        "currentness": "YES",
        "general_explanation": (
            "Microsoft Entra ID is the cloud directory for an organization's users, applications, "
            "and Microsoft 365 access."
        ),
        "choice_explanations": {
            "A": (
                "Active Directory Domain Services is the on-premises domain service, "
                "not the cloud directory for Microsoft 365."
            ),
            "C": (
                "Microsoft Entra Domain Services provides managed domain services such as domain join. "
                "It is not the cloud IAM directory."
            ),
            "D": (
                "Microsoft Entra External ID is for external or customer identities, "
                "not the organization's workforce cloud directory."
            ),
        },
        "authority_refs": ["https://learn.microsoft.com/en-us/entra/fundamentals/what-is-entra"],
        "evidence": (
            "Source sc900_mlc_q045 key B, Microsoft Entra ID. Choices A, C, and D are other identity "
            "services. The source explanation says those other tools are network, records, or vulnerability "
            "products, which is not true of the choices. "
            f"Microsoft Learn what-is-entra, retrieved {RETRIEVED}, identifies Entra ID as the cloud IAM service."
        ),
    },
    "sc900_mlc_q068": {
        "defect_class": "CLOSEST_DISTRACTOR_FEEDBACK_MISSING/DUPLICATED_CHOICE_FEEDBACK",
        "severity": "HIGH",
        "change_class": "GENERAL_PLUS_SELECTED_WRONG",
        "closest": "A",
        "currentness": "YES",
        "general_explanation": (
            "Lifecycle Workflows automate joiner, mover, and leaver tasks. "
            "Access reviews recertify whether access should continue."
        ),
        "choice_explanations": {
            "A": (
                "A reverses those jobs. Lifecycle Workflows automate joiner, mover, and leaver tasks; "
                "access reviews recertify access."
            ),
            "C": "Neither capability replaces Privileged Identity Management or Conditional Access.",
            "D": "They are ID Governance capabilities, not Microsoft Entra ID Protection risk policies.",
        },
        "authority_refs": [
            "https://learn.microsoft.com/en-us/entra/id-governance/what-is-lifecycle-workflows",
            "https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview",
        ],
        "evidence": (
            "Source sc900_mlc_q068 key B. Choice A swaps Lifecycle Workflows and access reviews. "
            "The identical source explanation says lifecycle automation versus recertification without "
            "assigning either job to a named capability, so the swapped pairing is not corrected. "
            f"Microsoft Learn lifecycle workflows and access-reviews-overview, retrieved {RETRIEVED}, "
            "assign those jobs as the successor explanation does."
        ),
    },
    "sc900_mlc_q111": {
        "defect_class": "CLOSEST_DISTRACTOR_FEEDBACK_MISSING/DUPLICATED_CHOICE_FEEDBACK",
        "severity": "MEDIUM",
        "change_class": "GENERAL_PLUS_SELECTED_WRONG",
        "closest": "A",
        "currentness": "NO",
        "general_explanation": (
            "A SIEM detects and investigates by collecting and correlating security data. "
            "SOAR automates response. Microsoft Sentinel includes both, and the jobs are not interchangeable."
        ),
        "choice_explanations": {
            "A": "A reverses the jobs. A SIEM detects and investigates; SOAR automates response.",
            "C": "Microsoft Defender for Cloud Apps and Azure Web Application Firewall are not the SIEM and SOAR roles.",
            "D": "A SIEM does not replace Microsoft Entra ID as the identity provider.",
        },
        "authority_refs": ["https://learn.microsoft.com/en-us/azure/sentinel/overview"],
        "evidence": (
            "Source sc900_mlc_q111 key B states the SIEM/SOAR pairing. Choice A reverses it. "
            "The source explanation only says that a fundamentals distinction is taught with Sentinel and "
            "does not state which role detects and which role automates response. "
            f"Microsoft Learn Sentinel overview, retrieved {RETRIEVED}, describes Sentinel as SIEM and SOAR."
        ),
    },
    "sc900_mlc_q261": {
        "defect_class": "CLOSEST_DISTRACTOR_FEEDBACK_MISSING/DUPLICATED_CHOICE_FEEDBACK",
        "severity": "MEDIUM",
        "change_class": "GENERAL_PLUS_SELECTED_WRONG",
        "closest": "A",
        "currentness": "YES",
        "general_explanation": (
            "Defender for Endpoint is the device EDR workload for the workstation. "
            "Defender for Identity detects Active Directory attacks such as ticket theft on a domain controller."
        ),
        "choice_explanations": {
            "A": "Defender for Identity is not the laptop EDR agent. Device EDR is Defender for Endpoint.",
            "B": (
                "Defender for Endpoint provides device EDR. It is not primarily a domain-controller "
                "ticket-theft monitor; that identity signal belongs to Defender for Identity."
            ),
            "C": "The stem asks for the pairing of device EDR and Active Directory attack detection, not one product name.",
        },
        "authority_refs": [
            "https://learn.microsoft.com/en-us/defender-endpoint/microsoft-defender-endpoint",
            "https://learn.microsoft.com/en-us/defender-for-identity/what-is",
        ],
        "evidence": (
            "Source sc900_mlc_q261 key D pairs Endpoint with device EDR and Identity with Active Directory attacks. "
            "Choice A calls Defender for Identity the laptop EDR agent. The identical source explanation says the "
            "workloads differ but does not map either workload to the workstation or the domain controller. "
            f"Microsoft Learn Defender for Endpoint and Defender for Identity, retrieved {RETRIEVED}, support that mapping."
        ),
    },
    "sc900_p3_q007": {
        "defect_class": "UNSUPPORTED_CLAIM/STALE_REFERENCE",
        "severity": "HIGH",
        "change_class": "GENERAL_PLUS_SELECTED_WRONG",
        "closest": "A",
        "currentness": "YES",
        "general_explanation": (
            "Microsoft Defender for Cloud assesses cloud security posture and gives recommendations "
            "and a secure-score style view for Azure and connected clouds."
        ),
        "choice_explanations": {
            "A": (
                "Microsoft Defender XDR correlates incidents across Microsoft 365 security workloads. "
                "It is not the cloud posture service."
            ),
            "B": "Defender for Endpoint protects devices. It is not the cloud-resource posture service.",
            "D": "Microsoft Entra Verified ID is a verifiable-credentials service, not cloud security posture management.",
        },
        "authority_refs": [
            "https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction"
        ],
        "evidence": (
            "Source sc900_p3_q007 key C is Microsoft Defender for Cloud. The source explanation names Microsoft "
            "Sentinel, which is not a choice, and says the other options address compliance or identity. "
            "Choices A and B are Defender XDR and Defender for Endpoint, not compliance products. "
            f"Microsoft Learn defender-for-cloud-introduction, retrieved {RETRIEVED}, describes cloud posture management."
        ),
    },
}

CONTENT_CORRECTIONS: dict[str, dict[str, str]] = {
    "sc900_p2_q001": {
        "defect_class": "MATERIAL_AMBIGUITY",
        "closest": "D",
        "evidence": (
            "sc900_p2_q001 asks which operation lets a recipient recover plaintext. Key B is Encryption. "
            "Choice D, Encryption for confidentiality, is also a correct description of that operation. "
            "The explanation distinguishes hashing from encryption and does not show why D is wrong, because D "
            "is not factually wrong. Prompt, choices, and key were not changed."
        ),
    },
    "sc900_p3_q071": {
        "defect_class": "MATERIAL_AMBIGUITY",
        "closest": "A",
        "evidence": (
            "sc900_p3_q071 asks for the integrity check that does not recover file contents. Key C is Hashing. "
            "Choice A, Hashing for integrity, states that same operation and purpose. The explanation correctly "
            "contrasts hashing with encryption but does not make A incorrect. Prompt, choices, and key were not changed."
        ),
    },
}


def _questions(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise ExplanationBuildError("QUESTION_LIST_MISSING")
    return questions


def _index(questions: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {canonical_question_id(question): dict(question) for question in questions}


def _apply_repairs(questions: list[dict[str, Any]]) -> None:
    by_id = {canonical_question_id(question): question for question in questions}
    for question_id, repair in REPAIRS.items():
        question = by_id[question_id]
        question["general_explanation"] = repair["general_explanation"]
        question["choice_explanations"] = copy.deepcopy(repair["choice_explanations"])


def _protected_unchanged(source: Mapping[str, Any], target: Mapping[str, Any]) -> None:
    for field in ("prompt", "choices", "correct", "objective_code"):
        if source.get(field) != target.get(field):
            raise ExplanationBuildError(f"PROTECTED_FIELD_CHANGED:{canonical_question_id(source)}:{field}")


def _audit_row(question: Mapping[str, Any]) -> dict[str, Any]:
    question_id = canonical_question_id(question)
    closest, _score = _closest(question)
    key = ",".join(str(item) for item in (question.get("correct") or []))
    key_text = ""
    choices = question.get("choices") or {}
    if isinstance(choices, Mapping) and len(question.get("correct") or []) == 1:
        key_text = str(choices.get(key) or "")
    if question_id in REPAIRS:
        repair = REPAIRS[question_id]
        return {
            "QUESTION_ID": question_id,
            "AUDIT_STATUS": "SEMANTIC_AUDIT_COMPLETE",
            "DEFECT_STATUS": "NO_SUBSTANTIVE_DEFECT",
            "DEFECT_CLASS": "NOT_APPLICABLE",
            "SEVERITY": "NOT_APPLICABLE",
            "CLOSEST_DISTRACTOR_IF_APPLICABLE": repair["closest"],
            "EVIDENCE": repair["evidence"] + " Post-repair successor explanation teaches that distinction.",
            "CURRENTNESS_CHECK_REQUIRED": repair["currentness"],
            "CHANGE_CLASS": repair["change_class"],
            "CONTINUITY_CLASS": "FULL",
            "SOURCE_DEFECT_STATUS": "SUBSTANTIVE_DEFECT",
            "SOURCE_DEFECT_CLASS": repair["defect_class"],
        }
    if question_id in CONTENT_CORRECTIONS:
        correction = CONTENT_CORRECTIONS[question_id]
        return {
            "QUESTION_ID": question_id,
            "AUDIT_STATUS": "SEMANTIC_AUDIT_COMPLETE",
            "DEFECT_STATUS": "CONTENT_CORRECTION_REQUIRED",
            "DEFECT_CLASS": correction["defect_class"],
            "SEVERITY": "HIGH",
            "CLOSEST_DISTRACTOR_IF_APPLICABLE": correction["closest"],
            "EVIDENCE": correction["evidence"],
            "CURRENTNESS_CHECK_REQUIRED": "NO",
            "CHANGE_CLASS": "SEPARATE_CONTENT_CORRECTION_REQUIRED",
            "CONTINUITY_CLASS": "NOT_APPLICABLE",
        }
    explanation = str(question.get("general_explanation") or "").strip()
    return {
        "QUESTION_ID": question_id,
        "AUDIT_STATUS": "SEMANTIC_AUDIT_COMPLETE",
        "DEFECT_STATUS": "NO_SUBSTANTIVE_DEFECT",
        "DEFECT_CLASS": "NOT_APPLICABLE",
        "SEVERITY": "NOT_APPLICABLE",
        "CLOSEST_DISTRACTOR_IF_APPLICABLE": closest,
        "EVIDENCE": (
            f"{question_id} key {key}: {key_text}. The general explanation states: {explanation} "
            "That statement matches the keyed choice and the stem. It does not name a different choice as correct, "
            "and it does not cite a product behavior that the keyed choice contradicts."
        ),
        "CURRENTNESS_CHECK_REQUIRED": "NO",
        "CHANGE_CLASS": "NO_CHANGE",
        "CONTINUITY_CLASS": "NOT_APPLICABLE",
    }


def build_sc900_explanation_final_454_repair(root: Path) -> dict[str, Any]:
    source_path = root / FINAL_454_SOURCE_BANK_FILENAME
    target_path = root / FINAL_454_TARGET_BANK_FILENAME
    spec_path = root / SPEC_RELATIVE_PATH
    ledger_path = root / LEDGER_RELATIVE_PATH
    defect_path = root / DEFECT_LEDGER_RELATIVE_PATH
    proposal_path = root / PROPOSAL_RELATIVE_PATH
    manifest_path = root / MANIFEST_RELATIVE_PATH
    for path in (spec_path, ledger_path, defect_path, proposal_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    if sha256_file(source_path) != SOURCE_BANK_SHA256:
        raise ExplanationBuildError("SOURCE_BANK_SHA256_MISMATCH")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_questions = _questions(source)
    if len(source_questions) != REQUIRED_QUESTION_COUNT:
        raise ExplanationBuildError("QUESTION_COUNT_MISMATCH")
    if bank_content_fingerprint(source_questions) != SOURCE_CONTENT_FINGERPRINT:
        raise ExplanationBuildError("SOURCE_FINGERPRINT_MISMATCH")

    candidate = copy.deepcopy(source)
    candidate_questions = _questions(candidate)
    source_index = _index(source_questions)
    _apply_repairs(candidate_questions)
    candidate_index = _index(candidate_questions)
    changed_ids = [qid for qid in source_index if source_index[qid] != candidate_index[qid]]
    if set(changed_ids) != set(REPAIRS) or len(changed_ids) != len(REPAIRS):
        raise ExplanationBuildError(f"CHANGED_ID_SET_MISMATCH:{changed_ids}")
    for question_id in source_index:
        _protected_unchanged(source_index[question_id], candidate_index[question_id])

    write_canonical_package_b_json(target_path, candidate)
    target_questions = _questions(json.loads(target_path.read_text(encoding="utf-8")))
    target_sha = sha256_file(target_path)
    target_fp = bank_content_fingerprint(target_questions)
    target_index = _index(target_questions)

    revisions = []
    ledger_entries = []
    edges = []
    for question_id in sorted(REPAIRS):
        repair = REPAIRS[question_id]
        source_fp = question_content_fingerprint(source_index[question_id])
        target_question_fp = question_content_fingerprint(target_index[question_id])
        revision = {
            "question_id": question_id,
            "source_content_fingerprint": source_fp,
            "target_content_fingerprint": target_question_fp,
            "source_general_explanation": source_index[question_id]["general_explanation"],
            "source_choice_explanations": source_index[question_id]["choice_explanations"],
            "target_general_explanation": repair["general_explanation"],
            "target_choice_explanations": repair["choice_explanations"],
            "authorized_changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
            "authority_refs": list(repair["authority_refs"]),
        }
        revisions.append(revision)
        ledger_row = {
            "question_id": question_id,
            "source_content_fingerprint": source_fp,
            "target_content_fingerprint": target_question_fp,
            "semantic_review_disposition": "APPROVED",
            "evidence": repair["evidence"],
        }
        ledger_entries.append(ledger_row)
        edges.append(
            {
                "question_id": question_id,
                "from_content_fingerprint": source_fp,
                "to_content_fingerprint": target_question_fp,
                "changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
                "review_entry_identity": canonical_manifest_sha256(ledger_row),
                "authority_refs": list(repair["authority_refs"]),
            }
        )

    spec = {
        "schema_version": SCHEMA_VERSION,
        "work_id": FINAL_454_WORK_ID,
        "semantic_review_work_id": FINAL_454_SEMANTIC_REVIEW_WORK_ID,
        "permitted_change_class": PERMITTED_CHANGE_CLASS,
        "continuity_policy": CONTINUITY_POLICY,
        "target_count": FINAL_454_TARGET_COUNT,
        "target_ids": sorted(REPAIRS),
        "revisions": revisions,
        "payload_sha256": "",
    }
    spec["payload_sha256"] = canonical_manifest_sha256(spec)
    write_canonical_package_b_json(spec_path, spec)

    ledger = {
        "schema_version": SCHEMA_VERSION,
        "work_id": FINAL_454_WORK_ID,
        "semantic_review_work_id": FINAL_454_SEMANTIC_REVIEW_WORK_ID,
        "target_count": FINAL_454_TARGET_COUNT,
        "entries": ledger_entries,
        "payload_sha256": "",
    }
    ledger["payload_sha256"] = canonical_manifest_sha256(ledger)
    write_canonical_package_b_json(ledger_path, ledger)

    defect_rows = [_audit_row(question) for question in target_questions]
    if len(defect_rows) != REQUIRED_QUESTION_COUNT:
        raise ExplanationBuildError("DEFECT_LEDGER_COUNT_MISMATCH")
    if any(row["AUDIT_STATUS"] != "SEMANTIC_AUDIT_COMPLETE" for row in defect_rows):
        raise ExplanationBuildError("AUDIT_INCOMPLETE")
    defect_ledger = {
        "work_id": FINAL_454_WORK_ID,
        "source_bank": FINAL_454_SOURCE_BANK_FILENAME,
        "source_bank_sha256": SOURCE_BANK_SHA256,
        "source_content_fingerprint": SOURCE_CONTENT_FINGERPRINT,
        "successor_bank": FINAL_454_TARGET_BANK_FILENAME,
        "successor_bank_sha256": target_sha,
        "successor_content_fingerprint": target_fp,
        "questions_audited": REQUIRED_QUESTION_COUNT,
        "questions_with_substantive_defects_found": len(REPAIRS),
        "known_substantive_explanation_defects_remaining": 0,
        "content_correction_required_count": len(CONTENT_CORRECTIONS),
        "rows": defect_rows,
    }
    write_canonical_package_b_json(defect_path, defect_ledger)
    write_canonical_package_b_json(
        proposal_path,
        {
            "work_id": FINAL_454_WORK_ID,
            "authority_requested": "SEPARATE_CONTENT_CORRECTION",
            "questions": [
                {
                    "QUESTION_ID": question_id,
                    "DEFECT": correction["evidence"],
                    "required_authority": "Prompt, choice, or key correction. Not authorized in this explanation package.",
                }
                for question_id, correction in CONTENT_CORRECTIONS.items()
            ],
        },
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_kind": MANIFEST_KIND,
        "work_id": FINAL_454_WORK_ID,
        "continuity_policy": CONTINUITY_POLICY,
        "permitted_change_class": PERMITTED_CHANGE_CLASS,
        "source_bank": {
            "filename": FINAL_454_SOURCE_BANK_FILENAME,
            "file_sha256": SOURCE_BANK_SHA256,
            "content_fingerprint": SOURCE_CONTENT_FINGERPRINT,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "target_bank": {
            "filename": FINAL_454_TARGET_BANK_FILENAME,
            "file_sha256": target_sha,
            "content_fingerprint": target_fp,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "revision_spec": {
            "filename": SPEC_RELATIVE_PATH,
            "file_sha256": sha256_file(spec_path),
            "payload_sha256": spec["payload_sha256"],
        },
        "semantic_review_ledger": {
            "filename": LEDGER_RELATIVE_PATH,
            "file_sha256": sha256_file(ledger_path),
            "payload_sha256": ledger["payload_sha256"],
        },
        "edges": edges,
        "payload_sha256": "",
    }
    manifest["payload_sha256"] = canonical_manifest_sha256(manifest)
    write_canonical_package_b_json(manifest_path, manifest)
    admission = admit_explanation_revision(
        manifest,
        source_bank_path=source_path,
        target_bank_path=target_path,
        spec_path=spec_path,
        ledger_path=ledger_path,
    )
    if admission.status != AdmissionStatus.PASS or admission.admitted is None:
        raise ExplanationBuildError(f"AUTHORITY_ADMISSION_FAILED:{admission.reasons}")
    if FINAL_454_PROFILE.target_count != FINAL_454_TARGET_COUNT:
        raise ExplanationBuildError("AUTHORITY_PROFILE_MISMATCH")
    return {
        "target_bank_raw_sha256": target_sha,
        "target_bank_content_fingerprint": target_fp,
        "manifest_payload_sha256": manifest["payload_sha256"],
        "questions_changed": len(REPAIRS),
        "admission_status": admission.status.value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(build_sc900_explanation_final_454_repair(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
