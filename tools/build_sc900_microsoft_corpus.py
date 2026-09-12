from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ingestion.importer import promotion_counts
from ingestion.models import canonicalize_record, load_taxonomy, normalize_text
from tools.build_sc900_phase2 import review_content_sha256
from tools.sc900_final_predecessor_overlay import overlay_row, validate_overlay
from tools.validate_sc900_microsoft_corpus import (
    CORPUS_ROOT,
    DEFAULT_BANK,
    EXISTING_AUDIT_PATH,
    EXPECTED_DEFAULT_BANK_SHA256,
    INVENTORY_PATH,
    KNOWLEDGE_UNITS_PATH,
    SCOPE_PATH,
    default_bank_errors,
    existing_audit_errors,
    inventory_schema_errors,
    knowledge_unit_errors,
    load_json,
    load_jsonl,
    pr13_isolation_errors,
    promotion_currentness_errors,
    sha256_file,
)
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS

ROOT = Path(__file__).resolve().parents[1]
PHASE3_STORE = ROOT / "content" / "sc900" / "phase3" / "store"
PHASE3_COMPILED = ROOT / "content" / "sc900" / "phase3" / "compiled" / "sc900_phase3_reviewed_bank.json"
BATCHES = CORPUS_ROOT / "batches"
REVIEWS = CORPUS_ROOT / "reviews"
ANSWER_REVIEWS = CORPUS_ROOT / "answer_reviews"
STORE = CORPUS_ROOT / "store"
COMPILED_PATH = CORPUS_ROOT / "compiled" / "sc900_microsoft_learn_corpus_bank.json"
BUILD_RECEIPT_PATH = CORPUS_ROOT / "build_receipt.json"
ACCEPTANCE_PATH = CORPUS_ROOT / "acceptance_report.json"
ANALYTICS_PATH = CORPUS_ROOT / "analytics.json"
SEMANTIC_AUDIT_PATH = CORPUS_ROOT / "semantic_family_audit.json"

WORK_ID = "SC900-FINAL-BANK-AUDIT-001"
BUILD_EPOCH = "final-bank-audit-deterministic-build"
DETERMINISTIC_IMPORT_AT = "2026-09-12T18:30:00+00:00"
REVIEWER = "cursor-grok-4.6-microsoft-corpus-separate-review"
REVIEW_METHOD = "separate adversarial review pass after authoring; independent answer verification against frozen Microsoft inventory"
FROZEN_PROBE_FAMILIES = {
    "azure_key_vault",
    "entra_roles_rbac",
    "multifactor_authentication",
    "privileged_identity_management",
    "purview_portal",
    "shared_responsibility_model",
    "zero_trust_and_identity_perimeter",
}
EXTRA_REVIEW_FIELDS = ("independent_answer_verified", "adversarial_item_reviewed")


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    payload.update(context)
    return payload


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def load_predecessor_records() -> list[dict[str, Any]]:
    rows = _read_rows(PHASE3_STORE / "questions.json")
    if len(rows) != 200:
        raise ValueError(f"expected 200 predecessor questions, found {len(rows)}")
    return rows


def load_new_records(taxonomy: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not BATCHES.is_dir():
        return records
    for path in sorted(BATCHES.glob("batch-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            record = canonicalize_record(raw, taxonomy)
            record["promotion_status"] = "pending"
            provenance = dict(record.get("provenance") or {})
            provenance["imported_at"] = DETERMINISTIC_IMPORT_AT
            record["provenance"] = provenance
            records.append(record)
    return records


def load_reviews() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not REVIEWS.is_dir():
        return result
    for path in sorted(REVIEWS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("reviews", []) if isinstance(payload, Mapping) else []
        for row in rows:
            if isinstance(row, dict) and normalize_text(row.get("question_id")):
                qid = normalize_text(row["question_id"])
                if qid in result:
                    raise ValueError(f"duplicate review receipt for {qid}")
                result[qid] = row
    return result


def pending_before_approval_errors(
    records: Sequence[Mapping[str, Any]],
    new_ids: Sequence[str],
) -> list[dict[str, Any]]:
    new_id_set = set(new_ids)
    errors: list[dict[str, Any]] = []
    for record in records:
        qid = normalize_text(record.get("id"))
        if qid not in new_id_set:
            continue
        if normalize_text(record.get("promotion_status")) == "approved":
            errors.append(_error("IMPORT_BYPASSES_PENDING", "new items must import as pending", question_id=qid))
    return errors


def review_custody_errors(
    records: Sequence[Mapping[str, Any]],
    reviews: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for record in records:
        qid = normalize_text(record.get("id"))
        receipt = reviews.get(qid)
        if receipt is None:
            errors.append(_error("MISSING_REVIEW_RECEIPT", "approved/new item missing review receipt", question_id=qid))
            continue
        expected = review_content_sha256(record)
        actual = normalize_text(receipt.get("reviewed_content_sha256")).lower()
        if actual != expected:
            errors.append(
                _error(
                    "REVIEW_HASH_MISMATCH",
                    "review custody hash does not match authored content",
                    question_id=qid,
                    expected=expected,
                    actual=actual,
                )
            )
        failed = [field for field in (*REVIEW_CHECK_FIELDS, *EXTRA_REVIEW_FIELDS) if receipt.get(field) is not True]
        if normalize_text(receipt.get("disposition")) == "approved" and failed:
            errors.append(
                _error(
                    "REVIEW_RECEIPT_INCOMPLETE",
                    "approved review is missing required checks",
                    question_id=qid,
                    fields=failed,
                )
            )
    extra = sorted(set(reviews) - {normalize_text(row.get("id")) for row in records})
    if extra:
        errors.append(_error("ORPHAN_REVIEW_RECEIPT", "review receipts without authored rows", question_ids=extra[:20]))
    return errors


def apply_reviews(records: Sequence[dict[str, Any]], reviews: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for record in records:
        updated = dict(record)
        receipt = reviews.get(normalize_text(record.get("id")))
        if receipt is not None:
            disposition = normalize_text(receipt.get("disposition")).lower()
            if disposition in {"approved", "pending", "withheld"}:
                updated["promotion_status"] = disposition
        applied.append(updated)
    return applied


def overlay_predecessor(
    records: Sequence[Mapping[str, Any]],
    audit_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    overlayed: list[dict[str, Any]] = []
    for record in records:
        updated = json.loads(json.dumps(record))
        qid = normalize_text(record.get("id"))
        audit = audit_by_id.get(qid, {})
        metadata = dict(updated.get("metadata") or {})
        metadata["provenance_category"] = "EXISTING_REPOSITORY_REVERIFIED"
        metadata["existing_classification"] = normalize_text(audit.get("classification")) or "UNVERIFIED"
        metadata["currentness_status"] = normalize_text(audit.get("currentness_status")) or "UNVERIFIED"
        metadata["future_probe_suitability"] = "not_assigned_to_frozen_probe"
        final_overlay = overlay_row(qid)
        metadata["tested_decision"] = final_overlay["tested_decision"]
        metadata["semantic_independence"] = final_overlay["semantic_independence"]
        if final_overlay.get("related_to"):
            metadata["semantic_related_to"] = final_overlay["related_to"]
        updated["metadata"] = metadata
        if final_overlay["disposition"] == "withheld":
            updated["promotion_status"] = "withheld"
        elif audit.get("reuse_as_approved") is True and metadata["currentness_status"] in {
            "CURRENT",
            "CURRENT_WITH_TERMINOLOGY_NOTE",
            "CURRENT_BUT_VOLATILE",
        }:
            updated["promotion_status"] = "approved"
        elif audit.get("reuse_as_approved") is False:
            updated["promotion_status"] = normalize_text(audit.get("disposition")) or "withheld"
        overlayed.append(updated)
    return overlayed


def semantic_duplicate_errors(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    stems: dict[str, str] = {}
    family_decisions: dict[tuple[str, str], tuple[str, str]] = {}
    for record in records:
        qid = normalize_text(record.get("id"))
        stem = normalize_text(record.get("stem")).casefold()
        if stem in stems:
            errors.append(
                _error("EXACT_STEM_DUPLICATE", "exact stem duplicate", question_id=qid, related_to=stems[stem])
            )
        stems[stem] = qid
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        family = normalize_text(metadata.get("semantic_family_id"))
        decision = normalize_text(metadata.get("tested_decision")).casefold()
        independence = normalize_text(metadata.get("semantic_independence")).casefold()
        if family and decision:
            key = (family, decision)
            if key in family_decisions:
                previous_id, previous_independence = family_decisions[key]
                independent_variant = independence == "independent_or_primary" or previous_independence == (
                    "independent_or_primary"
                )
                if not independent_variant:
                    errors.append(
                        _error(
                            "SEMANTIC_DECISION_DUPLICATE",
                            "same semantic family tests the same learner decision",
                            question_id=qid,
                            related_to=previous_id,
                            semantic_family_id=family,
                        )
                    )
            else:
                family_decisions[key] = (qid, independence)
        elif not decision:
            errors.append(
                _error(
                    "EMPTY_TESTED_DECISION",
                    "approved question is missing a durable tested_decision",
                    question_id=qid,
                )
            )
        if (
            metadata.get("assigned_probe_authority")
            or normalize_text(metadata.get("future_probe_suitability")) == "PROBE"
        ):
            errors.append(
                _error(
                    "FROZEN_PROBE_ASSIGNMENT",
                    "new corpus items must not be assigned into frozen PROBE authority",
                    question_id=qid,
                )
            )
    return errors


def analytics_for(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = promotion_counts(records)
    approved = [row for row in records if row.get("promotion_status") == "approved"]
    domains: Counter[str] = Counter()
    objectives: Counter[str] = Counter()
    leaves: Counter[str] = Counter()
    difficulties: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    types: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    families: Counter[str] = Counter()
    answer_pos: Counter[str] = Counter()
    microsoft_approved = 0
    for row in approved:
        domains[normalize_text(row.get("domain"))] += 1
        objectives[normalize_text(row.get("objective"))] += 1
        metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
        leaves[normalize_text(metadata.get("blueprint_leaf_id"))] += 1
        difficulties[normalize_text(row.get("difficulty"))] += 1
        styles[normalize_text(metadata.get("stem_style") or "direct_concept")] += 1
        types["multi" if len(row.get("correct_answer") or []) > 1 else "single"] += 1
        sources[normalize_text(metadata.get("provenance_category") or "MICROSOFT_LEARN_PRIMARY")] += 1
        families[normalize_text(metadata.get("semantic_family_id"))] += 1
        answers = row.get("correct_answer") or []
        choices = row.get("choices") or []
        id_to_letter = {item["id"]: "ABCD"[index] for index, item in enumerate(choices) if index < 4}
        if answers:
            answer_pos[id_to_letter.get(str(answers[0]), str(answers[0]).upper())] += 1
        if normalize_text(metadata.get("provenance_category")) in {
            "MICROSOFT_LEARN_PRIMARY",
            "MICROSOFT_PRODUCT_DOC_PRIMARY",
            "EXISTING_REPOSITORY_REVERIFIED",
        }:
            microsoft_approved += 1
    family_count = len([key for key in families if key])
    return {
        "approved": counts["approved"],
        "pending": counts["pending"],
        "withheld": counts["withheld"],
        "approved_by_domain": dict(sorted(domains.items())),
        "approved_by_objective": dict(sorted(objectives.items())),
        "approved_by_leaf_skill": dict(sorted(leaves.items())),
        "difficulty_distribution": dict(sorted(difficulties.items())),
        "stem_style_distribution": dict(sorted(styles.items())),
        "single_multi_distribution": dict(sorted(types.items())),
        "source_distribution": dict(sorted(sources.items())),
        "answer_position_distribution": dict(sorted(answer_pos.items())),
        "semantic_family_count": family_count,
        "average_questions_per_semantic_family": round(len(approved) / family_count, 3) if family_count else 0,
        "microsoft_approved": microsoft_approved,
        "uncovered_leaves": sorted(
            {
                str(leaf["id"])
                for row in load_taxonomy().get("objective_details", [])
                for leaf in row.get("leaf_skills", [])
            }
            - set(leaves)
        ),
    }


def compile_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    compiled = []
    for record in records:
        if record.get("promotion_status") != "approved":
            continue
        metadata = dict(record.get("metadata") or {})
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        choice_map = {letters[index]: item["text"] for index, item in enumerate(record["choices"])}
        id_to_letter = {item["id"]: letters[index] for index, item in enumerate(record["choices"])}
        compiled.append(
            {
                "id": record["id"],
                "question_number": len(compiled) + 1,
                "prompt": record["stem"],
                "choices": choice_map,
                "correct": [id_to_letter[value] for value in record["correct_answer"]],
                "general_explanation": record["explanation"],
                "choice_explanations": {letter: record["explanation"] for letter in choice_map},
                "domain": record["domain"],
                "domain_code": record["domain"],
                "chapter": record["objective"],
                "topics": record["tags"] or [record["objective"]],
                "objective_code": record["objective"],
                "subobjective": record.get("subobjective", ""),
                "question_type": "single" if len(record["correct_answer"]) == 1 else "multi",
                "source_name": str(
                    (record.get("provenance") or {}).get("source", {}).get("title") or "Microsoft Learn"
                ),
                "provenance": record.get("provenance"),
                "blueprint_leaf_id": metadata.get("blueprint_leaf_id", ""),
                "semantic_family_id": metadata.get("semantic_family_id", ""),
                "tested_decision": metadata.get("tested_decision", ""),
                "source_family_id": metadata.get("source_family_id", ""),
                "stem_style": metadata.get("stem_style", ""),
                "future_probe_suitability": metadata.get("future_probe_suitability", "not_assigned_to_frozen_probe"),
                "authoring_origin": metadata.get("authoring_origin", ""),
                "provenance_category": metadata.get("provenance_category", ""),
                "currentness_status": metadata.get("currentness_status", ""),
                "semantic_independence": metadata.get("semantic_independence", ""),
                "references": list(record.get("references") or []),
            }
        )
    return {"title": "SC-900 Microsoft Learn Corpus Candidate Bank", "questions": compiled}


def compiled_file_bytes(bank: Mapping[str, Any]) -> bytes:
    return (json.dumps(bank, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_compiled_bank(bank: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(compiled_file_bytes(bank))


def build_corpus(*, write: bool = True) -> dict[str, Any]:
    taxonomy = load_taxonomy()
    inventory = load_json(INVENTORY_PATH)
    scope = load_json(SCOPE_PATH)
    units = load_jsonl(KNOWLEDGE_UNITS_PATH) if KNOWLEDGE_UNITS_PATH.is_file() else []
    audit = load_json(EXISTING_AUDIT_PATH) if EXISTING_AUDIT_PATH.is_file() else {"items": []}
    predecessor = overlay_predecessor(
        load_predecessor_records(),
        {normalize_text(row.get("question_id")): row for row in audit.get("items", []) if isinstance(row, Mapping)},
    )
    new_records = load_new_records(taxonomy)
    new_ids = [normalize_text(row.get("id")) for row in new_records]
    authored_pending = [{**row, "promotion_status": "pending"} for row in new_records]
    reviews = load_reviews()
    new_reviewed = apply_reviews(authored_pending, reviews)
    records = predecessor + new_reviewed

    errors: list[dict[str, Any]] = []
    for message in validate_overlay([normalize_text(row.get("id")) for row in predecessor]):
        errors.append(_error("PREDECESSOR_OVERLAY_INVALID", message))
    errors.extend(inventory_schema_errors(inventory))
    errors.extend(knowledge_unit_errors(units, inventory, taxonomy))
    errors.extend(existing_audit_errors(audit, [row["id"] for row in predecessor]))
    errors.extend(pending_before_approval_errors(authored_pending, new_ids))
    approved_new = [row for row in new_reviewed if row.get("promotion_status") == "approved"]
    if approved_new:
        errors.extend(review_custody_errors(approved_new, reviews))
    errors.extend(promotion_currentness_errors(records))
    errors.extend(semantic_duplicate_errors([row for row in records if row.get("promotion_status") == "approved"]))
    errors.extend(default_bank_errors())
    errors.extend(pr13_isolation_errors())
    if sha256_file(DEFAULT_BANK) != EXPECTED_DEFAULT_BANK_SHA256:
        errors.append(_error("DEFAULT_BANK_CHANGED", "default launch bank digest changed"))

    compiled_bank = compile_records(records)
    compiled_sha256 = _sha256_bytes(compiled_file_bytes(compiled_bank))
    analytics = analytics_for(records)
    counts = promotion_counts(records)
    report = {
        "work_id": WORK_ID,
        "build_epoch": BUILD_EPOCH,
        "source_inventory_captured_at": inventory.get("source_inventory_captured_at"),
        "sc900_study_guide_last_updated": inventory.get("sc900_study_guide_last_updated"),
        "sc900_skills_effective_date": inventory.get("sc900_skills_effective_date"),
        "current_sc900_scope_verified": bool(scope.get("current_sc900_scope_verified")),
        "approved": counts["approved"],
        "pending": counts["pending"],
        "withheld": counts["withheld"],
        "compiled_count": len(compiled_bank["questions"]),
        "compiled_sha256": compiled_sha256,
        "compiled_bank": compiled_bank,
        "analytics": analytics,
        "errors": errors,
        "default_bank_unchanged": not default_bank_errors(),
        "final_bank_activated": False,
        "pr13_imported": False,
        "pr13_modified": False,
        "pr13_merged": False,
        "day1_started": False,
        "book_supplement_started": False,
        "frozen_probe_families": sorted(FROZEN_PROBE_FAMILIES),
        "target_microsoft_approved": 500,
        "actual_microsoft_approved": analytics["microsoft_approved"],
        "inventory_counts": inventory.get("counts", {}),
        "knowledge_unit_count": len(units),
        "new_candidate_count": len(new_records),
        "existing_reverified_count": sum(1 for row in predecessor if row.get("promotion_status") == "approved"),
    }
    if write:
        STORE.mkdir(parents=True, exist_ok=True)
        _write_json(STORE / "questions.json", records)
        write_compiled_bank(compiled_bank, COMPILED_PATH)
        receipt = {key: value for key, value in report.items() if key != "compiled_bank"}
        _write_json(BUILD_RECEIPT_PATH, receipt)
        _write_json(ANALYTICS_PATH, analytics)
        _write_json(
            ACCEPTANCE_PATH,
            {
                **receipt,
                "microsoft_corpus_phase_complete": False,
                "quality_gates": "PENDING" if errors else "PASS",
            },
        )
        _write_json(
            SEMANTIC_AUDIT_PATH,
            {
                "semantic_family_count": analytics["semantic_family_count"],
                "average_questions_per_semantic_family": analytics["average_questions_per_semantic_family"],
                "errors": [row for row in errors if str(row.get("code", "")).startswith("SEMANTIC")],
            },
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the SC-900 Microsoft Learn corpus candidate bank.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_corpus(write=not args.check)
    print(
        json.dumps(
            {
                "approved": report["approved"],
                "pending": report["pending"],
                "withheld": report["withheld"],
                "compiled_sha256": report["compiled_sha256"],
                "error_count": len(report["errors"]),
                "actual_microsoft_approved": report["actual_microsoft_approved"],
            },
            indent=2,
        )
    )
    return 1 if report["errors"] and not args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
