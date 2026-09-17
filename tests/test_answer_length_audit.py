from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.answer_length_audit import (
    analyze_bank,
    analyze_question,
    choice_length,
    normalize_choice_text,
    rank_longest_outliers,
    write_json_report,
    write_markdown_report,
)


def make_question(
    question_id: str,
    correct_letter: str,
    choices: dict[str, str],
    *,
    domain: str = "Domain A",
    question_number: int = 1,
) -> dict:
    return {
        "id": question_id,
        "question_number": question_number,
        "question_type": "single",
        "domain": domain,
        "choices": dict(choices),
        "correct": [correct_letter],
    }


class AnswerLengthAuditTests(unittest.TestCase):
    def test_choice_length_normalizes_whitespace_only(self):
        self.assertEqual("alpha beta!", normalize_choice_text("  alpha\n beta!  "))
        self.assertEqual((11, 2), choice_length("  alpha\n beta!  "))

    def test_single_answer_question_reports_length_metrics(self):
        question = make_question(
            "q1",
            "B",
            {
                "A": "short",
                "B": "the clearly much longer correct choice",
                "C": "medium text",
                "D": "other",
            },
        )
        row = analyze_question(question)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertTrue(row["correct_is_strict_longest"])
        self.assertTrue(row["correct_is_among_longest"])
        self.assertFalse(row["correct_is_strict_shortest"])
        self.assertEqual("B", row["correct_letter"])
        self.assertGreater(row["correct_characters"], row["max_distractor_characters"])
        self.assertGreater(row["absolute_gap"], 0)
        self.assertGreater(row["relative_gap"], 0)
        self.assertEqual("q1", row["question_id"])

    def test_non_single_or_invalid_questions_are_not_analyzable(self):
        cases = [
            {"id": "q2", "question_type": "multiple", "choices": {"A": "x", "B": "y"}, "correct": ["A", "B"]},
            {"id": "q3", "question_type": "single", "choices": {"A": "x", "B": "y"}, "correct": []},
            {"id": "q4", "question_type": "single", "choices": {"A": "x", "B": "y"}, "correct": ["C"]},
            {"id": "q5", "question_type": "single", "choices": {"A": "x", "B": ""}, "correct": ["A"]},
        ]
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertIsNone(analyze_question(case))

    def test_ties_are_not_strict_longest_or_shortest(self):
        row = analyze_question(
            make_question("q6", "A", {"A": "abcd", "B": "abcd", "C": "xx", "D": "yy"})
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertFalse(row["correct_is_strict_longest"])
        self.assertTrue(row["correct_is_among_longest"])
        self.assertFalse(row["correct_is_strict_shortest"])

    def test_bank_metrics_detect_longest_and_shortest_heuristics(self):
        questions = [
            make_question(
                "q1",
                "A",
                {"A": "123456789", "B": "12", "C": "123", "D": "1234"},
                domain="D1",
                question_number=1,
            ),
            make_question(
                "q2",
                "D",
                {"A": "123456", "B": "12345", "C": "1234", "D": "1"},
                domain="D1",
                question_number=2,
            ),
        ]
        report = analyze_bank(questions)
        self.assertEqual(2, report["question_count"])
        self.assertEqual(2, report["analyzable_count"])
        self.assertEqual(0.5, report["strict_longest_correct_rate"])
        self.assertEqual(0.5, report["strict_shortest_correct_rate"])
        self.assertEqual(0.5, report["unique_longest_heuristic_success_rate"])
        self.assertEqual(0.5, report["unique_shortest_heuristic_success_rate"])
        self.assertEqual({"A": 1, "D": 1}, report["correct_letter_distribution"])
        self.assertEqual(0.5, report["most_common_answer_letter_rate"])
        self.assertEqual(2, report["per_domain"]["D1"]["analyzable_count"])

    def test_outlier_ranking_is_deterministic_by_relative_then_absolute_gap(self):
        rows = [
            {"question_id": "b", "absolute_gap": 20, "relative_gap": 0.5},
            {"question_id": "a", "absolute_gap": 10, "relative_gap": 0.5},
            {"question_id": "c", "absolute_gap": 5, "relative_gap": 0.75},
            {"question_id": "ignored", "absolute_gap": 0, "relative_gap": 1.0},
        ]
        ranked = rank_longest_outliers(rows)
        self.assertEqual(["c", "b", "a"], [row["question_id"] for row in ranked])

    def test_reports_are_deterministic_and_do_not_emit_answer_text(self):
        report = analyze_bank(
            [
                make_question(
                    "q1",
                    "A",
                    {"A": "a deliberately distinctive secret correct text", "B": "bb", "C": "ccc", "D": "dddd"},
                    domain="D1",
                )
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_a = root / "a.json"
            json_b = root / "b.json"
            md = root / "report.md"
            write_json_report(report, json_a)
            write_json_report(report, json_b)
            write_markdown_report(report, md)
            self.assertEqual(json_a.read_bytes(), json_b.read_bytes())
            loaded = json.loads(json_a.read_text(encoding="utf-8"))
            self.assertEqual(report, loaded)
            markdown = md.read_text(encoding="utf-8")
            self.assertIn("q1", markdown)
            self.assertNotIn("distinctive secret correct text", markdown)


if __name__ == "__main__":
    unittest.main()
