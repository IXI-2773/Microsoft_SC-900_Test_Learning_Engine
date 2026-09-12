from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ingestion.models import load_taxonomy, normalize_text
from tools.validate_sc900_phase1 import PROHIBITED_ASSESSMENT_MARKERS, REVIEW_CHECK_FIELDS

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "content" / "sc900" / "microsoft-learn-corpus"
INVENTORY_PATH = CORPUS_ROOT / "source_inventory.json"
SCOPE_PATH = CORPUS_ROOT / "scope_reconciliation.json"
KNOWLEDGE_UNITS_PATH = CORPUS_ROOT / "knowledge_units.jsonl"
EXISTING_AUDIT_PATH = CORPUS_ROOT / "existing_bank_audit.json"
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"
EXPECTED_DEFAULT_BANK_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"
EXPECTED_LEAF_COUNT = 58
EXPECTED_OBJECTIVE_COUNT = 14
STUDY_GUIDE_URL = "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900"
REQUIRED_PATH_IDS = (
    "path-concepts",
    "path-entra",
    "path-security-solutions",
    "path-compliance-solutions",
)
REQUIRED_INVENTORY_FIELDS = (
    "source_inventory_captured_at",
    "sc900_study_guide_last_updated",
    "sc900_skills_effective_date",
    "exam",
    "sources",
)
REQUIRED_SOURCE_FIELDS = (
    "source_id",
    "source_type",
    "title",
    "url",
    "retrieved_at",
    "content_hash",
    "assessment_content_used",
)
REQUIRED_KNOWLEDGE_FIELDS = (
    "knowledge_unit_id",
    "domain_id",
    "objective_id",
    "leaf_skill_id",
    "concept",
    "claim_summary",
    "source_title",
    "source_locator",
    "source_url",
    "retrieved_at",
    "authority_level",
    "currentness_status",
    "question_opportunities",
    "semantic_family_hint",
)
CURRENTNESS_APPROVABLE = {"CURRENT", "CURRENT_WITH_TERMINOLOGY_NOTE", "CURRENT_BUT_VOLATILE"}
AUTHORITY_LEVELS = {
    "study_guide",
    "learning_path",
    "module",
    "unit",
    "product_documentation",
    "taxonomy",
}
OUT_OF_SCOPE_SOURCE_IDS = {
    "module-security-copilot-getting-started",
}


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    payload.update(context)
    return payload


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_canonical(payload: Mapping[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256_text(material)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        rows.append(payload)
    return rows


def taxonomy_leaf_ids(taxonomy: Mapping[str, Any] | None = None) -> set[str]:
    taxonomy = taxonomy or load_taxonomy()
    return {str(leaf["id"]) for row in taxonomy.get("objective_details", []) for leaf in row.get("leaf_skills", [])}


def default_bank_errors() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not DEFAULT_BANK.is_file():
        return [_error("DEFAULT_BANK_MISSING", "default launch bank is missing", path=str(DEFAULT_BANK))]
    digest = sha256_file(DEFAULT_BANK)
    if digest != EXPECTED_DEFAULT_BANK_SHA256:
        errors.append(
            _error(
                "DEFAULT_BANK_CHANGED",
                "default launch bank digest changed",
                expected=EXPECTED_DEFAULT_BANK_SHA256,
                actual=digest,
            )
        )
    return errors


def pr13_isolation_errors() -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for name in ("measurement_day1.py", "cand01r3_day1.py", "start_day1.py"):
        if (ROOT / name).exists():
            errors.append(_error("PR13_IMPORTED", "forbidden PR13 artifact present", path=name))
    runtime = ROOT / "cand01r3_runtime.py"
    if runtime.is_file():
        text = runtime.read_text(encoding="utf-8")
        if "DAY1_STARTED" in text or "begin_day_1" in text:
            errors.append(_error("DAY1_STARTED", "PR13 day-1 runtime markers present"))
    if (CORPUS_ROOT / "train_probe_manifest.json").exists():
        errors.append(
            _error(
                "FROZEN_PROBE_AUTHORITY_TOUCHED",
                "microsoft-learn corpus must not create a train/probe partition",
            )
        )
    return errors


def inventory_schema_errors(inventory: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for field in REQUIRED_INVENTORY_FIELDS:
        if not inventory.get(field):
            errors.append(_error("INVENTORY_FIELD_MISSING", f"missing {field}", field=field))
    if normalize_text(inventory.get("exam")) != "SC-900":
        errors.append(_error("INVENTORY_EXAM_INVALID", "exam must be SC-900"))
    if normalize_text(inventory.get("sc900_skills_effective_date")) != "2026-07-28":
        errors.append(
            _error(
                "SKILLS_EFFECTIVE_DATE_MISMATCH",
                "inventory skills effective date must match the live July 28, 2026 study guide",
                actual=inventory.get("sc900_skills_effective_date"),
            )
        )
    sources = inventory.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(_error("INVENTORY_SOURCES_MISSING", "sources must be a non-empty list"))
        return errors
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    types: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            errors.append(_error("INVENTORY_SOURCE_MALFORMED", "source must be an object", index=index))
            continue
        source_id = normalize_text(source.get("source_id"))
        url = normalize_text(source.get("url"))
        for field in REQUIRED_SOURCE_FIELDS:
            if source.get(field) in (None, ""):
                errors.append(
                    _error(
                        "INVENTORY_SOURCE_FIELD_MISSING", f"source missing {field}", source_id=source_id, field=field
                    )
                )
        if source_id in seen_ids:
            errors.append(_error("INVENTORY_DUPLICATE_SOURCE_ID", "duplicate source_id", source_id=source_id))
        seen_ids.add(source_id)
        if url in seen_urls:
            errors.append(_error("INVENTORY_DUPLICATE_URL", "duplicate source url", url=url))
        seen_urls.add(url)
        types.add(normalize_text(source.get("source_type")))
        if source.get("assessment_content_used") is not False:
            errors.append(
                _error(
                    "ASSESSMENT_CONTENT_USED",
                    "Microsoft assessment/knowledge-check content must not be used as question text",
                    source_id=source_id,
                )
            )
        lowered = url.casefold()
        if any(marker in lowered for marker in PROHIBITED_ASSESSMENT_MARKERS):
            errors.append(_error("PROHIBITED_ASSESSMENT_URL", "assessment URL is not admissible", url=url))
        digest = normalize_text(source.get("content_hash")).lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            errors.append(_error("INVENTORY_HASH_INVALID", "content_hash must be sha256 hex", source_id=source_id))
        if "microsoft.com" not in lowered and "learn.microsoft.com" not in lowered:
            errors.append(_error("NON_MICROSOFT_SOURCE", "source URL is not official Microsoft authority", url=url))
        units = source.get("units") or []
        if units and not isinstance(units, list):
            errors.append(_error("INVENTORY_UNITS_MALFORMED", "units must be a list", source_id=source_id))
    if "study_guide" not in types:
        errors.append(_error("STUDY_GUIDE_MISSING", "inventory must include the current SC-900 study guide"))
    missing_paths = [item for item in REQUIRED_PATH_IDS if item not in seen_ids]
    if missing_paths:
        errors.append(_error("LEARNING_PATH_MISSING", "required learning path missing", source_ids=missing_paths))
    if STUDY_GUIDE_URL.rstrip("/") not in {url.rstrip("/") for url in seen_urls}:
        errors.append(_error("STUDY_GUIDE_URL_MISSING", "study guide URL missing from inventory"))
    if "module" not in types:
        errors.append(_error("MODULES_MISSING", "inventory must include constituent modules"))
    return errors


def knowledge_unit_errors(
    units: Sequence[Mapping[str, Any]],
    inventory: Mapping[str, Any],
    taxonomy: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    taxonomy = taxonomy or load_taxonomy()
    leaves = taxonomy_leaf_ids(taxonomy)
    objective_owner = {
        str(objective): str(domain["id"])
        for domain in taxonomy.get("domains", [])
        for objective in domain["objectives"]
    }
    source_urls = {
        normalize_text(source.get("url")).rstrip("/")
        for source in inventory.get("sources", [])
        if isinstance(source, Mapping)
    }
    errors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    covered: set[str] = set()
    for unit in units:
        unit_id = normalize_text(unit.get("knowledge_unit_id"))
        for field in REQUIRED_KNOWLEDGE_FIELDS:
            if unit.get(field) in (None, "", []):
                errors.append(
                    _error("KNOWLEDGE_UNIT_FIELD_MISSING", f"knowledge unit missing {field}", knowledge_unit_id=unit_id)
                )
        if unit_id in seen_ids:
            errors.append(
                _error("KNOWLEDGE_UNIT_DUPLICATE_ID", "duplicate knowledge_unit_id", knowledge_unit_id=unit_id)
            )
        seen_ids.add(unit_id)
        leaf = normalize_text(unit.get("leaf_skill_id"))
        objective = normalize_text(unit.get("objective_id"))
        domain = normalize_text(unit.get("domain_id"))
        if leaf not in leaves:
            errors.append(_error("KNOWLEDGE_UNIT_UNKNOWN_LEAF", "leaf is not in current taxonomy", leaf_skill_id=leaf))
        else:
            covered.add(leaf)
        if objective_owner.get(objective) != domain:
            errors.append(
                _error(
                    "KNOWLEDGE_UNIT_TAXONOMY_MISMATCH",
                    "knowledge unit domain/objective do not match taxonomy",
                    knowledge_unit_id=unit_id,
                )
            )
        claim = normalize_text(unit.get("claim_summary"))
        if len(claim) > 420:
            errors.append(
                _error(
                    "KNOWLEDGE_UNIT_TOO_LONG",
                    "claim_summary must stay compact; do not store source passages",
                    knowledge_unit_id=unit_id,
                    length=len(claim),
                )
            )
        authority = normalize_text(unit.get("authority_level"))
        if authority not in AUTHORITY_LEVELS:
            errors.append(
                _error("KNOWLEDGE_UNIT_AUTHORITY_INVALID", "invalid authority_level", knowledge_unit_id=unit_id)
            )
        currentness = normalize_text(unit.get("currentness_status"))
        if currentness not in CURRENTNESS_APPROVABLE | {"UNVERIFIED", "OUT_OF_SCOPE", "RETIRED"}:
            errors.append(
                _error("KNOWLEDGE_UNIT_CURRENTNESS_INVALID", "invalid currentness_status", knowledge_unit_id=unit_id)
            )
        source_url = normalize_text(unit.get("source_url")).rstrip("/")
        if source_url not in source_urls:
            errors.append(
                _error(
                    "KNOWLEDGE_UNIT_SOURCE_NOT_IN_INVENTORY",
                    "knowledge unit source_url is not in the frozen inventory",
                    knowledge_unit_id=unit_id,
                    source_url=source_url,
                )
            )
        if any(marker in source_url.casefold() for marker in PROHIBITED_ASSESSMENT_MARKERS):
            errors.append(
                _error(
                    "KNOWLEDGE_UNIT_ASSESSMENT_SOURCE",
                    "knowledge units must not cite assessment/knowledge-check URLs",
                    knowledge_unit_id=unit_id,
                )
            )
    missing = sorted(leaves - covered)
    if missing:
        errors.append(_error("KNOWLEDGE_LEAF_UNCOVERED", "leaf skill has no knowledge units", leaf_ids=missing))
    return errors


def existing_audit_errors(
    audit: Mapping[str, Any],
    predecessor_ids: Sequence[str],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    items = audit.get("items")
    if not isinstance(items, list) or not items:
        return [_error("EXISTING_AUDIT_MISSING", "existing bank audit items are required")]
    allowed = {
        "CURRENT_MICROSOFT_SUPPORTED",
        "CURRENT_BUT_NEEDS_SOURCE_REFRESH",
        "NEEDS_REWRITE",
        "SEMANTIC_DUPLICATE",
        "OUTDATED",
        "UNVERIFIED",
    }
    seen: set[str] = set()
    for row in items:
        if not isinstance(row, Mapping):
            errors.append(_error("EXISTING_AUDIT_ROW_MALFORMED", "audit row must be an object"))
            continue
        qid = normalize_text(row.get("question_id"))
        classification = normalize_text(row.get("classification"))
        if qid in seen:
            errors.append(_error("EXISTING_AUDIT_DUPLICATE_ID", "duplicate audit question_id", question_id=qid))
        seen.add(qid)
        if classification not in allowed:
            errors.append(
                _error("EXISTING_AUDIT_CLASSIFICATION_INVALID", "invalid existing-item classification", question_id=qid)
            )
        if classification in {"UNVERIFIED", "OUTDATED"} and row.get("reuse_as_approved") is True:
            errors.append(
                _error(
                    "EXISTING_AUDIT_UNVERIFIED_REUSE",
                    "outdated or unverified items must not be reused as approved",
                    question_id=qid,
                )
            )
    missing = sorted(set(predecessor_ids) - seen)
    extra = sorted(seen - set(predecessor_ids))
    if missing:
        errors.append(
            _error(
                "EXISTING_AUDIT_INCOMPLETE",
                "predecessor questions missing from audit",
                question_ids=missing[:20],
                count=len(missing),
            )
        )
    if extra:
        errors.append(
            _error(
                "EXISTING_AUDIT_UNKNOWN_ID",
                "audit contains unknown predecessor IDs",
                question_ids=extra[:20],
                count=len(extra),
            )
        )
    return errors


def review_pass_errors(receipt: Mapping[str, Any], extra_fields: Sequence[str] = ()) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    required = list(REVIEW_CHECK_FIELDS) + list(extra_fields)
    failed = [field for field in required if receipt.get(field) is not True]
    if failed:
        errors.append(
            _error(
                "REVIEW_RECEIPT_INCOMPLETE",
                "review receipt is missing required affirmative checks",
                question_id=receipt.get("question_id"),
                fields=failed,
            )
        )
    return errors


def promotion_currentness_errors(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for record in records:
        if normalize_text(record.get("promotion_status")) != "approved":
            continue
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        currentness = normalize_text(metadata.get("currentness_status"))
        if currentness not in CURRENTNESS_APPROVABLE:
            errors.append(
                _error(
                    "UNAPPROVABLE_CURRENTNESS",
                    "approved questions must be currently verified",
                    question_id=record.get("id"),
                    currentness_status=currentness,
                )
            )
        if currentness in {"UNVERIFIED", "OUT_OF_SCOPE", "RETIRED"}:
            errors.append(
                _error(
                    "FORBIDDEN_APPROVED_CURRENTNESS",
                    "UNVERIFIED, OUT_OF_SCOPE, and RETIRED items must not be approved",
                    question_id=record.get("id"),
                )
            )
    return errors
