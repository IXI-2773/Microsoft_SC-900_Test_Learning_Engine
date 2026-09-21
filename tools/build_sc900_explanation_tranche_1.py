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
    EXPECTED_SOURCE_BANK_SHA256,
    EXPECTED_SOURCE_CONTENT_FINGERPRINT,
    MANIFEST_KIND,
    PERMITTED_CHANGE_CLASS,
    REQUIRED_QUESTION_COUNT,
    SCHEMA_VERSION,
    SEMANTIC_REVIEW_WORK_ID,
    SOURCE_BANK_FILENAME,
    TARGET_BANK_FILENAME,
    WORK_ID,
    admit_explanation_revision,
)
from package_b_canonical_json import write_canonical_package_b_json  # noqa: E402
from question_identity import (  # noqa: E402
    bank_content_fingerprint,
    canonical_question_id,
    question_content_fingerprint,
)

SPEC_RELATIVE_PATH = "content_revision_evidence/specs/sc900_explanation_tranche_1.json"
LEDGER_RELATIVE_PATH = "content_revision_evidence/reviews/SC900-EXPLANATION-TRANCHE-1/semantic_review_ledger.json"
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_explanation_tranche_1.json"
RECEIPT_RELATIVE_PATH = "content_revision_evidence/receipts/sc900_explanation_tranche_1.json"
VERIFICATION_RESULTS_RELATIVE_PATH = (
    "content_revision_evidence/verification/sc900_explanation_tranche_1_test_results.json"
)
SOURCE_CORRECTION_MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_content_correction_001.json"
EXPECTED_SOURCE_CORRECTION_MANIFEST_PAYLOAD_SHA256 = "5d32c7c9b24192e6911a943fb8f9538369aad0331a6927fdbf5e95a81234c0f1"
EXPECTED_SPEC_PAYLOAD_SHA256 = "033b07455324a6fabe81785f1b00ecbe0081483148b52bd13df3d9966a047fc2"
EXPECTED_LEDGER_PAYLOAD_SHA256 = "e20f46110bc660f1ab75213cb7662fb66d37873488446058c05b7ed6415a9969"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"


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


def _load_verification_results(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "BUILD_VERIFIED_TESTS_PENDING",
            "full_repository_tests": "PENDING",
            "quality_differential": "PENDING",
        }
    payload = _load_object(path)
    return copy.deepcopy(payload)


def build_sc900_explanation_tranche_1(
    root: Path = ROOT,
    *,
    verification_results_path: Path | None = None,
) -> dict[str, Any]:
    root = Path(root)
    source_path = root / SOURCE_BANK_FILENAME
    target_path = root / TARGET_BANK_FILENAME
    spec_path = root / SPEC_RELATIVE_PATH
    ledger_path = root / LEDGER_RELATIVE_PATH
    manifest_path = root / MANIFEST_RELATIVE_PATH
    receipt_path = root / RECEIPT_RELATIVE_PATH
    correction_manifest_path = root / SOURCE_CORRECTION_MANIFEST_RELATIVE_PATH
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

    source_correction_manifest = _load_object(correction_manifest_path)
    if canonical_manifest_sha256(source_correction_manifest) != EXPECTED_SOURCE_CORRECTION_MANIFEST_PAYLOAD_SHA256:
        raise ExplanationBuildError("SOURCE_CORRECTION_MANIFEST_MISMATCH")

    spec = _load_object(spec_path)
    ledger = _load_object(ledger_path)
    if canonical_manifest_sha256(spec) != EXPECTED_SPEC_PAYLOAD_SHA256:
        raise ExplanationBuildError("SPEC_HASH_MISMATCH")
    if spec.get("payload_sha256") != EXPECTED_SPEC_PAYLOAD_SHA256:
        raise ExplanationBuildError("SPEC_STORED_HASH_MISMATCH")
    if canonical_manifest_sha256(ledger) != EXPECTED_LEDGER_PAYLOAD_SHA256:
        raise ExplanationBuildError("LEDGER_HASH_MISMATCH")
    if ledger.get("payload_sha256") != EXPECTED_LEDGER_PAYLOAD_SHA256:
        raise ExplanationBuildError("LEDGER_STORED_HASH_MISMATCH")
    if (
        spec.get("work_id") != WORK_ID
        or spec.get("semantic_review_work_id") != SEMANTIC_REVIEW_WORK_ID
        or spec.get("permitted_change_class") != PERMITTED_CHANGE_CLASS
        or spec.get("continuity_policy") != CONTINUITY_POLICY
    ):
        raise ExplanationBuildError("SPEC_AUTHORITY_MISMATCH")

    revisions = spec.get("revisions")
    target_ids = list(spec.get("target_ids") or [])
    if not isinstance(revisions, list) or len(revisions) != 48 or len(target_ids) != 48:
        raise ExplanationBuildError("TARGET_SET_MISMATCH")
    if len(set(target_ids)) != 48:
        raise ExplanationBuildError("DUPLICATE_TARGET_ID")
    revision_by_id = {str(row.get("question_id")): row for row in revisions if isinstance(row, Mapping)}
    if set(revision_by_id) != set(target_ids):
        raise ExplanationBuildError("TARGET_SET_MISMATCH")

    source_index = _index(source_questions)
    candidate = copy.deepcopy(source)
    candidate_questions = candidate["questions"]
    candidate_index = _index(candidate_questions)

    for qid in target_ids:
        source_question = source_index.get(qid)
        target_question = candidate_index.get(qid)
        row = revision_by_id[qid]
        if source_question is None or target_question is None:
            raise ExplanationBuildError(f"TARGET_MISSING:{qid}")
        if question_content_fingerprint(source_question) != row.get("source_content_fingerprint"):
            raise ExplanationBuildError(f"SOURCE_FINGERPRINT_MISMATCH:{qid}")
        if source_question.get("general_explanation") != row.get("source_general_explanation"):
            raise ExplanationBuildError(f"SOURCE_GENERAL_MISMATCH:{qid}")
        if source_question.get("choice_explanations") != row.get("source_choice_explanations"):
            raise ExplanationBuildError(f"SOURCE_CHOICE_FEEDBACK_MISMATCH:{qid}")
        if list(row.get("authorized_changed_fields") or []) != list(AUTHORIZED_CHANGED_FIELDS):
            raise ExplanationBuildError(f"AUTHORIZED_FIELDS_MISMATCH:{qid}")

        target_question["general_explanation"] = str(row["target_general_explanation"])
        target_question["choice_explanations"] = copy.deepcopy(dict(row["target_choice_explanations"]))
        if question_content_fingerprint(target_question) != row.get("target_content_fingerprint"):
            raise ExplanationBuildError(f"TARGET_FINGERPRINT_MISMATCH:{qid}")
        if _changed_fields(source_question, target_question) != list(AUTHORIZED_CHANGED_FIELDS):
            raise ExplanationBuildError(f"UNDECLARED_CHANGE:{qid}")

    candidate_ids = [canonical_question_id(q) for q in candidate_questions]
    source_ids = [canonical_question_id(q) for q in source_questions]
    if candidate_ids != source_ids:
        raise ExplanationBuildError("QUESTION_ORDER_MISMATCH")
    actual_changed_ids = [qid for qid in source_ids if source_index[qid] != candidate_index[qid]]
    if actual_changed_ids != target_ids:
        raise ExplanationBuildError("CHANGED_ID_SET_MISMATCH")

    write_canonical_package_b_json(target_path, candidate)
    target_raw_sha = sha256_file(target_path)
    target_fp = bank_content_fingerprint(candidate_questions)

    ledger_entries = ledger.get("entries")
    if not isinstance(ledger_entries, list) or len(ledger_entries) != 48:
        raise ExplanationBuildError("LEDGER_TARGET_SET_MISMATCH")
    ledger_by_id = {str(row.get("question_id")): row for row in ledger_entries if isinstance(row, Mapping)}
    if set(ledger_by_id) != set(target_ids):
        raise ExplanationBuildError("LEDGER_TARGET_SET_MISMATCH")

    edges = []
    for qid in target_ids:
        row = revision_by_id[qid]
        ledger_row = ledger_by_id[qid]
        edges.append(
            {
                "question_id": qid,
                "from_content_fingerprint": row["source_content_fingerprint"],
                "to_content_fingerprint": row["target_content_fingerprint"],
                "changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
                "review_entry_identity": canonical_manifest_sha256(ledger_row),
                "authority_refs": list(row["authority_refs"]),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_kind": MANIFEST_KIND,
        "work_id": WORK_ID,
        "continuity_policy": CONTINUITY_POLICY,
        "permitted_change_class": PERMITTED_CHANGE_CLASS,
        "source_bank": {
            "filename": SOURCE_BANK_FILENAME,
            "file_sha256": EXPECTED_SOURCE_BANK_SHA256,
            "content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "target_bank": {
            "filename": TARGET_BANK_FILENAME,
            "file_sha256": target_raw_sha,
            "content_fingerprint": target_fp,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "revision_spec": {
            "filename": SPEC_RELATIVE_PATH,
            "file_sha256": sha256_file(spec_path),
            "payload_sha256": EXPECTED_SPEC_PAYLOAD_SHA256,
        },
        "semantic_review_ledger": {
            "filename": LEDGER_RELATIVE_PATH,
            "file_sha256": sha256_file(ledger_path),
            "payload_sha256": EXPECTED_LEDGER_PAYLOAD_SHA256,
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

    selected_wrong_count = sum(len(candidate_index[qid].get("choice_explanations") or {}) for qid in target_ids)
    if selected_wrong_count != 106:
        raise ExplanationBuildError(f"SELECTED_WRONG_FEEDBACK_COUNT_MISMATCH:{selected_wrong_count}")

    verification_evidence = _load_verification_results(verification_path)
    receipt = {
        "schema_version": 2,
        "work_id": WORK_ID,
        "semantic_review_work_id": SEMANTIC_REVIEW_WORK_ID,
        "source_bank": {
            "filename": SOURCE_BANK_FILENAME,
            "file_sha256": EXPECTED_SOURCE_BANK_SHA256,
            "content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "source_correction_manifest_payload_sha256": EXPECTED_SOURCE_CORRECTION_MANIFEST_PAYLOAD_SHA256,
        "revision_spec_payload_sha256": EXPECTED_SPEC_PAYLOAD_SHA256,
        "semantic_review_ledger_payload_sha256": EXPECTED_LEDGER_PAYLOAD_SHA256,
        "manifest_payload_sha256": manifest["payload_sha256"],
        "target_bank": {
            "filename": TARGET_BANK_FILENAME,
            "file_sha256": target_raw_sha,
            "content_fingerprint": target_fp,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "changed_question_ids": target_ids,
        "changed_question_count": len(actual_changed_ids),
        "changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
        "general_explanation_changed_count": sum(
            source_index[qid]["general_explanation"] != candidate_index[qid]["general_explanation"]
            for qid in target_ids
        ),
        "choice_explanations_changed_count": sum(
            source_index[qid]["choice_explanations"] != candidate_index[qid]["choice_explanations"]
            for qid in target_ids
        ),
        "selected_wrong_feedback_entry_count": selected_wrong_count,
        "q118_unchanged": source_index["sc900_mlc_q118"] == candidate_index["sc900_mlc_q118"],
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
        "target_bank_path": str(target_path),
        "target_bank_raw_sha256": target_raw_sha,
        "target_bank_content_fingerprint": target_fp,
        "manifest_path": str(manifest_path),
        "manifest_payload_sha256": manifest["payload_sha256"],
        "receipt_path": str(receipt_path),
        "receipt_payload_sha256": receipt["payload_sha256"],
        "changed_question_count": len(actual_changed_ids),
        "selected_wrong_feedback_entry_count": selected_wrong_count,
        "admission_status": admission.status.value,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--verification-results", type=Path, default=None)
    args = parser.parse_args()
    result = build_sc900_explanation_tranche_1(
        args.root,
        verification_results_path=args.verification_results,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
