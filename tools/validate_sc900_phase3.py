from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from ingestion.bank_quality import phase1_review_status, validate_phase1_question
from ingestion.models import ValidationError, normalize_text
from tools.build_sc900_phase2 import review_content_sha256
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS, validate_source_inventory
from tools.validate_sc900_phase2 import validate_question_source_links

EXPECTED_PHASE3_DOMAIN_COUNTS = {
    "security_compliance_identity": 24,
    "microsoft_entra": 56,
    "microsoft_security_solutions": 76,
    "microsoft_compliance_solutions": 44,
}
EXPECTED_PHASE3_OBJECTIVE_COUNTS = {
    "security_compliance_concepts": 12,
    "identity_concepts": 12,
    "entra_identity_types_and_function": 12,
    "entra_authentication": 16,
    "entra_access_management": 12,
    "entra_identity_protection_governance": 16,
    "azure_infrastructure_security": 24,
    "azure_security_management": 16,
    "microsoft_sentinel": 12,
    "defender_xdr": 24,
    "service_trust_privacy": 8,
    "purview_compliance_management": 8,
    "purview_information_protection_lifecycle": 16,
    "purview_insider_risk_ediscovery_audit": 12,
}
EXPECTED_BLUEPRINT_LEAF_COUNT = 58


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(context)
    return payload


def _review_index(
    review_receipts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]]]:
    index: dict[str, Mapping[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for receipt in review_receipts:
        question_id = normalize_text(receipt.get("question_id"))
        if not question_id:
            continue
        if question_id in index:
            errors.append(
                _error(
                    "DUPLICATE_REVIEW_RECEIPT",
                    "review receipts must be unique by question_id",
                    question_id=question_id,
                )
            )
            continue
        index[question_id] = receipt
    return index, errors


def _parse_iso_date(value: Any) -> date | None:
    text = normalize_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def validate_phase3_source_inventory(
    inventory: Mapping[str, Any], taxonomy: Mapping[str, Any]
) -> list[dict[str, Any]]:
    errors = list(validate_source_inventory(inventory, taxonomy))
    effective = _parse_iso_date(taxonomy.get("skills_effective_date"))
    for index, raw_source in enumerate(inventory.get("sources", [])):
        if not isinstance(raw_source, Mapping):
            continue
        retrieved = _parse_iso_date(raw_source.get("retrieved_at"))
        if retrieved is None or (effective is not None and retrieved < effective):
            errors.append(
                _error(
                    "STALE_OR_MISSING_SOURCE_RETRIEVAL",
                    "Phase 3 source evidence must be retrieved on or after the active blueprint effective date",
                    index=index,
                    source_id=normalize_text(raw_source.get("source_id")),
                    retrieved_at=normalize_text(raw_source.get("retrieved_at")),
                )
            )
    return errors


def validate_phase3_set(
    questions: Sequence[Mapping[str, Any]],
    taxonomy: Mapping[str, Any],
    review_receipts: Sequence[Mapping[str, Any]],
    phase3_question_ids: Sequence[str],
    *,
    source_inventory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    approved = [row for row in questions if phase1_review_status(row) == "approved"]
    pending = [row for row in questions if phase1_review_status(row) == "pending"]
    withheld = [row for row in questions if phase1_review_status(row) == "withheld"]
    quality_errors: list[dict[str, Any]] = []

    ids = [normalize_text(row.get("id")) for row in approved]
    id_counts = Counter(ids)
    duplicate_ids = sorted(
        question_id
        for question_id, count in id_counts.items()
        if question_id and count > 1
    )
    if duplicate_ids:
        quality_errors.append(
            _error(
                "DUPLICATE_APPROVED_ID",
                "approved question IDs must be unique",
                ids=duplicate_ids,
            )
        )

    if len(approved) != 200:
        quality_errors.append(
            _error(
                "APPROVED_COUNT_MISMATCH",
                "Phase 3 requires exactly 200 approved cumulative questions",
                expected=200,
                actual=len(approved),
            )
        )
    if pending:
        quality_errors.append(
            _error(
                "PENDING_RECORDS_PRESENT",
                "Phase 3 terminal structural state requires zero pending cumulative questions",
                actual=len(pending),
            )
        )
    if withheld:
        quality_errors.append(
            _error(
                "WITHHELD_RECORDS_PRESENT",
                "Phase 3 terminal structural state requires zero withheld cumulative questions",
                actual=len(withheld),
            )
        )

    phase3_id_list = [
        normalize_text(value)
        for value in phase3_question_ids
        if normalize_text(value)
    ]
    phase3_id_set = set(phase3_id_list)
    if len(phase3_id_list) != 100 or len(phase3_id_set) != 100:
        quality_errors.append(
            _error(
                "PHASE3_BATCH_ID_SET_INVALID",
                "Phase 3 authored batches must identify exactly 100 unique question IDs",
                actual_rows=len(phase3_id_list),
                unique_ids=len(phase3_id_set),
            )
        )

    approved_id_set = {question_id for question_id in ids if question_id}
    phase3_new_approved_count = len(phase3_id_set & approved_id_set)
    if phase3_new_approved_count != 100:
        quality_errors.append(
            _error(
                "PHASE3_NEW_APPROVED_COUNT_MISMATCH",
                "Phase 3 requires exactly 100 newly approved Phase-3 questions",
                expected=100,
                actual=phase3_new_approved_count,
            )
        )

    domain_counts = dict(
        sorted(Counter(normalize_text(row.get("domain")) for row in approved).items())
    )
    objective_counts = dict(
        sorted(
            Counter(normalize_text(row.get("objective")) for row in approved).items()
        )
    )
    if domain_counts != EXPECTED_PHASE3_DOMAIN_COUNTS:
        quality_errors.append(
            _error(
                "DOMAIN_ALLOCATION_MISMATCH",
                "approved questions must match the frozen cumulative Phase-3 domain allocation",
                expected=EXPECTED_PHASE3_DOMAIN_COUNTS,
                actual=domain_counts,
            )
        )
    if objective_counts != EXPECTED_PHASE3_OBJECTIVE_COUNTS:
        quality_errors.append(
            _error(
                "OBJECTIVE_ALLOCATION_MISMATCH",
                "approved questions must match the frozen cumulative Phase-3 objective allocation",
                expected=EXPECTED_PHASE3_OBJECTIVE_COUNTS,
                actual=objective_counts,
            )
        )

    distinct_leaves = {
        normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id"))
        for row in approved
        if isinstance(row.get("metadata"), Mapping)
        and normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id"))
    }
    if len(distinct_leaves) != EXPECTED_BLUEPRINT_LEAF_COUNT:
        quality_errors.append(
            _error(
                "BLUEPRINT_LEAF_COVERAGE_MISMATCH",
                "all 58 SC-900 blueprint leaves must remain represented cumulatively",
                expected=EXPECTED_BLUEPRINT_LEAF_COUNT,
                actual=len(distinct_leaves),
            )
        )

    reviews, review_index_errors = _review_index(review_receipts)
    quality_errors.extend(review_index_errors)
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
                    "every approved cumulative question requires a review receipt",
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
        failed_checks = [
            field for field in REVIEW_CHECK_FIELDS if receipt.get(field) is not True
        ]
        if failed_checks:
            quality_errors.append(
                _error(
                    "REVIEW_RECEIPT_INCOMPLETE",
                    "review receipt is missing required affirmative checks",
                    question_id=question_id,
                    fields=failed_checks,
                )
            )
        if not normalize_text(receipt.get("reviewer")) or not normalize_text(
            receipt.get("reviewed_at")
        ):
            quality_errors.append(
                _error(
                    "REVIEW_CUSTODY_INCOMPLETE",
                    "review receipt must identify reviewer and reviewed_at",
                    question_id=question_id,
                )
            )
        if question_id in phase3_id_set:
            expected_hash = review_content_sha256(record)
            actual_hash = normalize_text(receipt.get("reviewed_content_sha256")).lower()
            if actual_hash != expected_hash:
                quality_errors.append(
                    _error(
                        "REVIEW_CONTENT_HASH_MISMATCH",
                        "Phase-3 review receipt is not bound to the exact reviewed question content",
                        question_id=question_id,
                        expected=expected_hash,
                        actual=actual_hash,
                    )
                )

    source_inventory_errors: list[dict[str, Any]] = []
    if source_inventory is not None:
        source_inventory_errors.extend(
            validate_phase3_source_inventory(source_inventory, taxonomy)
        )
        phase3_questions = [
            row
            for row in approved
            if normalize_text(row.get("id")) in phase3_id_set
        ]
        source_inventory_errors.extend(
            validate_question_source_links(phase3_questions, source_inventory)
        )
        quality_errors.extend(source_inventory_errors)

    status = "PHASE_3_TASK12_READY" if not quality_errors else "PHASE_3_INCOMPLETE"
    return {
        "status": status,
        "approved_count": len(approved),
        "phase3_new_approved_count": phase3_new_approved_count,
        "pending_count": len(pending),
        "withheld_count": len(withheld),
        "domain_counts": domain_counts,
        "objective_counts": objective_counts,
        "distinct_leaf_count": len(distinct_leaves),
        "source_inventory_errors": source_inventory_errors,
        "quality_errors": quality_errors,
        "cand01_gate2_status": "GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE",
        "implementation_authorized": False,
    }
