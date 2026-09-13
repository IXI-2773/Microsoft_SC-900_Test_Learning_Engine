from __future__ import annotations

import json
import time
import unittest
from pathlib import Path

from app_constants import MODE_EXAM, MODE_PRACTICE
from progress_store import default_progress_record, normalize_progress_record
from question_bank import load_bank, stable_shuffle_question
from question_identity import bank_content_fingerprint, canonical_question_id
from session_identity import canonical_session_signature, ordered_question_ids
from session_models import apply_answer_state
from session_store import build_session_snapshot, migrate_session_snapshot
from smart_practice_profile import smart_practice_role_allocation
from tools.validate_sc900_microsoft_corpus import DEFAULT_BANK, EXPECTED_DEFAULT_BANK_SHA256, sha256_file

ROOT = Path(__file__).resolve().parents[1]
FINAL_BANK = (
    ROOT / "content" / "sc900" / "microsoft-learn-corpus" / "compiled" / "sc900_microsoft_learn_corpus_bank.json"
)
EXPECTED_FINAL_SHA256 = "8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254"


def _blank_answer() -> dict:
    return {
        "selected": [],
        "pending": [],
        "answered": False,
        "flagged": False,
        "suspended": False,
        "last_confidence": "",
        "last_miss_reason": "",
        "recall_ready": False,
        "session_tag": "",
        "smart_primary_role": "",
        "smart_selection_reasons": [],
        "smart_utility": 0.0,
        "smart_utility_breakdown": {},
        "smart_policy_version": "",
        "smart_policy_id": "",
        "smart_concept_key": "",
        "smart_root_cause": "",
        "smart_root_cause_confidence": 0.0,
        "smart_supporting_concepts": [],
        "smart_graph_version": "",
        "smart_information_value": 0.0,
        "smart_information_breakdown": {},
        "smart_question_quality_status": "",
        "smart_question_quality_confidence": 0.0,
        "smart_graph_bottleneck": 0.0,
        "repair_stage": "",
        "repair_concept_key": "",
        "legacy_repair_concept_key": "",
        "prediction_id": "",
        "prediction_snapshot": {},
    }


class FinalBankRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        started = time.perf_counter()
        cls.bank = load_bank(FINAL_BANK)
        cls.load_ms = (time.perf_counter() - started) * 1000
        cls.questions = cls.bank["questions"]
        cls.ids = [canonical_question_id(row) for row in cls.questions]
        cls.fingerprint = bank_content_fingerprint(cls.questions)

    def test_frozen_bank_digest_and_default_bank_isolation(self):
        self.assertEqual(sha256_file(FINAL_BANK), EXPECTED_FINAL_SHA256)
        self.assertEqual(sha256_file(DEFAULT_BANK), EXPECTED_DEFAULT_BANK_SHA256)
        self.assertNotEqual(sha256_file(FINAL_BANK), EXPECTED_DEFAULT_BANK_SHA256)

    def test_load_and_identity_for_large_candidate_bank(self):
        self.assertGreaterEqual(len(self.questions), 400)
        self.assertEqual(len(self.ids), len(set(self.ids)))
        self.assertEqual(len(self.fingerprint), 64)
        self.assertLess(self.load_ms, 5000)
        empty_td = [row["id"] for row in self.questions if not str(row.get("tested_decision") or "").strip()]
        self.assertEqual(empty_td, [])
        self.assertEqual(sum(1 for row in self.questions if row.get("question_type") == "multi"), 5)

    def test_practice_exam_and_smart_practice_builders(self):
        ordered = ordered_question_ids(self.questions)
        self.assertEqual(ordered, self.ids)
        practice = canonical_session_signature(MODE_PRACTICE, self.fingerprint, ordered[:25])
        exam = canonical_session_signature(MODE_EXAM, self.fingerprint, ordered[:50])
        self.assertNotEqual(practice, exam)
        shuffled = ordered_question_ids([stable_shuffle_question(dict(row)) for row in self.questions[:40]])
        self.assertEqual(len(shuffled), 40)
        self.assertEqual(sum(smart_practice_role_allocation(25).values()), 25)

    def test_resume_snapshot_round_trip_on_final_bank(self):
        subset = list(self.questions[:12])
        ids = ordered_question_ids(subset)
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=str(FINAL_BANK),
            mode=MODE_PRACTICE,
            builder_context={
                "mode": MODE_PRACTICE,
                "count": "12",
                "source_label": "Final candidate bank",
                "session_source": "All",
                "randomize": False,
                "domain_filter": "All domains",
                "topic_filter": "All topics",
                "status_filter": "All questions",
            },
            source_label="Final candidate bank",
            question_numbers=[row["question_number"] for row in subset],
            restore_question_numbers=[row["question_number"] for row in subset],
            session_base_question_count=len(subset),
            session_question_limit=len(subset),
            current_index=3,
            elapsed_seconds=0,
            exam_reveal=True,
            checkpoints_saved=[],
            session_rewards=[],
            unlocked_rewards=[],
            session_answer_history=[],
            current_quests=[],
            quest_completion_keys=[],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=0,
            answers=[_blank_answer() for _ in subset],
            bank_fingerprint=self.fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
        )
        migrated = migrate_session_snapshot(
            snapshot,
            MODE_PRACTICE,
            [row["question_number"] for row in subset],
            bank_fingerprint=self.fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
            available_question_ids=ids,
        )
        self.assertEqual(migrated["bank_fingerprint"], self.fingerprint)
        self.assertEqual(migrated["question_ids"], ids)
        self.assertEqual(migrated["current_index"], 3)

    def test_confidence_and_progress_records_for_final_ids(self):
        question = dict(self.questions[0])
        progress = normalize_progress_record(default_progress_record())
        self.assertEqual(progress["last_confidence"], "")
        updated = apply_answer_state(
            question, {"selected": ["A"], "pending": ["A"], "answered": True, "last_confidence": "Sure"}
        )
        self.assertEqual(updated["last_confidence"], "Sure")
        self.assertTrue(updated["answered"])

    def test_soak_session_signatures_do_not_collapse(self):
        signatures = []
        for count in (10, 25, 50, 100):
            ordered = ordered_question_ids(self.questions[:count])
            signatures.append(canonical_session_signature(MODE_PRACTICE, self.fingerprint, ordered))
            signatures.append(canonical_session_signature(MODE_EXAM, self.fingerprint, ordered))
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_fingerprint_is_stable_across_reload(self):
        again = load_bank(FINAL_BANK)["questions"]
        self.assertEqual(bank_content_fingerprint(again), self.fingerprint)
        self.assertEqual(json.dumps(self.ids), json.dumps([canonical_question_id(row) for row in again]))

    def test_ledger_covers_every_original_item(self):
        ledger_path = ROOT / "content" / "sc900" / "microsoft-learn-corpus" / "research" / "final_audit_ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(ledger["original_approved_count"], 500)
        self.assertEqual(len(ledger["items"]), 500)
        self.assertEqual(ledger["questions_with_empty_tested_decision"], 0)
        self.assertTrue(ledger["all_final_questions_audited"])
        self.assertEqual(ledger["final_approved_count"], len(self.questions))


if __name__ == "__main__":
    unittest.main()
