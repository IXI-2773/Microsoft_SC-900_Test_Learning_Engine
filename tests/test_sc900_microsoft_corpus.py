from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path

from ingestion.models import load_taxonomy
from tools.build_sc900_phase2 import review_content_sha256
from tools.validate_sc900_microsoft_corpus import (
    CORPUS_ROOT,
    DEFAULT_BANK,
    EXISTING_AUDIT_PATH,
    EXPECTED_DEFAULT_BANK_SHA256,
    EXPECTED_LEAF_COUNT,
    INVENTORY_PATH,
    KNOWLEDGE_UNITS_PATH,
    SCOPE_PATH,
    STUDY_GUIDE_URL,
    default_bank_errors,
    existing_audit_errors,
    inventory_schema_errors,
    knowledge_unit_errors,
    pr13_isolation_errors,
    promotion_currentness_errors,
    sha256_file,
)
from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS

ROOT = Path(__file__).resolve().parents[1]
PHASE3_COMPILED = ROOT / "content" / "sc900" / "phase3" / "compiled" / "sc900_phase3_reviewed_bank.json"


def _load_builder():
    return importlib.import_module("tools.build_sc900_microsoft_corpus")


class MicrosoftCorpusContractTests(unittest.TestCase):
    def test_inventory_file_exists_with_required_schema(self):
        self.assertTrue(INVENTORY_PATH.is_file())
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        errors = inventory_schema_errors(inventory)
        self.assertEqual(errors, [])
        self.assertEqual(inventory["sc900_skills_effective_date"], "2026-07-28")
        self.assertFalse(inventory["page_bodies_stored"])
        self.assertFalse(inventory["assessment_content_used"])
        self.assertGreaterEqual(inventory["counts"]["learning_paths"], 4)
        self.assertGreaterEqual(inventory["counts"]["modules"], 13)
        self.assertGreaterEqual(inventory["counts"]["units"], 40)
        self.assertGreaterEqual(inventory["counts"]["product_documentation"], 20)

    def test_study_guide_and_required_paths_are_present(self):
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        by_id = {row["source_id"]: row for row in inventory["sources"]}
        self.assertIn("sc900-study-guide-2026-07-28", by_id)
        self.assertEqual(by_id["sc900-study-guide-2026-07-28"]["url"].rstrip("/"), STUDY_GUIDE_URL.rstrip("/"))
        for source_id in (
            "path-concepts",
            "path-entra",
            "path-security-solutions",
            "path-compliance-solutions",
        ):
            self.assertEqual(by_id[source_id]["source_type"], "learning_path")

    def test_security_copilot_is_inventoried_but_out_of_exam_scope(self):
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        copilot = next(
            row for row in inventory["sources"] if row["source_id"] == "module-security-copilot-getting-started"
        )
        self.assertFalse(copilot["exam_in_scope"])
        self.assertEqual(copilot["assessment_content_used"], False)

    def test_scope_reconciliation_does_not_rewrite_taxonomy(self):
        scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
        taxonomy = load_taxonomy()
        self.assertTrue(scope["live_study_guide_matches_repository_taxonomy"])
        self.assertFalse(scope["taxonomy_rewrite_performed"])
        self.assertTrue(scope["current_sc900_scope_verified"])
        self.assertEqual(scope["leaf_skill_count"], EXPECTED_LEAF_COUNT)
        self.assertEqual(taxonomy["skills_effective_date"], "2026-07-28")
        self.assertGreaterEqual(len(scope["discrepancies"]), 3)
        self.assertTrue(any(row["id"] == "security-copilot-on-learning-path" for row in scope["discrepancies"]))

    def test_knowledge_units_cover_every_leaf_without_passages(self):
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        units = [
            json.loads(line) for line in KNOWLEDGE_UNITS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        errors = knowledge_unit_errors(units, inventory)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(units), EXPECTED_LEAF_COUNT)

    def test_existing_200_are_audited(self):
        predecessor = json.loads(PHASE3_COMPILED.read_text(encoding="utf-8"))["questions"]
        audit = json.loads(EXISTING_AUDIT_PATH.read_text(encoding="utf-8"))
        errors = existing_audit_errors(audit, [row["id"] for row in predecessor])
        self.assertEqual(errors, [])
        self.assertEqual(len(predecessor), 200)

    def test_unverified_or_retired_cannot_be_approved(self):
        errors = promotion_currentness_errors(
            [
                {
                    "id": "q-bad",
                    "promotion_status": "approved",
                    "metadata": {"currentness_status": "UNVERIFIED"},
                }
            ]
        )
        self.assertTrue(any(row["code"] == "UNAPPROVABLE_CURRENTNESS" for row in errors))

    def test_new_questions_must_start_pending(self):
        builder = _load_builder()
        record = {
            "id": "sc900_mlc_q001",
            "promotion_status": "approved",
            "metadata": {"batch": "mlc-batch-01"},
        }
        errors = builder.pending_before_approval_errors([record], ["sc900_mlc_q001"])
        self.assertTrue(any(row["code"] == "IMPORT_BYPASSES_PENDING" for row in errors))

    def test_review_custody_hash_is_required(self):
        builder = _load_builder()
        record = {
            "id": "sc900_mlc_q001",
            "exam": "SC-900",
            "domain": "security_compliance_identity",
            "objective": "security_compliance_concepts",
            "subobjective": "shared responsibility model",
            "difficulty": "beginner",
            "type": "multiple_choice",
            "stem": "Synthetic custody question?",
            "choices": [{"id": "a", "text": "Yes"}, {"id": "b", "text": "No"}],
            "correct_answer": ["a"],
            "explanation": "Synthetic explanation.",
            "references": [STUDY_GUIDE_URL],
            "tags": ["shared_responsibility_model"],
            "source": {"title": "Microsoft Learn", "url": STUDY_GUIDE_URL},
            "metadata": {"blueprint_leaf_id": "shared_responsibility_model"},
        }
        errors = builder.review_custody_errors([record], {})
        self.assertTrue(any(row["code"] == "MISSING_REVIEW_RECEIPT" for row in errors))
        stale = {
            "question_id": record["id"],
            "disposition": "approved",
            "reviewed_content_sha256": "0" * 64,
            **{field: True for field in REVIEW_CHECK_FIELDS},
            "independent_answer_verified": True,
            "adversarial_item_reviewed": True,
        }
        errors = builder.review_custody_errors([record], {record["id"]: stale})
        self.assertTrue(any(row["code"] == "REVIEW_HASH_MISMATCH" for row in errors))
        receipt = {
            "question_id": record["id"],
            "disposition": "approved",
            "reviewed_content_sha256": review_content_sha256(record),
            **{field: True for field in REVIEW_CHECK_FIELDS},
            "independent_answer_verified": True,
            "adversarial_item_reviewed": True,
        }
        self.assertEqual(builder.review_custody_errors([record], {record["id"]: receipt}), [])

    def test_default_bank_and_pr13_remain_untouched(self):
        self.assertEqual(default_bank_errors(), [])
        self.assertEqual(pr13_isolation_errors(), [])
        self.assertEqual(sha256_file(DEFAULT_BANK), EXPECTED_DEFAULT_BANK_SHA256)
        self.assertFalse((CORPUS_ROOT / "train_probe_manifest.json").exists())

    def test_compiler_is_deterministic_and_idempotent(self):
        builder = _load_builder()
        first = builder.build_corpus(write=False)
        second = builder.build_corpus(write=False)
        self.assertEqual(first["compiled_sha256"], second["compiled_sha256"])
        self.assertEqual(first["approved"], second["approved"])
        self.assertTrue(first["default_bank_unchanged"])
        self.assertFalse(first["final_bank_activated"])
        self.assertEqual(first["pr13_imported"], False)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bank.json"
            builder.write_compiled_bank(first["compiled_bank"], output)
            builder.write_compiled_bank(first["compiled_bank"], output)
            self.assertEqual(sha256_file(output), first["compiled_sha256"])

    def test_expansion_batches_are_complete_and_unique(self):
        from tools.sc900_microsoft_corpus_qemit import redistribute_single_select
        from tools.sc900_microsoft_corpus_questions import BATCHES

        self.assertGreaterEqual(len(BATCHES), 12)
        seen_ids = set()
        seen_decisions = set()
        multi = 0
        intermediate = 0
        for batch_id, factory in BATCHES:
            records = redistribute_single_select(factory())
            self.assertEqual(len(records), 25, batch_id)
            for record in records:
                qid = record["id"]
                self.assertNotIn(qid, seen_ids, qid)
                seen_ids.add(qid)
                metadata = record["metadata"]
                key = (metadata["semantic_family_id"], metadata["tested_decision"])
                self.assertNotIn(key, seen_decisions, key)
                seen_decisions.add(key)
                self.assertNotEqual(metadata.get("future_probe_suitability"), "PROBE")
                stem = record["stem"].casefold()
                self.assertNotIn("security copilot", stem)
                self.assertNotIn("unified catalog", stem)
                self.assertNotIn("global secure access", stem)
                if record["type"] == "multi_select":
                    multi += 1
                    self.assertIn("choose", stem)
                    self.assertIsInstance(record["correct_answer"], list)
                    self.assertGreaterEqual(len(record["correct_answer"]), 2)
                if record["difficulty"] == "intermediate":
                    intermediate += 1
        expansion = [qid for qid in seen_ids if int(qid.rsplit("q", 1)[-1]) >= 201]
        self.assertGreaterEqual(len(expansion), 100)
        self.assertGreaterEqual(intermediate, 60)
        self.assertGreaterEqual(multi, 4)

    def test_expanded_candidate_bank_stays_in_working_range(self):
        builder = _load_builder()
        report = builder.build_corpus(write=False)
        self.assertGreaterEqual(report["approved"], 500)
        self.assertLessEqual(report["approved"], 600)
        self.assertEqual(report["pending"], 0)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["default_bank_unchanged"])
        self.assertFalse(report["final_bank_activated"])
        self.assertEqual(sha256_file(DEFAULT_BANK), EXPECTED_DEFAULT_BANK_SHA256)

    def test_large_candidate_bank_runtime_compatibility(self):
        from app_constants import MODE_EXAM, MODE_PRACTICE
        from question_bank import load_bank, stable_shuffle_question
        from question_identity import bank_content_fingerprint, canonical_question_id
        from session_identity import canonical_session_signature, ordered_question_ids
        from smart_practice_profile import smart_practice_role_allocation
        from tools.validate_sc900_microsoft_corpus import CORPUS_ROOT

        compiled = CORPUS_ROOT / "compiled" / "sc900_microsoft_learn_corpus_bank.json"
        bank = load_bank(compiled)
        questions = bank["questions"]
        self.assertGreaterEqual(len(questions), 500)
        self.assertLessEqual(len(questions), 600)
        ids = [canonical_question_id(row) for row in questions]
        self.assertEqual(len(ids), len(set(ids)))
        fingerprint = bank_content_fingerprint(questions)
        self.assertEqual(len(fingerprint), 64)
        ordered = ordered_question_ids(questions)
        self.assertEqual(ordered, ids)
        randomized = ordered_question_ids([stable_shuffle_question(dict(row)) for row in questions[:25]])
        self.assertEqual(len(randomized), 25)
        practice = canonical_session_signature(MODE_PRACTICE, fingerprint, ordered[:25])
        exam = canonical_session_signature(MODE_EXAM, fingerprint, ordered[:50])
        self.assertNotEqual(practice, exam)
        allocation = smart_practice_role_allocation(25)
        self.assertEqual(sum(allocation.values()), 25)
        self.assertEqual(sha256_file(DEFAULT_BANK), EXPECTED_DEFAULT_BANK_SHA256)


if __name__ == "__main__":
    unittest.main()
