from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.bank_quality import phase1_review_status, validate_phase1_question
from ingestion.models import ValidationError, load_taxonomy, normalize_text
from tools.validate_bank import validate_bank
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS, validate_source_inventory

EXPECTED_PHASE2_DOMAIN_COUNTS = {
    "security_compliance_identity": 12,
    "microsoft_entra": 28,
    "microsoft_security_solutions": 38,
    "microsoft_compliance_solutions": 22,
}
EXPECTED_PHASE2_OBJECTIVE_COUNTS = {
    "security_compliance_concepts": 6,
    "identity_concepts": 6,
    "entra_identity_types_and_function": 6,
    "entra_authentication": 8,
    "entra_access_management": 6,
    "entra_identity_protection_governance": 8,
    "azure_infrastructure_security": 12,
    "azure_security_management": 8,
    "microsoft_sentinel": 6,
    "defender_xdr": 12,
    "service_trust_privacy": 4,
    "purview_compliance_management": 4,
    "purview_information_protection_lifecycle": 8,
    "purview_insider_risk_ediscovery_audit": 6,
}
MANIFEST_ROLES = {"TRAIN", "PROBE", "UNASSIGNED"}
RESOLVED_FAMILY_STATE = "resolved"


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(context)
    return payload


def _review_index(review_receipts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for receipt in review_receipts:
        question_id = normalize_text(receipt.get("question_id"))
        if question_id:
            index[question_id] = receipt
    return index


def validate_phase2_set(
    questions: Sequence[Mapping[str, Any]],
    taxonomy: Mapping[str, Any],
    review_receipts: Sequence[Mapping[str, Any]],
    phase2_question_ids: Sequence[str],
) -> dict[str, Any]:
    approved = [row for row in questions if phase1_review_status(row) == "approved"]
    pending = [row for row in questions if phase1_review_status(row) == "pending"]
    withheld = [row for row in questions if phase1_review_status(row) == "withheld"]
    domain_counts = dict(sorted(Counter(normalize_text(row.get("domain")) for row in approved).items()))
    objective_counts = dict(sorted(Counter(normalize_text(row.get("objective")) for row in approved).items()))
    quality_errors: list[dict[str, Any]] = []

    ids = [normalize_text(row.get("id")) for row in approved]
    id_counts = Counter(ids)
    duplicate_ids = sorted(question_id for question_id, count in id_counts.items() if question_id and count > 1)
    if duplicate_ids:
        quality_errors.append(
            _error("DUPLICATE_APPROVED_ID", "approved question IDs must be unique", ids=duplicate_ids)
        )

    if len(approved) != 100:
        quality_errors.append(
            _error(
                "APPROVED_COUNT_MISMATCH",
                "Phase 2 requires exactly 100 approved cumulative questions",
                expected=100,
                actual=len(approved),
            )
        )

    phase2_id_set = {normalize_text(value) for value in phase2_question_ids if normalize_text(value)}
    approved_id_set = {question_id for question_id in ids if question_id}
    phase2_new_approved_count = len(phase2_id_set & approved_id_set)
    if phase2_new_approved_count != 50:
        quality_errors.append(
            _error(
                "PHASE2_NEW_APPROVED_COUNT_MISMATCH",
                "Phase 2 requires exactly 50 newly approved Phase-2 questions",
                expected=50,
                actual=phase2_new_approved_count,
            )
        )

    if domain_counts != EXPECTED_PHASE2_DOMAIN_COUNTS:
        quality_errors.append(
            _error(
                "DOMAIN_ALLOCATION_MISMATCH",
                "approved questions must match the frozen cumulative Phase-2 domain allocation",
                expected=EXPECTED_PHASE2_DOMAIN_COUNTS,
                actual=domain_counts,
            )
        )
    if objective_counts != EXPECTED_PHASE2_OBJECTIVE_COUNTS:
        quality_errors.append(
            _error(
                "OBJECTIVE_ALLOCATION_MISMATCH",
                "approved questions must match the frozen cumulative Phase-2 objective allocation",
                expected=EXPECTED_PHASE2_OBJECTIVE_COUNTS,
                actual=objective_counts,
            )
        )

    reviews = _review_index(review_receipts)
    for record in approved:
        question_id = normalize_text(record.get("id"))
        try:
            validate_phase1_question(record, taxonomy)
        except ValidationError as error:
            for issue in error.issues:
                quality_errors.append(
                    _error(issue["code"], issue["message"], question_id=question_id)
                )

        receipt = reviews.get(question_id)
        if receipt is None:
            quality_errors.append(
                _error(
                    "MISSING_REVIEW_RECEIPT",
                    "every approved cumulative question requires an independent review receipt",
                    question_id=question_id,
                )
            )
            continue
        if normalize_text(receipt.get("disposition")).lower() != "approved":
            quality_errors.append(
                _error(
                    "REVIEW_DISPOSITION_MISMATCH",
                    "approved question must have an approved review receipt",
                    question_id=question_id,
                )
            )
        failed_checks = [field for field in REVIEW_CHECK_FIELDS if receipt.get(field) is not True]
        if failed_checks:
            quality_errors.append(
                _error(
                    "REVIEW_RECEIPT_INCOMPLETE",
                    "review receipt is missing required affirmative checks",
                    question_id=question_id,
                    fields=failed_checks,
                )
            )
        if not normalize_text(receipt.get("reviewer")) or not normalize_text(receipt.get("reviewed_at")):
            quality_errors.append(
                _error(
                    "REVIEW_CUSTODY_INCOMPLETE",
                    "review receipt must identify reviewer and reviewed_at",
                    question_id=question_id,
                )
            )

    distinct_leaves = {
        normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id"))
        for row in approved
        if isinstance(row.get("metadata"), Mapping)
        and normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id"))
    }
    semantic_families = {
        normalize_text((row.get("metadata") or {}).get("semantic_family_id"))
        for row in approved
        if isinstance(row.get("metadata"), Mapping)
        and normalize_text((row.get("metadata") or {}).get("semantic_family_id"))
    }
    probe_suitability_counts = dict(
        sorted(
            Counter(
                normalize_text((row.get("metadata") or {}).get("future_probe_suitability"))
                for row in approved
                if isinstance(row.get("metadata"), Mapping)
            ).items()
        )
    )

    status = "PHASE_2_STRUCTURALLY_ACCEPTED" if not quality_errors else "PHASE_2_INCOMPLETE"
    return {
        "status": status,
        "approved_count": len(approved),
        "phase2_new_approved_count": phase2_new_approved_count,
        "pending_count": len(pending),
        "withheld_count": len(withheld),
        "domain_counts": domain_counts,
        "objective_counts": objective_counts,
        "distinct_leaf_count": len(distinct_leaves),
        "semantic_family_count": len(semantic_families),
        "probe_suitability_counts": probe_suitability_counts,
        "quality_errors": quality_errors,
    }


def validate_train_probe_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not normalize_text(manifest.get("schema_version")):
        errors.append(_error("MISSING_MANIFEST_SCHEMA_VERSION", "manifest schema_version is required"))
    if not normalize_text(manifest.get("partition_epoch")):
        errors.append(_error("MISSING_PARTITION_EPOCH", "manifest partition_epoch is required"))

    raw_items = manifest.get("items")
    items = list(raw_items) if isinstance(raw_items, list) else []
    seen_ids: set[str] = set()
    roles_by_family: dict[str, set[str]] = defaultdict(set)

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, Mapping):
            errors.append(_error("MALFORMED_MANIFEST_ITEM", "manifest item must be an object", index=index))
            continue

        question_id = normalize_text(raw_item.get("question_id"))
        semantic_family_id = normalize_text(raw_item.get("semantic_family_id"))
        source_family_id = normalize_text(raw_item.get("source_family_id"))
        role = normalize_text(raw_item.get("role")).upper()
        promotion_status = normalize_text(raw_item.get("promotion_status")).lower()
        probe_suitability = normalize_text(raw_item.get("future_probe_suitability"))
        family_state = normalize_text(raw_item.get("family_state")).lower()

        if not question_id:
            errors.append(_error("MISSING_MANIFEST_QUESTION_ID", "question_id is required", index=index))
        elif question_id in seen_ids:
            errors.append(
                _error(
                    "DUPLICATE_MANIFEST_QUESTION_ID",
                    "manifest question IDs must be unique",
                    question_id=question_id,
                )
            )
        else:
            seen_ids.add(question_id)

        if not semantic_family_id:
            errors.append(
                _error(
                    "MISSING_MANIFEST_SEMANTIC_FAMILY",
                    "semantic_family_id is required and unknown families must fail closed",
                    question_id=question_id,
                )
            )
        if not source_family_id:
            errors.append(
                _error(
                    "MISSING_MANIFEST_SOURCE_FAMILY",
                    "source_family_id is required",
                    question_id=question_id,
                )
            )
        if role not in MANIFEST_ROLES:
            errors.append(
                _error(
                    "INVALID_MANIFEST_ROLE",
                    "role must be TRAIN, PROBE, or UNASSIGNED",
                    question_id=question_id,
                    role=role,
                )
            )
        elif semantic_family_id and role in {"TRAIN", "PROBE"}:
            roles_by_family[semantic_family_id].add(role)

        if role == "PROBE":
            if promotion_status != "approved":
                errors.append(
                    _error(
                        "PROBE_REQUIRES_APPROVED",
                        "PROBE assignment requires approved content",
                        question_id=question_id,
                    )
                )
            if probe_suitability != "eligible":
                errors.append(
                    _error(
                        "PROBE_REQUIRES_ELIGIBLE",
                        "PROBE assignment requires future_probe_suitability=eligible",
                        question_id=question_id,
                    )
                )
            if family_state != RESOLVED_FAMILY_STATE:
                errors.append(
                    _error(
                        "PROBE_REQUIRES_RESOLVED_FAMILY",
                        "PROBE assignment requires resolved semantic-family membership",
                        question_id=question_id,
                        family_state=family_state,
                    )
                )

        if family_state in {"unknown", "disputed", "needs_review", ""} and role in {"TRAIN", "PROBE"}:
            errors.append(
                _error(
                    "UNRESOLVED_FAMILY_MUST_BE_UNASSIGNED",
                    "unknown or disputed semantic-family membership must fail closed to UNASSIGNED",
                    question_id=question_id,
                    family_state=family_state,
                )
            )

    for family_id, roles in sorted(roles_by_family.items()):
        if roles == {"TRAIN", "PROBE"}:
            errors.append(
                _error(
                    "SEMANTIC_FAMILY_SPLIT",
                    "a semantic family cannot span TRAIN and PROBE",
                    semantic_family_id=family_id,
                )
            )
    return errors


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_review_receipts(*paths: Path) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for review_path in sorted(path.glob("*.json")):
            payload = _load_json(review_path, [])
            rows = payload.get("reviews", []) if isinstance(payload, Mapping) else payload
            if isinstance(rows, list):
                receipts.extend(row for row in rows if isinstance(row, dict))
    return receipts


def _load_phase2_ids(path: Path) -> list[str]:
    ids: list[str] = []
    if not path.exists():
        return ids
    for batch_path in sorted(path.glob("*.jsonl")):
        for line in batch_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, Mapping):
                question_id = normalize_text(payload.get("id"))
                if question_id:
                    ids.append(question_id)
    return ids


def _bank_validation_issues(compiled_path: Path) -> tuple[int, list[dict[str, Any]]]:
    if not compiled_path.exists():
        return 0, [_error("COMPILED_BANK_MISSING", "compiled candidate bank does not exist")]
    payload = _load_json(compiled_path, {})
    questions = payload.get("questions", []) if isinstance(payload, Mapping) else []
    compiled_count = len(questions) if isinstance(questions, list) else 0
    if compiled_count == 0:
        return 0, [_error("COMPILED_BANK_EMPTY", "compiled candidate bank contains no questions")]
    result = validate_bank(compiled_path)
    issues = [
        _error("BANK_VALIDATION_ISSUE", body, title=title)
        for title, body in result.get("issues", [])
    ]
    issues.extend(
        _error("BANK_VALIDATION_WARNING", body, title=title)
        for title, body in result.get("warnings", [])
    )
    return compiled_count, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the reviewed SC-900 Phase-2 candidate bank.")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--compiled", type=Path, required=True)
    parser.add_argument("--phase1-reviews", type=Path, required=True)
    parser.add_argument("--phase2-reviews", type=Path, required=True)
    parser.add_argument("--phase2-batches", type=Path, required=True)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    taxonomy = load_taxonomy()
    questions = _load_json(args.store / "questions.json", [])
    if not isinstance(questions, list):
        questions = []
    reviews = _load_review_receipts(args.phase1_reviews, args.phase2_reviews)
    phase2_ids = _load_phase2_ids(args.phase2_batches)
    inventory = _load_json(args.source_inventory, {})
    if not isinstance(inventory, Mapping):
        inventory = {}

    source_errors = validate_source_inventory(inventory, taxonomy)
    result = validate_phase2_set(questions, taxonomy, reviews, phase2_ids)
    compiled_count, bank_issues = _bank_validation_issues(args.compiled)
    result["source_inventory_errors"] = source_errors
    result["bank_validation_issues"] = bank_issues
    result["compiled_count"] = compiled_count
    result["cand01_gate2_status"] = "GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE"
    result["implementation_authorized"] = False

    if compiled_count != result["approved_count"]:
        result["quality_errors"].append(
            _error(
                "COMPILED_COUNT_MISMATCH",
                "compiled candidate count must equal the approved question count",
                approved=result["approved_count"],
                compiled=compiled_count,
            )
        )
    if source_errors or bank_issues or result["quality_errors"]:
        result["status"] = "PHASE_2_INCOMPLETE"
    else:
        result["status"] = "PHASE_2_STRUCTURALLY_ACCEPTED"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PHASE_2_STRUCTURALLY_ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
