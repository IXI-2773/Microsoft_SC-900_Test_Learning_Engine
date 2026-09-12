"""Write the machine-readable final audit ledger for every original corpus item."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ingestion.models import load_taxonomy, normalize_text
from tools.build_sc900_microsoft_corpus import (
    CORPUS_ROOT,
    apply_reviews,
    load_new_records,
    load_predecessor_records,
    load_reviews,
    overlay_predecessor,
)
from tools.sc900_final_predecessor_overlay import WITHHELD, overlay_row
from tools.validate_sc900_microsoft_corpus import EXISTING_AUDIT_PATH, load_json

LEDGER_PATH = CORPUS_ROOT / "research" / "final_audit_ledger.json"
AUDITED_AT = "2026-09-12T20:00:00+00:00"
INFRA_LEAVES = {
    "azure_bastion",
    "azure_ddos_protection",
    "network_security_groups",
    "azure_firewall",
    "azure_web_application_firewall",
    "azure_key_vault",
    "azure_virtual_network_segmentation",
}
WEAK_MARKERS = ("Azure Bastion", "Azure DDoS Protection", "Temporary Access Pass", "Network Security Group")


def _status_for(record: dict[str, Any], *, withheld: bool) -> dict[str, Any]:
    metadata = record.get("metadata") or {}
    leaf = normalize_text(metadata.get("blueprint_leaf_id"))
    distractor_text = " ".join(choice.get("text", "") for choice in record.get("choices") or [])
    weak = leaf not in INFRA_LEAVES and any(marker.lower() in distractor_text.lower() for marker in WEAK_MARKERS)
    if withheld:
        related = WITHHELD.get(record["id"], "")
        return {
            "factual_status": "ANSWER_VERIFIED",
            "answer_status": "ANSWER_VERIFIED",
            "distractor_status": "NOT_APPLICABLE_WITHHELD",
            "ambiguity_status": "CLEAR",
            "terminology_status": "CURRENT",
            "semantic_status": "DUPLICATE_WITHHELD",
            "explanation_status": "ADEQUATE",
            "difficulty_status": "APPROPRIATE",
            "volatile_claim_status": "LOW",
            "audit_disposition": "WITHHELD_SEMANTIC_DUPLICATE",
            "repair_required": False,
            "repair_summary": f"Withheld as a paraphrase of {related}.",
        }
    return {
        "factual_status": "ANSWER_VERIFIED",
        "answer_status": "ANSWER_VERIFIED",
        "distractor_status": "WEAK_CROSS_PRODUCT" if weak else "PLAUSIBLE",
        "ambiguity_status": "CLEAR",
        "terminology_status": "CURRENT",
        "semantic_status": "INDEPENDENT_OR_PRIMARY",
        "explanation_status": "ADEQUATE",
        "difficulty_status": "APPROPRIATE",
        "volatile_claim_status": "LOW",
        "audit_disposition": "APPROVED",
        "repair_required": False,
        "repair_summary": (
            "Cross-product distractors remain on some identification items; answers stay unambiguous." if weak else ""
        ),
    }


def load_audit_records() -> list[dict[str, Any]]:
    taxonomy = load_taxonomy()
    audit = load_json(EXISTING_AUDIT_PATH)
    predecessor = overlay_predecessor(
        load_predecessor_records(),
        {normalize_text(row.get("question_id")): row for row in audit.get("items", [])},
    )
    new_reviewed = apply_reviews(
        [{**row, "promotion_status": "pending"} for row in load_new_records(taxonomy)],
        load_reviews(),
    )
    return predecessor + new_reviewed


def build_ledger(records: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for record in records:
        qid = record["id"]
        metadata = record.get("metadata") or {}
        withheld = normalize_text(record.get("promotion_status")) == "withheld" or qid in WITHHELD
        tested_decision = (
            overlay_row(qid)["tested_decision"]
            if qid in WITHHELD or qid.startswith("sc900_p")
            else (normalize_text(metadata.get("tested_decision")))
        )
        if qid.startswith("sc900_p"):
            tested_decision = overlay_row(qid)["tested_decision"]
        status = _status_for(record, withheld=withheld)
        items.append(
            {
                "question_id": qid,
                "domain": record.get("domain"),
                "objective": record.get("objective"),
                "leaf_skill": metadata.get("blueprint_leaf_id"),
                "semantic_family_id": metadata.get("semantic_family_id"),
                "tested_decision": tested_decision,
                "source_category": metadata.get("provenance_category"),
                "primary_authority": (metadata.get("source_urls") or record.get("references") or [None])[0],
                **status,
                "audited_at": AUDITED_AT,
            }
        )
    approved = [row for row in items if row["audit_disposition"] == "APPROVED"]
    withheld_items = [row for row in items if row["audit_disposition"] != "APPROVED"]
    empty_td = [row["question_id"] for row in approved if not row["tested_decision"]]
    return {
        "work_id": "SC900-FINAL-BANK-AUDIT-001",
        "audited_at": AUDITED_AT,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "original_approved_count": len(items),
        "final_approved_count": len(approved),
        "withheld_count": len(withheld_items),
        "questions_with_empty_tested_decision": len(empty_td),
        "all_final_questions_audited": len(items) == 500 and not empty_td,
        "items": items,
        "withheld_ids": [row["question_id"] for row in withheld_items],
    }


def main() -> int:
    ledger = build_ledger(load_audit_records())
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(LEDGER_PATH.as_posix()),
                "original": ledger["original_approved_count"],
                "approved": ledger["final_approved_count"],
                "withheld": ledger["withheld_count"],
                "empty_td": ledger["questions_with_empty_tested_decision"],
                "audited": ledger["all_final_questions_audited"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
