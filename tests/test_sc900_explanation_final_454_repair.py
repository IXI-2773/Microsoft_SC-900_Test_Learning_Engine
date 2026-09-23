from __future__ import annotations

import json
import unittest
from pathlib import Path

from cert_config import QUESTION_BANK_FILENAME
from content_revision_authority import sha256_file
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS
from question_identity import bank_content_fingerprint, canonical_question_id
from tools.bank_warning_policy import GOVERNED_ACTIVE_BANK_FILENAME
from tools.build_sc900_explanation_final_454_repair import (
    CONTENT_CORRECTIONS,
    REPAIRS,
    SOURCE_BANK_SHA256,
    SOURCE_CONTENT_FINGERPRINT,
    build_sc900_explanation_final_454_repair,
)

ROOT = Path(__file__).resolve().parents[1]


class Final454ExplanationRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = build_sc900_explanation_final_454_repair(ROOT)
        cls.source = json.loads((ROOT / "sc900_bank_v8_explanation_q118_repair.json").read_text(encoding="utf-8"))
        cls.target = json.loads((ROOT / "sc900_bank_v8_explanation_final_454_repair.json").read_text(encoding="utf-8"))

    def test_source_bank_binding_is_unchanged(self) -> None:
        self.assertEqual(SOURCE_BANK_SHA256, sha256_file(ROOT / "sc900_bank_v8_explanation_q118_repair.json"))
        self.assertEqual(454, len(self.source["questions"]))
        self.assertEqual(SOURCE_CONTENT_FINGERPRINT, bank_content_fingerprint(self.source["questions"]))

    def test_successor_changes_only_explanation_fields(self) -> None:
        source_by_id = {canonical_question_id(question): question for question in self.source["questions"]}
        target_by_id = {canonical_question_id(question): question for question in self.target["questions"]}
        self.assertEqual(list(source_by_id), list(target_by_id))
        changed = []
        for question_id, source_question in source_by_id.items():
            target_question = target_by_id[question_id]
            if source_question != target_question:
                changed.append(question_id)
                self.assertEqual(source_question["prompt"], target_question["prompt"])
                self.assertEqual(source_question["choices"], target_question["choices"])
                self.assertEqual(source_question["correct"], target_question["correct"])
                self.assertEqual(source_question["objective_code"], target_question["objective_code"])
        self.assertEqual(sorted(REPAIRS), sorted(changed))
        self.assertTrue(set(CONTENT_CORRECTIONS).isdisjoint(changed))

    def test_production_bank_is_not_activated(self) -> None:
        self.assertEqual("sc900_bank_v8_explanation_q118_repair.json", QUESTION_BANK_FILENAME)
        self.assertEqual("sc900_bank_v8_explanation_q118_repair.json", GOVERNED_ACTIVE_BANK_FILENAME)
        self.assertEqual(8, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertNotIn(
            "manifests/sc900_explanation_final_454_repair.json",
            AUTHORIZED_CONTENT_REVISION_MANIFESTS,
        )
        self.assertEqual("PASS", self.result["admission_status"])

    def test_defect_ledger_covers_every_successor_question(self) -> None:
        ledger = json.loads(
            (
                ROOT / "content_revision_evidence/reviews/SC900-FINAL-454-EXPLANATION-AUDIT-001/defect_ledger.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(454, ledger["questions_audited"])
        self.assertEqual(454, len(ledger["rows"]))
        self.assertEqual(0, ledger["known_substantive_explanation_defects_remaining"])
        self.assertEqual(2, ledger["content_correction_required_count"])
        self.assertTrue(all(row["AUDIT_STATUS"] == "SEMANTIC_AUDIT_COMPLETE" for row in ledger["rows"]))


if __name__ == "__main__":
    unittest.main()
