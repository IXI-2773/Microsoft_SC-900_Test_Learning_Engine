import copy
import unittest

from ingestion.bank_quality import phase1_review_status, validate_phase1_question
from ingestion.models import ValidationError, load_taxonomy


def valid_phase1_question():
    source_url = "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-mfa-howitworks"
    return {
        "id": "q_phase1_test",
        "record_kind": "question",
        "exam": "SC-900",
        "domain": "microsoft_entra",
        "objective": "entra_authentication",
        "subobjective": "multifactor authentication",
        "difficulty": "beginner",
        "type": "multiple_choice",
        "stem": "Which control requires more than one category of credential before access is granted?",
        "choices": [
            {"id": "a", "text": "Multifactor authentication"},
            {"id": "b", "text": "Single sign-on"},
        ],
        "correct_answer": ["a"],
        "explanation": "Multifactor authentication requires two or more verification factors.",
        "references": [source_url],
        "tags": ["entra", "authentication"],
        "metadata": {
            "blueprint_leaf_id": "multifactor_authentication",
            "source_authority": "microsoft_learn",
            "source_urls": [source_url],
            "source_retrieved_at": "2026-09-11",
            "source_family_id": "learn-entra-authentication",
            "semantic_family_id": "entra-mfa-purpose",
            "stem_style": "short_scenario",
            "future_probe_suitability": "eligible",
            "authoring_origin": "original_from_official_source",
        },
        "promotion_status": "pending",
    }


class SC900BankQualityTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()

    def assert_reason(self, record, code):
        with self.assertRaises(ValidationError) as caught:
            validate_phase1_question(record, self.taxonomy)
        self.assertIn(code, caught.exception.reason_codes)

    def test_valid_phase1_question_passes(self):
        validate_phase1_question(valid_phase1_question(), self.taxonomy)

    def test_requires_blueprint_leaf(self):
        record = valid_phase1_question()
        del record["metadata"]["blueprint_leaf_id"]
        self.assert_reason(record, "MISSING_BLUEPRINT_LEAF")

    def test_rejects_leaf_objective_mismatch(self):
        record = valid_phase1_question()
        record["metadata"]["blueprint_leaf_id"] = "azure_key_vault"
        self.assert_reason(record, "BLUEPRINT_LEAF_OBJECTIVE_MISMATCH")

    def test_rejects_non_https_or_non_microsoft_source_url(self):
        for url in (
            "http://learn.microsoft.com/en-us/entra/identity/authentication/concept-mfa-howitworks",
            "https://example.com/sc900",
        ):
            with self.subTest(url=url):
                record = valid_phase1_question()
                record["metadata"]["source_urls"] = [url]
                record["references"] = [url]
                self.assert_reason(record, "INVALID_SOURCE_URL")

    def test_requires_source_and_semantic_family_ids(self):
        for field, code in (
            ("source_family_id", "MISSING_SOURCE_FAMILY"),
            ("semantic_family_id", "MISSING_SEMANTIC_FAMILY"),
        ):
            with self.subTest(field=field):
                record = valid_phase1_question()
                record["metadata"][field] = ""
                self.assert_reason(record, code)

    def test_rejects_invalid_stem_style(self):
        record = valid_phase1_question()
        record["metadata"]["stem_style"] = "trick_question"
        self.assert_reason(record, "INVALID_STEM_STYLE")

    def test_rejects_invalid_probe_suitability(self):
        record = valid_phase1_question()
        record["metadata"]["future_probe_suitability"] = "probe_now"
        self.assert_reason(record, "INVALID_PROBE_SUITABILITY")

    def test_rejects_wrong_authoring_origin(self):
        record = valid_phase1_question()
        record["metadata"]["authoring_origin"] = "copied_assessment"
        self.assert_reason(record, "INVALID_AUTHORING_ORIGIN")

    def test_requires_references(self):
        record = valid_phase1_question()
        record["references"] = []
        self.assert_reason(record, "MISSING_REFERENCE")

    def test_rejects_practice_or_module_assessment_sources(self):
        for url in (
            "https://learn.microsoft.com/en-us/credentials/certifications/practice-assessments-for-microsoft-certifications",
            "https://learn.microsoft.com/en-us/training/modules/example/assessment",
            "https://learn.microsoft.com/en-us/training/modules/example/knowledge-check",
        ):
            with self.subTest(url=url):
                record = valid_phase1_question()
                record["metadata"]["source_urls"] = [url]
                record["references"] = [url]
                self.assert_reason(record, "ASSESSMENT_SOURCE_PROHIBITED")

    def test_source_authority_and_retrieval_date_are_required(self):
        record = valid_phase1_question()
        record["metadata"]["source_authority"] = "blog"
        self.assert_reason(record, "INVALID_SOURCE_AUTHORITY")

        record = valid_phase1_question()
        record["metadata"]["source_retrieved_at"] = ""
        self.assert_reason(record, "MISSING_SOURCE_RETRIEVED_AT")

    def test_review_status_is_derived_from_promotion_status(self):
        self.assertEqual("pending", phase1_review_status({"promotion_status": "pending"}))
        self.assertEqual("approved", phase1_review_status({"promotion_status": "approved"}))
        self.assertEqual("withheld", phase1_review_status({"promotion_status": "withheld"}))
        self.assertEqual("pending", phase1_review_status({"promotion_status": "unknown"}))
        self.assertEqual("pending", phase1_review_status({}))


if __name__ == "__main__":
    unittest.main()
