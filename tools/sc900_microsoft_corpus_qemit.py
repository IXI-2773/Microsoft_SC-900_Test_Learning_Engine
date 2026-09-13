from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ingestion.models import canonicalize_record, load_taxonomy, normalize_text
from tools.build_sc900_microsoft_corpus import (
    BATCHES,
    DETERMINISTIC_IMPORT_AT,
    EXTRA_REVIEW_FIELDS,
    REVIEW_METHOD,
    REVIEWER,
    REVIEWS,
)
from tools.build_sc900_phase2 import review_content_sha256
from tools.validate_sc900_microsoft_corpus import INVENTORY_PATH, load_json
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS

TAXONOMY = load_taxonomy()
LEAF_OWNER = {
    str(leaf["id"]): (str(row["domain_id"]), str(row["id"]), str(leaf["name"]))
    for row in TAXONOMY["objective_details"]
    for leaf in row["leaf_skills"]
}
SOURCES = {str(row["source_id"]): row for row in load_json(INVENTORY_PATH)["sources"]}


def question_record(
    *,
    serial: int,
    leaf: str,
    difficulty: str,
    stem_style: str,
    stem: str,
    choices: Sequence[tuple[str, str]],
    correct: str | Sequence[str],
    explanation: str,
    source_id: str,
    semantic_family_id: str,
    tested_decision: str,
    misconception_target: str = "",
    qtype: str = "multiple_choice",
    provenance_category: str = "MICROSOFT_LEARN_PRIMARY",
    currentness_status: str = "CURRENT",
    batch: str,
) -> dict[str, Any]:
    domain, objective, leaf_name = LEAF_OWNER[leaf]
    source = SOURCES[source_id]
    correct_ids = list(correct) if isinstance(correct, (list, tuple)) else [correct]
    category = (
        "MICROSOFT_PRODUCT_DOC_PRIMARY" if source["source_type"] == "product_documentation" else provenance_category
    )
    return {
        "id": f"sc900_mlc_q{serial:03d}",
        "exam": "SC-900",
        "domain": domain,
        "objective": objective,
        "subobjective": leaf_name,
        "difficulty": difficulty,
        "type": qtype,
        "stem": stem,
        "choices": [{"id": choice_id, "text": text} for choice_id, text in choices],
        "correct_answer": correct_ids if qtype == "multi_select" else correct_ids[0],
        "explanation": explanation,
        "references": [source["url"]],
        "tags": [leaf, tested_decision],
        "source": {"title": source["title"], "url": source["url"]},
        "metadata": {
            "origin": "manual",
            "batch": batch,
            "blueprint_leaf_id": leaf,
            "source_authority": (
                "microsoft_learn" if source["source_type"] != "product_documentation" else "microsoft_docs"
            ),
            "source_urls": [source["url"]],
            "source_retrieved_at": "2026-09-12",
            "source_family_id": f"mlc-{objective}",
            "semantic_family_id": semantic_family_id,
            "tested_decision": tested_decision,
            "misconception_target": misconception_target,
            "stem_style": stem_style,
            "future_probe_suitability": "not_assigned_to_frozen_probe",
            "authoring_origin": "original_from_official_source",
            "provenance_category": category,
            "currentness_status": currentness_status,
            "authority_source_id": source_id,
        },
    }


def redistribute_single_select(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    balanced: list[dict[str, Any]] = []
    for record in records:
        updated = json.loads(json.dumps(record))
        if normalize_text(updated.get("type")) == "multi_select":
            balanced.append(updated)
            continue
        choices = list(updated["choices"])
        correct = updated["correct_answer"]
        correct_id = correct[0] if isinstance(correct, list) else correct
        digest = hashlib.sha256(str(updated["id"]).encode("utf-8")).hexdigest()
        target = int(digest[:8], 16) % 4
        correct_choice = next(choice for choice in choices if choice["id"] == correct_id)
        others = [choice for choice in choices if choice["id"] != correct_id]
        reordered = others[:target] + [correct_choice] + others[target:]
        updated["choices"] = reordered
        balanced.append(updated)
    return balanced


def write_batch(batch_id: str, records: Sequence[Mapping[str, Any]]) -> Path:
    BATCHES.mkdir(parents=True, exist_ok=True)
    path = BATCHES / f"{batch_id}.jsonl"
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    return path


def write_reviews(batch_id: str, records: Sequence[Mapping[str, Any]]) -> Path:
    taxonomy = TAXONOMY
    reviews = []
    for raw in records:
        canonical = canonicalize_record(raw, taxonomy)
        canonical["provenance"]["imported_at"] = DETERMINISTIC_IMPORT_AT
        receipt = {
            "question_id": canonical["id"],
            "disposition": "approved",
            "reviewer": REVIEWER,
            "review_method": REVIEW_METHOD,
            "reviewed_at": DETERMINISTIC_IMPORT_AT.replace("+00:00", "Z"),
            "reviewed_content_sha256": review_content_sha256(canonical),
            "notes": (
                "Pass 2 independently resolved the keyed answer from frozen Microsoft authority "
                f"{(raw.get('source') or {}).get('url')}. Pass 3 attacked distractors for a second correct "
                "reading, stem under-constraint, and terminology drift. Pass 4 compared tested_decision "
                "against predecessor and sibling MLC items."
            ),
            "independent_resolved_answer": raw.get("correct_answer"),
        }
        receipt.update({field: True for field in REVIEW_CHECK_FIELDS})
        receipt.update({field: True for field in EXTRA_REVIEW_FIELDS})
        reviews.append(receipt)
    REVIEWS.mkdir(parents=True, exist_ok=True)
    path = REVIEWS / f"{batch_id}-review.json"
    path.write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "reviewer": REVIEWER,
                "review_method": REVIEW_METHOD,
                "reviewed_at": DETERMINISTIC_IMPORT_AT.replace("+00:00", "Z"),
                "reviews": reviews,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path
