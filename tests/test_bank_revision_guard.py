from __future__ import annotations

import unittest

from tools.bank_revision_guard import compare_bank_invariants, compare_bias_metrics


def question(
    question_id: str,
    *,
    correct: list[str] | None = None,
    objective_code: str = "1.1",
    tier: str = "CORE",
    eligible: bool = True,
) -> dict:
    return {
        "id": question_id,
        "question_number": 1,
        "question_type": "single",
        "choices": {"A": "a", "B": "bb", "C": "ccc", "D": "dddd"},
        "correct": list(correct or ["A"]),
        "objective_code": objective_code,
        "exam_calibration_tier": tier,
        "exam_simulation_eligible": eligible,
    }


def metric_report(
    *,
    longest: float = 0.60,
    unique_longest: float = 0.60,
    shortest: float = 0.10,
    unique_shortest: float = 0.10,
    common_letter: float = 0.30,
    domain_longest: float = 0.60,
    domain_n: int = 25,
) -> dict:
    return {
        "strict_longest_correct_rate": longest,
        "unique_longest_heuristic_success_rate": unique_longest,
        "strict_shortest_correct_rate": shortest,
        "unique_shortest_heuristic_success_rate": unique_shortest,
        "most_common_answer_letter_rate": common_letter,
        "per_domain": {
            "D1": {
                "analyzable_count": domain_n,
                "strict_longest_correct_rate": domain_longest,
            }
        },
    }


class BankRevisionInvariantTests(unittest.TestCase):
    def test_identical_invariants_pass(self):
        baseline = [question("q1"), question("q2", correct=["B"], objective_code="2.1", tier="APPLIED")]
        candidate = [dict(row) for row in baseline]
        self.assertEqual([], compare_bank_invariants(baseline, candidate, expected_count=2))

    def test_question_removed_fails(self):
        failures = compare_bank_invariants([question("q1"), question("q2")], [question("q1")])
        self.assertTrue(any(item.startswith("QUESTION_IDS_REMOVED") for item in failures))
        self.assertTrue(any(item.startswith("QUESTION_COUNT_CHANGED") for item in failures))

    def test_question_added_fails(self):
        failures = compare_bank_invariants([question("q1")], [question("q1"), question("q2")])
        self.assertTrue(any(item.startswith("QUESTION_IDS_ADDED") for item in failures))
        self.assertTrue(any(item.startswith("QUESTION_COUNT_CHANGED") for item in failures))

    def test_canonical_id_change_fails_as_remove_and_add(self):
        failures = compare_bank_invariants([question("q1")], [question("q9")])
        self.assertTrue(any(item.startswith("QUESTION_IDS_REMOVED") for item in failures))
        self.assertTrue(any(item.startswith("QUESTION_IDS_ADDED") for item in failures))

    def test_correct_key_change_fails(self):
        failures = compare_bank_invariants([question("q1", correct=["A"])], [question("q1", correct=["B"])])
        self.assertTrue(any("CORRECT_KEYS_CHANGED" in item for item in failures))

    def test_objective_change_fails(self):
        failures = compare_bank_invariants([question("q1", objective_code="1.1")], [question("q1", objective_code="2.1")])
        self.assertTrue(any("OBJECTIVE_CODES_CHANGED" in item for item in failures))

    def test_tier_change_fails(self):
        failures = compare_bank_invariants([question("q1", tier="CORE")], [question("q1", tier="STRETCH")])
        self.assertTrue(any("TIERS_CHANGED" in item for item in failures))

    def test_exam_eligibility_change_fails(self):
        failures = compare_bank_invariants([question("q1", eligible=True)], [question("q1", eligible=False)])
        self.assertTrue(any("EXAM_ELIGIBILITY_CHANGED" in item for item in failures))

    def test_expected_count_mismatch_fails(self):
        failures = compare_bank_invariants([question("q1")], [question("q1")], expected_count=454)
        self.assertTrue(any(item.startswith("QUESTION_COUNT_CHANGED") for item in failures))


class BankRevisionBiasTests(unittest.TestCase):
    def test_tranche_requires_longest_metric_improvement(self):
        baseline = metric_report()
        candidate = metric_report()
        failures = compare_bias_metrics(baseline, candidate)
        self.assertTrue(any(item.startswith("NO_LONGEST_LEAKAGE_IMPROVEMENT") for item in failures))

    def test_tranche_allows_one_longest_metric_to_improve_while_other_is_nearly_flat(self):
        baseline = metric_report(longest=0.60, unique_longest=0.60)
        candidate = metric_report(longest=0.55, unique_longest=0.603)
        self.assertEqual([], compare_bias_metrics(baseline, candidate))

    def test_tranche_rejects_more_than_half_percent_worsening_in_other_longest_metric(self):
        baseline = metric_report(longest=0.60, unique_longest=0.60)
        candidate = metric_report(longest=0.55, unique_longest=0.606)
        failures = compare_bias_metrics(baseline, candidate)
        self.assertTrue(any(item.startswith("UNIQUE_LONGEST_WORSENED") for item in failures))

    def test_tranche_rejects_shortest_bias_substitution(self):
        baseline = metric_report(shortest=0.10, unique_shortest=0.10)
        candidate = metric_report(longest=0.55, shortest=0.121, unique_shortest=0.121)
        failures = compare_bias_metrics(baseline, candidate)
        self.assertTrue(any(item.startswith("STRICT_SHORTEST_BIAS_INCREASED") for item in failures))
        self.assertTrue(any(item.startswith("UNIQUE_SHORTEST_BIAS_INCREASED") for item in failures))

    def test_tranche_rejects_answer_letter_bias_substitution(self):
        baseline = metric_report(common_letter=0.30)
        candidate = metric_report(longest=0.55, common_letter=0.321)
        failures = compare_bias_metrics(baseline, candidate)
        self.assertTrue(any(item.startswith("ANSWER_LETTER_BIAS_INCREASED") for item in failures))

    def test_tranche_rejects_domain_worsening_when_domain_is_large_enough(self):
        baseline = metric_report(domain_longest=0.50, domain_n=25)
        candidate = metric_report(longest=0.55, domain_longest=0.551, domain_n=25)
        failures = compare_bias_metrics(baseline, candidate)
        self.assertTrue(any(item.startswith("DOMAIN_LONGEST_WORSENED") for item in failures))

    def test_small_domain_does_not_trigger_domain_worsening_gate(self):
        baseline = metric_report(domain_longest=0.50, domain_n=19)
        candidate = metric_report(longest=0.55, domain_longest=0.80, domain_n=19)
        self.assertEqual([], compare_bias_metrics(baseline, candidate))

    def test_final_gate_enforces_strong_thresholds(self):
        baseline = metric_report()
        candidate = metric_report(longest=0.40, unique_longest=0.40, domain_longest=0.46)
        failures = compare_bias_metrics(baseline, candidate, final_gate=True)
        self.assertTrue(any(item.startswith("FINAL_STRICT_LONGEST_TARGET_FAILED") for item in failures))
        self.assertTrue(any(item.startswith("FINAL_UNIQUE_LONGEST_TARGET_FAILED") for item in failures))
        self.assertTrue(any(item.startswith("FINAL_DOMAIN_LONGEST_TARGET_FAILED") for item in failures))

    def test_final_gate_passes_below_bank_thresholds_and_at_domain_ceiling(self):
        baseline = metric_report()
        candidate = metric_report(longest=0.39, unique_longest=0.39, domain_longest=0.45)
        self.assertEqual([], compare_bias_metrics(baseline, candidate, final_gate=True))


if __name__ == "__main__":
    unittest.main()
