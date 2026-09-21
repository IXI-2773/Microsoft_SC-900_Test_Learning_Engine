from __future__ import annotations

import argparse
import copy
import json
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
    MANIFEST_KIND,
    PERMITTED_CHANGE_CLASS,
    Q118_PROFILE,
    Q118_SEMANTIC_REVIEW_DISPOSITION,
    Q118_SEMANTIC_REVIEW_WORK_ID,
    Q118_SOURCE_BANK_FILENAME,
    Q118_TARGET_BANK_FILENAME,
    Q118_TARGET_COUNT,
    Q118_WORDING_AUTHORITY,
    Q118_WORK_ID,
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

QUESTION_ID = "sc900_mlc_q118"
SPEC_RELATIVE_PATH = "content_revision_evidence/specs/sc900_explanation_q118_repair_001.json"
LEDGER_RELATIVE_PATH = "content_revision_evidence/reviews/SC900-EXPLANATION-Q118-REPAIR-001/semantic_review_ledger.json"
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_explanation_q118_repair_001.json"
RECEIPT_RELATIVE_PATH = "content_revision_evidence/receipts/sc900_explanation_q118_repair_001.json"
VERIFICATION_RESULTS_RELATIVE_PATH = (
    "content_revision_evidence/verification/sc900_explanation_q118_repair_001_test_results.json"
)
TRANCHE_1_SPEC_RELATIVE_PATH = "content_revision_evidence/specs/sc900_explanation_tranche_1.json"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
EXPECTED_SOURCE_BANK_SHA256 = "b6006ddb62aaea9549778d91e12ae1df4e9db9001186abe565a4de0af5e672e5"
EXPECTED_SOURCE_CONTENT_FINGERPRINT = "f6e0040474383b32232f149d2ee2665e6af924806e8971dd96a8658d109150ff"
EXPECTED_SOURCE_Q118_FINGERPRINT = "abaddff647ab335935215f33e851c4ca90a619aae8973252335c1c7b114786b1"
EXPECTED_TARGET_BANK_SHA256 = "f18b2ad5174518f1c992c59663b93ad48d69483cefc1b72675af6d1486b1976d"
EXPECTED_TARGET_CONTENT_FINGERPRINT = "875ba756392033279c8ab86abbbed287ca290ba780acd7852fe359b80752c8a6"
EXPECTED_TARGET_Q118_FINGERPRINT = "73a81f5a7c49ce8843b165ab747bb604323fec780f6fa55d64d03ea65e87d3c8"
EXPECTED_PROMPT = (
    "Leadership wants a prioritized list of exposed software weaknesses on endpoints, "
    "not a SIEM correlation timeline. Which capability fits?"
)
EXPECTED_CHOICES = {
    "A": "Microsoft Sentinel hunting",
    "B": "Microsoft Defender for Identity",
    "C": "Microsoft Defender for Office 365",
    "D": "Microsoft Defender Vulnerability Management",
}
EXPECTED_CORRECT = ["D"]
EXPECTED_OBJECTIVE_CODE = "defender_xdr"
EXPECTED_TESTED_DECISION = "mdvm_not_siem_timeline"
EXPECTED_QUESTION_NUMBER = 272
TARGET_GENERAL_EXPLANATION = (
    "Microsoft Defender Vulnerability Management helps organizations discover, assess, prioritize, "
    "and remediate vulnerabilities and misconfigurations across endpoints. A request for a prioritized "
    "list of exposed software weaknesses therefore maps to Defender Vulnerability Management."
)
TARGET_CHOICE_EXPLANATIONS = {
    "A": (
        "Microsoft Sentinel hunting is used to investigate security data with hunting queries; "
        "it does not provide the endpoint vulnerability-prioritization capability asked for here."
    ),
    "B": (
        "Microsoft Defender for Identity focuses on identity-related threats involving Active Directory "
        "and hybrid identities, not prioritized endpoint software vulnerabilities."
    ),
    "C": (
        "Microsoft Defender for Office 365 protects email and collaboration workloads from threats; "
        "it is not the endpoint vulnerability-management capability."
    ),
}
AUTHORITY_REFS = (
    "https://learn.microsoft.com/en-us/defender-vulnerability-management/defender-vulnerability-management",
    "https://learn.microsoft.com/en-us/azure/sentinel/hunting",
    "https://learn.microsoft.com/en-us/defender-for-identity/what-is",
    "https://learn.microsoft.com/en-us/defender-office-365/mdo-about",
)
PR37_PRESERVED_IDS = (
    "sc900_mlc_q064",
    "sc900_mlc_q150",
    "sc900_mlc_q198",
    "sc900_mlc_q219",
    "sc900_mlc_q226",
    "sc900_mlc_q242",
    "sc900_mlc_q249",
    "sc900_mlc_q269",
)
CURRENTNESS_CHECKED_AT = "2026-09-21"


class ExplanationBuildError(ValueError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExplanationBuildError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExplanationBuildError(f"object required: {path}")
    return value


def _index(questions: list[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for question in questions:
        if not isinstance(question, dict):
            raise ExplanationBuildError("question object required")
        qid = canonical_question_id(question)
        if not qid or qid in result:
            raise ExplanationBuildError(f"invalid/duplicate question id: {qid!r}")
        result[qid] = question
    return result


def _changed_fields(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def _require_protected_q118(question: Mapping[str, Any]) -> None:
    if question.get("prompt") != EXPECTED_PROMPT:
        raise ExplanationBuildError("Q118_PROMPT_MISMATCH")
    if question.get("choices") != EXPECTED_CHOICES:
        raise ExplanationBuildError("Q118_CHOICES_MISMATCH")
    if list(question.get("correct") or []) != EXPECTED_CORRECT:
        raise ExplanationBuildError("Q118_KEY_MISMATCH")
    if question.get("objective_code") != EXPECTED_OBJECTIVE_CODE:
        raise ExplanationBuildError("Q118_OBJECTIVE_MISMATCH")
    if question.get("tested_decision") != EXPECTED_TESTED_DECISION:
        raise ExplanationBuildError("Q118_TESTED_DECISION_MISMATCH")
    if question.get("question_number") != EXPECTED_QUESTION_NUMBER:
        raise ExplanationBuildError("Q118_QUESTION_NUMBER_MISMATCH")


def _require_sparse_feedback(question: Mapping[str, Any]) -> None:
    feedback = question.get("choice_explanations")
    if feedback != TARGET_CHOICE_EXPLANATIONS:
        raise ExplanationBuildError("MALFORMED_SPARSE_FEEDBACK")
    if not isinstance(feedback, Mapping):
        raise ExplanationBuildError("MALFORMED_SPARSE_FEEDBACK")
    if set(feedback) != {"A", "B", "C"}:
        raise ExplanationBuildError("MALFORMED_SPARSE_FEEDBACK")
    if any(not isinstance(value, str) or not value.strip() for value in feedback.values()):
        raise ExplanationBuildError("MALFORMED_SPARSE_FEEDBACK")
    if "D" in feedback or any(key in set(EXPECTED_CORRECT) for key in feedback):
        raise ExplanationBuildError("CORRECT_CHOICE_FEEDBACK_PRESENT")


def _load_verification_results(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "BUILD_VERIFIED_TESTS_PENDING",
            "full_repository_tests": "PENDING",
            "quality_differential": "PENDING",
        }
    return copy.deepcopy(_load_object(path))


def build_sc900_explanation_q118_repair(
    root: Path = ROOT,
    *,
    verification_results_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(root)
    source_path = root / Q118_SOURCE_BANK_FILENAME
    target_path = root / Q118_TARGET_BANK_FILENAME
    spec_path = root / SPEC_RELATIVE_PATH
    ledger_path = root / LEDGER_RELATIVE_PATH
    manifest_path = root / MANIFEST_RELATIVE_PATH
    receipt_path = root / RECEIPT_RELATIVE_PATH
    verification_path = (
        Path(verification_results_path)
        if verification_results_path is not None
        else root / VERIFICATION_RESULTS_RELATIVE_PATH
    )

    if sha256_file(source_path) != EXPECTED_SOURCE_BANK_SHA256:
        raise ExplanationBuildError("SOURCE_BANK_FILE_HASH_MISMATCH")
    source = _load_object(source_path)
    source_questions = source.get("questions")
    if not isinstance(source_questions, list) or len(source_questions) != REQUIRED_QUESTION_COUNT:
        raise ExplanationBuildError("QUESTION_COUNT_MISMATCH")
    if bank_content_fingerprint(source_questions) != EXPECTED_SOURCE_CONTENT_FINGERPRINT:
        raise ExplanationBuildError("SOURCE_CONTENT_FINGERPRINT_MISMATCH")

    source_index = _index(source_questions)
    source_question = source_index.get(QUESTION_ID)
    if source_question is None:
        raise ExplanationBuildError("Q118_MISSING")
    if question_content_fingerprint(source_question) != EXPECTED_SOURCE_Q118_FINGERPRINT:
        raise ExplanationBuildError("Q118_SOURCE_FINGERPRINT_MISMATCH")
    _require_protected_q118(source_question)

    spec = _load_object(spec_path)
    ledger = _load_object(ledger_path)
    spec_hash = canonical_manifest_sha256(spec)
    ledger_hash = canonical_manifest_sha256(ledger)
    if spec.get("payload_sha256") != spec_hash or ledger.get("payload_sha256") != ledger_hash:
        raise ExplanationBuildError("SPEC_OR_LEDGER_HASH_MISMATCH")
    if (
        spec.get("work_id") != Q118_WORK_ID
        or spec.get("semantic_review_work_id") != Q118_SEMANTIC_REVIEW_WORK_ID
        or spec.get("permitted_change_class") != PERMITTED_CHANGE_CLASS
        or spec.get("continuity_policy") != CONTINUITY_POLICY
        or spec.get("target_count") != Q118_TARGET_COUNT
        or spec.get("wording_authority") != Q118_WORDING_AUTHORITY
        or spec.get("independent_pre_implementation_semantic_review") is not False
        or ledger.get("work_id") != Q118_WORK_ID
        or ledger.get("semantic_review_work_id") != Q118_SEMANTIC_REVIEW_WORK_ID
        or ledger.get("target_count") != Q118_TARGET_COUNT
        or ledger.get("wording_authority") != Q118_WORDING_AUTHORITY
        or ledger.get("independent_pre_implementation_semantic_review") is not False
    ):
        raise ExplanationBuildError("SPEC_AUTHORITY_MISMATCH")

    revisions = spec.get("revisions")
    target_ids = list(spec.get("target_ids") or [])
    if target_ids != [QUESTION_ID] or not isinstance(revisions, list) or len(revisions) != 1:
        raise ExplanationBuildError("TARGET_SET_MISMATCH")
    row = revisions[0]
    if not isinstance(row, Mapping) or row.get("question_id") != QUESTION_ID:
        raise ExplanationBuildError("TARGET_SET_MISMATCH")
    if row.get("target_general_explanation") != TARGET_GENERAL_EXPLANATION:
        raise ExplanationBuildError("FROZEN_TARGET_WORDING_MISMATCH")
    if row.get("target_choice_explanations") != TARGET_CHOICE_EXPLANATIONS:
        raise ExplanationBuildError("FROZEN_TARGET_WORDING_MISMATCH")
    if row.get("source_content_fingerprint") != EXPECTED_SOURCE_Q118_FINGERPRINT:
        raise ExplanationBuildError("Q118_SOURCE_FINGERPRINT_MISMATCH")
    if row.get("target_content_fingerprint") != EXPECTED_TARGET_Q118_FINGERPRINT:
        raise ExplanationBuildError("Q118_TARGET_FINGERPRINT_MISMATCH")
    if list(row.get("authorized_changed_fields") or []) != list(AUTHORIZED_CHANGED_FIELDS):
        raise ExplanationBuildError("AUTHORIZED_FIELDS_MISMATCH")
    if list(row.get("authority_refs") or []) != list(AUTHORITY_REFS):
        raise ExplanationBuildError("AUTHORITY_REFS_MISMATCH")
    if source_question.get("general_explanation") != row.get("source_general_explanation"):
        raise ExplanationBuildError("SOURCE_GENERAL_MISMATCH")
    if source_question.get("choice_explanations") != row.get("source_choice_explanations"):
        raise ExplanationBuildError("SOURCE_CHOICE_FEEDBACK_MISMATCH")

    candidate = copy.deepcopy(source)
    candidate_questions = candidate["questions"]
    candidate_index = _index(candidate_questions)
    target_question = candidate_index[QUESTION_ID]
    target_question["general_explanation"] = TARGET_GENERAL_EXPLANATION
    target_question["choice_explanations"] = copy.deepcopy(TARGET_CHOICE_EXPLANATIONS)
    _require_protected_q118(target_question)
    _require_sparse_feedback(target_question)
    if question_content_fingerprint(target_question) != EXPECTED_TARGET_Q118_FINGERPRINT:
        raise ExplanationBuildError("Q118_TARGET_FINGERPRINT_MISMATCH")
    if _changed_fields(source_question, target_question) != list(AUTHORIZED_CHANGED_FIELDS):
        raise ExplanationBuildError("UNDECLARED_Q118_CHANGE")

    source_ids = [canonical_question_id(question) for question in source_questions]
    candidate_ids = [canonical_question_id(question) for question in candidate_questions]
    if candidate_ids != source_ids:
        raise ExplanationBuildError("QUESTION_ORDER_MISMATCH")
    actual_changed_ids = [qid for qid in source_ids if source_index[qid] != candidate_index[qid]]
    if actual_changed_ids != [QUESTION_ID]:
        raise ExplanationBuildError("CHANGED_ID_SET_MISMATCH")

    tranche_spec = _load_object(root / TRANCHE_1_SPEC_RELATIVE_PATH)
    tranche_ids = list(tranche_spec.get("target_ids") or [])
    if len(tranche_ids) != 48 or QUESTION_ID in tranche_ids:
        raise ExplanationBuildError("TRANCHE_1_MEMBERSHIP_MISMATCH")
    for qid in tranche_ids:
        if source_index[qid] != candidate_index[qid]:
            raise ExplanationBuildError(f"PR38_DELTA_NOT_PRESERVED:{qid}")
    for qid in PR37_PRESERVED_IDS:
        if source_index[qid] != candidate_index[qid]:
            raise ExplanationBuildError(f"PR37_CORRECTION_NOT_PRESERVED:{qid}")

    write_canonical_package_b_json(target_path, candidate)
    target_raw_sha = sha256_file(target_path)
    target_fp = bank_content_fingerprint(candidate_questions)
    if target_raw_sha != EXPECTED_TARGET_BANK_SHA256 or target_fp != EXPECTED_TARGET_CONTENT_FINGERPRINT:
        raise ExplanationBuildError("TARGET_DETERMINISM_MISMATCH")
    if len(candidate_questions) != REQUIRED_QUESTION_COUNT:
        raise ExplanationBuildError("QUESTION_COUNT_MISMATCH")

    ledger_entries = ledger.get("entries")
    if not isinstance(ledger_entries, list) or len(ledger_entries) != 1:
        raise ExplanationBuildError("LEDGER_TARGET_SET_MISMATCH")
    ledger_row = ledger_entries[0]
    if not isinstance(ledger_row, Mapping) or ledger_row.get("question_id") != QUESTION_ID:
        raise ExplanationBuildError("LEDGER_TARGET_SET_MISMATCH")
    if ledger_row.get("semantic_review_disposition") != Q118_SEMANTIC_REVIEW_DISPOSITION:
        raise ExplanationBuildError("LEDGER_DISPOSITION_MISMATCH")
    if ledger_row.get("independent_pre_implementation_semantic_review") is not False:
        raise ExplanationBuildError("LEDGER_FALSE_REVIEW_CLAIM")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_kind": MANIFEST_KIND,
        "work_id": Q118_WORK_ID,
        "continuity_policy": CONTINUITY_POLICY,
        "permitted_change_class": PERMITTED_CHANGE_CLASS,
        "source_bank": {
            "filename": Q118_SOURCE_BANK_FILENAME,
            "file_sha256": EXPECTED_SOURCE_BANK_SHA256,
            "content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "target_bank": {
            "filename": Q118_TARGET_BANK_FILENAME,
            "file_sha256": target_raw_sha,
            "content_fingerprint": target_fp,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "revision_spec": {
            "filename": SPEC_RELATIVE_PATH,
            "file_sha256": sha256_file(spec_path),
            "payload_sha256": spec_hash,
        },
        "semantic_review_ledger": {
            "filename": LEDGER_RELATIVE_PATH,
            "file_sha256": sha256_file(ledger_path),
            "payload_sha256": ledger_hash,
        },
        "edges": [
            {
                "question_id": QUESTION_ID,
                "from_content_fingerprint": EXPECTED_SOURCE_Q118_FINGERPRINT,
                "to_content_fingerprint": EXPECTED_TARGET_Q118_FINGERPRINT,
                "changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
                "review_entry_identity": canonical_manifest_sha256(ledger_row),
                "authority_refs": list(AUTHORITY_REFS),
            }
        ],
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
    if admission.admitted.manifest_sha256 != manifest["payload_sha256"]:
        raise ExplanationBuildError("AUTHORITY_ADMISSION_FAILED")
    if Q118_PROFILE.work_id != Q118_WORK_ID or Q118_PROFILE.target_count != Q118_TARGET_COUNT:
        raise ExplanationBuildError("AUTHORITY_PROFILE_MISMATCH")

    verification_evidence = _load_verification_results(verification_path)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "work_id": Q118_WORK_ID,
        "semantic_review_work_id": Q118_SEMANTIC_REVIEW_WORK_ID,
        "wording_authority": Q118_WORDING_AUTHORITY,
        "independent_pre_implementation_semantic_review": False,
        "source_bank": {
            "filename": Q118_SOURCE_BANK_FILENAME,
            "file_sha256": EXPECTED_SOURCE_BANK_SHA256,
            "content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "revision_spec_payload_sha256": spec_hash,
        "semantic_review_ledger_payload_sha256": ledger_hash,
        "manifest_payload_sha256": manifest["payload_sha256"],
        "target_bank": {
            "filename": Q118_TARGET_BANK_FILENAME,
            "file_sha256": target_raw_sha,
            "content_fingerprint": target_fp,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "q118_source_content_fingerprint": EXPECTED_SOURCE_Q118_FINGERPRINT,
        "q118_target_content_fingerprint": EXPECTED_TARGET_Q118_FINGERPRINT,
        "changed_question_ids": [QUESTION_ID],
        "changed_question_count": 1,
        "changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
        "general_explanation_changed_count": 1,
        "choice_explanations_changed_count": 1,
        "selected_wrong_feedback_entry_count": 3,
        "correct_choice_feedback_present": False,
        "prompt_changed_count": 0,
        "choices_changed_count": 0,
        "correct_key_changed_count": 0,
        "objective_changed_count": 0,
        "tested_decision_changed_count": 0,
        "protected_metadata_changed_count": 0,
        "question_order_changed": False,
        "pr38_48_question_delta_preserved": True,
        "pr37_nine_question_correction_preserved": True,
        "authority_admission": "PASS",
        "production_content_activation": False,
        "runtime_bank": PRODUCTION_BANK_FILENAME,
        "verification_evidence": verification_evidence,
        "payload_sha256": "",
    }
    receipt["payload_sha256"] = canonical_manifest_sha256(receipt)
    write_canonical_package_b_json(receipt_path, receipt)

    return {
        "source_bank_raw_sha256": EXPECTED_SOURCE_BANK_SHA256,
        "source_bank_content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
        "source_q118_content_fingerprint": EXPECTED_SOURCE_Q118_FINGERPRINT,
        "target_bank_path": str(target_path),
        "target_bank_raw_sha256": target_raw_sha,
        "target_bank_content_fingerprint": target_fp,
        "target_q118_content_fingerprint": EXPECTED_TARGET_Q118_FINGERPRINT,
        "manifest_path": str(manifest_path),
        "manifest_payload_sha256": manifest["payload_sha256"],
        "receipt_path": str(receipt_path),
        "receipt_payload_sha256": receipt["payload_sha256"],
        "changed_question_count": 1,
        "selected_wrong_feedback_entry_count": 3,
        "admission_status": admission.status.value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--verification-results", type=Path, default=None)
    args = parser.parse_args()
    result = build_sc900_explanation_q118_repair(
        args.root,
        verification_results_path=args.verification_results,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
