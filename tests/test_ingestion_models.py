import unittest

from ingestion.models import ValidationError, canonicalize_record, load_taxonomy


class IngestionModelTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        self.record = {
            "exam": "SC-900",
            "domain": "microsoft_entra",
            "objective": "entra_identity_access",
            "difficulty": "beginner",
            "type": "multiple_choice",
            "stem": "Which service provides cloud identity management?",
            "choices": [
                {"id": "a", "text": "Microsoft Purview"},
                {"id": "b", "text": "Microsoft Entra ID"},
            ],
            "correct_answer": "b",
            "explanation": "Microsoft Entra ID provides identity and access management.",
            "source": {"book_id": "book-1", "title": "SC-900 Guide", "page": 42},
            "tags": ["identity"],
            "metadata": {"origin": "extracted", "extractor_version": "1.0"},
        }

    def test_canonical_question_has_deterministic_id_and_provenance(self):
        first = canonicalize_record(self.record, self.taxonomy)
        second = canonicalize_record(self.record, self.taxonomy)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual("question", first["record_kind"])
        self.assertEqual("extracted", first["provenance"]["origin"])
        self.assertEqual("SC-900", first["exam"])

    def test_rejects_malformed_question_with_actionable_reason(self):
        invalid = dict(self.record, stem="", correct_answer="z")
        with self.assertRaises(ValidationError) as error:
            canonicalize_record(invalid, self.taxonomy)
        self.assertIn("MISSING_STEM", error.exception.reason_codes)
        self.assertIn("INVALID_CORRECT_ANSWER", error.exception.reason_codes)

    def test_rejects_duplicate_normalized_choices_and_unknown_objective(self):
        invalid = dict(
            self.record,
            objective="not-a-real-objective",
            choices=[{"id": "a", "text": "Same answer"}, {"id": "b", "text": " same  answer "}],
        )
        with self.assertRaises(ValidationError) as error:
            canonicalize_record(invalid, self.taxonomy)
        self.assertIn("DUPLICATE_CHOICES", error.exception.reason_codes)
        self.assertIn("INVALID_OBJECTIVE", error.exception.reason_codes)


if __name__ == "__main__":
    unittest.main()
