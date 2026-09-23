from __future__ import annotations

import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bank_warning_policy import (  # noqa: E402
    GOVERNED_ACTIVE_BANK_FILENAME,
    GOVERNED_ACTIVE_BANK_SHA256,
    GOVERNED_ACTIVE_BANK_WARNINGS,
    evaluate_production_warnings,
)
from tools.lint_bank import lint_bank  # noqa: E402
from tools.smoke_test import release_bank_gate_failures  # noqa: E402

FROZEN_WARNING = (
    "Repeated answer-pattern bias",
    "C streak on Q394-Q399 (6 in a row)",
)
EXTRA_WARNING = ("Synthetic extra warning", "not part of the frozen contract")
DIFFERENT_WARNING = ("Different warning title", "different warning body")
ACTIVE_BANK = ROOT / GOVERNED_ACTIVE_BANK_FILENAME
BASELINE_BANK = ROOT / "sc900_bank_v8_baseline.json"
ALTERED_SHA = "0" * 64


class WarningPolicyBindingTests(unittest.TestCase):
    def test_wg003_policy_is_bound_to_filename_sha_and_exact_warning_set(self):
        self.assertEqual("sc900_bank_v8_final_content_correction_002.json", GOVERNED_ACTIVE_BANK_FILENAME)
        self.assertEqual(
            "f97f76591ebb41dd1b92ca5623c6f040b2d9a75ca6f7f1d5b0ebd9adf371581f",
            GOVERNED_ACTIVE_BANK_SHA256,
        )
        self.assertEqual((FROZEN_WARNING,), GOVERNED_ACTIVE_BANK_WARNINGS)
        self.assertEqual(1, len(GOVERNED_ACTIVE_BANK_WARNINGS))

    def test_wg004_exact_frozen_active_bank_and_exact_warning_passes(self):
        decision = evaluate_production_warnings(
            ACTIVE_BANK,
            [FROZEN_WARNING],
            bank_sha256=GOVERNED_ACTIVE_BANK_SHA256,
        )
        self.assertTrue(decision.passed)
        self.assertEqual((), decision.failures)
        self.assertEqual(1, decision.known_frozen_warning_count)
        self.assertEqual(0, decision.unexpected_warning_count)
        self.assertTrue(decision.governed)

    def test_wg005_exact_frozen_bank_plus_extra_warning_fails(self):
        decision = evaluate_production_warnings(
            ACTIVE_BANK,
            [FROZEN_WARNING, EXTRA_WARNING],
            bank_sha256=GOVERNED_ACTIVE_BANK_SHA256,
        )
        self.assertFalse(decision.passed)
        self.assertTrue(decision.failures)
        self.assertEqual(1, decision.unexpected_warning_count)

    def test_wg006_exact_frozen_bank_with_substituted_warning_fails(self):
        decision = evaluate_production_warnings(
            ACTIVE_BANK,
            [DIFFERENT_WARNING],
            bank_sha256=GOVERNED_ACTIVE_BANK_SHA256,
        )
        self.assertFalse(decision.passed)
        self.assertTrue(decision.failures)

    def test_wg007_exact_frozen_bank_with_zero_warnings_fails(self):
        decision = evaluate_production_warnings(
            ACTIVE_BANK,
            [],
            bank_sha256=GOVERNED_ACTIVE_BANK_SHA256,
        )
        self.assertFalse(decision.passed)
        self.assertTrue(any("missing" in failure.lower() for failure in decision.failures))
        self.assertEqual(0, decision.known_frozen_warning_count)

    def test_wg008_same_filename_with_altered_sha_fails(self):
        decision = evaluate_production_warnings(
            Path(GOVERNED_ACTIVE_BANK_FILENAME),
            [FROZEN_WARNING],
            bank_sha256=ALTERED_SHA,
        )
        self.assertFalse(decision.passed)
        self.assertTrue(any("sha" in failure.lower() for failure in decision.failures))
        self.assertNotEqual(GOVERNED_ACTIVE_BANK_SHA256, ALTERED_SHA)

    def test_wg009_historical_baseline_with_zero_warnings_passes(self):
        decision = evaluate_production_warnings(BASELINE_BANK, [])
        self.assertTrue(decision.passed)
        self.assertEqual((), decision.failures)
        self.assertFalse(decision.governed)

    def test_wg010_historical_baseline_with_any_warning_fails(self):
        decision = evaluate_production_warnings(
            BASELINE_BANK,
            [FROZEN_WARNING],
            bank_sha256="unused-for-non-governed",
        )
        self.assertFalse(decision.passed)
        self.assertTrue(decision.failures)
        self.assertEqual(1, decision.unexpected_warning_count)

    def test_wg011_arbitrary_non_governed_bank_warning_fails_strict_default(self):
        decision = evaluate_production_warnings(
            Path("arbitrary_bank.json"),
            [EXTRA_WARNING],
            bank_sha256="abc123",
        )
        self.assertFalse(decision.passed)
        self.assertTrue(decision.failures)
        self.assertFalse(decision.governed)


class LintBankProductionGateTests(unittest.TestCase):
    def test_wg004_standard_active_lint_passes_and_reports_frozen_warning_counts(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            rc = lint_bank(
                ACTIVE_BANK,
                expected_count=454,
                fail_on_warnings=True,
                label="SC-900 default-bank lint",
            )
        combined = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(0, rc)
        self.assertIn("KNOWN_FROZEN_WARNING_COUNT = 1", combined)
        self.assertIn("UNEXPECTED_WARNING_COUNT = 0", combined)
        self.assertIn("Repeated answer-pattern bias", combined)
        self.assertIn("C streak on Q394-Q399 (6 in a row)", combined)

    def test_wg005_lint_fails_when_active_bank_has_an_additional_warning(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch(
                "tools.lint_bank.validate_bank",
                return_value={
                    "question_count": 454,
                    "issues": [],
                    "warnings": [FROZEN_WARNING, EXTRA_WARNING],
                },
            ),
            mock.patch("sys.stdout", stdout),
            mock.patch("sys.stderr", stderr),
        ):
            rc = lint_bank(
                ACTIVE_BANK,
                expected_count=454,
                fail_on_warnings=True,
                label="SC-900 default-bank lint",
            )
        self.assertEqual(1, rc)
        self.assertIn("failed", stderr.getvalue().lower())

    def test_wg006_lint_fails_when_active_bank_warning_is_substituted(self):
        with mock.patch(
            "tools.lint_bank.validate_bank",
            return_value={"question_count": 454, "issues": [], "warnings": [DIFFERENT_WARNING]},
        ), mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
            rc = lint_bank(
                ACTIVE_BANK,
                expected_count=454,
                fail_on_warnings=True,
                label="SC-900 default-bank lint",
            )
        self.assertEqual(1, rc)

    def test_wg007_lint_fails_when_expected_frozen_warning_disappears(self):
        with mock.patch(
            "tools.lint_bank.validate_bank",
            return_value={"question_count": 454, "issues": [], "warnings": []},
        ), mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
            rc = lint_bank(
                ACTIVE_BANK,
                expected_count=454,
                fail_on_warnings=True,
                label="SC-900 default-bank lint",
            )
        self.assertEqual(1, rc)

    def test_wg008_lint_fails_when_active_filename_has_altered_sha(self):
        with (
            mock.patch(
                "tools.lint_bank.validate_bank",
                return_value={"question_count": 454, "issues": [], "warnings": [FROZEN_WARNING]},
            ),
            mock.patch("tools.bank_warning_policy.hash_bank_file", return_value=ALTERED_SHA),
            mock.patch("sys.stdout", io.StringIO()),
            mock.patch("sys.stderr", io.StringIO()),
        ):
            rc = lint_bank(
                ACTIVE_BANK,
                expected_count=454,
                fail_on_warnings=True,
                label="SC-900 default-bank lint",
            )
        self.assertEqual(1, rc)

    def test_wg009_baseline_lint_passes_with_zero_warnings(self):
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", io.StringIO()):
            rc = lint_bank(
                BASELINE_BANK,
                expected_count=8,
                fail_on_warnings=True,
                label="SC-900 bank lint",
            )
        self.assertEqual(0, rc)
        self.assertIn("8 questions", stdout.getvalue())

    def test_wg010_baseline_lint_fails_on_any_warning(self):
        with mock.patch(
            "tools.lint_bank.validate_bank",
            return_value={"question_count": 8, "issues": [], "warnings": [EXTRA_WARNING]},
        ), mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
            rc = lint_bank(
                BASELINE_BANK,
                expected_count=8,
                fail_on_warnings=True,
                label="SC-900 bank lint",
            )
        self.assertEqual(1, rc)

    def test_wg012_allow_warnings_is_diagnostic_and_separate_from_production(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch(
                "tools.lint_bank.validate_bank",
                return_value={
                    "question_count": 454,
                    "issues": [],
                    "warnings": [FROZEN_WARNING, EXTRA_WARNING],
                },
            ),
            mock.patch("sys.stdout", stdout),
            mock.patch("sys.stderr", stderr),
        ):
            rc = lint_bank(
                ACTIVE_BANK,
                expected_count=454,
                fail_on_warnings=False,
                label="SC-900 default-bank lint",
            )
        combined = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(0, rc)
        self.assertIn("allow-warnings", combined.lower())
        self.assertNotIn("KNOWN_FROZEN_WARNING_COUNT = 1", combined)

    def test_standard_production_cli_passes_on_active_bank(self):
        result = subprocess.run(
            [sys.executable, "tools/lint_bank.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        combined = result.stdout + result.stderr
        self.assertEqual(0, result.returncode, combined)
        self.assertIn("KNOWN_FROZEN_WARNING_COUNT = 1", combined)
        self.assertIn("UNEXPECTED_WARNING_COUNT = 0", combined)


class SmokeWarningGateTests(unittest.TestCase):
    def test_wg013_smoke_accepts_only_the_exact_governed_warning_set(self):
        failures = release_bank_gate_failures(
            {
                "question_count": 454,
                "issues": [],
                "warnings": [FROZEN_WARNING],
            },
            ACTIVE_BANK,
        )
        self.assertEqual([], failures)

    def test_wg014_smoke_rejects_additional_warning(self):
        failures = release_bank_gate_failures(
            {
                "question_count": 454,
                "issues": [],
                "warnings": [FROZEN_WARNING, EXTRA_WARNING],
            },
            ACTIVE_BANK,
        )
        self.assertTrue(failures)

    def test_wg014_smoke_rejects_different_warning(self):
        failures = release_bank_gate_failures(
            {
                "question_count": 454,
                "issues": [],
                "warnings": [DIFFERENT_WARNING],
            },
            ACTIVE_BANK,
        )
        self.assertTrue(failures)

    def test_wg014_smoke_rejects_missing_expected_warning(self):
        failures = release_bank_gate_failures(
            {"question_count": 454, "issues": [], "warnings": []},
            ACTIVE_BANK,
        )
        self.assertTrue(failures)

    def test_smoke_still_fails_on_count_or_structural_issues(self):
        failures = release_bank_gate_failures(
            {
                "question_count": 453,
                "issues": [],
                "warnings": [FROZEN_WARNING],
            },
            ACTIVE_BANK,
        )
        self.assertTrue(any("454-question bank gate" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
