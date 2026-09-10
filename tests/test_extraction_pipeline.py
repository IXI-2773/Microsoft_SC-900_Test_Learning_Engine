from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from extraction.pipeline import extract_pdf_to_jsonl
from ingestion.adapter import adapt_exchange_jsonl
from ingestion.importer import apply_review_decision, compile_question_bank, import_jsonl
from ingestion.models import load_taxonomy
from tests.pdf_fixtures import write_text_pdf

QUESTION_PAGE = """
Question 1
Which service provides cloud identity management?
A. Microsoft Purview
B. Microsoft Entra ID
C. Microsoft Defender
D. Microsoft Intune
Answer: B
Explanation: Microsoft Entra ID provides identity and access management.
Objective: entra_identity_access
Domain: microsoft_entra
"""

UNKNOWN_TAXONOMY = """
Question 2
Which service is mentioned here?
A. Microsoft Purview
B. Microsoft Entra ID
C. Microsoft Defender
D. Microsoft Intune
Answer: B
Explanation: Taxonomy is unknown on purpose.
Objective: not-a-real-objective
Domain: not-a-real-domain
"""


class PipelineTests(unittest.TestCase):
    def test_extract_import_stays_pending_until_explicit_approval(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_text_pdf(root / "guide.pdf", [QUESTION_PAGE.strip()])
            jsonl = extract_pdf_to_jsonl(pdf, root / "extracted.jsonl")
            rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual("sc900.extractor.exchange/v1", rows[0]["contract_version"])
            self.assertEqual("SOURCE_EXTRACTED", rows[0]["origin"])
            self.assertEqual(1, rows[0]["source_page"])
            canonical = root / "canonical.jsonl"
            adapted = adapt_exchange_jsonl(jsonl, canonical, load_taxonomy())
            self.assertEqual(1, adapted["adapted"])
            report = import_jsonl(canonical, root / "store", load_taxonomy())
            self.assertEqual(1, report["accepted"])
            self.assertEqual(1, report["pending"])
            self.assertEqual(0, report["approved"])
            stored = json.loads((root / "store" / "questions.json").read_text(encoding="utf-8"))
            self.assertEqual(1, stored[0]["provenance"]["source"]["page"])
            self.assertEqual("extracted", stored[0]["provenance"]["origin"])
            self.assertEqual([], stored[0]["metadata"].get("warnings") or [])
            compile_first = compile_question_bank(root / "store", root / "runtime.json")
            self.assertEqual(0, compile_first["compiled"])
            apply_review_decision(root / "store", stored[0]["id"], "approved", actor="reviewer")
            promotion = compile_question_bank(root / "store", root / "runtime.json")
            self.assertEqual(1, promotion["compiled"])
            compiled = json.loads((root / "runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(1, compiled["questions"][0]["provenance"]["source"]["page"])
            second = import_jsonl(canonical, root / "store", load_taxonomy())
            self.assertEqual(0, second["accepted"])
            self.assertEqual(1, second["skipped"])

    def test_unknown_taxonomy_is_quarantined_not_invented(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_text_pdf(root / "unknown.pdf", [UNKNOWN_TAXONOMY.strip()])
            jsonl = extract_pdf_to_jsonl(pdf, root / "extracted.jsonl")
            canonical = adapt_exchange_jsonl(jsonl, root / "canonical.jsonl", load_taxonomy())
            self.assertGreaterEqual(canonical["adapted"], 1)
            report = import_jsonl(root / "canonical.jsonl", root / "store", load_taxonomy())
            self.assertEqual(0, report["accepted"])
            self.assertEqual(1, report["rejected"])
            self.assertIn("INVALID_OBJECTIVE", report["reason_codes"])
            warnings = json.loads((root / "extracted.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertTrue(warnings["extraction_warnings"] or warnings["objective"] == "not-a-real-objective")

    def test_extraction_is_deterministic(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = write_text_pdf(root / "guide.pdf", [QUESTION_PAGE.strip()])
            first = extract_pdf_to_jsonl(pdf, root / "a.jsonl").read_text(encoding="utf-8")
            second = extract_pdf_to_jsonl(pdf, root / "b.jsonl").read_text(encoding="utf-8")
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
