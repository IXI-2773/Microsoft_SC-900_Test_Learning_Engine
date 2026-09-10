from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAXONOMY_PATH = ROOT / "config" / "certifications" / "sc900-2026.json"
SUPPORTED_TYPES = {"multiple_choice", "multi_select"}
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class ValidationError(ValueError):
    def __init__(self, issues: list[dict[str, str]]):
        self.issues = issues
        self.reason_codes = [issue["code"] for issue in issues]
        super().__init__("; ".join(f"{item['code']}: {item['message']}" for item in issues))


def load_taxonomy(path: Path = DEFAULT_TAXONOMY_PATH) -> dict[str, Any]:
    taxonomy = json.loads(path.read_text(encoding="utf-8"))
    if taxonomy.get("exam") != "SC-900":
        raise ValueError("Taxonomy must identify SC-900.")
    return taxonomy


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _taxonomy_objectives(taxonomy: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(objective): str(domain["id"])
        for domain in taxonomy.get("domains", [])
        for objective in domain.get("objectives", [])
    }


def _canonical_choices(value: Any) -> list[dict[str, str]]:
    if isinstance(value, Mapping):
        value = [{"id": key, "text": text} for key, text in value.items()]
    if not isinstance(value, list):
        return []
    return [
        {"id": normalize_text(item.get("id")), "text": normalize_text(item.get("text"))}
        for item in value
        if isinstance(item, Mapping)
    ]


def _fingerprint(payload: Mapping[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def canonicalize_record(raw: Mapping[str, Any], taxonomy: Mapping[str, Any]) -> dict[str, Any]:
    kind = normalize_text(raw.get("record_kind") or "question").lower()
    source_raw = raw.get("source") if isinstance(raw.get("source"), Mapping) else {}
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
    provenance = {
        "origin": normalize_text(metadata.get("origin") or raw.get("origin") or "extracted").lower(),
        "source": {key: value for key, value in source_raw.items() if value not in (None, "")},
        "extractor_version": normalize_text(metadata.get("extractor_version")),
        "batch": normalize_text(metadata.get("batch") or raw.get("extraction_batch")),
        "imported_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    issues: list[dict[str, str]] = []
    if kind not in {"question", "source_material"}:
        issues.append({"code": "UNSUPPORTED_RECORD_KIND", "message": "record_kind must be question or source_material"})
    if normalize_text(raw.get("exam")) != "SC-900":
        issues.append({"code": "INVALID_EXAM", "message": "exam must be SC-900"})
    if provenance["origin"] not in {"extracted", "generated", "manual"}:
        issues.append({"code": "INVALID_ORIGIN", "message": "origin must be extracted, generated, or manual"})
    if kind == "source_material":
        body = normalize_text(raw.get("body") or raw.get("stem"))
        if not body:
            issues.append({"code": "MISSING_SOURCE_BODY", "message": "source material needs body"})
        if issues:
            raise ValidationError(issues)
        identity = {"kind": kind, "exam": "SC-900", "body": body, "source": provenance["source"]}
        return {
            "id": "src_" + _fingerprint(identity)[:24],
            "record_kind": kind,
            "exam": "SC-900",
            "body": body,
            "tags": [normalize_text(tag) for tag in raw.get("tags", []) if normalize_text(tag)],
            "metadata": dict(metadata),
            "provenance": provenance,
        }

    stem = normalize_text(raw.get("stem"))
    choices = _canonical_choices(raw.get("choices"))
    correct = raw.get("correct_answer")
    correct_ids = [
        normalize_text(item) for item in (correct if isinstance(correct, list) else [correct]) if normalize_text(item)
    ]
    objective = normalize_text(raw.get("objective"))
    domain = normalize_text(raw.get("domain"))
    expected_domain = _taxonomy_objectives(taxonomy).get(objective)
    if not stem:
        issues.append({"code": "MISSING_STEM", "message": "question stem is required"})
    if not choices:
        issues.append({"code": "MISSING_CHOICES", "message": "question choices are required"})
    if len({choice["id"] for choice in choices}) != len(choices) or any(
        not choice["id"] or not choice["text"] for choice in choices
    ):
        issues.append({"code": "MALFORMED_CHOICES", "message": "choice ids and text must be non-empty and unique"})
    if len({normalize_text(choice["text"]).casefold() for choice in choices}) != len(choices):
        issues.append({"code": "DUPLICATE_CHOICES", "message": "choice text must be unique after normalization"})
    if not correct_ids or not set(correct_ids).issubset({choice["id"] for choice in choices}):
        issues.append({"code": "INVALID_CORRECT_ANSWER", "message": "correct_answer must identify supplied choices"})
    if normalize_text(raw.get("type")) not in SUPPORTED_TYPES:
        issues.append({"code": "UNSUPPORTED_QUESTION_TYPE", "message": "type is not supported"})
    if expected_domain is None or expected_domain != domain:
        issues.append({"code": "INVALID_OBJECTIVE", "message": "objective must belong to the declared domain"})
    if normalize_text(raw.get("difficulty") or "intermediate") not in VALID_DIFFICULTIES:
        issues.append({"code": "INVALID_DIFFICULTY", "message": "difficulty is invalid"})
    if not normalize_text(raw.get("explanation")):
        issues.append({"code": "MISSING_EXPLANATION", "message": "question explanation is required"})
    if issues:
        raise ValidationError(issues)
    identity = {
        "exam": "SC-900",
        "objective": objective,
        "stem": stem.casefold(),
        "choices": sorted(choice["text"].casefold() for choice in choices),
        "correct": sorted(correct_ids),
        "source": provenance["source"],
    }
    return {
        "id": normalize_text(raw.get("id")) or "q_" + _fingerprint(identity)[:24],
        "record_kind": "question",
        "exam": "SC-900",
        "taxonomy_version": str(taxonomy.get("blueprint_version")),
        "domain": domain,
        "objective": objective,
        "subobjective": normalize_text(raw.get("subobjective")),
        "difficulty": normalize_text(raw.get("difficulty") or "intermediate"),
        "type": normalize_text(raw.get("type")),
        "stem": stem,
        "choices": choices,
        "correct_answer": correct_ids,
        "explanation": normalize_text(raw.get("explanation")),
        "references": list(raw.get("references") or []),
        "tags": [normalize_text(tag) for tag in raw.get("tags", []) if normalize_text(tag)],
        "metadata": dict(metadata),
        "provenance": provenance,
        "fingerprint": _fingerprint(identity),
    }
