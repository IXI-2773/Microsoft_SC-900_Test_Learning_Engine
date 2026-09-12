from __future__ import annotations

import unittest
from collections import Counter

from tools.sc900_exam_calibration import (
    CALIBRATED_BANK_SHA256,
    CALIBRATION_ROOT,
    CALIBRATION_VERSION,
    COMPILED_BANK_PATH,
    CORE,
    DEFAULT_BANK,
    EXPECTED_DEFAULT_BANK_SHA256,
    PRECALIBRATION_BANK_SHA256,
    STRETCH,
    VALID_TIERS,
    exam_simulation_eligible,
    load_classification,
    load_json,
    load_overlay,
    sha256_file,
)
from tools.validate_sc900_microsoft_corpus import EXPECTED_LEAF_COUNT, taxonomy_leaf_ids


class ExamCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = load_json(COMPILED_BANK_PATH)
        cls.questions = cls.bank["questions"]
        cls.classification = load_classification()
        cls.overlay = load_overlay()

    def test_default_bank_unchanged(self):
        self.assertEqual(sha256_file(DEFAULT_BANK), EXPECTED_DEFAULT_BANK_SHA256)
        self.assertNotEqual(sha256_file(COMPILED_BANK_PATH), EXPECTED_DEFAULT_BANK_SHA256)

    def test_calibrated_bank_digest_is_frozen(self):
        self.assertEqual(sha256_file(COMPILED_BANK_PATH), CALIBRATED_BANK_SHA256)
        self.assertNotEqual(CALIBRATED_BANK_SHA256, PRECALIBRATION_BANK_SHA256)

    def test_every_approved_item_is_calibrated(self):
        self.assertEqual(len(self.questions), 454)
        self.assertEqual(len(self.classification), 454)
        for question in self.questions:
            qid = question["id"]
            self.assertIn(question["exam_calibration_tier"], VALID_TIERS, qid)
            self.assertIsInstance(question["reasoning_steps"], int)
            self.assertIn(question["exam_simulation_eligible"], (True, False))
            self.assertEqual(question["calibration_version"], CALIBRATION_VERSION)
            self.assertTrue(str(question.get("tested_decision") or "").strip(), qid)
            self.assertEqual(
                question["exam_simulation_eligible"],
                exam_simulation_eligible(question["exam_calibration_tier"]),
            )

    def test_target_mix_and_stretch_minority(self):
        tiers = Counter(row["exam_calibration_tier"] for row in self.questions)
        total = len(self.questions)
        self.assertGreaterEqual(tiers[CORE] / total, 0.60)
        self.assertLessEqual(tiers[STRETCH] / total, 0.10)
        self.assertEqual(tiers[STRETCH], 23)
        self.assertEqual(sum(1 for row in self.questions if row["exam_simulation_eligible"]), total - tiers[STRETCH])

    def test_all_current_leaves_remain_covered(self):
        leaves = {str(row.get("blueprint_leaf_id") or "") for row in self.questions}
        self.assertEqual(len(leaves), EXPECTED_LEAF_COUNT)
        self.assertEqual(leaves, taxonomy_leaf_ids())

    def test_overlay_preserves_tested_decision_and_identity(self):
        by_id = {row["id"]: row for row in self.questions}
        for qid, item in self.overlay.items():
            self.assertTrue(item.get("preserve_identity", True), qid)
            self.assertEqual(
                by_id[qid]["tested_decision"], item.get("tested_decision") or by_id[qid]["tested_decision"]
            )
            self.assertNotIn("correct_answer", item)

    def test_zero_trust_least_privilege_was_simplified(self):
        question = next(row for row in self.questions if row["id"] == "sc900_mlc_q201")
        self.assertIn("permissions required for their work", question["prompt"])
        self.assertNotIn("yet many accounts", question["prompt"])
        self.assertEqual(question["correct"], ["A"])
        self.assertEqual(question["exam_calibration_tier"], CORE)

    def test_builder_applies_calibration_without_errors(self):
        from tools.build_sc900_microsoft_corpus import build_corpus

        report = build_corpus(write=False)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["compiled_sha256"], CALIBRATED_BANK_SHA256)
        self.assertEqual(report["precalibration_bank_sha256"], PRECALIBRATION_BANK_SHA256)
        self.assertFalse(report["final_bank_activated"])

    def test_classification_and_ledger_exist(self):
        ledger = (CALIBRATION_ROOT / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(ledger), 454)
        self.assertTrue((CALIBRATION_ROOT / "rewrite_overlay.json").is_file())
        self.assertTrue((CALIBRATION_ROOT / "classification.json").is_file())


if __name__ == "__main__":
    unittest.main()
