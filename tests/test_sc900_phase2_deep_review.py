import unittest
from copy import deepcopy

from ingestion.models import load_taxonomy
from tests.test_sc900_phase2 import _complete_phase2_set, _load_phase2_module

class Phase2DeepReviewRegressionTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_taxonomy()
        self.module = _load_phase2_module(self)

    def test_terminal_acceptance_rejects_pending_or_withheld_records(self):
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        pending = deepcopy(questions[0]); pending["id"] = "pending_extra"; pending["promotion_status"] = "pending"
        result = self.module.validate_phase2_set(questions + [pending], self.taxonomy, reviews, phase2_ids)
        self.assertIn("PENDING_RECORDS_PRESENT", {row["code"] for row in result["quality_errors"]})
        withheld = deepcopy(questions[0]); withheld["id"] = "withheld_extra"; withheld["promotion_status"] = "withheld"
        result = self.module.validate_phase2_set(questions + [withheld], self.taxonomy, reviews, phase2_ids)
        self.assertIn("WITHHELD_RECORDS_PRESENT", {row["code"] for row in result["quality_errors"]})

    def manifest_item(self, **overrides):
        item = {"question_id":"q1","semantic_family_id":"family-a","source_family_id":"source-a","role":"TRAIN","promotion_status":"approved","future_probe_suitability":"train_only","family_state":"resolved","assignment_rationale":"test","assignment_receipt":{"reviewer":"reviewer","reviewed_at":"2026-09-11T00:00:00Z"},"blueprint_version":"2026-07-28"}
        item.update(overrides); return item

    def manifest(self, item, **overrides):
        data = {"schema_version":"sc900.train-probe-manifest/v1","partition_epoch":"epoch","blueprint_version":"2026-07-28","items":[item]}
        data.update(overrides); return data

    def test_train_rejects_pending_withheld_and_unresolved_family(self):
        for status in ("pending", "withheld"):
            codes = {row["code"] for row in self.module.validate_train_probe_manifest(self.manifest(self.manifest_item(promotion_status=status)))}
            self.assertIn("TRAIN_REQUIRES_APPROVED", codes)
        codes = {row["code"] for row in self.module.validate_train_probe_manifest(self.manifest(self.manifest_item(family_state="disputed")))}
        self.assertIn("TRAIN_REQUIRES_RESOLVED_FAMILY", codes)
        self.assertIn("UNRESOLVED_FAMILY_MUST_BE_UNASSIGNED", codes)

    def test_python_manifest_validator_requires_published_schema_fields(self):
        errors = self.module.validate_train_probe_manifest({"schema_version":"wrong","partition_epoch":"epoch","items":[self.manifest_item(assignment_rationale="", assignment_receipt=None, blueprint_version="")]})
        codes = {row["code"] for row in errors}
        self.assertIn("INVALID_MANIFEST_SCHEMA_VERSION", codes)
        self.assertIn("MISSING_MANIFEST_BLUEPRINT_VERSION", codes)
        self.assertIn("MISSING_ITEM_BLUEPRINT_VERSION", codes)
        self.assertIn("MISSING_ASSIGNMENT_RATIONALE", codes)
        self.assertIn("MISSING_ASSIGNMENT_RECEIPT", codes)

    def test_phase2_id_list_must_be_exactly_50_unique_ids(self):
        questions, reviews, phase2_ids = _complete_phase2_set(self.taxonomy)
        result = self.module.validate_phase2_set(questions, self.taxonomy, reviews, phase2_ids[:-1] + [phase2_ids[0]])
        self.assertIn("PHASE2_BATCH_ID_SET_INVALID", {row["code"] for row in result["quality_errors"]})

if __name__ == "__main__":
    unittest.main()
