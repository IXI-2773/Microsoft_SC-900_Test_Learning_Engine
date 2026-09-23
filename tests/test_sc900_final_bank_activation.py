from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

import app
import cert_config
from exam_runtime_eligibility import exam_runtime_eligible, filter_new_exam_pool
from question_bank import load_bank
from release_resources import REQUIRED_RUNTIME_RESOURCES
from tools import build_release
from tools.sc900_exam_calibration import APPLIED, CORE, STRETCH, VALID_TIERS
from tools.validate_bank import validate_bank

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CALIBRATED_BANK = (
    ROOT / "content" / "sc900" / "microsoft-learn-corpus" / "compiled" / "sc900_microsoft_learn_corpus_bank.json"
)
HISTORICAL_BASELINE_BANK = ROOT / "sc900_bank_v8_baseline.json"
ACTIVE_RUNTIME_BANK_FILENAME = "sc900_bank_v8_final.json"
EXPECTED_ACTIVE_COUNT = 454
EXPECTED_CORE_COUNT = 301
EXPECTED_APPLIED_COUNT = 130
EXPECTED_STRETCH_COUNT = 23
EXPECTED_EXAM_ELIGIBLE_COUNT = 431
EXPECTED_ACTIVE_SHA256 = "177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c"
EXPECTED_BASELINE_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FinalBankActivationContractTests(unittest.TestCase):
    def test_a1_runtime_config_resolves_to_governed_target_not_baseline(self):
        profile = json.loads((ROOT / "cert_profile_sc900.json").read_text(encoding="utf-8"))
        self.assertEqual("sc900_bank_v8_final_content_correction_002.json", profile["runtime_bank"])
        self.assertEqual("sc900_bank_v8_final_content_correction_002.json", cert_config.QUESTION_BANK_FILENAME)
        self.assertNotEqual("sc900_bank_v8_baseline.json", cert_config.QUESTION_BANK_FILENAME)
        self.assertEqual(cert_config.QUESTION_BANK_FILENAME, app.DEFAULT_BANK.name)

    def test_a2_installation_verification_uses_active_count_authority(self):
        source = (ROOT / "tools" / "verify_installation.py").read_text(encoding="utf-8")
        self.assertIn("RUNTIME_BANK_QUESTION_COUNT", source)
        self.assertNotIn("instead of 8", source)
        self.assertEqual(EXPECTED_ACTIVE_COUNT, cert_config.RUNTIME_BANK_QUESTION_COUNT)
        self.assertNotIn("placeholder_bank_question_count", source)

    def test_a3_release_count_authority_uses_active_runtime_count(self):
        source = (ROOT / "tools" / "build_release.py").read_text(encoding="utf-8")
        self.assertIn("RUNTIME_BANK_QUESTION_COUNT", source)
        self.assertEqual(EXPECTED_ACTIVE_COUNT, build_release.EXPECTED_QUESTION_COUNT)
        self.assertEqual(cert_config.RUNTIME_BANK_QUESTION_COUNT, build_release.EXPECTED_QUESTION_COUNT)
        self.assertEqual(cert_config.QUESTION_BANK_FILENAME, build_release.BANK_FILE.name)
        self.assertNotIn("placeholder_bank_question_count", source)

    def test_a4_active_runtime_bank_count_is_454(self):
        active_path = ROOT / cert_config.QUESTION_BANK_FILENAME
        self.assertEqual("sc900_bank_v8_final_content_correction_002.json", active_path.name)
        self.assertTrue(active_path.is_file())
        questions = load_bank(active_path)["questions"]
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(questions))
        self.assertEqual(EXPECTED_ACTIVE_COUNT, cert_config.RUNTIME_BANK_QUESTION_COUNT)

    def test_a5_canonical_calibrated_bank_is_runtime_valid(self):
        self.assertEqual(EXPECTED_ACTIVE_SHA256, sha256_file(CANONICAL_CALIBRATED_BANK))
        questions = load_bank(CANONICAL_CALIBRATED_BANK)["questions"]
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(questions))
        tiers = Counter(row["exam_calibration_tier"] for row in questions)
        self.assertEqual(EXPECTED_CORE_COUNT, tiers[CORE])
        self.assertEqual(EXPECTED_APPLIED_COUNT, tiers[APPLIED])
        self.assertEqual(EXPECTED_STRETCH_COUNT, tiers[STRETCH])
        result = validate_bank(CANONICAL_CALIBRATED_BANK)
        self.assertEqual(EXPECTED_ACTIVE_COUNT, result["question_count"])
        self.assertEqual([], result["issues"])

    def test_a6_active_ordinary_exam_pool_is_431(self):
        questions = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)["questions"]
        eligible = filter_new_exam_pool(questions)
        stretch = [row for row in questions if row.get("exam_calibration_tier") == STRETCH]
        self.assertEqual(EXPECTED_EXAM_ELIGIBLE_COUNT, len(eligible))
        self.assertEqual(EXPECTED_STRETCH_COUNT, len(stretch))
        self.assertTrue(all(not exam_runtime_eligible(row) for row in stretch))
        self.assertTrue(all(row not in eligible for row in stretch))

    def test_a7_practice_retains_all_454(self):
        questions = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)["questions"]
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(questions))
        stretch_ids = [row["id"] for row in questions if row.get("exam_calibration_tier") == STRETCH]
        self.assertEqual(EXPECTED_STRETCH_COUNT, len(stretch_ids))

    def test_a8_smart_practice_source_retains_stretch_eligibility(self):
        questions = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)["questions"]
        stretch = [row for row in questions if row.get("exam_calibration_tier") == STRETCH]
        self.assertEqual(EXPECTED_STRETCH_COUNT, len(stretch))
        self.assertTrue(all(row.get("exam_simulation_eligible") is False for row in stretch))
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(questions))

    def test_historical_final_bank_remains_byte_identical_to_canonical_calibrated_bank(self):
        final_path = ROOT / ACTIVE_RUNTIME_BANK_FILENAME
        self.assertTrue(final_path.is_file())
        self.assertEqual(CANONICAL_CALIBRATED_BANK.read_bytes(), final_path.read_bytes())
        self.assertEqual(EXPECTED_ACTIVE_SHA256, sha256_file(final_path))
        self.assertEqual(sha256_file(CANONICAL_CALIBRATED_BANK), sha256_file(final_path))

    def test_historical_baseline_bank_remains_byte_identical(self):
        self.assertTrue(HISTORICAL_BASELINE_BANK.is_file())
        self.assertEqual(EXPECTED_BASELINE_SHA256, sha256_file(HISTORICAL_BASELINE_BANK))
        baseline = load_bank(HISTORICAL_BASELINE_BANK)["questions"]
        self.assertEqual(8, len(baseline))
        self.assertEqual({"1": 2, "2": 2, "3": 2, "4": 2}, dict(Counter(q["domain_code"] for q in baseline)))

    def test_placeholder_count_remains_historical_and_does_not_drive_production(self):
        profile = json.loads((ROOT / "cert_profile_sc900.json").read_text(encoding="utf-8"))
        self.assertEqual(8, profile["placeholder_bank_question_count"])
        self.assertEqual(EXPECTED_ACTIVE_COUNT, profile["runtime_bank_question_count"])
        self.assertEqual(EXPECTED_ACTIVE_COUNT, cert_config.RUNTIME_BANK_QUESTION_COUNT)
        self.assertNotEqual(profile["placeholder_bank_question_count"], cert_config.RUNTIME_BANK_QUESTION_COUNT)
        lint_source = (ROOT / "tools" / "lint_bank.py").read_text(encoding="utf-8")
        smoke_source = (ROOT / "tools" / "smoke_test.py").read_text(encoding="utf-8")
        self.assertIn("RUNTIME_BANK_QUESTION_COUNT", lint_source)
        self.assertNotIn("placeholder_bank_question_count", lint_source)
        self.assertIn("RUNTIME_BANK_QUESTION_COUNT", smoke_source)
        self.assertNotIn("8-question clean-bank gate", smoke_source)

    def test_packaging_includes_active_runtime_bank(self):
        names = [path.as_posix() for path in REQUIRED_RUNTIME_RESOURCES]
        self.assertIn(cert_config.QUESTION_BANK_FILENAME, names)
        self.assertIn("cert_profile_sc900.json", names)
        self.assertIn("config/certifications/sc900-2026.json", names)
        self.assertIn("sc900_bank_v8_baseline.json", names)

    def test_active_bank_tier_counts_match_frozen_calibration(self):
        questions = load_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)["questions"]
        tiers = Counter(row["exam_calibration_tier"] for row in questions)
        self.assertEqual(EXPECTED_CORE_COUNT, tiers[CORE])
        self.assertEqual(EXPECTED_APPLIED_COUNT, tiers[APPLIED])
        self.assertEqual(EXPECTED_STRETCH_COUNT, tiers[STRETCH])
        self.assertEqual(set(VALID_TIERS), set(tiers))


if __name__ == "__main__":
    unittest.main()
