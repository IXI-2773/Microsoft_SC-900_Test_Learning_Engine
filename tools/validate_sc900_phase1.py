from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.bank_quality import phase1_review_status, validate_phase1_question
from ingestion.models import ValidationError, load_taxonomy, normalize_text
from tools.validate_bank import validate_bank

EXPECTED_DOMAIN_COUNTS = {
    "security_compliance_identity": 6,
    "microsoft_entra": 14,
    "microsoft_security_solutions": 19,
    "microsoft_compliance_solutions": 11,
}
EXPECTED_OBJECTIVE_COUNTS = {
    "security_compliance_concepts": 3,
    "identity_concepts": 3,
    "entra_identity_types_and_function": 3,
    "entra_authentication": 4,
    "entra_access_management": 3,
    "entra_identity_protection_governance": 4,
    "azure_infrastructure_security": 6,
    "azure_security_management": 4,
    "microsoft_sentinel": 3,
    "defender_xdr": 6,
    "service_trust_privacy": 2,
    "purview_compliance_management": 2,
    "purview_information_protection_lifecycle": 4,
    "purview_insider_risk_ediscovery_audit": 3,
}
SOURCE_TYPES = {"study_guide", "learning_path", "module", "product_documentation"}
REVIEW_CHECK_FIELDS = (
    "factual_source_checked",
    "objective_leaf_checked",
    "correct_answer_unique",
    "all_distractors_defensibly_wrong",
    "explanation_supported",
    "originality_boundary_checked",
    "duplicate_reviewed",
    "semantic_family_reviewed",
    "probe_suitability_reviewed",
)
PROHIBITED_ASSESSMENT_MARKERS = (
    "practice-assessment",
    "practice_assessment",
    "/assessment",
    "/knowledge-check",
    "/knowledgecheck",
)


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(context)
    return payload


def _is_official_source_url(value: Any) -> bool:
    parsed = urlparse(normalize_text(value))
    if parsed.scheme.lower() != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host == "learn.microsoft.com" or host == "microsoft.com" or host.endswith(".microsoft.com")


def _is_assessment_url(value: Any) -> bool:
    text = normalize_text(value).lower()
    return any(marker in text for marker in PROHIBITED_ASSESSMENT_MARKERS)


def _taxonomy_maps(taxonomy: Mapping[str, Any]) -> tuple[set[str], dict[str, str]]:
    objective_ids = {
        str(objective)
        for domain in taxonomy.get("domains", [])
        for objective in domain.get("objectives", [])
    }
    leaf_owners: dict[str, str] = {}
    for detail in taxonomy.get("objective_details", []):
        objective_id = normalize_text(detail.get("id"))
        for leaf in detail.get("leaf_skills", []):
            leaf_id = normalize_text(leaf.get("id"))
            if leaf_id:
                leaf_owners[leaf_id] = objective_id
    return objective_ids, leaf_owners


def validate_source_inventory(inventory: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    objective_ids, leaf_owners = _taxonomy_maps(taxonomy)

    if normalize_text(inventory.get("exam")) != "SC-900":
        errors.append(_error("INVALID_INVENTORY_EXAM", "source inventory must identify SC-900"))
    if normalize_text(inventory.get("skills_effective_date")) != normalize_text(taxonomy.get("skills_effective_date")):
        errors.append(
            _error(
                "INVENTORY_BLUEPRINT_DATE_MISMATCH",
                "source inventory skills_effective_date must match the taxonomy",
            )
        )

    raw_sources = inventory.get("sources")
    sources = list(raw_sources) if isinstance(raw_sources, list) else []
    covered_objectives: set[str] = set()
    covered_leaves: set[str] = set()
    seen_source_ids: set[str] = set()

    for index, raw_source in enumerate(sources):
        if not isinstance(raw_source, Mapping):
            errors.append(_error("MALFORMED_SOURCE_ENTRY", "source entry must be an object", index=index))
            continue
        source_id = normalize_text(raw_source.get("source_id"))
        if not source_id:
            errors.append(_error("MISSING_SOURCE_ID", "source_id is required", index=index))
        elif source_id in seen_source_ids:
            errors.append(_error("DUPLICATE_SOURCE_ID", "source_id must be unique", source_id=source_id))
        else:
            seen_source_ids.add(source_id)

        url = normalize_text(raw_source.get("url"))
        if not _is_official_source_url(url):
            errors.append(_error("INVALID_SOURCE_URL", "source URL must be HTTPS on an official Microsoft host", source_id=source_id))
        if _is_assessment_url(url):
            errors.append(
                _error(
                    "ASSESSMENT_SOURCE_PROHIBITED",
                    "Practice Assessment and module-assessment sources are prohibited",
                    source_id=source_id,
                )
            )
        if normalize_text(raw_source.get("source_type")) not in SOURCE_TYPES:
            errors.append(_error("INVALID_SOURCE_TYPE", "source_type is invalid", source_id=source_id))
        if not normalize_text(raw_source.get("title")):
            errors.append(_error("MISSING_SOURCE_TITLE", "source title is required", source_id=source_id))
        if not normalize_text(raw_source.get("retrieved_at")):
            errors.append(_error("MISSING_SOURCE_RETRIEVED_AT", "retrieved_at is required", source_id=source_id))
        if raw_source.get("assessment_content_used") is not False:
            errors.append(
                _error(
                    "ASSESSMENT_CONTENT_USED",
                    "assessment_content_used must be explicitly false",
                    source_id=source_id,
                )
            )

        entry_objectives = {
            normalize_text(value)
            for value in raw_source.get("objective_ids", [])
            if normalize_text(value)
        }
        entry_leaves = {
            normalize_text(value)
            for value in raw_source.get("leaf_ids", [])
            if normalize_text(value)
        }
        for objective_id in sorted(entry_objectives):
            if objective_id not in objective_ids:
                errors.append(
                    _error(
                        "UNKNOWN_SOURCE_OBJECTIVE",
                        "source references an unknown objective",
                        source_id=source_id,
                        objective_id=objective_id,
                    )
                )
            else:
                covered_objectives.add(objective_id)
        for leaf_id in sorted(entry_leaves):
            owner = leaf_owners.get(leaf_id)
            if owner is None:
                errors.append(
                    _error(
                        "UNKNOWN_SOURCE_LEAF",
                        "source references an unknown blueprint leaf",
                        source_id=source_id,
                        leaf_id=leaf_id,
                    )
                )
                continue
            covered_leaves.add(leaf_id)
            if entry_objectives and owner not in entry_objectives:
                errors.append(
                    _error(
                        "SOURCE_LEAF_OBJECTIVE_MISMATCH",
                        "source leaf must belong to one of the source objective_ids",
                        source_id=source_id,
                        leaf_id=leaf_id,
                        owner=owner,
                    )
                )

    for objective_id in sorted(objective_ids - covered_objectives):
        errors.append(
            _error(
                "MISSING_OBJECTIVE_SOURCE",
                "every SC-900 objective must have at least one official source entry",
                objective_id=objective_id,
            )
        )
    for leaf_id in sorted(set(leaf_owners) - covered_leaves):
        errors.append(
            _error(
                "MISSING_LEAF_SOURCE",
                "every SC-900 blueprint leaf must have at least one official source entry",
                leaf_id=leaf_id,
            )
        )
    return errors


def _review_index(review_receipts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for receipt in review_receipts:
        question_id = normalize_text(receipt.get("question_id"))
        if question_id:
            index[question_id] = receipt
    return index


def validate_phase1_set(
    questions: Sequence[Mapping[str, Any]],
    taxonomy: Mapping[str, Any],
    review_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    approved = [row for row in questions if phase1_review_status(row) == "approved"]
    pending = [row for row in questions if phase1_review_status(row) == "pending"]
    withheld = [row for row in questions if phase1_review_status(row) == "withheld"]
    domain_counts = dict(sorted(Counter(normalize_text(row.get("domain")) for row in approved).items()))
    objective_counts = dict(sorted(Counter(normalize_text(row.get("objective")) for row in approved).items()))
    quality_errors: list[dict[str, Any]] = []

    ids = [normalize_text(row.get("id")) for row in approved]
    duplicate_ids = sorted(question_id for question_id, count in Counter(ids).items() if question_id and count > 1)
    if duplicate_ids:
        quality_errors.append(_error("DUPLICATE_APPROVED_ID", "approved question IDs must be unique", ids=duplicate_ids))

    if len(approved) != 50:
        quality_errors.append(
            _error(
                "APPROVED_COUNT_MISMATCH",
                "Phase 1 requires exactly 50 approved questions",
                expected=50,
                actual=len(approved),
            )
        )
    if domain_counts != EXPECTED_DOMAIN_COUNTS:
        quality_errors.append(
            _error(
                "DOMAIN_ALLOCATION_MISMATCH",
                "approved questions must match the frozen Phase-1 domain allocation",
                expected=EXPECTED_DOMAIN_COUNTS,
                actual=domain_counts,
            )
        )
    if objective_counts != EXPECTED_OBJECTIVE_COUNTS:
        quality_errors.append(
            _error(
                "OBJECTIVE_ALLOCATION_MISMATCH",
                "approved questions must match the frozen Phase-1 objective allocation",
                expected=EXPECTED_OBJECTIVE_COUNTS,
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
                    _error(
                        issue["code"],
                        issue["message"],
                        question_id=question_id,
                    )
                )
        receipt = reviews.get(question_id)
        if receipt is None:
            quality_errors.append(
                _error(
                    "MISSING_REVIEW_RECEIPT",
                    "every approved question requires an independent review receipt",
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
    status = "PHASE_1_STRUCTURALLY_ACCEPTED" if not quality_errors else "PHASE_1_INCOMPLETE"
    return {
        "status": status,
        "approved_count": len(approved),
        "pending_count": len(pending),
        "withheld_count": len(withheld),
        "domain_counts": domain_counts,
        "objective_counts": objective_counts,
        "distinct_leaf_count": len(distinct_leaves),
        "semantic_family_count": len(semantic_families),
        "probe_suitability_counts": probe_suitability_counts,
        "quality_errors": quality_errors,
    }


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_review_receipts(path: Path) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    if not path.exists():
        return receipts
    for review_path in sorted(path.glob("*.json")):
        payload = _load_json(review_path, [])
        rows = payload.get("reviews", []) if isinstance(payload, Mapping) else payload
        if isinstance(rows, list):
            receipts.extend(row for row in rows if isinstance(row, dict))
    return receipts


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
    parser = argparse.ArgumentParser(description="Validate the reviewed SC-900 Phase-1 candidate bank.")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--compiled", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    taxonomy = load_taxonomy()
    questions = _load_json(args.store / "questions.json", [])
    if not isinstance(questions, list):
        questions = []
    reviews = _load_review_receipts(args.reviews)
    inventory = _load_json(args.source_inventory, {})
    if not isinstance(inventory, Mapping):
        inventory = {}

    source_errors = validate_source_inventory(inventory, taxonomy)
    result = validate_phase1_set(questions, taxonomy, reviews)
    compiled_count, bank_issues = _bank_validation_issues(args.compiled)
    result["source_inventory_errors"] = source_errors
    result["bank_validation_issues"] = bank_issues
    result["compiled_count"] = compiled_count

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
        result["status"] = "PHASE_1_INCOMPLETE"
    else:
        result["status"] = "PHASE_1_STRUCTURALLY_ACCEPTED"

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PHASE_1_STRUCTURALLY_ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
