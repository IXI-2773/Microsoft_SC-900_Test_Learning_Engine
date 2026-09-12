from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ingestion.models import normalize_text
from tools.build_sc900_phase2 import review_content_sha256
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS
from tools.validate_sc900_phase3 import (
    EXPECTED_PHASE3_DOMAIN_COUNTS,
    EXPECTED_PHASE3_OBJECTIVE_COUNTS,
)

ROOT = Path(__file__).resolve().parents[1]
PHASE3_ROOT = ROOT / "content" / "sc900" / "phase3"
COMPILED_PATH = PHASE3_ROOT / "compiled" / "sc900_phase3_reviewed_bank.json"
BUILD_RECEIPT_PATH = PHASE3_ROOT / "phase3_build_receipt.json"
ACCEPTANCE_REPORT_PATH = PHASE3_ROOT / "phase3_acceptance_report.json"
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"
SEMANTIC_AUDIT_PATH = PHASE3_ROOT / "semantic_family_audit.json"
EXPECTED_SEMANTIC_AUDIT_SHA256 = "e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701"
EXPECTED_PHASE3_IDS = [f"sc900_p3_q{index:03d}" for index in range(1, 101)]
GATE2_STATUS = "GATE_2_BLOCKED_INSUFFICIENT_BANK_STRUCTURE"


def _load_builder():
    from tools import build_sc900_phase3 as module

    return module


def _codes(errors):
    return {row["code"] if isinstance(row, dict) else str(row) for row in errors}


def _sample_phase3_record():
    path = PHASE3_ROOT / "batches" / "batch-01.jsonl"
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def _approved_receipt(record, **overrides):
    receipt = {
        "question_id": record["id"],
        "disposition": "approved",
        "reviewer": "test-reviewer",
        "reviewed_at": "2026-09-11T18:00:00Z",
        "reviewed_content_sha256": review_content_sha256(record),
    }
    receipt.update({field: True for field in REVIEW_CHECK_FIELDS})
    receipt.update(overrides)
    return receipt


class SC900Phase3BuilderContractTests(unittest.TestCase):
    def setUp(self):
        self.builder = _load_builder()

    def test_imported_approved_phase3_item_fails_pending_invariant(self):
        record = _sample_phase3_record()
        record["promotion_status"] = "approved"
        errors = self.builder.pending_before_approval_errors(
            [record],
            [record["id"]],
            approved_predecessor_count=100,
        )
        self.assertIn("IMPORT_BYPASSES_PENDING", _codes(errors))

    def test_missing_review_receipt_fails_closed(self):
        record = _sample_phase3_record()
        errors = self.builder.phase3_review_custody_errors([record], {})
        self.assertIn("MISSING_REVIEW_RECEIPT", _codes(errors))

    def test_stale_review_hash_fails_closed(self):
        record = _sample_phase3_record()
        receipt = _approved_receipt(record, reviewed_content_sha256="0" * 64)
        errors = self.builder.phase3_review_custody_errors([record], {record["id"]: receipt})
        self.assertIn("STALE_REVIEW_HASH", _codes(errors))

    def test_incomplete_review_checks_fail_closed(self):
        record = _sample_phase3_record()
        receipt = _approved_receipt(record, factual_source_checked=False)
        errors = self.builder.phase3_review_custody_errors([record], {record["id"]: receipt})
        self.assertIn("REVIEW_RECEIPT_INCOMPLETE", _codes(errors))

    def test_store_semantic_mismatch_fails_closed(self):
        record = _sample_phase3_record()
        record["promotion_status"] = "approved"
        record["metadata"] = dict(record.get("metadata") or {})
        record["metadata"]["semantic_family_id"] = "authored_not_audited"
        audit = {
            "family_count": 1,
            "decisions": [
                {
                    "question_id": record["id"],
                    "semantic_family_id": "task4_canonical_family",
                    "decision_type": "merged",
                    "family_state": "resolved",
                }
            ],
        }
        errors = self.builder.store_semantic_application_errors([record], audit, expected_family_count=1)
        self.assertIn("SEMANTIC_AUDIT_STORE_MISMATCH", _codes(errors))

    def test_unknown_audit_id_fails_closed(self):
        record = _sample_phase3_record()
        record["promotion_status"] = "approved"
        audit = {
            "family_count": 1,
            "decisions": [
                {
                    "question_id": "sc900_unknown_q999",
                    "semantic_family_id": "orphan_family",
                    "decision_type": "retained",
                    "family_state": "resolved",
                }
            ],
        }
        errors = self.builder.store_semantic_application_errors([record], audit, expected_family_count=1)
        self.assertIn("UNKNOWN_AUDIT_ID", _codes(errors))

    def test_wrong_family_count_fails_closed(self):
        record = _sample_phase3_record()
        record["promotion_status"] = "approved"
        family_id = normalize_text((record.get("metadata") or {}).get("semantic_family_id"))
        audit = {
            "family_count": 27,
            "decisions": [
                {
                    "question_id": record["id"],
                    "semantic_family_id": family_id,
                    "decision_type": "retained",
                    "family_state": "resolved",
                }
            ],
        }
        errors = self.builder.store_semantic_application_errors([record], audit, expected_family_count=27)
        self.assertIn("SEMANTIC_FAMILY_COUNT_MISMATCH", _codes(errors))

    def test_posix_repo_path_rejects_platform_separators(self):
        relative = self.builder.posix_repo_path(PHASE3_ROOT / "batches" / "batch-01.jsonl")
        self.assertEqual(relative, "content/sc900/phase3/batches/batch-01.jsonl")
        self.assertNotIn("\\", relative)

    def test_live_build_proves_pending_before_approval_and_terminal_counts(self):
        with tempfile.TemporaryDirectory(prefix="sc900-phase3-task5-") as temp_dir:
            build = self.builder.build_phase3(Path(temp_dir))
        receipt = build["receipt"]
        self.assertEqual(100, receipt["phase3_authored_count"])
        self.assertEqual(100, receipt["phase3_imported_pending_count_before_review"])
        self.assertEqual(0, receipt["phase3_approved_before_review_application"])
        self.assertEqual(100, receipt["phase3_review_receipts_applied"])
        self.assertEqual(100, receipt["phase3_approved_after_review"])
        self.assertEqual(0, receipt["phase3_pending_after_review"])
        self.assertEqual(0, receipt["phase3_withheld_after_review"])
        self.assertEqual(200, receipt["approved_count"])
        self.assertEqual(200, receipt["compiled_count"])
        self.assertEqual(0, receipt["pending_count"])
        self.assertEqual(0, receipt["withheld_count"])
        self.assertEqual(EXPECTED_PHASE3_IDS, receipt["phase3_ids"])
        self.assertEqual(EXPECTED_PHASE3_DOMAIN_COUNTS, receipt["domain_counts"])
        self.assertEqual(EXPECTED_PHASE3_OBJECTIVE_COUNTS, receipt["objective_counts"])
        self.assertEqual(58, receipt["distinct_leaf_count"])
        self.assertEqual(27, receipt["semantic_family_count"])
        self.assertEqual(EXPECTED_SEMANTIC_AUDIT_SHA256, receipt["inputs"]["semantic_audit_sha256"])
        self.assertEqual(GATE2_STATUS, receipt["cand01_gate2_status"])
        self.assertFalse(receipt["implementation_authorized"])
        self.assertEqual("REPRODUCIBLE", receipt["status"])
        self.assertEqual([], receipt["build_errors"])

    def test_task4_family_wins_over_authored_family(self):
        with tempfile.TemporaryDirectory(prefix="sc900-phase3-task5-family-") as temp_dir:
            build = self.builder.build_phase3(Path(temp_dir))
            questions = json.loads(Path(build["store_dir"]).joinpath("questions.json").read_text(encoding="utf-8"))
        audit = json.loads(SEMANTIC_AUDIT_PATH.read_text(encoding="utf-8"))
        decisions = {
            normalize_text(row["question_id"]): normalize_text(row["semantic_family_id"]) for row in audit["decisions"]
        }
        families = set()
        for record in questions:
            qid = normalize_text(record["id"])
            actual = normalize_text((record.get("metadata") or {}).get("semantic_family_id"))
            self.assertEqual(decisions[qid], actual, qid)
            families.add(actual)
        self.assertEqual(27, len(families))

    def test_rebuild_is_byte_identical(self):
        with tempfile.TemporaryDirectory(prefix="sc900-phase3-task5-a-") as first_dir:
            first = self.builder.build_phase3(Path(first_dir))
            with tempfile.TemporaryDirectory(prefix="sc900-phase3-task5-b-") as second_dir:
                second = self.builder.build_phase3(Path(second_dir))
                for name in self.builder.STORE_FILES:
                    self.assertEqual(
                        Path(first["store_dir"]).joinpath(name).read_bytes(),
                        Path(second["store_dir"]).joinpath(name).read_bytes(),
                        name,
                    )
                self.assertEqual(
                    Path(first["compiled_path"]).read_bytes(),
                    Path(second["compiled_path"]).read_bytes(),
                )
        self.assertEqual(first["receipt"], second["receipt"])
        self.assertEqual(first["acceptance_report"], second["acceptance_report"])

    def test_default_launch_bank_is_immutable(self):
        before = hashlib.sha256(DEFAULT_BANK.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="sc900-phase3-task5-bank-") as temp_dir:
            build = self.builder.build_phase3(Path(temp_dir))
        after = hashlib.sha256(DEFAULT_BANK.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual(before, build["receipt"]["outputs"]["default_launch_bank_sha256"])
        self.assertNotEqual(DEFAULT_BANK.resolve(), Path(build["compiled_path"]).resolve())

    def test_gate2_authority_is_preserved_in_acceptance_report(self):
        with tempfile.TemporaryDirectory(prefix="sc900-phase3-task5-gate-") as temp_dir:
            build = self.builder.build_phase3(Path(temp_dir))
        report = build["acceptance_report"]
        self.assertEqual(5, report["task"])
        self.assertEqual(GATE2_STATUS, report["cand01_gate2_status"])
        self.assertFalse(report["implementation_authorized"])
        self.assertFalse(report["phase_3_structurally_accepted"])
        self.assertTrue(report["task_6_required"])
        self.assertTrue(report["default_bank_unchanged"])
        self.assertEqual("REPRODUCIBLE", report["reproducibility"])


class SC900Phase3CommittedBuilderArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.builder = _load_builder()

    def test_committed_compiled_bank_has_exactly_200_questions(self):
        payload = json.loads(COMPILED_PATH.read_text(encoding="utf-8"))
        questions = payload["questions"]
        self.assertEqual(200, len(questions))
        self.assertEqual(200, len({row["id"] for row in questions}))

    def test_committed_receipt_uses_posix_paths_and_frozen_audit_hash(self):
        receipt = json.loads(BUILD_RECEIPT_PATH.read_text(encoding="utf-8"))
        for section in ("batches", "reviews", "phase1_batches", "phase2_batches", "phase1_reviews", "phase2_reviews"):
            if section not in receipt["inputs"]:
                continue
            keys = list(receipt["inputs"][section])
            self.assertTrue(keys, section)
            self.assertTrue(all("\\" not in key and "/" in key for key in keys), keys)
        self.assertEqual(EXPECTED_SEMANTIC_AUDIT_SHA256, receipt["inputs"]["semantic_audit_sha256"])
        self.assertEqual(GATE2_STATUS, receipt["cand01_gate2_status"])
        self.assertFalse(receipt["implementation_authorized"])

    def test_committed_acceptance_report_does_not_authorize_runtime(self):
        report = json.loads(ACCEPTANCE_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(200, report["approved_count"])
        self.assertEqual(200, report["compiled_count"])
        self.assertEqual(100, report["phase3_new_count"])
        self.assertEqual(0, report["pending_count"])
        self.assertEqual(0, report["withheld_count"])
        self.assertEqual(58, report["distinct_leaf_count"])
        self.assertEqual(27, report["semantic_family_count"])
        self.assertEqual(158, report["semantic_merge_override_count"])
        self.assertEqual(0, report["semantic_split_override_count"])
        self.assertEqual(0, report["semantic_unresolved_family_count"])
        self.assertEqual([], report["source_inventory_errors"])
        self.assertEqual([], report["review_custody_errors"])
        self.assertEqual([], report["semantic_audit_errors"])
        self.assertEqual([], report["build_errors"])
        self.assertTrue(report["default_bank_unchanged"])
        self.assertEqual(GATE2_STATUS, report["cand01_gate2_status"])
        self.assertFalse(report["implementation_authorized"])
        self.assertTrue(report["task_6_required"])
        self.assertFalse(report["phase_3_structurally_accepted"])

    def test_committed_outputs_match_independent_rebuild(self):
        errors = self.builder.verify_committed_phase3_build()
        self.assertEqual([], errors)

    def test_default_launch_bank_bytes_unchanged_from_pre_task5_identity(self):
        receipt = json.loads(BUILD_RECEIPT_PATH.read_text(encoding="utf-8"))
        actual = hashlib.sha256(DEFAULT_BANK.read_bytes()).hexdigest()
        self.assertEqual(receipt["outputs"]["default_launch_bank_sha256"], actual)


class SC900Phase3BuilderMutationGuardTests(unittest.TestCase):
    def test_apply_does_not_silently_keep_authored_family(self):
        builder = _load_builder()
        record = _sample_phase3_record()
        record = copy.deepcopy(record)
        record["promotion_status"] = "approved"
        authored = normalize_text((record.get("metadata") or {}).get("semantic_family_id"))
        audit = {
            "audit_version": "sc900-semantic-family-audit/v2",
            "audit_epoch": "phase3-task4-cumulative-200",
            "family_count": 1,
            "decisions": [
                {
                    "question_id": record["id"],
                    "semantic_family_id": "task4_forced_family",
                    "prior_semantic_family_id": authored,
                    "decision_type": "merged",
                    "family_state": "resolved",
                    "future_probe_suitability": "eligible",
                }
            ],
        }
        builder.apply_task4_semantic_audit([record], audit)
        metadata = record["metadata"]
        self.assertEqual("task4_forced_family", metadata["semantic_family_id"])
        self.assertEqual(authored, metadata["prior_semantic_family_id"])
        self.assertNotEqual(authored, "task4_forced_family")


if __name__ == "__main__":
    unittest.main()
