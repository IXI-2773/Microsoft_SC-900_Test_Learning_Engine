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


def _unique_correct_answers(questions):
    for question in questions:
        marker = question["id"]
        question["choices"][0]["text"] = f"Correct choice {marker}"


def _leaf_members(questions):
    members = {}
    for question in questions:
        leaf = question["metadata"]["blueprint_leaf_id"]
        members.setdefault(leaf, []).append(question["id"])
    for leaf in members:
        members[leaf].sort()
    return members


def _valid_phase3_semantic_audit(questions):
    reviewer = "cursor-grok-4.6-cumulative-adversarial-semantic-audit"
    reviewed_at = "2026-09-11T18:00:00Z"
    review_method = "cumulative adversarial semantic-family audit of Phase 1+2+3"
    by_leaf = _leaf_members(questions)
    by_id = {question["id"]: question for question in questions}
    families = []
    decisions = []
    for leaf, members in sorted(by_leaf.items()):
        prior_ids = sorted({by_id[qid]["metadata"]["semantic_family_id"] for qid in members})
        family_decision = "retained" if prior_ids == [leaf] else "merged"
        families.append(
            {
                "semantic_family_id": leaf,
                "family_state": "resolved",
                "members": members,
                "prior_family_ids": prior_ids,
                "decision_type": family_decision,
                "rationale": f"Same-leaf cluster for {leaf} remains one family without independent-proposition evidence.",
                "evidence_class": ["same_leaf_transfer"],
                "blueprint_leaf_ids": [leaf],
            }
        )
        for qid in members:
            question = by_id[qid]
            prior = question["metadata"]["semantic_family_id"]
            decisions.append(
                {
                    "question_id": qid,
                    "semantic_family_id": leaf,
                    "prior_semantic_family_id": prior,
                    "family_state": "resolved",
                    "decision_type": "retained" if prior == leaf else "merged",
                    "rationale": f"Conservative same-leaf family assignment for {leaf}.",
                    "evidence_class": ["same_leaf_transfer"],
                    "relationship_evidence": [{"edge_class": "same_leaf", "members": members}],
                    "component_members": members,
                    "blueprint_leaf_ids": [leaf],
                    "blueprint_leaf_id": leaf,
                    "correct_answer_text": question["choices"][0]["text"],
                    "reviewer": reviewer,
                    "review_method": review_method,
                    "reviewed_at": reviewed_at,
                    "future_probe_suitability": question["metadata"]["future_probe_suitability"],
                    "probe_suitability_consequence": "unchanged",
                }
            )
    decisions.sort(key=lambda row: row["question_id"])
    question_ids = sorted(question["id"] for question in questions)
    return {
        "work_id": "SC900-BANK-PHASE3-001",
        "audit_version": "sc900-semantic-family-audit/v2",
        "audit_epoch": "phase3-task4-cumulative-200",
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "review_method": review_method,
        "question_count": len(questions),
        "question_ids": question_ids,
        "family_count": len(families),
        "merge_override_count": sum(row["decision_type"] == "merged" for row in decisions),
        "split_override_count": 0,
        "unresolved_family_count": 0,
        "explicit_transfer_edge_count": 0,
        "transfer_edges": [],
        "independence_adjudications": [],
        "families": families,
        "decisions": decisions,
    }


def _load_phase3_builder(testcase):
    testcase.assertIsNotNone(
        importlib.util.find_spec("tools.build_sc900_phase3"),
        "tools.build_sc900_phase3 must exist",
    )
    return importlib.import_module("tools.build_sc900_phase3")


class SC900Phase3SemanticFamilyAuditTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        questions, _reviews, _phase3_ids = _complete_phase3_set(self.taxonomy)
        _unique_correct_answers(questions)
        self.questions = questions
        self.audit = _valid_phase3_semantic_audit(questions)
        self.builder = _load_phase3_builder(self)

    def _codes(self, audit=None, questions=None):
        return {
            row["code"]
            for row in self.builder.validate_phase3_semantic_audit(
                questions if questions is not None else self.questions,
                audit if audit is not None else self.audit,
            )
        }

    def test_valid_audit_has_no_errors(self):
        self.assertEqual([], self.builder.validate_phase3_semantic_audit(self.questions, self.audit))

    def test_missing_audit_record_fails_closed(self):
        self.audit["decisions"].pop()
        self.audit["question_count"] = len(self.audit["decisions"])
        self.assertIn("MISSING_AUDIT_DECISION", self._codes())

    def test_duplicate_audit_decision_fails_closed(self):
        self.audit["decisions"].append(copy.deepcopy(self.audit["decisions"][0]))
        self.assertIn("DUPLICATE_AUDIT_DECISION", self._codes())

    def test_unknown_audit_id_fails_closed(self):
        extra = copy.deepcopy(self.audit["decisions"][0])
        extra["question_id"] = "sc900_unknown_q999"
        self.audit["decisions"].append(extra)
        self.assertIn("UNKNOWN_AUDIT_ID", self._codes())

    def test_unresolved_family_state_treated_as_resolved_fails_closed(self):
        target = self.audit["decisions"][0]
        target["family_state"] = "unresolved"
        target["decision_type"] = "retained"
        self.assertIn("UNRESOLVED_FAMILY_TREATED_AS_RESOLVED", self._codes())

    def test_missing_family_rationale_fails_closed(self):
        self.audit["decisions"][0]["rationale"] = ""
        self.assertIn("MISSING_FAMILY_RATIONALE", self._codes())

    def test_missing_decision_provenance_fails_closed(self):
        self.audit["decisions"][0]["reviewer"] = ""
        self.audit["decisions"][0]["review_method"] = ""
        self.audit["decisions"][0]["reviewed_at"] = ""
        codes = self._codes()
        self.assertIn("MISSING_DECISION_PROVENANCE", codes)

    def test_conflicting_family_assignments_fail_closed(self):
        duplicate = copy.deepcopy(self.audit["decisions"][0])
        duplicate["semantic_family_id"] = "conflicting_identity"
        self.audit["decisions"].append(duplicate)
        codes = self._codes()
        self.assertIn("DUPLICATE_AUDIT_DECISION", codes)
        self.assertIn("CONFLICTING_FAMILY_ASSIGNMENT", codes)

    def test_contradictory_family_identities_fail_closed(self):
        left = self.audit["decisions"][0]
        members = left["component_members"]
        self.assertGreaterEqual(len(members), 2)
        right = next(row for row in self.audit["decisions"] if row["question_id"] == members[1])
        right["semantic_family_id"] = "contradictory_identity"
        self.assertIn("CONTRADICTORY_FAMILY_IDENTITY", self._codes())

    def test_known_transfer_edge_unaccounted_fails_closed(self):
        left = self.questions[0]
        right = next(
            row
            for row in self.questions
            if row["metadata"]["blueprint_leaf_id"] != left["metadata"]["blueprint_leaf_id"]
        )
        left["id"] = "sc900_p1_q037"
        right["id"] = "sc900_p2_q033"
        audit = _valid_phase3_semantic_audit(self.questions)
        self.assertIn("TRANSFER_EDGE_UNACCOUNTED", self._codes(audit=audit, questions=self.questions))

    def test_same_leaf_high_risk_pair_without_adjudication_fails_closed(self):
        left = self.audit["decisions"][0]
        members = left["component_members"]
        self.assertGreaterEqual(len(members), 2)
        right = next(row for row in self.audit["decisions"] if row["question_id"] == members[1])
        right["semantic_family_id"] = "independent_without_adjudication"
        right["component_members"] = [right["question_id"]]
        left["component_members"] = [left["question_id"]]
        self.assertIn("HIGH_RISK_PAIR_UNADJUDICATED", self._codes())

    def test_unresolved_family_remaining_probe_eligible_fails_closed(self):
        target = self.audit["decisions"][0]
        target["family_state"] = "unresolved"
        target["decision_type"] = "unresolved"
        target["future_probe_suitability"] = "eligible"
        self.assertIn("UNRESOLVED_FAMILY_PROBE_ELIGIBLE", self._codes())

    def test_audit_count_not_exactly_200_fails_closed(self):
        self.audit["question_count"] = 199
        self.assertIn("AUDIT_COUNT_MISMATCH", self._codes())

    def test_committed_cumulative_audit_covers_exactly_200_questions(self):
        questions = self.builder.load_cumulative_approved_questions()
        audit = self.builder.load_phase3_semantic_family_audit()
        self.assertEqual(200, len(questions))
        self.assertEqual(200, len({row["id"] for row in questions}))
        self.assertEqual(
            [],
            self.builder.validate_phase3_semantic_audit(questions, audit),
        )


if __name__ == "__main__":
    unittest.main()

