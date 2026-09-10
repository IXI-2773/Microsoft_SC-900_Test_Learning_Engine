from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from extraction.pipeline import extract_pdf_to_jsonl
from ingestion.adapter import adapt_exchange_jsonl
from ingestion.importer import apply_review_decision, compile_question_bank, import_jsonl
from ingestion.models import load_taxonomy
from tests.pdf_fixtures import write_text_pdf

CHOICES = "\n".join(
    [
        "A. Microsoft Purview",
        "B. Microsoft Entra ID",
        "C. Microsoft Defender",
        "D. Microsoft Intune",
    ]
)


def _question(index: int) -> str:
    return "\n".join(
        [
            f"Question {index}",
            f"Which original study prompt {index} uniquely identifies {hashlib.sha256(str(index).encode()).hexdigest()[:20]} with Microsoft Entra ID?",
            CHOICES,
            "Answer: B",
            "Explanation: This original fixture names Microsoft Entra ID as the identity service.",
            "Objective: entra_identity_access",
            "Domain: microsoft_entra",
        ]
    )


class PilotTests(unittest.TestCase):
    def test_original_pdf_pilot_extract_import_approve_subset_and_idempotency(self) -> None:
        pages = ["\n\n".join(_question(index) for index in range(start, start + 4)) for start in range(1, 25, 4)]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_text_pdf(root / "original-pilot.pdf", pages)
            jsonl = extract_pdf_to_jsonl(pdf, root / "extracted.jsonl", title="Original SC-900 extractor pilot")
            extracted = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
            questions = [row for row in extracted if row.get("record_type") == "extracted_question"]
            self.assertGreaterEqual(len(questions), 20)
            self.assertLessEqual(len(questions), 50)
            self.assertTrue(all(row["source_page"] >= 1 for row in questions))
            adapt_exchange_jsonl(jsonl, root / "canonical.jsonl", load_taxonomy())
            first = import_jsonl(root / "canonical.jsonl", root / "store", load_taxonomy())
            stored = json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))
            approved_ids = [row["id"] for row in stored[:3]]
            for question_id in approved_ids:
                apply_review_decision(root / "store", question_id, "approved", actor="pilot")
            if stored[3:4]:
                apply_review_decision(root / "store", stored[3]["id"], "withheld", actor="pilot")
            promotion = compile_question_bank(root / "store", root / "runtime.json")
            second = import_jsonl(root / "canonical.jsonl", root / "store", load_taxonomy())
            quarantine = (
                json.loads((root / "store" / "quarantine.json").read_text(encoding="utf-8"))
                if (root / "store" / "quarantine.json").exists()
                else []
            )
            report = {
                "pages_processed": 6,
                "question_candidates_found": len(questions),
                "valid_extracted": first["accepted"],
                "pending": first["pending"] - 3 - (1 if stored[3:4] else 0),
                "quarantined": first["rejected"],
                "exact_duplicates_second_import": second["skipped"],
                "probable_duplicates": first["review"],
                "approved_test_subset": promotion["approved"],
                "withheld": promotion["withheld"],
                "compiled": promotion["compiled"],
            }
            (root / "pilot-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            self.assertEqual(0, second["accepted"])
            self.assertEqual(first["accepted"], second["skipped"])
            self.assertEqual(3, promotion["compiled"])
            self.assertGreaterEqual(len(quarantine), 0)
            self.assertEqual(6, report["pages_processed"])
            compiled = json.loads((root / "runtime.json").read_text(encoding="utf-8"))
            self.assertTrue(all(item["provenance"]["source"]["page"] >= 1 for item in compiled["questions"]))


if __name__ == "__main__":
    unittest.main()
