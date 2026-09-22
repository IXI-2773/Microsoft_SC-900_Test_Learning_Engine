import hashlib
import json
import os
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cert_config
import app
from app_info import APP_NAME, APP_VERSION
from question_bank import load_bank
from tools.validate_bank import validate_bank
from tools import build_release

HISTORICAL_BASELINE_BANK = ROOT / "sc900_bank_v8_baseline.json"
EXPECTED_BASELINE_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"
EXPECTED_ACTIVE_SHA256 = "f18b2ad5174518f1c992c59663b93ad48d69483cefc1b72675af6d1486b1976d"
EXPECTED_ACTIVE_COUNT = 454


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SC900HistoricalBaselineContractTests(unittest.TestCase):
    def test_historical_baseline_bank_exists_with_original_digest(self):
        self.assertTrue(HISTORICAL_BASELINE_BANK.is_file())
        self.assertEqual(EXPECTED_BASELINE_SHA256, sha256_file(HISTORICAL_BASELINE_BANK))
        self.assertNotEqual(HISTORICAL_BASELINE_BANK.name, cert_config.QUESTION_BANK_FILENAME)

    def test_historical_baseline_has_eight_original_placeholder_questions_balanced_by_domain(self):
        data = load_bank(HISTORICAL_BASELINE_BANK)
        questions = data["questions"]
        self.assertEqual(8, len(questions))
        self.assertEqual(8, len({q["id"] for q in questions}))
        self.assertEqual({"1", "2", "3", "4"}, {q["domain_code"] for q in questions})
        self.assertEqual({"1": 2, "2": 2, "3": 2, "4": 2}, dict(Counter(q["domain_code"] for q in questions)))
        for question in questions:
            self.assertTrue(question["prompt"].strip())
            self.assertTrue(question["general_explanation"].strip())
            self.assertEqual(4, len(question["choices"]))
            self.assertEqual(set(question["choices"]), set(question["choice_explanations"]))
            corpus = json.dumps(question).lower()
            self.assertNotIn("comptia", corpus)
            self.assertNotIn("sy0-701", corpus)
            self.assertNotIn("security+", corpus)

    def test_validator_reports_clean_historical_baseline_bank(self):
        result = validate_bank(HISTORICAL_BASELINE_BANK)
        self.assertEqual(8, result["question_count"])
        self.assertEqual([], result["issues"])
        self.assertEqual([], result["warnings"])


class SC900ActiveProductionRuntimeContractTests(unittest.TestCase):
    def test_profile_is_sc900_and_keeps_official_scoring_separate_from_readiness(self):
        profile = json.loads((ROOT / "cert_profile_sc900.json").read_text(encoding="utf-8"))
        self.assertEqual("Microsoft", profile["vendor"])
        self.assertEqual("SC-900", profile["exam_code"])
        self.assertEqual(700, profile["official_scaled_pass_score"])
        self.assertEqual(1000, profile["official_scaled_score_max"])
        self.assertEqual(82.5, profile["internal_readiness_threshold_pct"])
        self.assertIn("not a conversion", profile["scoring_disclaimer"].lower())
        self.assertEqual([10, 20, 40, 50], profile["practice_question_count_options"])
        self.assertEqual(50, profile["practice_question_count_default"])
        self.assertEqual("sc900_bank_v8_explanation_q118_repair.json", profile["runtime_bank"])
        self.assertEqual(EXPECTED_ACTIVE_COUNT, profile["runtime_bank_question_count"])
        self.assertEqual(8, profile["placeholder_bank_question_count"])

    def test_config_is_single_sc900_runtime_identity(self):
        self.assertEqual("SC-900", cert_config.EXAM_CODE)
        self.assertEqual("Microsoft SC-900 Test Learning Engine", APP_NAME)
        self.assertEqual("8.0.0", APP_VERSION)
        self.assertEqual("sc900_bank_v8_explanation_q118_repair.json", cert_config.QUESTION_BANK_FILENAME)
        self.assertEqual(EXPECTED_ACTIVE_COUNT, cert_config.RUNTIME_BANK_QUESTION_COUNT)
        self.assertEqual("SC900TestLearningEngine", cert_config.USER_DATA_DIRNAME)

    def test_active_runtime_bank_has_calibrated_count_and_digest(self):
        active_path = ROOT / cert_config.QUESTION_BANK_FILENAME
        self.assertEqual("sc900_bank_v8_explanation_q118_repair.json", active_path.name)
        self.assertEqual(EXPECTED_ACTIVE_SHA256, sha256_file(active_path))
        data = load_bank(active_path)
        questions = data["questions"]
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(questions))
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len({q["id"] for q in questions}))
        self.assertEqual(
            {
                "security_compliance_identity",
                "microsoft_entra",
                "microsoft_security_solutions",
                "microsoft_compliance_solutions",
            },
            {q["domain_code"] for q in questions},
        )
        for question in questions[:8]:
            corpus = json.dumps(question).lower()
            self.assertNotIn("comptia", corpus)
            self.assertNotIn("sy0-701", corpus)
            self.assertNotIn("security+", corpus)

    def test_runtime_defaults_to_sc900_bank_and_user_data_namespace(self):
        self.assertEqual(cert_config.QUESTION_BANK_FILENAME, app.DEFAULT_BANK.name)
        with (
            mock.patch.object(app.sys, "frozen", True, create=True),
            mock.patch.dict(os.environ, {"LOCALAPPDATA": str(ROOT / "tmp-local")}),
        ):
            self.assertEqual("SC900TestLearningEngine", app.resolve_user_data_dir().name)

    def test_validator_loads_active_production_bank(self):
        result = validate_bank(ROOT / cert_config.QUESTION_BANK_FILENAME)
        self.assertEqual(EXPECTED_ACTIVE_COUNT, result["question_count"])
        self.assertEqual([], result["issues"])

    def test_release_contract_targets_active_sc900_bank(self):
        self.assertEqual(EXPECTED_ACTIVE_COUNT, build_release.EXPECTED_QUESTION_COUNT)
        self.assertEqual(cert_config.RUNTIME_BANK_QUESTION_COUNT, build_release.EXPECTED_QUESTION_COUNT)
        self.assertEqual("SC900TestLearningEngine.exe", build_release.RELEASE_EXE.name)
        self.assertEqual(cert_config.QUESTION_BANK_FILENAME, build_release.BANK_FILE.name)
        self.assertEqual(EXPECTED_ACTIVE_SHA256, sha256_file(build_release.BANK_FILE))


if __name__ == "__main__":
    unittest.main()
