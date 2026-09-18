import copy
import json
import unittest

from answer_length_audit import audit_questions, ranked_strict_longest_outliers


class AnswerLengthAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = [
            {
                "id": "q-alpha-long",
                "domain": "alpha",
                "choices": {"A": "aaaaaa", "B": "bb", "C": "ccc", "D": "dddd"},
                "correct": ["A"],
            },
            {
                "id": "q-beta-short",
                "domain": "beta",
                "choices": {"A": "aaaaa", "B": "b", "C": "ccc", "D": "dddd"},
                "correct": ["B"],
            },
            {
                "id": "q-alpha-tied",
                "domain": "alpha",
                "choices": {"A": "aa", "B": "bb", "C": "cc", "D": "dd"},
                "correct": ["C"],
            },
            {
                "id": "q-beta-middle",
                "domain": "beta",
                "choices": {"A": "a", "B": "bbbbbb", "C": "cccc", "D": "ddd"},
                "correct": ["D"],
            },
        ]

    def test_core_metrics_use_explicit_applicable_denominators(self):
        result = audit_questions(self.fixtures)

        self.assertEqual(result["question_count"], 4)
        self.assertEqual(result["analyzable_single_answer"], 4)
        self.assertEqual(result["strict_longest_correct"]["count"], 1)
        self.assertEqual(result["strict_shortest_correct"]["count"], 1)
        self.assertEqual(result["unique_longest_heuristic"]["denominator"], 3)
        self.assertEqual(result["unique_shortest_heuristic"]["denominator"], 3)

    def test_length_rules_strip_outer_whitespace_and_split_words(self):
        questions = [
            {
                "id": "q-spaces",
                "domain": "spacing",
                "choices": {
                    "A": "  one two  ",
                    "B": "three",
                    "C": "four",
                    "D": "five",
                },
                "correct": "A",
            }
        ]

        row = ranked_strict_longest_outliers(questions)[0]

        self.assertEqual(row["char_lengths"], {"A": 7, "B": 5, "C": 4, "D": 4})
        self.assertEqual(row["word_lengths"], {"A": 2, "B": 1, "C": 1, "D": 1})

    def test_tied_outlier_severity_uses_canonical_question_id(self):
        questions = [
            {
                "id": "q-zeta",
                "domain": "ties",
                "choices": {"A": "aaaa", "B": "b", "C": "cc", "D": "dd"},
                "correct": ["A"],
            },
            {
                "id": "q-alpha",
                "domain": "ties",
                "choices": {"D": "dd", "C": "cc", "B": "b", "A": "aaaa"},
                "correct": ["A"],
            },
        ]

        rows = ranked_strict_longest_outliers(questions)

        self.assertEqual([row["question_id"] for row in rows], ["q-alpha", "q-zeta"])
        self.assertEqual([row["absolute_gap"] for row in rows], [2, 2])
        self.assertEqual([row["relative_gap"] for row in rows], [1.0, 1.0])

    def test_domain_metrics_use_bank_level_denominator_rules(self):
        result = audit_questions(self.fixtures)

        self.assertEqual(result["domains"]["alpha"]["question_count"], 2)
        self.assertEqual(result["domains"]["alpha"]["analyzable_single_answer"], 2)
        self.assertEqual(result["domains"]["alpha"]["unique_longest_heuristic"]["denominator"], 1)
        self.assertEqual(result["domains"]["alpha"]["unique_shortest_heuristic"]["denominator"], 1)
        self.assertEqual(result["domains"]["beta"]["unique_longest_heuristic"]["denominator"], 2)
        self.assertEqual(result["domains"]["beta"]["unique_shortest_heuristic"]["denominator"], 2)

    def test_correct_letter_counts_match_fixture_truth(self):
        result = audit_questions(self.fixtures)

        self.assertEqual(result["correct_letter_counts"], {"A": 1, "B": 1, "C": 1, "D": 1})

    def test_malformed_choice_mappings_are_skipped_deterministically(self):
        malformed = [
            {
                "id": "q-extra-key",
                "domain": "invalid",
                "choices": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
                "correct": ["A"],
            },
            {
                "id": "q-missing-key",
                "domain": "invalid",
                "choices": {"A": "a", "B": "b", "C": "c"},
                "correct": ["A"],
            },
            {
                "id": "q-nonstring-choice",
                "domain": "invalid",
                "choices": {"A": "a", "B": "b", "C": "c", "D": 4},
                "correct": ["A"],
            },
            {"id": "q-no-choices", "domain": "invalid", "correct": ["A"]},
        ]

        result = audit_questions(list(reversed(malformed)))

        self.assertEqual(result["analyzable_single_answer"], 0)
        self.assertEqual(
            result["skipped_question_ids"],
            ["q-extra-key", "q-missing-key", "q-no-choices", "q-nonstring-choice"],
        )
        self.assertEqual(result["domains"]["invalid"]["question_count"], 4)
        self.assertEqual(result["domains"]["invalid"]["analyzable_single_answer"], 0)

    def test_invalid_multiple_and_unresolved_correct_answers_are_skipped(self):
        invalid = [
            {
                "id": "q-empty",
                "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct": [],
            },
            {
                "id": "q-multiple",
                "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct": ["A", "B"],
            },
            {
                "id": "q-unresolved",
                "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct": ["E"],
            },
            {
                "id": "q-nonscalar",
                "choices": {"A": "a", "B": "b", "C": "c", "D": "d"},
                "correct": {"A": True},
            },
        ]

        result = audit_questions(invalid)

        self.assertEqual(result["analyzable_single_answer"], 0)
        self.assertEqual(result["skipped_question_ids"], ["q-empty", "q-multiple", "q-nonscalar", "q-unresolved"])

    def test_audit_does_not_mutate_inputs(self):
        before = copy.deepcopy(self.fixtures)

        audit_questions(self.fixtures)
        ranked_strict_longest_outliers(self.fixtures)

        self.assertEqual(self.fixtures, before)

    def test_result_is_strict_json_serializable_in_zero_denominator_case(self):
        result = audit_questions(
            [
                {
                    "id": "q-invalid",
                    "domain": "empty",
                    "choices": {"A": "a", "B": "b", "C": "c"},
                    "correct": ["A"],
                }
            ]
        )

        encoded = json.dumps(result, allow_nan=False, sort_keys=True)

        self.assertIsInstance(encoded, str)
        self.assertEqual(result["strict_longest_correct"]["rate"], 0.0)
        self.assertEqual(result["unique_longest_heuristic"]["rate"], 0.0)
        self.assertEqual(result["mean_correct_chars"], 0.0)

    def test_ranking_and_full_result_are_stable_across_repeated_runs(self):
        first_audit = audit_questions(self.fixtures)
        first_ranking = ranked_strict_longest_outliers(self.fixtures)

        for _ in range(5):
            self.assertEqual(audit_questions(self.fixtures), first_audit)
            self.assertEqual(ranked_strict_longest_outliers(self.fixtures), first_ranking)


if __name__ == "__main__":
    unittest.main()
