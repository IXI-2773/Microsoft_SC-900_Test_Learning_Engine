import unittest
from copy import deepcopy

from ingestion.models import load_taxonomy
from tests.test_sc900_phase2 import _approved_question, _complete_phase2_set, _load_phase2_module


class Phase2DeepReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        self.module = _load_phase2_module(self)

    def test_terminal_acceptance_rejects_pending_or_withheld_records(self):
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        pending = deepcopy(questions[0])
        pending["id"] = "pending_extra"
        pending["promotion_status"] = "pending"
        result = self.module.validate_phase2_set(questions + [pending], self.taxonomy, reviews, phase2_ids)
        self.assertIn("PENDING_RECORDS_PRESENT", {row["code"] for row in result["quality_errors"]})
        withheld = deepcopy(questions[0])
        withheld["id"] = "withheld_extra"
        withheld["promotion_status"] = "withheld"
        result = self.module.validate_phase2_set(questions + [withheld], self.taxonomy, reviews, phase2_ids)
        self.assertIn("WITHHELD_RECORDS_PRESENT", {row["code"] for row in result["quality_errors"]})

    def manifest_item(self, **overrides):
        item = {
            "question_id": "q1",
            "semantic_family_id": "family-a",
            "source_family_id": "source-a",
            "role": "TRAIN",
            "promotion_status": "approved",
            "future_probe_suitability": "train_only",
            "family_state": "resolved",
            "assignment_rationale": "test",
            "assignment_receipt": {
                "reviewer": "reviewer",
                "reviewed_at": "2026-09-11T00:00:00Z",
            },
            "blueprint_version": "2026-07-28",
        }
        item.update(overrides)
        return item

    def manifest(self, item, **overrides):
        data = {
            "schema_version": "sc900.train-probe-manifest/v1",
            "partition_epoch": "epoch",
            "blueprint_version": "2026-07-28",
            "items": [item],
        }
        data.update(overrides)
        return data

    def test_train_rejects_pending_withheld_and_unresolved_family(self):
        for status in ("pending", "withheld"):
            codes = {
                row["code"]
                for row in self.module.validate_train_probe_manifest(
                    self.manifest(self.manifest_item(promotion_status=status))
                )
            }
            self.assertIn("TRAIN_REQUIRES_APPROVED", codes)
        codes = {
            row["code"]
            for row in self.module.validate_train_probe_manifest(
                self.manifest(self.manifest_item(family_state="disputed"))
            )
        }
        self.assertIn("TRAIN_REQUIRES_RESOLVED_FAMILY", codes)
        self.assertIn("UNRESOLVED_FAMILY_MUST_BE_UNASSIGNED", codes)

    def test_python_manifest_validator_requires_published_schema_fields(self):
        errors = self.module.validate_train_probe_manifest(
            {
                "schema_version": "wrong",
                "partition_epoch": "epoch",
                "items": [
                    self.manifest_item(
                        assignment_rationale="",
                        assignment_receipt=None,
                        blueprint_version="",
                    )
                ],
            }
        )
        codes = {row["code"] for row in errors}
        self.assertIn("INVALID_MANIFEST_SCHEMA_VERSION", codes)
        self.assertIn("MISSING_MANIFEST_BLUEPRINT_VERSION", codes)
        self.assertIn("MISSING_ITEM_BLUEPRINT_VERSION", codes)
        self.assertIn("MISSING_ASSIGNMENT_RATIONALE", codes)
        self.assertIn("MISSING_ASSIGNMENT_RECEIPT", codes)

    def test_manifest_rejects_missing_or_non_array_items(self):
        missing = self.manifest(self.manifest_item())
        del missing["items"]
        missing_codes = {
            row["code"] for row in self.module.validate_train_probe_manifest(missing)
        }
        self.assertIn("MISSING_MANIFEST_ITEMS", missing_codes)

        malformed = self.manifest(self.manifest_item(), items={"question_id": "q1"})
        malformed_codes = {
            row["code"] for row in self.module.validate_train_probe_manifest(malformed)
        }
        self.assertIn("INVALID_MANIFEST_ITEMS_TYPE", malformed_codes)

    def test_unassigned_item_rejects_invalid_schema_enums(self):
        item = self.manifest_item(
            role="UNASSIGNED",
            promotion_status="garbage",
            future_probe_suitability="garbage",
            family_state="garbage",
        )
        codes = {
            row["code"]
            for row in self.module.validate_train_probe_manifest(self.manifest(item))
        }
        self.assertIn("INVALID_PROMOTION_STATUS", codes)
        self.assertIn("INVALID_PROBE_SUITABILITY", codes)
        self.assertIn("INVALID_FAMILY_STATE", codes)

    def test_manifest_rejects_schema_forbidden_extra_fields_and_bad_receipt_fields(self):
        item = self.manifest_item(unexpected_item_field=True)
        item["assignment_receipt"] = {
            "reviewer": "reviewer",
            "reviewed_at": "2026-09-11T00:00:00Z",
            "override_type": "invalid",
            "prior_family_ids": "not-an-array",
            "unexpected_receipt_field": True,
        }
        manifest = self.manifest(item, unexpected_manifest_field=True)
        codes = {
            row["code"]
            for row in self.module.validate_train_probe_manifest(manifest)
        }
        self.assertIn("UNEXPECTED_MANIFEST_FIELD", codes)
        self.assertIn("UNEXPECTED_MANIFEST_ITEM_FIELD", codes)
        self.assertIn("INVALID_ASSIGNMENT_OVERRIDE_TYPE", codes)
        self.assertIn("INVALID_PRIOR_FAMILY_IDS", codes)
        self.assertIn("UNEXPECTED_ASSIGNMENT_RECEIPT_FIELD", codes)

    def test_phase2_id_list_must_be_exactly_50_unique_ids(self):
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        result = self.module.validate_phase2_set(
            questions,
            self.taxonomy,
            reviews,
            phase2_ids[:-1] + [phase2_ids[0]],
        )
        self.assertIn(
            "PHASE2_BATCH_ID_SET_INVALID",
            {row["code"] for row in result["quality_errors"]},
        )


class Phase2EvidenceChainTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        self.module = _load_phase2_module(self)

    def test_review_content_hash_detects_substantive_mutation(self):
        from tools.build_sc900_phase2 import review_content_sha256

        question = _approved_question(
            1,
            "security_compliance_concepts",
            "security_compliance_identity",
            "shared_responsibility_model",
            phase2=True,
        )
        original = review_content_sha256(question)
        question["stem"] += " changed"
        self.assertNotEqual(original, review_content_sha256(question))

    def test_semantic_audit_merges_same_leaf_even_when_prior_family_differs(self):
        from tools.build_sc900_phase2 import compute_semantic_family_audit

        left = _approved_question(
            1,
            "entra_authentication",
            "microsoft_entra",
            "multifactor_authentication",
            phase2=False,
        )
        right = _approved_question(
            2,
            "entra_authentication",
            "microsoft_entra",
            "multifactor_authentication",
            phase2=True,
        )
        left["metadata"]["semantic_family_id"] = "old-a"
        right["metadata"]["semantic_family_id"] = "old-b"
        audit = compute_semantic_family_audit([left, right])
        families = {row["semantic_family_id"] for row in audit["decisions"]}
        self.assertEqual({"multifactor_authentication"}, families)

    def test_source_link_validation_requires_exact_inventory_join(self):
        question = _approved_question(
            1,
            "security_compliance_concepts",
            "security_compliance_identity",
            "shared_responsibility_model",
            phase2=True,
        )
        errors = self.module.validate_question_source_links([question], {"sources": []})
        self.assertIn(
            "QUESTION_SOURCE_NOT_IN_INVENTORY", {row["code"] for row in errors}
        )


if __name__ == "__main__":
    unittest.main()
