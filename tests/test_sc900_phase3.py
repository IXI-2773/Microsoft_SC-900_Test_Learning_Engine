import copy
import importlib
import importlib.util
import unittest

from ingestion.models import load_taxonomy


PHASE1_OBJECTIVE_COUNTS = {
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

EXPECTED_PHASE3_OBJECTIVE_COUNTS = {
    key: value * 4 for key, value in PHASE1_OBJECTIVE_COUNTS.items()
}
EXPECTED_PHASE3_DOMAIN_COUNTS = {
    "security_compliance_identity": 24,
    "microsoft_entra": 56,
    "microsoft_security_solutions": 76,
    "microsoft_compliance_solutions": 44,
}
REVIEW_FIELDS = (
    "factual_source_checked",
    "objective_leaf_checked",
    "correct_answer_unique",
    "all_distractors_defensibly_wrong",
    "explanation_supported",
    "originality_boundary_checked",
    "duplicate_reviewed",
    "semantic_family_reviewed",
    "probe_suitability_reviewed",
)
SOURCE_URL = "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900"


def _load_phase3_module(testcase):
    testcase.assertIsNotNone(
        importlib.util.find_spec("tools.validate_sc900_phase3"),
        "tools.validate_sc900_phase3 must exist",
    )
    return importlib.import_module("tools.validate_sc900_phase3")


def _question(serial, phase, objective, domain, leaf):
    return {
        "id": f"q_{phase}_{serial:03d}",
        "record_kind": "question",
        "exam": "SC-900",
        "domain": domain,
        "objective": objective,
        "subobjective": leaf,
        "difficulty": "beginner",
        "type": "multiple_choice",
        "stem": f"Synthetic Phase 3 structural question {phase}-{serial}?",
        "choices": [
            {"id": "a", "text": "Correct choice"},
            {"id": "b", "text": "Distractor"},
        ],
        "correct_answer": ["a"],
        "explanation": "Synthetic structural test explanation.",
        "references": [SOURCE_URL],
        "tags": [objective],
        "source": {"title": "Microsoft Learn", "url": SOURCE_URL},
        "metadata": {
            "blueprint_leaf_id": leaf,
            "source_authority": "microsoft_learn",
            "source_urls": [SOURCE_URL],
            "source_retrieved_at": "2026-09-11",
            "source_family_id": f"source-{objective}",
            "semantic_family_id": f"family-{phase}-{serial:03d}",
            "stem_style": "direct_concept",
            "future_probe_suitability": "eligible",
            "authoring_origin": "original_from_official_source",
        },
        "promotion_status": "approved",
    }


def _review(question, *, phase3=False):
    receipt = {
        "question_id": question["id"],
        "reviewer": "openai-gpt5.6-sol-separate-adversarial-review",
        "review_method": "separate adversarial review pass after authoring",
        "reviewed_at": "2026-09-11T00:00:00Z",
        "disposition": "approved",
        "notes": "",
    }
    receipt.update({field: True for field in REVIEW_FIELDS})
    if phase3:
        from tools.build_sc900_phase2 import review_content_sha256

        receipt["reviewed_content_sha256"] = review_content_sha256(question)
    return receipt


def _complete_phase3_set(taxonomy):
    objective_owner = {
        objective: domain["id"]
        for domain in taxonomy["domains"]
        for objective in domain["objectives"]
    }
    leaves_by_objective = {
        row["id"]: [leaf["id"] for leaf in row["leaf_skills"]]
        for row in taxonomy["objective_details"]
    }
    questions = []
    reviews = []
    phase3_ids = []
    predecessor_serial = 0
    phase3_serial = 0
    for objective, base_count in PHASE1_OBJECTIVE_COUNTS.items():
        leaves = leaves_by_objective[objective]
        predecessor_count = base_count * 2
        increment_count = base_count * 2
        for offset in range(predecessor_count):
            predecessor_serial += 1
            question = _question(
                predecessor_serial,
                "pre",
                objective,
                objective_owner[objective],
                leaves[offset % len(leaves)],
            )
            questions.append(question)
            reviews.append(_review(question))
        for offset in range(increment_count):
            phase3_serial += 1
            question = _question(
                phase3_serial,
                "p3",
                objective,
                objective_owner[objective],
                leaves[(predecessor_count + offset) % len(leaves)],
            )
            questions.append(question)
            reviews.append(_review(question, phase3=True))
            phase3_ids.append(question["id"])
    return questions, reviews, phase3_ids


def _inventory_for(taxonomy):
    objective_ids = [
        objective
        for domain in taxonomy["domains"]
        for objective in domain["objectives"]
    ]
    leaf_ids = [
        leaf["id"]
        for row in taxonomy["objective_details"]
        for leaf in row["leaf_skills"]
    ]
    return {
        "authority": "Microsoft Learn / official Microsoft documentation",
        "exam": "SC-900",
        "inventory_frozen_at": "2026-09-11",
        "per_question_source_join_required": True,
        "skills_effective_date": taxonomy["skills_effective_date"],
        "sources": [
            {
                "assessment_content_used": False,
                "leaf_ids": leaf_ids,
                "objective_ids": objective_ids,
                "retrieved_at": "2026-09-11",
                "source_id": "study-guide",
                "source_type": "study_guide",
                "title": "Study guide for Exam SC-900",
                "url": SOURCE_URL,
            }
        ],
    }


class SC900Phase3StructuralTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()

    def test_phase3_validator_module_exists(self):
        _load_phase3_module(self)

    def test_complete_phase3_set_requires_200_total_and_100_new_approvals(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        result = module.validate_phase3_set(
            questions,
            self.taxonomy,
            reviews,
            phase3_ids,
            source_inventory=_inventory_for(self.taxonomy),
        )
        self.assertEqual("PHASE_3_TASK12_READY", result["status"])
        self.assertEqual(200, result["approved_count"])
        self.assertEqual(100, result["phase3_new_approved_count"])
        self.assertEqual(58, result["distinct_leaf_count"])
        self.assertEqual(EXPECTED_PHASE3_DOMAIN_COUNTS, result["domain_counts"])
        self.assertEqual(EXPECTED_PHASE3_OBJECTIVE_COUNTS, result["objective_counts"])
        self.assertEqual([], result["quality_errors"])

    def test_rejects_wrong_total_and_new_counts(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        removed = questions.pop()
        reviews = [row for row in reviews if row["question_id"] != removed["id"]]
        phase3_ids.remove(removed["id"])
        result = module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        codes = {row["code"] for row in result["quality_errors"]}
        self.assertIn("APPROVED_COUNT_MISMATCH", codes)
        self.assertIn("PHASE3_NEW_APPROVED_COUNT_MISMATCH", codes)

    def test_phase3_id_set_must_be_exactly_100_unique_ids(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        bad_ids = phase3_ids[:-1] + [phase3_ids[0]]
        result = module.validate_phase3_set(questions, self.taxonomy, reviews, bad_ids)
        self.assertIn(
            "PHASE3_BATCH_ID_SET_INVALID",
            {row["code"] for row in result["quality_errors"]},
        )

    def test_rejects_duplicate_approved_id(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        questions[-1]["id"] = questions[-2]["id"]
        result = module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        self.assertIn(
            "DUPLICATE_APPROVED_ID",
            {row["code"] for row in result["quality_errors"]},
        )

    def test_terminal_acceptance_rejects_pending_and_withheld_records(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        pending = copy.deepcopy(questions[0])
        pending["id"] = "pending-extra"
        pending["promotion_status"] = "pending"
        result = module.validate_phase3_set(questions + [pending], self.taxonomy, reviews, phase3_ids)
        self.assertIn("PENDING_RECORDS_PRESENT", {row["code"] for row in result["quality_errors"]})
        withheld = copy.deepcopy(questions[0])
        withheld["id"] = "withheld-extra"
        withheld["promotion_status"] = "withheld"
        result = module.validate_phase3_set(questions + [withheld], self.taxonomy, reviews, phase3_ids)
        self.assertIn("WITHHELD_RECORDS_PRESENT", {row["code"] for row in result["quality_errors"]})

    def test_rejects_wrong_domain_and_objective_allocation(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        questions[-1]["domain"] = "microsoft_entra"
        questions[-1]["objective"] = "entra_authentication"
        result = module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        codes = {row["code"] for row in result["quality_errors"]}
        self.assertIn("DOMAIN_ALLOCATION_MISMATCH", codes)
        self.assertIn("OBJECTIVE_ALLOCATION_MISMATCH", codes)

    def test_requires_all_58_blueprint_leaves(self):
        module = _load_phase3_module(self)
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        target_leaf = questions[0]["metadata"]["blueprint_leaf_id"]
        replacement_leaf = questions[1]["metadata"]["blueprint_leaf_id"]
        for question in questions:
            if question["metadata"]["blueprint_leaf_id"] == target_leaf:
                question["metadata"]["blueprint_leaf_id"] = replacement_leaf
                question["subobjective"] = replacement_leaf
        result = module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        self.assertIn(
            "BLUEPRINT_LEAF_COVERAGE_MISMATCH",
            {row["code"] for row in result["quality_errors"]},
        )


class SC900Phase3CustodyAndProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        self.module = _load_phase3_module(self)

    def test_missing_phase3_review_receipt_fails_closed(self):
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        reviews = [row for row in reviews if row["question_id"] != phase3_ids[0]]
        result = self.module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        self.assertIn(
            "MISSING_REVIEW_RECEIPT",
            {row["code"] for row in result["quality_errors"]},
        )

    def test_incomplete_or_nonapproved_review_receipt_fails_closed(self):
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        target = next(row for row in reviews if row["question_id"] == phase3_ids[0])
        target["disposition"] = "withheld"
        target["factual_source_checked"] = False
        result = self.module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        codes = {row["code"] for row in result["quality_errors"]}
        self.assertIn("REVIEW_DISPOSITION_MISMATCH", codes)
        self.assertIn("REVIEW_RECEIPT_INCOMPLETE", codes)

    def test_phase3_review_receipt_is_bound_to_exact_content_hash(self):
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        question = next(row for row in questions if row["id"] == phase3_ids[0])
        question["stem"] += " mutated after review"
        result = self.module.validate_phase3_set(questions, self.taxonomy, reviews, phase3_ids)
        self.assertIn(
            "REVIEW_CONTENT_HASH_MISMATCH",
            {row["code"] for row in result["quality_errors"]},
        )

    def test_question_source_must_join_exact_inventory_url_and_scope(self):
        questions, reviews, phase3_ids = _complete_phase3_set(self.taxonomy)
        inventory = _inventory_for(self.taxonomy)
        inventory["sources"][0]["url"] = "https://learn.microsoft.com/en-us/other-authority"
        result = self.module.validate_phase3_set(
            questions,
            self.taxonomy,
            reviews,
            phase3_ids,
            source_inventory=inventory,
        )
        self.assertIn(
            "QUESTION_SOURCE_NOT_IN_INVENTORY",
            {row["code"] for row in result["quality_errors"]},
        )

    def test_source_inventory_requires_current_retrieval_metadata(self):
        inventory = _inventory_for(self.taxonomy)
        inventory["sources"][0]["retrieved_at"] = ""
        errors = self.module.validate_phase3_source_inventory(inventory, self.taxonomy)
        codes = {row["code"] for row in errors}
        self.assertIn("MISSING_SOURCE_RETRIEVED_AT", codes)
        self.assertIn("STALE_OR_MISSING_SOURCE_RETRIEVAL", codes)


if __name__ == "__main__":
    unittest.main()
