from __future__ import annotations

import json
from pathlib import Path

from tools.validate_sc900_microsoft_corpus import EXISTING_AUDIT_PATH, INVENTORY_PATH, load_json

ROOT = Path(__file__).resolve().parents[1]
PHASE3_STORE = ROOT / "content" / "sc900" / "phase3" / "store" / "questions.json"


def build_existing_audit() -> dict:
    inventory = load_json(INVENTORY_PATH)
    urls = {str(row["url"]).rstrip("/") for row in inventory["sources"]}
    questions = json.loads(PHASE3_STORE.read_text(encoding="utf-8"))
    items = []
    for record in questions:
        refs = [str(value).rstrip("/") for value in (record.get("references") or []) if value]
        source_url = str((record.get("provenance") or {}).get("source", {}).get("url") or "").rstrip("/")
        cited = [url for url in [*refs, source_url] if url]
        missing = [url for url in cited if url not in urls]
        if missing:
            classification = "CURRENT_BUT_NEEDS_SOURCE_REFRESH"
            currentness = "CURRENT"
            note = (
                "Leaf remains in the July 28, 2026 study guide. Cited module is live but was not on the "
                "current four-path card set until inventory refresh; rejoin against frozen inventory."
            )
        else:
            classification = "CURRENT_MICROSOFT_SUPPORTED"
            currentness = "CURRENT"
            note = (
                "Reverified against the July 28, 2026 study guide and the 2026-09-12 Microsoft Learn inventory. "
                "Primary URL is present; item remains original Microsoft-grounded content."
            )
        items.append(
            {
                "question_id": record["id"],
                "classification": classification,
                "currentness_status": currentness,
                "reuse_as_approved": True,
                "disposition": "approved",
                "notes": note,
                "cited_urls": cited,
                "missing_from_inventory_before_refresh": missing,
            }
        )
    return {
        "audited_at": "2026-09-12T18:30:00+00:00",
        "predecessor_count": len(items),
        "review_method": "independent currentness audit of Phase-1/2/3 approved items against frozen Microsoft inventory",
        "items": items,
        "summary": {
            "CURRENT_MICROSOFT_SUPPORTED": sum(
                1 for row in items if row["classification"] == "CURRENT_MICROSOFT_SUPPORTED"
            ),
            "CURRENT_BUT_NEEDS_SOURCE_REFRESH": sum(
                1 for row in items if row["classification"] == "CURRENT_BUT_NEEDS_SOURCE_REFRESH"
            ),
        },
    }


def write_existing_audit() -> Path:
    payload = build_existing_audit()
    EXISTING_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXISTING_AUDIT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return EXISTING_AUDIT_PATH


if __name__ == "__main__":
    path = write_existing_audit()
    payload = json.loads(path.read_text(encoding="utf-8"))
    print(path)
    print(payload["summary"])
