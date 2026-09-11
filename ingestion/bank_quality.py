from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from ingestion.models import ValidationError, normalize_text

PHASE1_STEM_STYLES = {
    "direct_concept",
    "short_scenario",
    "capability_selection",
    "distinction_comparison",
    "responsibility_governance",
}
PHASE1_PROBE_SUITABILITY = {"eligible", "train_only", "needs_review"}
PHASE1_AUTHORING_ORIGIN = "original_from_official_source"
PHASE1_SOURCE_AUTHORITIES = {"microsoft_learn", "microsoft_documentation"}
PROHIBITED_ASSESSMENT_MARKERS = (
    "practice-assessment",
    "practice_assessment",
    "/assessment",
    "/knowledge-check",
    "/knowledgecheck",
)


def _leaf_owners(taxonomy: Mapping[str, Any]) -> dict[str, str]:
    owners: dict[str, str] = {}
    for objective in taxonomy.get("objective_details", []):
        objective_id = normalize_text(objective.get("id"))
        for leaf in objective.get("leaf_skills", []):
            leaf_id = normalize_text(leaf.get("id"))
            if leaf_id:
                owners[leaf_id] = objective_id
    return owners


def _is_official_microsoft_url(value: Any) -> bool:
    text = normalize_text(value)
    if not text:
        return False
    parsed = urlparse(text)
    if parsed.scheme.lower() != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host == "learn.microsoft.com" or host == "microsoft.com" or host.endswith(".microsoft.com")


def _is_prohibited_assessment_url(value: Any) -> bool:
    text = normalize_text(value).lower()
    return any(marker in text for marker in PROHIBITED_ASSESSMENT_MARKERS)


def phase1_review_status(record: Mapping[str, Any]) -> str:
    status = normalize_text(record.get("promotion_status")).lower() or "pending"
    return status if status in {"approved", "pending", "withheld"} else "pending"


def validate_phase1_question(record: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> None:
    """Raise ValidationError when a record violates the Phase-1 bank-quality contract."""

    raw_metadata = record.get("metadata")
    metadata: Mapping[str, Any] = raw_metadata if isinstance(raw_metadata, Mapping) else {}
    issues: list[dict[str, str]] = []

    leaf_id = normalize_text(metadata.get("blueprint_leaf_id"))
    if not leaf_id:
        issues.append({"code": "MISSING_BLUEPRINT_LEAF", "message": "blueprint_leaf_id is required"})
    else:
        owner = _leaf_owners(taxonomy).get(leaf_id)
        if owner != normalize_text(record.get("objective")):
            issues.append(
                {
                    "code": "BLUEPRINT_LEAF_OBJECTIVE_MISMATCH",
                    "message": "blueprint_leaf_id must belong to the question objective",
                }
            )

    authority = normalize_text(metadata.get("source_authority")).lower()
    if authority not in PHASE1_SOURCE_AUTHORITIES:
        issues.append(
            {
                "code": "INVALID_SOURCE_AUTHORITY",
                "message": "source_authority must identify official Microsoft Learn/documentation",
            }
        )

    source_urls = metadata.get("source_urls")
    urls = list(source_urls) if isinstance(source_urls, list) else []
    if not urls or any(not _is_official_microsoft_url(url) for url in urls):
        issues.append(
            {
                "code": "INVALID_SOURCE_URL",
                "message": "source_urls must contain only HTTPS official Microsoft documentation URLs",
            }
        )
    if any(_is_prohibited_assessment_url(url) for url in urls):
        issues.append(
            {
                "code": "ASSESSMENT_SOURCE_PROHIBITED",
                "message": "Practice Assessment and module-assessment sources are prohibited",
            }
        )

    if not normalize_text(metadata.get("source_retrieved_at")):
        issues.append(
            {
                "code": "MISSING_SOURCE_RETRIEVED_AT",
                "message": "source_retrieved_at is required",
            }
        )
    if not normalize_text(metadata.get("source_family_id")):
        issues.append({"code": "MISSING_SOURCE_FAMILY", "message": "source_family_id is required"})
    if not normalize_text(metadata.get("semantic_family_id")):
        issues.append({"code": "MISSING_SEMANTIC_FAMILY", "message": "semantic_family_id is required"})

    if normalize_text(metadata.get("stem_style")) not in PHASE1_STEM_STYLES:
        issues.append({"code": "INVALID_STEM_STYLE", "message": "stem_style is not approved for Phase 1"})
    if normalize_text(metadata.get("future_probe_suitability")) not in PHASE1_PROBE_SUITABILITY:
        issues.append(
            {
                "code": "INVALID_PROBE_SUITABILITY",
                "message": "future_probe_suitability must be eligible, train_only, or needs_review",
            }
        )
    if normalize_text(metadata.get("authoring_origin")) != PHASE1_AUTHORING_ORIGIN:
        issues.append(
            {
                "code": "INVALID_AUTHORING_ORIGIN",
                "message": "authoring_origin must identify original authoring from official sources",
            }
        )

    references = record.get("references")
    reference_urls = list(references) if isinstance(references, list) else []
    if not reference_urls:
        issues.append({"code": "MISSING_REFERENCE", "message": "at least one factual reference is required"})
    else:
        if any(not _is_official_microsoft_url(url) for url in reference_urls):
            issues.append(
                {
                    "code": "INVALID_SOURCE_URL",
                    "message": "references must contain only HTTPS official Microsoft documentation URLs",
                }
            )
        if any(_is_prohibited_assessment_url(url) for url in reference_urls):
            issues.append(
                {
                    "code": "ASSESSMENT_SOURCE_PROHIBITED",
                    "message": "Practice Assessment and module-assessment references are prohibited",
                }
            )

    if issues:
        raise ValidationError(issues)
