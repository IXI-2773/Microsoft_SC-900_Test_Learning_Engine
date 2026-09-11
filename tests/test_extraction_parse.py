from __future__ import annotations

import unittest

from extraction.pages import PageText
from extraction.parse import parse_question_blocks


def _pages(*texts: str) -> tuple[PageText, ...]:
    return tuple(
        PageText(page_number=index, text=text, character_count=len(text), warnings=())
        for index, text in enumerate(texts, start=1)
    )


COMPLETE = """
Question 1
Which service provides cloud identity management?
A. Microsoft Purview
B. Microsoft Entra ID
C. Microsoft Defender
D. Microsoft Intune
Answer: B
Explanation: Microsoft Entra ID provides identity and access management.
Objective: entra_identity_types_and_function
Domain: microsoft_entra
"""


class ParseTests(unittest.TestCase):
    def test_parses_headers_choices_answer_and_explanation(self) -> None:
        records = parse_question_blocks(_pages(COMPLETE.strip()))
        self.assertEqual(1, len(records))
        record = records[0]
        self.assertEqual("Which service provides cloud identity management?", record.question_text)
        self.assertEqual(["A", "B", "C", "D"], [choice["id"] for choice in record.choices])
        self.assertEqual(["B"], list(record.source_answer))
        self.assertIn("Entra ID", record.source_explanation or "")
        self.assertEqual(1, record.source_page)
        self.assertEqual("entra_identity_types_and_function", record.objective)

    def test_supports_alternate_question_and_choice_markers(self) -> None:
        text = """
Q. 2 Which control evaluates Conditional Access?
(A) Microsoft Purview
B) Microsoft Entra ID
C: Microsoft Defender
D. Microsoft Sentinel
Correct answer: B
Rationale: Conditional Access is an Entra capability.
Objective: entra_identity_types_and_function
Domain: microsoft_entra
"""
        records = parse_question_blocks(_pages(text.strip()))
        self.assertEqual(1, len(records))
        self.assertEqual("Which control evaluates Conditional Access?", records[0].question_text)
        self.assertEqual(["B"], list(records[0].source_answer))

    def test_missing_answer_stays_unresolved(self) -> None:
        text = """
1. Which service stores audit logs?
A. Microsoft Entra ID
B. Microsoft Purview
C. Microsoft Defender
D. Microsoft Intune
Explanation: The source does not print a key.
Objective: entra_identity_types_and_function
Domain: microsoft_entra
"""
        records = parse_question_blocks(_pages(text.strip()))
        self.assertEqual([], list(records[0].source_answer))
        self.assertIn("UNRESOLVED_ANSWER", record_warnings := records[0].warnings)
        self.assertTrue(record_warnings)

    def test_malformed_duplicate_choice_labels_are_warned(self) -> None:
        text = """
Question 3
Which service is identity-related?
A. Microsoft Entra ID
A. Microsoft Purview
B. Microsoft Defender
C. Microsoft Intune
D. Microsoft Sentinel
Answer: A
Explanation: Duplicate labels are invalid.
Objective: entra_identity_types_and_function
Domain: microsoft_entra
"""
        records = parse_question_blocks(_pages(text.strip()))
        self.assertIn("DUPLICATE_CHOICE_LABELS", records[0].warnings)

    def test_multi_page_question_keeps_start_and_end_pages(self) -> None:
        page_one = "Question 4 Which service protects identities?\nA. Microsoft Purview\nB. Microsoft Entra ID"
        page_two = "C. Microsoft Defender\nD. Microsoft Intune\nAnswer: B\nExplanation: Entra ID.\nObjective: entra_identity_types_and_function\nDomain: microsoft_entra"
        records = parse_question_blocks(_pages(page_one, page_two))
        self.assertEqual(1, len(records))
        self.assertEqual(1, records[0].source_page)
        self.assertEqual(2, records[0].source_page_end)
        self.assertEqual(["B"], list(records[0].source_answer))

    def test_output_is_deterministic(self) -> None:
        first = parse_question_blocks(_pages(COMPLETE.strip()))
        second = parse_question_blocks(_pages(COMPLETE.strip()))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
