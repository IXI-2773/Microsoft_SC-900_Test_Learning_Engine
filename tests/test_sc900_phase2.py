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

EXPECTED_PHASE2_OBJECTIVE_COUNTS = {
    key: value * 2 for key, value in PHASE1_OBJECTIVE_COUNTS.items()
}

EXPECTED_PHASE2_DOMAIN_COUNTS = {
    "security_compliance_identity": 12,
    "microsoft_entra": 28,
    "microsoft_security_solutions": 38,
    "microsoft_compliance_solutions": 22,
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


def _load_phase2_module(testcase):
    testcase.assertIsNotNone(
        importlib.util.find_spec("tools.validate_sc900_phase2"),
        "tools.validate_sc900_phase2 must exist",
    )
    return importlib.import_module("tools.validate_sc900_phase2")


def _approved_question(serial, objective, domain, leaf, phase2=False):
    source_url = "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/sc-900"
    phase = "p2" if phase2 else "p1"
    return {
        "id": f"q_{phase}_{serial:03d}",
        "record_kind": "question",
        "exam": "SC-900",
        "domain": domain,
        "objective": objective,
        "subobjective": leaf,
        "difficulty": "beginner",
        "type": "multiple_choice",
        "stem": f"Synthetic Phase 2 structural question {phase}-{serial}?",
        "choices": [
            {"id": "a", "text": "Correct choice"},
            {"id": "b", "text": "Distractor"},
        ],
        "correct_answer": ["a"],
        "explanation": "Synthetic structural test explanation.",
        "references": [source_url],
        "tags": [objective],
        "metadata": {
            "blueprint_leaf_id": leaf,
            "source_authority": "microsoft_learn",
            "source_urls": [source_url],
            "source_retrieved_at": "2026-09-11",
            "source_family_id": f"source-{objective}",
            "semantic_family_id": f"family-{phase}-{serial:03d}",
            "stem_style": "direct_concept",
            "future_probe_suitability": "eligible",
            "authoring_origin": "original_from_official_source",
        },
        "promotion_status": "approved",
    }


def _review(question_id):
    receipt = {
        "question_id": question_id,
        "reviewer": "phase2-test-reviewer",
        "reviewed_at": "2026-09-11T00:00:00Z",
        "disposition": "approved",
        "notes": "",
    }
    receipt.update({field: True for field in REVIEW_FIELDS})
    return receipt


def _complete_phase2_set(taxonomy):
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
    phase2_ids = []
    p1_serial = 0
    p2_serial = 0
    for objective, phase1_count in PHASE1_OBJECTIVE_COUNTS.items():
        leaves = leaves_by_objective[objective]
        for offset in range(phase1_count):
            p1_serial += 1
            question = _approved_question(
                p1_serial,
                objective,
                objective_owner[objective],
                leaves[offset % len(leaves)],
                phase2=False,
            )
            questions.append(question)
            reviews.append(_review(question["id"]))
        for offset in range(phase1_count):
            p2_serial += 1
            question = _approved_question(
                p2_serial,
                objective,
                objective_owner[objective],
                leaves[(offset + 1) % len(leaves)],
                phase2=True,
            )
            questions.append(question)
            reviews.append(_review(question["id"]))
            phase2_ids.append(question["id"])
    return questions, reviews, phase2_ids


class SC900Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()

    def test_phase2_validator_module_exists(self):
        _load_phase2_module(self)

    def test_complete_phase2_set_requires_100_total_and_50_new_approvals(self):
        module = _load_phase2_module(self)
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        result = module.validate_phase2_set(questions, self.taxonomy, reviews, phase2_ids)
        self.assertEqual("PHASE_2_STRUCTURALLY_ACCEPTED", result["status"])
        self.assertEqual(100, result["approved_count"])
        self.assertEqual(50, result["phase2_new_approved_count"])
        self.assertEqual(EXPECTED_PHASE2_DOMAIN_COUNTS, result["domain_counts"])
        self.assertEqual(EXPECTED_PHASE2_OBJECTIVE_COUNTS, result["objective_counts"])
        self.assertEqual([], result["quality_errors"])

    def test_phase2_set_rejects_99_approved_questions(self):
        module = _load_phase2_module(self)
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        removed = questions.pop()
        reviews = [row for row in reviews if row["question_id"] != removed["id"]]
        phase2_ids.remove(removed["id"])
        result = module.validate_phase2_set(questions, self.taxonomy, reviews, phase2_ids)
        codes = {row["code"] for row in result["quality_errors"]}
        self.assertEqual("PHASE_2_INCOMPLETE", result["status"])
        self.assertIn("APPROVED_COUNT_MISMATCH", codes)
        self.assertIn("PHASE2_NEW_APPROVED_COUNT_MISMATCH", codes)

    def test_phase2_set_rejects_duplicate_id_and_missing_review(self):
        module = _load_phase2_module(self)
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        questions[-1]["id"] = questions[-2]["id"]
        reviews = reviews[:-1]
        result = module.validate_phase2_set(questions, self.taxonomy, reviews, phase2_ids)
        codes = {row["code"] for row in result["quality_errors"]}
        self.assertEqual("PHASE_2_INCOMPLETE", result["status"])
        self.assertIn("DUPLICATE_APPROVED_ID", codes)
        self.assertIn("MISSING_REVIEW_RECEIPT", codes)

    def test_phase2_set_rejects_wrong_domain_and_objective_allocation(self):
        module = _load_phase2_module(self)
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        questions[-1]["domain"] = "microsoft_entra"
        questions[-1]["objective"] = "entra_authentication"
        result = module.validate_phase2_set(questions, self.taxonomy, reviews, phase2_ids)
        codes = {row["code"] for row in result["quality_errors"]}
        self.assertIn("DOMAIN_ALLOCATION_MISMATCH", codes)
        self.assertIn("OBJECTIVE_ALLOCATION_MISMATCH", codes)

    def test_manifest_rejects_semantic_family_split_across_train_and_probe(self):
        module = _load_phase2_module(self)
        manifest = {
            "schema_version": "sc900.train-probe-manifest/v1",
            "partition_epoch": "test-epoch",
            "items": [
                {
                    "question_id": "q1",
                    "semantic_family_id": "family-a",
                    "source_family_id": "source-a",
                    "role": "TRAIN",
                    "promotion_status": "approved",
                    "future_probe_suitability": "eligible",
                    "family_state": "resolved",
                },
                {
                    "question_id": "q2",
                    "semantic_family_id": "family-a",
                    "source_family_id": "source-b",
                    "role": "PROBE",
                    "promotion_status": "approved",
                    "future_probe_suitability": "eligible",
                    "family_state": "resolved",
                },
            ],
        }
        codes = {row["code"] for row in module.validate_train_probe_manifest(manifest)}
        self.assertIn("SEMANTIC_FAMILY_SPLIT", codes)

    def test_manifest_probe_requires_approved_eligible_resolved_family(self):
        module = _load_phase2_module(self)
        manifest = {
            "schema_version": "sc900.train-probe-manifest/v1",
            "partition_epoch": "test-epoch",
            "items": [
                {
                    "question_id": "q1",
                    "semantic_family_id": "family-a",
                    "source_family_id": "source-a",
                    "role": "PROBE",
                    "promotion_status": "pending",
                    "future_probe_suitability": "needs_review",
                    "family_state": "disputed",
                }
            ],
        }
        codes = {row["code"] for row in module.validate_train_probe_manifest(manifest)}
        self.assertIn("PROBE_REQUIRES_APPROVED", codes)
        self.assertIn("PROBE_REQUIRES_ELIGIBLE", codes)
        self.assertIn("PROBE_REQUIRES_RESOLVED_FAMILY", codes)

    def test_manifest_rejects_duplicate_ids_unknown_roles_and_missing_family(self):
        module = _load_phase2_module(self)
        manifest = {
            "schema_version": "sc900.train-probe-manifest/v1",
            "partition_epoch": "test-epoch",
            "items": [
                {
                    "question_id": "q1",
                    "semantic_family_id": "",
                    "source_family_id": "source-a",
                    "role": "MAYBE",
                    "promotion_status": "approved",
                    "future_probe_suitability": "eligible",
                    "family_state": "unknown",
                },
                {
                    "question_id": "q1",
                    "semantic_family_id": "family-b",
                    "source_family_id": "source-b",
                    "role": "UNASSIGNED",
                    "promotion_status": "approved",
                    "future_probe_suitability": "eligible",
                    "family_state": "resolved",
                },
            ],
        }
        codes = {row["code"] for row in module.validate_train_probe_manifest(manifest)}
        self.assertIn("DUPLICATE_MANIFEST_QUESTION_ID", codes)
        self.assertIn("INVALID_MANIFEST_ROLE", codes)
        self.assertIn("MISSING_MANIFEST_SEMANTIC_FAMILY", codes)

    def test_manifest_requires_schema_version_and_partition_epoch(self):
        module = _load_phase2_module(self)
        codes = {row["code"] for row in module.validate_train_probe_manifest({"items": []})}
        self.assertIn("MISSING_MANIFEST_SCHEMA_VERSION", codes)
        self.assertIn("MISSING_PARTITION_EPOCH", codes)


if __name__ == "__main__":
    unittest.main()
