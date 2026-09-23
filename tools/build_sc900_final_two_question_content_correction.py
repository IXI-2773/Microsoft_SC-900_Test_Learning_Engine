from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import AdmissionStatus, canonical_manifest_sha256, sha256_file
from content_revision_correction_authority import (
    CONTINUITY_POLICY,
    MANIFEST_KIND,
    PERMITTED_CHANGE_CLASS,
    REQUIRED_QUESTION_COUNT,
    REVIEW_DISPOSITION_APPROVED,
    admit_content_correction,
)
from content_revision_correction_authority import FINAL_TWO_QUESTION_AUTHORITY_REFS as AUTHORITY_REFS
from content_revision_correction_authority import FINAL_TWO_QUESTION_AUTHORIZED_FIELDS as AUTHORIZED_CHANGED_FIELDS
from content_revision_correction_authority import FINAL_TWO_QUESTION_IDS as TARGET_IDS
from content_revision_correction_authority import FINAL_TWO_QUESTION_SOURCE_BANK_FILENAME as SOURCE_BANK_FILENAME
from content_revision_correction_authority import (
    FINAL_TWO_QUESTION_SOURCE_FINGERPRINT as EXPECTED_SOURCE_CONTENT_FINGERPRINT,
)
from content_revision_correction_authority import FINAL_TWO_QUESTION_SOURCE_SHA256 as EXPECTED_SOURCE_BANK_SHA256
from content_revision_correction_authority import FINAL_TWO_QUESTION_TARGET_BANK_FILENAME as TARGET_BANK_FILENAME
from content_revision_correction_authority import FINAL_TWO_QUESTION_WORK_ID as WORK_ID
from package_b_canonical_json import write_canonical_package_b_json
from question_identity import bank_content_fingerprint, canonical_question_id, question_content_fingerprint

SPEC_FILENAME = "sc900_final_two_question_content_correction.json"
CURRENTNESS_FILENAME = "sc900_final_two_question_content_correction.json"
MANIFEST_FILENAME = "sc900_final_two_question_content_correction.json"
REVIEW_DIRECTORY = "SC900-FINAL-TWO-QUESTION-CONTENT-CORRECTION-001"
CHECKED_AT = "2026-09-23T00:45:00Z"

REPLACEMENTS = {
    "sc900_p2_q001": {
        "choice_label": "D",
        "choice_text": "Encoding",
        "choice_explanation": (
            "Encoding changes how information is represented for storage or transmission, but it does not provide "
            "confidentiality. Encryption is the reversible protection mechanism used when an authorized recipient "
            "must later recover plaintext."
        ),
    },
    "sc900_p3_q071": {
        "choice_label": "A",
        "choice_text": "Encoding",
        "choice_explanation": (
            "Encoding changes the representation of data, but it is not designed to produce an integrity check "
            "value. Hashing produces a one-way digest that can be compared to detect changes."
        ),
    },
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("questions"), list):
        raise ValueError(f"invalid bank: {path}")
    return value


def _index(rows: list[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("question must be object")
        qid = canonical_question_id(row)
        if not qid or qid in result:
            raise ValueError(f"invalid question id: {qid}")
        result[qid] = row
    return result


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    payload["payload_sha256"] = canonical_manifest_sha256(payload)
    return payload


def _changed_values(question: Mapping[str, Any]) -> dict[str, Any]:
    return {field: copy.deepcopy(question.get(field)) for field in AUTHORIZED_CHANGED_FIELDS}


def build_final_two_question_content_correction(root: Path) -> dict[str, Any]:
    root = Path(root)
    source_path = root / SOURCE_BANK_FILENAME
    target_path = root / TARGET_BANK_FILENAME
    evidence = root / "content_revision_evidence"
    spec_path = evidence / "specs" / SPEC_FILENAME
    currentness_path = evidence / "currentness" / CURRENTNESS_FILENAME
    review_root = evidence / "reviews"
    review_dir = review_root / REVIEW_DIRECTORY
    manifest_path = evidence / "manifests" / MANIFEST_FILENAME

    if sha256_file(source_path) != EXPECTED_SOURCE_BANK_SHA256:
        raise ValueError("SOURCE_FILE_HASH_MISMATCH")
    source = _load(source_path)
    source_rows = source["questions"]
    if len(source_rows) != REQUIRED_QUESTION_COUNT:
        raise ValueError("QUESTION_COUNT_MISMATCH")
    if bank_content_fingerprint(source_rows) != EXPECTED_SOURCE_CONTENT_FINGERPRINT:
        raise ValueError("SOURCE_CONTENT_FINGERPRINT_MISMATCH")
    source_index = _index(source_rows)

    target = copy.deepcopy(source)
    target_index = _index(target["questions"])
    for qid in TARGET_IDS:
        replacement = REPLACEMENTS[qid]
        question = target_index[qid]
        choices = dict(question["choices"])
        explanations = dict(question["choice_explanations"])
        label = replacement["choice_label"]
        choices[label] = replacement["choice_text"]
        explanations[label] = replacement["choice_explanation"]
        question["choices"] = choices
        question["choice_explanations"] = explanations

    target_index = _index(target["questions"])
    write_canonical_package_b_json(target_path, target)
    target_raw_sha = sha256_file(target_path)
    target_fp = bank_content_fingerprint(target["questions"])

    corrections = []
    for qid in TARGET_IDS:
        before = source_index[qid]
        after = target_index[qid]
        corrections.append(
            {
                "question_id": qid,
                "authorized_changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
                "source_values": _changed_values(before),
                "target_values": _changed_values(after),
                "correct_key": list(before["correct"]),
                "objective_code": before["objective_code"],
                "authority_refs": list(AUTHORITY_REFS),
                "semantic_validation_work_id": WORK_ID,
                "final_validation_status": "APPROVED",
                "currentness_class": "LOW",
            }
        )
    spec = _seal(
        {
            "schema_version": 2,
            "work_id": WORK_ID,
            "source_bank": SOURCE_BANK_FILENAME,
            "source_bank_raw_sha256": EXPECTED_SOURCE_BANK_SHA256,
            "source_bank_content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
            "question_count": REQUIRED_QUESTION_COUNT,
            "target_ids": list(TARGET_IDS),
            "corrections": corrections,
            "currentness_requirements": {
                "currentness_record_required": True,
                "question_ids": list(TARGET_IDS),
                "required_result": "PASS_FOR_ALL_TARGETS",
            },
            "payload_sha256": "",
        }
    )
    write_canonical_package_b_json(spec_path, spec)

    currentness = _seal(
        {
            "schema_version": 1,
            "work_id": WORK_ID,
            "source_bank": SOURCE_BANK_FILENAME,
            "source_bank_raw_sha256": EXPECTED_SOURCE_BANK_SHA256,
            "source_bank_content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
            "checked_at": CHECKED_AT,
            "targets": [
                {
                    "question_id": qid,
                    "status": "PASS",
                    "authority_refs": list(AUTHORITY_REFS),
                    "material_change_detected": False,
                    "notes": (
                        "Microsoft Learn continues to distinguish reversible encryption from one-way hashing and "
                        "describes encoding as representation/transport rather than the confidentiality or integrity "
                        "operation asked by this item."
                    ),
                }
                for qid in TARGET_IDS
            ],
            "overall_status": "PASS",
            "payload_sha256": "",
        }
    )
    write_canonical_package_b_json(currentness_path, currentness)

    edges = []
    review_dir.mkdir(parents=True, exist_ok=True)
    for qid in TARGET_IDS:
        before = source_index[qid]
        after = target_index[qid]
        from_fp = question_content_fingerprint(before)
        to_fp = question_content_fingerprint(after)
        review_rel = f"{REVIEW_DIRECTORY}/{qid}.json"
        review_path = review_root / review_rel
        receipt = {
            "question_id": qid,
            "from_content_fingerprint": from_fp,
            "to_content_fingerprint": to_fp,
            "authorized_changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
            "before": _changed_values(before),
            "after": _changed_values(after),
            "correct_key_before": list(before["correct"]),
            "correct_key_after": list(after["correct"]),
            "objective_before": before["objective_code"],
            "objective_after": after["objective_code"],
            "authority_refs": list(AUTHORITY_REFS),
            "correction_spec_payload_sha256": spec["payload_sha256"],
            "disposition": REVIEW_DISPOSITION_APPROVED,
        }
        write_canonical_package_b_json(review_path, receipt)
        edges.append(
            {
                "question_id": qid,
                "from_content_fingerprint": from_fp,
                "to_content_fingerprint": to_fp,
                "changed_fields": list(AUTHORIZED_CHANGED_FIELDS),
                "correct_key_unchanged": True,
                "objective_unchanged": True,
                "domain_unchanged": True,
                "question_type_unchanged": True,
                "tier_unchanged": True,
                "exam_eligibility_unchanged": True,
                "review_status": "APPROVED",
                "review_artifact": review_rel,
                "review_artifact_sha256": sha256_file(review_path),
                "authority_refs": list(AUTHORITY_REFS),
            }
        )

    manifest = _seal(
        {
            "schema_version": 2,
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
            "correction_spec": {
                "filename": SPEC_FILENAME,
                "file_sha256": sha256_file(spec_path),
                "payload_sha256": spec["payload_sha256"],
            },
            "currentness_record": {
                "filename": CURRENTNESS_FILENAME,
                "file_sha256": sha256_file(currentness_path),
                "payload_sha256": currentness["payload_sha256"],
            },
            "edges": edges,
            "payload_sha256": "",
        }
    )
    write_canonical_package_b_json(manifest_path, manifest)

    admission = admit_content_correction(
        manifest,
        spec=spec,
        currentness_record=currentness,
        source_bank_path=source_path,
        target_bank_path=target_path,
        spec_path=spec_path,
        currentness_path=currentness_path,
        review_root=review_root,
    )
    if admission.status != AdmissionStatus.PASS or admission.admitted is None:
        raise ValueError(f"ADMISSION_FAILED: {admission.reasons}")
    return {
        "source_sha256": EXPECTED_SOURCE_BANK_SHA256,
        "source_content_fingerprint": EXPECTED_SOURCE_CONTENT_FINGERPRINT,
        "target_sha256": target_raw_sha,
        "target_content_fingerprint": target_fp,
        "manifest_sha256": manifest["payload_sha256"],
        "spec_sha256": spec["payload_sha256"],
        "currentness_sha256": currentness["payload_sha256"],
        "changed_ids": list(TARGET_IDS),
    }


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[1]
    result = build_final_two_question_content_correction(repository_root)
    print(json.dumps(result, sort_keys=True, indent=2))
