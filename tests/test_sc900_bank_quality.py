import copy
import unittest

from ingestion.bank_quality import phase1_review_status, validate_phase1_question
from ingestion.models import ValidationError, load_taxonomy
from tools.validate_sc900_phase1 import validate_phase1_set, validate_source_inventory


EXPECTED_OBJECTIVE_COUNTS = {
    "security_compliance_concepts": 3,
    "identity_concepts": 3,
    "entra_identity_types_and_function": 3,
    "entra_authentication": 4,
    "entra_access_management": 3,
    "entra_identity_protection_governance": 4,
    "azure_infrastructure_security": 6,
    "azure_security_management": 4,
    "microsoft_sentinel": 3,
    "defender_xdr": 6,
    "service_trust_privacy": 2,
    "purview_compliance_management": 2,
    "purview_information_protection_lifecycle": 4,
    "purview_insider_risk_ediscovery_audit": 3,
}

EXPECTED_DOMAIN_COUNTS = {
    "security_compliance_identity": 6,
    "microsoft_entra": 14,
    "microsoft_security_solutions": 19,
    "microsoft_compliance_solutions": 11,
}


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


def valid_source_inventory(taxonomy):
    details = {row["id"]: row for row in taxonomy["objective_details"]}
    sources = []
    for objective_id, detail in details.items():
        sources.append(
            {
                "source_id": f"study-guide-{objective_id}",
                "url": "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900",
                "title": f"SC-900 study guide - {objective_id}",
                "source_type": "study_guide",
                "objective_ids": [objective_id],
                "leaf_ids": [leaf["id"] for leaf in detail["leaf_skills"]],
                "retrieved_at": "2026-09-11",
                "assessment_content_used": False,
            }
        )
    return {
        "exam": "SC-900",
        "skills_effective_date": "2026-07-28",
        "inventory_frozen_at": "2026-09-11",
        "authority": "Microsoft Learn / official Microsoft documentation",
        "sources": sources,
    }


def approved_phase1_set(taxonomy):
    objective_owner = {
        objective: domain["id"]
        for domain in taxonomy["domains"]
        for objective in domain["objectives"]
    }
    leaves_by_objective = {
        row["id"]: [leaf["id"] for leaf in row["leaf_skills"]]
        for row in taxonomy["objective_details"]
    }
    source_url = "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900"
    questions = []
    reviews = []
    serial = 0
    for objective, count in EXPECTED_OBJECTIVE_COUNTS.items():
        leaves = leaves_by_objective[objective]
        for offset in range(count):
            serial += 1
            leaf = leaves[offset % len(leaves)]
            question_id = f"q_phase1_{serial:03d}"
            questions.append(
                {
                    "id": question_id,
                    "record_kind": "question",
                    "exam": "SC-900",
                    "domain": objective_owner[objective],
                    "objective": objective,
                    "subobjective": leaf,
                    "difficulty": "beginner",
                    "type": "multiple_choice",
                    "stem": f"Original structural test question {serial}?",
                    "choices": [
                        {"id": "a", "text": "Correct choice"},
                        {"id": "b", "text": "Distractor"},
                    ],
                    "correct_answer": ["a"],
                    "explanation": "Structural test explanation.",
                    "references": [source_url],
                    "tags": [objective],
                    "metadata": {
                        "blueprint_leaf_id": leaf,
                        "source_authority": "microsoft_learn",
                        "source_urls": [source_url],
                        "source_retrieved_at": "2026-09-11",
                        "source_family_id": f"source-{objective}",
                        "semantic_family_id": f"family-{serial:03d}",
                        "stem_style": "direct_concept",
                        "future_probe_suitability": "eligible",
                        "authoring_origin": "original_from_official_source",
                    },
                    "promotion_status": "approved",
                }
            )
            reviews.append(
                {
                    "question_id": question_id,
                    "factual_source_checked": True,
                    "objective_leaf_checked": True,
                    "correct_answer_unique": True,
                    "all_distractors_defensibly_wrong": True,
                    "explanation_supported": True,
                    "originality_boundary_checked": True,
                    "duplicate_reviewed": True,
                    "semantic_family_reviewed": True,
                    "probe_suitability_reviewed": True,
                    "reviewer": "test-reviewer",
                    "reviewed_at": "2026-09-11T00:00:00Z",
                    "disposition": "approved",
                    "notes": "",
                }
            )
    return questions, reviews


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

    def test_valid_source_inventory_covers_all_14_objectives_and_known_leaves(self):
        inventory = valid_source_inventory(self.taxonomy)
        self.assertEqual([], validate_source_inventory(inventory, self.taxonomy))

    def test_source_inventory_rejects_unknown_leaf_unofficial_assessment_and_missing_objective_coverage(self):
        inventory = valid_source_inventory(self.taxonomy)
        inventory["sources"][0]["leaf_ids"].append("not-a-real-leaf")
        inventory["sources"][1]["url"] = "https://example.com/sc900"
        inventory["sources"][2]["url"] = "https://learn.microsoft.com/en-us/training/modules/example/assessment"
        inventory["sources"] = [
            row
            for row in inventory["sources"]
            if "defender_xdr" not in row["objective_ids"]
        ]
        codes = {error["code"] for error in validate_source_inventory(inventory, self.taxonomy)}
        self.assertIn("UNKNOWN_SOURCE_LEAF", codes)
        self.assertIn("INVALID_SOURCE_URL", codes)
        self.assertIn("ASSESSMENT_SOURCE_PROHIBITED", codes)
        self.assertIn("MISSING_OBJECTIVE_SOURCE", codes)

    def test_complete_phase1_set_requires_exact_50_and_frozen_allocations(self):
        questions, reviews = approved_phase1_set(self.taxonomy)
        result = validate_phase1_set(questions, self.taxonomy, reviews)
        self.assertEqual("PHASE_1_ACCEPTED", result["status"])
        self.assertEqual(50, result["approved_count"])
        self.assertEqual(EXPECTED_DOMAIN_COUNTS, result["domain_counts"])
        self.assertEqual(EXPECTED_OBJECTIVE_COUNTS, result["objective_counts"])
        self.assertEqual([], result["quality_errors"])

    def test_pending_items_do_not_count_toward_phase1_acceptance(self):
        questions, reviews = approved_phase1_set(self.taxonomy)
        questions[-1]["promotion_status"] = "pending"
        result = validate_phase1_set(questions, self.taxonomy, reviews)
        self.assertEqual("PHASE_1_INCOMPLETE", result["status"])
        self.assertEqual(49, result["approved_count"])
        self.assertEqual(1, result["pending_count"])

    def test_phase1_set_rejects_missing_review_receipt_and_wrong_distribution(self):
        questions, reviews = approved_phase1_set(self.taxonomy)
        reviews.pop()
        questions[-1]["domain"] = "microsoft_entra"
        result = validate_phase1_set(questions, self.taxonomy, reviews)
        codes = {error["code"] for error in result["quality_errors"]}
        self.assertEqual("PHASE_1_INCOMPLETE", result["status"])
        self.assertIn("MISSING_REVIEW_RECEIPT", codes)
        self.assertIn("DOMAIN_ALLOCATION_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
