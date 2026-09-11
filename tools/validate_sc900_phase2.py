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
from tools.build_sc900_phase2 import BUILD_RECEIPT_PATH, DEFAULT_BANK, SEMANTIC_AUDIT_PATH, review_content_sha256, sha256_file

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
MANIFEST_SCHEMA_VERSION = "sc900.train-probe-manifest/v1"


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

    if pending:
        quality_errors.append(
            _error(
                "PENDING_RECORDS_PRESENT",
                "Phase 2 terminal acceptance requires zero pending cumulative questions",
                actual=len(pending),
            )
        )
    if withheld:
        quality_errors.append(
            _error(
                "WITHHELD_RECORDS_PRESENT",
                "Phase 2 terminal acceptance requires zero withheld cumulative questions",
                actual=len(withheld),
            )
        )

    phase2_id_list = [normalize_text(value) for value in phase2_question_ids if normalize_text(value)]
    phase2_id_set = set(phase2_id_list)
    if len(phase2_id_list) != 50 or len(phase2_id_set) != 50:
        quality_errors.append(
            _error(
                "PHASE2_BATCH_ID_SET_INVALID",
                "Phase 2 authored batches must contain exactly 50 unique question IDs",
                actual_rows=len(phase2_id_list),
                unique_ids=len(phase2_id_set),
            )
        )
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
    manifest_fields = {"schema_version", "partition_epoch", "blueprint_version", "items"}
    item_fields = {
        "question_id",
        "semantic_family_id",
        "source_family_id",
        "role",
        "promotion_status",
        "future_probe_suitability",
        "family_state",
        "assignment_rationale",
        "assignment_receipt",
        "blueprint_version",
    }
    receipt_fields = {"override_type", "prior_family_ids", "reviewed_at", "reviewer"}
    promotion_statuses = {"approved", "pending", "withheld"}
    probe_suitabilities = {"eligible", "train_only", "needs_review"}
    family_states = {"resolved", "unknown", "disputed", "needs_review"}
    override_types = {"none", "family_merge", "family_split", "role_change"}

    for field in sorted(set(manifest) - manifest_fields):
        errors.append(
            _error(
                "UNEXPECTED_MANIFEST_FIELD",
                "manifest contains a field forbidden by the published schema",
                field=field,
            )
        )

    schema_version = normalize_text(manifest.get("schema_version"))
    if not schema_version:
        errors.append(_error("MISSING_MANIFEST_SCHEMA_VERSION", "manifest schema_version is required"))
    elif schema_version != MANIFEST_SCHEMA_VERSION:
        errors.append(
            _error(
                "INVALID_MANIFEST_SCHEMA_VERSION",
                "manifest schema_version must match the frozen Phase-2 contract",
                expected=MANIFEST_SCHEMA_VERSION,
                actual=schema_version,
            )
        )
    if not normalize_text(manifest.get("partition_epoch")):
        errors.append(_error("MISSING_PARTITION_EPOCH", "manifest partition_epoch is required"))
    if not normalize_text(manifest.get("blueprint_version")):
        errors.append(_error("MISSING_MANIFEST_BLUEPRINT_VERSION", "manifest blueprint_version is required"))

    if "items" not in manifest:
        errors.append(_error("MISSING_MANIFEST_ITEMS", "manifest items is required"))
        items: list[Any] = []
    else:
        raw_items = manifest.get("items")
        if not isinstance(raw_items, list):
            errors.append(
                _error("INVALID_MANIFEST_ITEMS_TYPE", "manifest items must be an array")
            )
            items = []
        else:
            items = raw_items
    seen_ids: set[str] = set()
    roles_by_family: dict[str, set[str]] = defaultdict(set)

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, Mapping):
            errors.append(
                _error(
                    "MALFORMED_MANIFEST_ITEM",
                    "manifest item must be an object",
                    index=index,
                )
            )
            continue

        for field in sorted(set(raw_item) - item_fields):
            errors.append(
                _error(
                    "UNEXPECTED_MANIFEST_ITEM_FIELD",
                    "manifest item contains a field forbidden by the published schema",
                    index=index,
                    field=field,
                )
            )

        question_id = normalize_text(raw_item.get("question_id"))
        semantic_family_id = normalize_text(raw_item.get("semantic_family_id"))
        source_family_id = normalize_text(raw_item.get("source_family_id"))
        role = normalize_text(raw_item.get("role")).upper()
        promotion_status = normalize_text(raw_item.get("promotion_status")).lower()
        probe_suitability = normalize_text(raw_item.get("future_probe_suitability"))
        family_state = normalize_text(raw_item.get("family_state")).lower()
        blueprint_version = normalize_text(raw_item.get("blueprint_version"))
        assignment_rationale = normalize_text(raw_item.get("assignment_rationale"))
        assignment_receipt = raw_item.get("assignment_receipt")

        if promotion_status not in promotion_statuses:
            errors.append(
                _error(
                    "INVALID_PROMOTION_STATUS",
                    "promotion_status must be approved, pending, or withheld",
                    question_id=question_id,
                    promotion_status=promotion_status,
                )
            )
        if probe_suitability not in probe_suitabilities:
            errors.append(
                _error(
                    "INVALID_PROBE_SUITABILITY",
                    "future_probe_suitability must match the published schema enum",
                    question_id=question_id,
                    future_probe_suitability=probe_suitability,
                )
            )
        if family_state not in family_states:
            errors.append(
                _error(
                    "INVALID_FAMILY_STATE",
                    "family_state must match the published schema enum",
                    question_id=question_id,
                    family_state=family_state,
                )
            )

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
        if not blueprint_version:
            errors.append(_error("MISSING_ITEM_BLUEPRINT_VERSION", "item blueprint_version is required", question_id=question_id))
        if not assignment_rationale:
            errors.append(_error("MISSING_ASSIGNMENT_RATIONALE", "assignment_rationale is required", question_id=question_id))
        if not isinstance(assignment_receipt, Mapping):
            errors.append(
                _error(
                    "MISSING_ASSIGNMENT_RECEIPT",
                    "assignment_receipt must be an object",
                    question_id=question_id,
                )
            )
        else:
            for field in sorted(set(assignment_receipt) - receipt_fields):
                errors.append(
                    _error(
                        "UNEXPECTED_ASSIGNMENT_RECEIPT_FIELD",
                        "assignment_receipt contains a field forbidden by the published schema",
                        question_id=question_id,
                        field=field,
                    )
                )
            if not normalize_text(assignment_receipt.get("reviewer")) or not normalize_text(
                assignment_receipt.get("reviewed_at")
            ):
                errors.append(
                    _error(
                        "INCOMPLETE_ASSIGNMENT_RECEIPT",
                        "assignment_receipt requires reviewer and reviewed_at",
                        question_id=question_id,
                    )
                )
            if "override_type" in assignment_receipt:
                override_type = normalize_text(assignment_receipt.get("override_type")).lower()
                if override_type not in override_types:
                    errors.append(
                        _error(
                            "INVALID_ASSIGNMENT_OVERRIDE_TYPE",
                            "assignment_receipt override_type must match the published schema enum",
                            question_id=question_id,
                            override_type=override_type,
                        )
                    )
            if "prior_family_ids" in assignment_receipt:
                prior_family_ids = assignment_receipt.get("prior_family_ids")
                valid_prior_ids = (
                    isinstance(prior_family_ids, list)
                    and all(
                        isinstance(value, str) and bool(value)
                        for value in prior_family_ids
                    )
                    and len(prior_family_ids) == len(set(prior_family_ids))
                )
                if not valid_prior_ids:
                    errors.append(
                        _error(
                            "INVALID_PRIOR_FAMILY_IDS",
                            "assignment_receipt prior_family_ids must be an array of unique non-empty strings",
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

        if role == "TRAIN":
            if promotion_status != "approved":
                errors.append(_error("TRAIN_REQUIRES_APPROVED", "TRAIN assignment requires approved content", question_id=question_id))
            if family_state != RESOLVED_FAMILY_STATE:
                errors.append(_error("TRAIN_REQUIRES_RESOLVED_FAMILY", "TRAIN assignment requires resolved semantic-family membership", question_id=question_id, family_state=family_state))

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


def _load_phase2_records(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for batch_path in sorted(path.glob("*.jsonl")):
        for line in batch_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def validate_phase2_review_custody(
    records: Sequence[Mapping[str, Any]], review_receipts: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    reviews = _review_index(review_receipts)
    ids = [normalize_text(row.get("id")) for row in records]
    if len(ids) != 50 or len(set(ids)) != 50:
        errors.append(_error("REVIEW_CUSTODY_INPUT_SET_INVALID", "custody verification requires exactly 50 unique Phase-2 authored records"))
    for record in records:
        qid = normalize_text(record.get("id"))
        receipt = reviews.get(qid)
        if receipt is None:
            errors.append(_error("MISSING_PHASE2_REVIEW_CUSTODY", "Phase-2 authored record lacks a review receipt", question_id=qid))
            continue
        expected = review_content_sha256(record)
        actual = normalize_text(receipt.get("reviewed_content_sha256")).lower()
        if actual != expected:
            errors.append(_error("REVIEW_CONTENT_HASH_MISMATCH", "review receipt is not bound to the authored question content", question_id=qid, expected=expected, actual=actual))
    return errors


def validate_question_source_links(questions: Sequence[Mapping[str, Any]], inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    by_url: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for source in inventory.get("sources", []):
        if isinstance(source, Mapping) and normalize_text(source.get("url")):
            by_url[normalize_text(source.get("url"))].append(source)
    for record in questions:
        if phase1_review_status(record) != "approved":
            continue
        qid = normalize_text(record.get("id"))
        objective = normalize_text(record.get("objective"))
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        leaf = normalize_text(metadata.get("blueprint_leaf_id"))
        urls = {normalize_text(value) for value in record.get("references", []) if normalize_text(value)}
        urls.update(normalize_text(value) for value in metadata.get("source_urls", []) if normalize_text(value))
        if not urls:
            errors.append(_error("QUESTION_SOURCE_LINK_MISSING", "approved question has no source URL to join to inventory", question_id=qid))
            continue
        for url in sorted(urls):
            candidates = by_url.get(url, [])
            if not candidates:
                errors.append(_error("QUESTION_SOURCE_NOT_IN_INVENTORY", "approved question source URL is absent from source inventory", question_id=qid, url=url))
                continue
            if not any(objective in set(source.get("objective_ids", [])) and leaf in set(source.get("leaf_ids", [])) for source in candidates):
                errors.append(_error("QUESTION_SOURCE_SCOPE_MISMATCH", "source inventory entry does not claim the question objective and blueprint leaf", question_id=qid, url=url, objective=objective, leaf=leaf))
    return errors


def validate_semantic_audit(questions: Sequence[Mapping[str, Any]], audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    approved = [row for row in questions if phase1_review_status(row) == "approved"]
    decisions = {normalize_text(row.get("question_id")): row for row in audit.get("decisions", []) if isinstance(row, Mapping)}
    approved_ids = {normalize_text(row.get("id")) for row in approved}
    if set(decisions) != approved_ids:
        errors.append(_error("SEMANTIC_AUDIT_COVERAGE_MISMATCH", "semantic-family audit must cover exactly every approved cumulative question", expected=len(approved_ids), actual=len(decisions)))
        return errors
    for record in approved:
        qid = normalize_text(record.get("id"))
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        actual_family = normalize_text(metadata.get("semantic_family_id"))
        expected_family = normalize_text(decisions[qid].get("semantic_family_id"))
        if not expected_family or actual_family != expected_family:
            errors.append(_error("SEMANTIC_AUDIT_STORE_MISMATCH", "canonical store family does not match audited family assignment", question_id=qid, expected=expected_family, actual=actual_family))
    reported_count = audit.get("family_count")
    actual_count = len({normalize_text(row.get("semantic_family_id")) for row in decisions.values()})
    if reported_count != actual_count:
        errors.append(_error("SEMANTIC_AUDIT_COUNT_MISMATCH", "semantic audit family_count is inconsistent", expected=actual_count, actual=reported_count))
    return errors


def validate_build_receipt(store_dir: Path, compiled_path: Path, receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if normalize_text(receipt.get("status")) != "REPRODUCIBLE":
        errors.append(_error("BUILD_RECEIPT_NOT_REPRODUCIBLE", "Phase-2 build receipt must declare REPRODUCIBLE"))
        return errors
    outputs = receipt.get("outputs") if isinstance(receipt.get("outputs"), Mapping) else {}
    store_hashes = outputs.get("store") if isinstance(outputs.get("store"), Mapping) else {}
    for name in ("questions.json", "source_material.json", "quarantine.json", "review.json", "review_decisions.json"):
        file_path = store_dir / name
        expected = normalize_text(store_hashes.get(name)).lower()
        actual = sha256_file(file_path) if file_path.exists() else ""
        if expected != actual:
            errors.append(_error("BUILD_STORE_HASH_MISMATCH", "committed store artifact differs from build receipt", file=name, expected=expected, actual=actual))
    expected_compiled = normalize_text(outputs.get("compiled_sha256")).lower()
    actual_compiled = sha256_file(compiled_path) if compiled_path.exists() else ""
    if expected_compiled != actual_compiled:
        errors.append(_error("BUILD_COMPILED_HASH_MISMATCH", "compiled candidate differs from build receipt", expected=expected_compiled, actual=actual_compiled))
    expected_default = normalize_text(outputs.get("default_launch_bank_sha256")).lower()
    actual_default = sha256_file(DEFAULT_BANK) if DEFAULT_BANK.exists() else ""
    if expected_default != actual_default:
        errors.append(_error("DEFAULT_BANK_HASH_MISMATCH", "default launch bank changed relative to Phase-2 build receipt", expected=expected_default, actual=actual_default))
    if receipt.get("pending_before_approval_count") != 50 or receipt.get("approved_after_review_count") != 100:
        errors.append(_error("BUILD_CUSTODY_COUNTS_INVALID", "build receipt does not prove 50 pending imports followed by 100 cumulative approvals"))
    return errors


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
    phase2_records = _load_phase2_records(args.phase2_batches)
    phase2_ids = [normalize_text(row.get("id")) for row in phase2_records]
    inventory = _load_json(args.source_inventory, {})
    if not isinstance(inventory, Mapping):
        inventory = {}

    source_errors = validate_source_inventory(inventory, taxonomy)
    source_errors.extend(validate_question_source_links(questions, inventory))
    result = validate_phase2_set(questions, taxonomy, reviews, phase2_ids)
    review_custody_errors = validate_phase2_review_custody(phase2_records, reviews)
    semantic_audit = _load_json(SEMANTIC_AUDIT_PATH, {})
    if not isinstance(semantic_audit, Mapping):
        semantic_audit = {}
    semantic_audit_errors = validate_semantic_audit(questions, semantic_audit)
    build_receipt = _load_json(BUILD_RECEIPT_PATH, {})
    if not isinstance(build_receipt, Mapping):
        build_receipt = {}
    build_receipt_errors = validate_build_receipt(args.store, args.compiled, build_receipt)
    compiled_count, bank_issues = _bank_validation_issues(args.compiled)
    result["source_inventory_errors"] = source_errors
    result["review_custody_errors"] = review_custody_errors
    result["semantic_audit_errors"] = semantic_audit_errors
    result["build_receipt_errors"] = build_receipt_errors
    result["bank_validation_issues"] = bank_issues
    result["compiled_count"] = compiled_count
    result["compiled_sha256"] = sha256_file(args.compiled) if args.compiled.exists() else ""
    result["default_launch_bank_sha256"] = sha256_file(DEFAULT_BANK) if DEFAULT_BANK.exists() else ""
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
    if source_errors or review_custody_errors or semantic_audit_errors or build_receipt_errors or bank_issues or result["quality_errors"]:
        result["status"] = "PHASE_2_INCOMPLETE"
    else:
        result["status"] = "PHASE_2_STRUCTURALLY_ACCEPTED"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PHASE_2_STRUCTURALLY_ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
