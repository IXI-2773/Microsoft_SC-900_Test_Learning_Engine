from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from ingestion.bank_quality import phase1_review_status, validate_phase1_question
from ingestion.models import ValidationError, normalize_text
from tools.build_sc900_phase2 import review_content_sha256
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS, validate_source_inventory
from tools.validate_sc900_phase2 import (
    validate_question_source_links,
)
from tools.validate_sc900_phase2 import (
    validate_train_probe_manifest as validate_phase2_train_probe_manifest,
)

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


def validate_phase3_source_inventory(inventory: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> list[dict[str, Any]]:
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
    duplicate_ids = sorted(question_id for question_id, count in id_counts.items() if question_id and count > 1)
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

    phase3_id_list = [normalize_text(value) for value in phase3_question_ids if normalize_text(value)]
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

    domain_counts = dict(sorted(Counter(normalize_text(row.get("domain")) for row in approved).items()))
    objective_counts = dict(sorted(Counter(normalize_text(row.get("objective")) for row in approved).items()))
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
                quality_errors.append(_error(issue["code"], issue["message"], question_id=question_id))

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
        source_inventory_errors.extend(validate_phase3_source_inventory(source_inventory, taxonomy))
        phase3_questions = [row for row in approved if normalize_text(row.get("id")) in phase3_id_set]
        source_inventory_errors.extend(validate_question_source_links(phase3_questions, source_inventory))
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


PHASE3_MANIFEST_SCHEMA_VERSION = "sc900.phase3.train-probe-manifest/v1"
PHASE2_ITEM_SCHEMA_VERSION = "sc900.train-probe-manifest/v1"
PHASE3_MANIFEST_VERSION = PHASE3_MANIFEST_SCHEMA_VERSION
FAMILY_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
UNRESOLVED_FAMILY_STATES = {"unresolved", "unknown", "disputed", "needs_review", ""}
PHASE2_ITEM_FIELDS = {
    "assignment_rationale",
    "assignment_receipt",
    "blueprint_version",
    "family_state",
    "future_probe_suitability",
    "promotion_status",
    "question_id",
    "role",
    "semantic_family_id",
    "source_family_id",
}
PHASE2_RECEIPT_FIELDS = {"override_type", "prior_family_ids", "reviewed_at", "reviewer"}
PHASE3_ITEM_FIELDS = PHASE2_ITEM_FIELDS | {"assignment_evidence"}
PHASE3_ASSIGNMENT_EVIDENCE_FIELDS = {
    "approved_state_checked",
    "assigned_at",
    "assignment_method",
    "assignment_reason",
    "family_isolation_checked",
    "family_resolved_checked",
    "partition_epoch",
    "probe_suitability_checked",
    "question_id",
    "role",
    "semantic_family_id",
    "source_task4_audit_hash",
    "source_task5_store_hash",
}
PHASE3_FAMILY_ASSIGNMENT_FIELDS = {
    "approved_state_checked",
    "assignment_method",
    "assignment_reason",
    "family_isolation_checked",
    "family_resolved_checked",
    "family_state",
    "member_count",
    "member_ids",
    "partition_epoch",
    "probe_suitability_checked",
    "role",
    "semantic_family_id",
    "source_task4_audit_hash",
    "source_task5_store_hash",
    "transfer_edge_isolation_checked",
}
PHASE3_MANIFEST_FIELDS = {
    "all_path_leakage_handoff",
    "allocation_report",
    "blueprint_version",
    "cand01_gate2_status",
    "compiled_sha256",
    "design_time_only",
    "family_assignments",
    "implementation_authorized",
    "inherited_item_schema",
    "items",
    "manifest_version",
    "partition_epoch",
    "phase_3_structurally_accepted",
    "question_count",
    "runtime_consumer_authorized",
    "schema_version",
    "semantic_audit_sha256",
    "semantic_family_count",
    "store_sha256",
    "work_id",
}
PHASE3_MANIFEST_REQUIRED = set(PHASE3_MANIFEST_FIELDS)
ALLOCATION_REPORT_REQUIRED = {
    "objectives_absent_from_probe",
    "probe",
    "train",
    "transfer_edge_isolation",
    "unassigned",
}
ALLOCATION_ROLE_REQUIRED = {
    "domain_counts",
    "family_count",
    "family_ids",
    "leaf_coverage",
    "objective_counts",
    "probe_eligible_count",
    "question_count",
}
ALLOCATION_PROBE_REQUIRED = ALLOCATION_ROLE_REQUIRED | {
    "effective_independent_family_count",
    "largest_family_size",
    "smallest_family_size",
}
TRANSFER_ISOLATION_REQUIRED = {"cross_family_edges", "train_probe_crossings"}
ALL_PATH_REQUIRED = {
    "contract",
    "design_time_only",
    "invariants",
    "paths_requiring_future_guards",
    "runtime_consumer_authorized",
}


def _phase2_projection(manifest: Mapping[str, Any]) -> dict[str, Any]:
    raw_items = manifest.get("items")
    items: list[Any] = []
    if isinstance(raw_items, list):
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                items.append(raw)
                continue
            item = {field: raw[field] for field in PHASE2_ITEM_FIELDS if field in raw}
            receipt = raw.get("assignment_receipt")
            if isinstance(receipt, Mapping):
                item["assignment_receipt"] = {
                    field: receipt[field] for field in PHASE2_RECEIPT_FIELDS if field in receipt
                }
            items.append(item)
    projection: dict[str, Any] = {
        "schema_version": PHASE2_ITEM_SCHEMA_VERSION,
        "items": items,
    }
    if "partition_epoch" in manifest:
        projection["partition_epoch"] = manifest.get("partition_epoch")
    if "blueprint_version" in manifest:
        projection["blueprint_version"] = manifest.get("blueprint_version")
    return projection


def _family_index(audit: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    if not isinstance(audit, Mapping):
        return index
    families = audit.get("families")
    if not isinstance(families, list):
        return index
    for row in families:
        if not isinstance(row, Mapping):
            continue
        family_id = normalize_text(row.get("semantic_family_id"))
        if family_id:
            index[family_id] = row
    return index


def validate_phase3_train_probe_manifest(
    manifest: Mapping[str, Any],
    *,
    questions: Sequence[Mapping[str, Any]] | None = None,
    audit: Mapping[str, Any] | None = None,
    expected_audit_sha256: str | None = None,
    expected_store_sha256: str | None = None,
    expected_compiled_sha256: str | None = None,
    expected_family_count: int = 27,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(manifest, Mapping):
        return [_error("MALFORMED_MANIFEST", "manifest must be an object")]

    for field in sorted(set(manifest) - PHASE3_MANIFEST_FIELDS):
        errors.append(
            _error(
                "UNEXPECTED_MANIFEST_FIELD",
                "manifest contains a field forbidden by the published Phase-3 schema",
                field=field,
            )
        )
    for field in sorted(PHASE3_MANIFEST_REQUIRED - set(manifest)):
        if field == "partition_epoch":
            errors.append(_error("MISSING_PARTITION_EPOCH", "manifest partition_epoch is required"))
        elif field == "allocation_report":
            errors.append(
                _error(
                    "INCOMPLETE_ALLOCATION_REPORT",
                    "allocation_report is required",
                    field=field,
                )
            )
        else:
            errors.append(
                _error(
                    "MISSING_MANIFEST_FIELD",
                    "required Phase-3 manifest field is missing",
                    field=field,
                )
            )

    schema_version = normalize_text(manifest.get("schema_version"))
    if schema_version and schema_version != PHASE3_MANIFEST_SCHEMA_VERSION:
        errors.append(
            _error(
                "INVALID_MANIFEST_SCHEMA_VERSION",
                "manifest schema_version must match the Phase-3 TRAIN/PROBE contract",
                expected=PHASE3_MANIFEST_SCHEMA_VERSION,
                actual=schema_version,
            )
        )
    inherited = normalize_text(manifest.get("inherited_item_schema"))
    if inherited and inherited != PHASE2_ITEM_SCHEMA_VERSION:
        errors.append(
            _error(
                "INVALID_INHERITED_ITEM_SCHEMA",
                "inherited_item_schema must remain the Phase-2 item contract",
                expected=PHASE2_ITEM_SCHEMA_VERSION,
                actual=inherited,
            )
        )

    partition_epoch = normalize_text(manifest.get("partition_epoch"))
    if "partition_epoch" in manifest and not partition_epoch:
        errors.append(_error("MISSING_PARTITION_EPOCH", "manifest partition_epoch is required"))

    if manifest.get("design_time_only") is not True:
        errors.append(_error("DESIGN_TIME_ONLY_REQUIRED", "design_time_only must be true"))
    if manifest.get("runtime_consumer_authorized") is not False:
        errors.append(
            _error(
                "RUNTIME_CONSUMER_MUST_BE_UNAUTHORIZED",
                "runtime_consumer_authorized must be false",
            )
        )
    if manifest.get("implementation_authorized") is not False:
        errors.append(
            _error(
                "IMPLEMENTATION_MUST_BE_UNAUTHORIZED",
                "implementation_authorized must be false",
            )
        )
    if manifest.get("phase_3_structurally_accepted") is not False:
        errors.append(
            _error(
                "PHASE3_MUST_NOT_BE_STRUCTURALLY_ACCEPTED",
                "phase_3_structurally_accepted must be false",
            )
        )

    manifest_audit_hash = normalize_text(manifest.get("semantic_audit_sha256")).lower()
    manifest_store_hash = normalize_text(manifest.get("store_sha256")).lower()
    manifest_compiled_hash = normalize_text(manifest.get("compiled_sha256")).lower()
    if expected_audit_sha256 and manifest_audit_hash != expected_audit_sha256.lower():
        errors.append(
            _error(
                "SEMANTIC_AUDIT_HASH_MISMATCH",
                "manifest semantic_audit_sha256 does not match the frozen Task-4 audit",
                expected=expected_audit_sha256.lower(),
                actual=manifest_audit_hash,
            )
        )
    if expected_store_sha256 and manifest_store_hash != expected_store_sha256.lower():
        errors.append(
            _error(
                "STORE_HASH_MISMATCH",
                "manifest store_sha256 does not match the frozen Task-5 candidate store",
                expected=expected_store_sha256.lower(),
                actual=manifest_store_hash,
            )
        )
    if expected_compiled_sha256 and manifest_compiled_hash != expected_compiled_sha256.lower():
        errors.append(
            _error(
                "COMPILED_HASH_MISMATCH",
                "manifest compiled_sha256 does not match the frozen Task-5 compiled bank",
                expected=expected_compiled_sha256.lower(),
                actual=manifest_compiled_hash,
            )
        )

    family_assignments = manifest.get("family_assignments")
    assignment_index: dict[str, Mapping[str, Any]] = {}
    if not isinstance(family_assignments, list):
        errors.append(
            _error(
                "INVALID_FAMILY_ASSIGNMENTS_TYPE",
                "family_assignments must be an array",
            )
        )
        family_assignments = []
    for index, row in enumerate(family_assignments):
        if not isinstance(row, Mapping):
            errors.append(
                _error(
                    "MALFORMED_FAMILY_ASSIGNMENT",
                    "family assignment must be an object",
                    index=index,
                )
            )
            continue
        for field in sorted(set(row) - PHASE3_FAMILY_ASSIGNMENT_FIELDS):
            errors.append(
                _error(
                    "UNEXPECTED_FAMILY_ASSIGNMENT_FIELD",
                    "family assignment contains a field forbidden by the published schema",
                    index=index,
                    field=field,
                )
            )
        family_id = normalize_text(row.get("semantic_family_id"))
        if not family_id:
            errors.append(
                _error(
                    "MALFORMED_SEMANTIC_FAMILY_ID",
                    "family assignment semantic_family_id is required",
                    index=index,
                )
            )
        elif not FAMILY_ID_RE.fullmatch(family_id):
            errors.append(
                _error(
                    "MALFORMED_SEMANTIC_FAMILY_ID",
                    "semantic_family_id must be a lowercase snake-case identifier",
                    semantic_family_id=family_id,
                )
            )
        elif family_id in assignment_index:
            errors.append(
                _error(
                    "DUPLICATE_FAMILY_ASSIGNMENT",
                    "family assignments must be unique by semantic_family_id",
                    semantic_family_id=family_id,
                )
            )
        else:
            assignment_index[family_id] = row
        row_epoch = normalize_text(row.get("partition_epoch"))
        if partition_epoch and row_epoch and row_epoch != partition_epoch:
            errors.append(
                _error(
                    "INCONSISTENT_PARTITION_EPOCH",
                    "family assignment partition_epoch must match the manifest epoch",
                    semantic_family_id=family_id,
                    expected=partition_epoch,
                    actual=row_epoch,
                )
            )

    items = manifest.get("items") if isinstance(manifest.get("items"), list) else []
    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, Mapping):
            continue
        for field in sorted(set(raw_item) - PHASE3_ITEM_FIELDS):
            errors.append(
                _error(
                    "UNEXPECTED_MANIFEST_ITEM_FIELD",
                    "manifest item contains a field forbidden by the published Phase-3 schema",
                    index=index,
                    field=field,
                )
            )
        family_id = normalize_text(raw_item.get("semantic_family_id"))
        if family_id and not FAMILY_ID_RE.fullmatch(family_id):
            errors.append(
                _error(
                    "MALFORMED_SEMANTIC_FAMILY_ID",
                    "semantic_family_id must be a lowercase snake-case identifier",
                    question_id=normalize_text(raw_item.get("question_id")),
                    semantic_family_id=family_id,
                )
            )
        evidence = raw_item.get("assignment_evidence")
        if not isinstance(evidence, Mapping):
            errors.append(
                _error(
                    "MISSING_ASSIGNMENT_EVIDENCE",
                    "assignment_evidence must be an object",
                    question_id=normalize_text(raw_item.get("question_id")),
                )
            )
        else:
            for field in sorted(set(evidence) - PHASE3_ASSIGNMENT_EVIDENCE_FIELDS):
                errors.append(
                    _error(
                        "UNEXPECTED_ASSIGNMENT_EVIDENCE_FIELD",
                        "assignment_evidence contains a field forbidden by the published schema",
                        question_id=normalize_text(raw_item.get("question_id")),
                        field=field,
                    )
                )
            evidence_epoch = normalize_text(evidence.get("partition_epoch")) or normalize_text(
                evidence.get("assigned_at")
            )
            if partition_epoch and evidence_epoch and evidence_epoch != partition_epoch:
                errors.append(
                    _error(
                        "INCONSISTENT_PARTITION_EPOCH",
                        "item assignment evidence partition_epoch must match the manifest epoch",
                        question_id=normalize_text(raw_item.get("question_id")),
                        expected=partition_epoch,
                        actual=evidence_epoch,
                    )
                )
        family_row = assignment_index.get(family_id)
        item_role = normalize_text(raw_item.get("role")).upper()
        if family_row is not None:
            family_role = normalize_text(family_row.get("role")).upper()
            if family_role and item_role and family_role != item_role:
                errors.append(
                    _error(
                        "FAMILY_ROLE_ITEM_ROLE_MISMATCH",
                        "item role must inherit the whole-family role",
                        question_id=normalize_text(raw_item.get("question_id")),
                        semantic_family_id=family_id,
                        family_role=family_role,
                        item_role=item_role,
                    )
                )

    errors.extend(validate_phase2_train_probe_manifest(_phase2_projection(manifest)))

    allocation_report = manifest.get("allocation_report")
    if "allocation_report" in manifest and not isinstance(allocation_report, Mapping):
        errors.append(_error("INCOMPLETE_ALLOCATION_REPORT", "allocation_report must be an object"))
        allocation_report = {}
    elif isinstance(allocation_report, Mapping):
        missing_report_fields = sorted(ALLOCATION_REPORT_REQUIRED - set(allocation_report))
        if missing_report_fields:
            errors.append(
                _error(
                    "INCOMPLETE_ALLOCATION_REPORT",
                    "allocation_report is missing required sections",
                    fields=missing_report_fields,
                )
            )
        for role, required_fields in (
            ("train", ALLOCATION_ROLE_REQUIRED),
            ("unassigned", ALLOCATION_ROLE_REQUIRED),
            ("probe", ALLOCATION_PROBE_REQUIRED),
        ):
            section = allocation_report.get(role)
            if not isinstance(section, Mapping):
                if role in allocation_report or role in ALLOCATION_REPORT_REQUIRED:
                    errors.append(
                        _error(
                            "INCOMPLETE_ALLOCATION_REPORT",
                            "allocation_report role section must be an object",
                            role=role,
                        )
                    )
                continue
            missing_role_fields = sorted(required_fields - set(section))
            if missing_role_fields:
                errors.append(
                    _error(
                        "INCOMPLETE_ALLOCATION_REPORT",
                        "allocation_report role section is missing required fields",
                        role=role,
                        fields=missing_role_fields,
                    )
                )
        isolation = allocation_report.get("transfer_edge_isolation")
        if isinstance(isolation, Mapping):
            missing_isolation = sorted(TRANSFER_ISOLATION_REQUIRED - set(isolation))
            if missing_isolation:
                errors.append(
                    _error(
                        "INCOMPLETE_ALLOCATION_REPORT",
                        "transfer_edge_isolation is missing required fields",
                        fields=missing_isolation,
                    )
                )

    handoff = manifest.get("all_path_leakage_handoff")
    if "all_path_leakage_handoff" in manifest:
        if not isinstance(handoff, Mapping):
            errors.append(
                _error(
                    "INCOMPLETE_ALL_PATH_LEAKAGE_HANDOFF",
                    "all_path_leakage_handoff must be an object",
                )
            )
        else:
            missing_handoff = sorted(ALL_PATH_REQUIRED - set(handoff))
            if missing_handoff:
                errors.append(
                    _error(
                        "INCOMPLETE_ALL_PATH_LEAKAGE_HANDOFF",
                        "all_path_leakage_handoff is missing required fields",
                        fields=missing_handoff,
                    )
                )

    question_index = {
        normalize_text(row.get("id")): row
        for row in (questions or [])
        if isinstance(row, Mapping) and normalize_text(row.get("id"))
    }
    assigned_ids: list[str] = []
    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        question_id = normalize_text(raw_item.get("question_id"))
        if question_id:
            assigned_ids.append(question_id)
            if question_index and question_id not in question_index:
                errors.append(
                    _error(
                        "UNKNOWN_QUESTION_ID",
                        "manifest question_id is not present in the candidate store",
                        question_id=question_id,
                    )
                )
            elif question_index:
                record = question_index[question_id]
                actual_status = normalize_text(record.get("promotion_status")).lower()
                item_status = normalize_text(raw_item.get("promotion_status")).lower()
                if actual_status and item_status and actual_status != item_status:
                    errors.append(
                        _error(
                            "PROMOTION_STATUS_STORE_MISMATCH",
                            "manifest promotion_status must match the candidate store",
                            question_id=question_id,
                            store_status=actual_status,
                            manifest_status=item_status,
                        )
                    )
    if question_index:
        for question_id in sorted(set(question_index) - set(assigned_ids)):
            errors.append(
                _error(
                    "MISSING_QUESTION_ASSIGNMENT",
                    "every store question requires exactly one partition assignment",
                    question_id=question_id,
                )
            )

    families = _family_index(audit)
    family_count = len(families)
    reported_family_count = manifest.get("semantic_family_count")
    if family_count and family_count != expected_family_count:
        errors.append(
            _error(
                "SEMANTIC_FAMILY_COUNT_MISMATCH",
                "semantic family count must match the frozen Task-4 27-family authority",
                expected=expected_family_count,
                actual=family_count,
            )
        )
    elif reported_family_count is not None and reported_family_count != expected_family_count:
        errors.append(
            _error(
                "SEMANTIC_FAMILY_COUNT_MISMATCH",
                "semantic family count must match the frozen Task-4 27-family authority",
                expected=expected_family_count,
                actual=reported_family_count,
            )
        )
    if families:
        for family_id, row in assignment_index.items():
            audit_family = families.get(family_id)
            if audit_family is None:
                errors.append(
                    _error(
                        "UNKNOWN_SEMANTIC_FAMILY_ID",
                        "family assignment is not present in the Task-4 audit",
                        semantic_family_id=family_id,
                    )
                )
                continue
            audit_state = normalize_text(audit_family.get("family_state")).lower()
            role = normalize_text(row.get("role")).upper()
            if audit_state in UNRESOLVED_FAMILY_STATES and role == "TRAIN":
                errors.append(
                    _error(
                        "TRAIN_REQUIRES_RESOLVED_FAMILY",
                        "TRAIN assignment requires resolved semantic-family membership",
                        semantic_family_id=family_id,
                        family_state=audit_state,
                    )
                )
            if audit_state in UNRESOLVED_FAMILY_STATES and role == "PROBE":
                errors.append(
                    _error(
                        "PROBE_REQUIRES_RESOLVED_FAMILY",
                        "PROBE assignment requires resolved semantic-family membership",
                        semantic_family_id=family_id,
                        family_state=audit_state,
                    )
                )
        for family_id in sorted(set(families) - set(assignment_index)):
            errors.append(
                _error(
                    "MISSING_FAMILY_ASSIGNMENT",
                    "every Task-4 family requires a whole-family partition role",
                    semantic_family_id=family_id,
                )
            )

        item_roles = {
            normalize_text(raw_item.get("question_id")): normalize_text(raw_item.get("role")).upper()
            for raw_item in items
            if isinstance(raw_item, Mapping) and normalize_text(raw_item.get("question_id"))
        }
        member_family = {}
        for family_id, row in families.items():
            members = row.get("members")
            if not isinstance(members, list):
                continue
            for member in members:
                member_id = normalize_text(member)
                if member_id:
                    member_family[member_id] = family_id
        transfer_edges = audit.get("transfer_edges") if isinstance(audit.get("transfer_edges"), list) else []
        for edge in transfer_edges:
            if not isinstance(edge, Mapping):
                continue
            left = normalize_text(edge.get("left"))
            right = normalize_text(edge.get("right"))
            left_role = item_roles.get(left)
            right_role = item_roles.get(right)
            if {left_role, right_role} == {"TRAIN", "PROBE"}:
                errors.append(
                    _error(
                        "TRAIN_PROBE_TRANSFER_EDGE_CROSSING",
                        "a known transfer edge cannot connect TRAIN and PROBE",
                        left=left,
                        right=right,
                        left_role=left_role,
                        right_role=right_role,
                        left_family=member_family.get(left),
                        right_family=member_family.get(right),
                    )
                )

    return errors
