from __future__ import annotations

import copy
import unittest

from cand01r3_fixtures import (
    DEFAULT_BANK,
    EXPECTED_DEFAULT_BANK_SHA256,
    QuestionFlowHarness,
    SessionBuilderHarness,
    activate_synthetic,
    ids_of,
    progress_record,
    question,
    sha256_file,
    synthetic_authority,
)


class Cand01R3AllPathTests(unittest.TestCase):
    def setUp(self):
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()
        self.authority = synthetic_authority(train_ids=["train_a", "train_b"], probe_ids=["probe_a"])
        self.train_a = question("train_a", question_number=1, family="family_train")
        self.train_b = question("train_b", question_number=2, family="family_train")
        self.probe = question("probe_a", question_number=9, family="family_probe")
        self.pool = [self.train_a, self.train_b, self.probe]

    def tearDown(self):
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()

    def activate(self, **kwargs):
        return activate_synthetic(self.authority, **kwargs)

    def test_g3_001_probe_rejected_from_normal_practice_pool(self):
        from cand01r3_runtime import filter_training_questions

        self.activate()
        filtered = filter_training_questions(self.pool)
        self.assertEqual({"train_a", "train_b"}, ids_of(filtered))
        harness = SessionBuilderHarness(self.pool)
        builder_pool = harness.get_session_builder_pool()
        self.assertNotIn("probe_a", ids_of(builder_pool))

    def test_g3_002_probe_rejected_from_smart_practice_source_pool(self):
        from cand01r3_runtime import filter_training_questions

        self.activate(policy_id="SMART_PRACTICE_CHAMPION")
        self.assertNotIn("probe_a", ids_of(filter_training_questions(self.pool)))

    def test_g3_003_probe_rejected_before_smart_practice_signal_computation(self):
        from cand01r3_runtime import derived_training_questions

        self.activate(policy_id="SMART_PRACTICE_CHAMPION")
        source = derived_training_questions(self.pool, stage="SMART_PRACTICE_SIGNAL")
        self.assertNotIn("probe_a", ids_of(source))

    def test_g3_004_probe_rejected_from_detached_worker_snapshot(self):
        self.activate(policy_id="SMART_PRACTICE_CHAMPION")
        harness = SessionBuilderHarness(self.pool)
        snapshot = harness._smart_practice_worker_snapshot(base_pool=self.pool)
        self.assertNotIn("probe_a", ids_of(snapshot.master_questions))
        self.assertNotIn("probe_a", ids_of(snapshot.base_pool or []))

    def test_g3_005_probe_rejected_from_prewarm_cache_candidate_set(self):
        from cand01r3_runtime import derived_training_questions, partition_cache_identity

        self.activate(policy_id="SMART_PRACTICE_CHAMPION")
        cached = derived_training_questions(self.pool, stage="PREWARM_CACHE")
        self.assertNotIn("probe_a", ids_of(cached))
        first = partition_cache_identity()
        activate_synthetic(self.authority, experiment_id="other-epoch", policy_id="SMART_PRACTICE_CHAMPION")
        self.assertNotEqual(first, partition_cache_identity())

    def test_g3_006_probe_rejected_from_due_review_path(self):
        records = {
            "1": progress_record(attempts=1, next_review="2020-01-01", learner_memory={"next_review_at": "2020-01-01"}),
            "9": progress_record(attempts=1, next_review="2020-01-01", learner_memory={"next_review_at": "2020-01-01"}),
        }
        self.activate()
        harness = SessionBuilderHarness(self.pool, records)
        pool = harness.build_due_review_pool()
        self.assertNotIn("probe_a", ids_of(pool))

    def test_g3_007_probe_rejected_from_weak_retest_path(self):
        records = {
            "1": progress_record(attempts=3, wrong_count=3, last_correct=False),
            "9": progress_record(attempts=3, wrong_count=3, last_correct=False),
        }
        self.activate()
        harness = SessionBuilderHarness(self.pool, records)
        pool = harness.build_weak_retest_pool()
        self.assertNotIn("probe_a", ids_of(pool))

    def test_g3_009_probe_cannot_enter_twin_injection(self):
        self.activate()
        harness = QuestionFlowHarness(self.pool)
        twins = harness.find_question_twins(self.train_a, limit=5)
        self.assertNotIn("probe_a", ids_of(twins))
        inserted = harness._insert_followup_questions(self.train_a, [self.probe], "twin")
        self.assertEqual([], inserted)

    def test_g3_010_through_g3_017_injection_paths_reject_probe(self):
        from cand01r3_runtime import filter_training_questions, revalidate_training_question

        self.activate()
        for stage in (
            "DELAYED_RECALL",
            "MEMORY_RAMP",
            "WRONG_ANSWER_MEMORY",
            "CONFUSION_PAIR",
            "STREAK_RESCUE",
            "MISCONCEPTION_REPAIR",
            "BOSS_ROUND",
            "STEALTH_CHECKPOINT",
        ):
            filtered = filter_training_questions(self.pool, stage=stage)
            self.assertNotIn("probe_a", ids_of(filtered), stage)
            decision = revalidate_training_question(self.probe, action=stage)
            self.assertEqual("NOT_ELIGIBLE", decision.role, stage)

    def test_g3_018_followup_candidate_index_contains_train_only(self):
        self.activate()
        harness = QuestionFlowHarness(self.pool)
        harness._rebuild_followup_candidate_index()
        by_number = harness.followup_candidate_index["by_number"]
        indexed_ids = ids_of(list(by_number.values()))
        self.assertIn("train_a", indexed_ids)
        self.assertNotIn("probe_a", indexed_ids)

    def test_g3_035_stale_experimental_session_restore_fails_closed(self):
        from cand01r3_runtime import restore_experimental_session

        self.activate()
        snapshot = {
            "cand01r3": {
                "partition_epoch": "stale-epoch",
                "manifest_sha256": "deadbeef",
                "store_sha256": "deadbeef",
                "semantic_audit_sha256": "deadbeef",
                "policy_id": "RRC_1_CHALLENGER",
                "experiment_id": "cand01r3-test",
                "evaluation_epoch": "eval-1",
            },
            "question_ids": ["train_a", "probe_a"],
        }
        result = restore_experimental_session(self.pool, snapshot)
        self.assertFalse(result.accepted)
        self.assertEqual("STALE_AUTHORITY", result.reason)
        self.assertEqual([], result.questions)

    def test_g3_036_normal_non_cand01r3_session_operates_without_manifest(self):
        from cand01r3_runtime import filter_training_questions, is_cand01r3_active, restore_experimental_session

        default_questions = [
            {"question_number": 1, "prompt": "default one", "domain": "Intro"},
            {"question_number": 2, "prompt": "default two", "domain": "Intro"},
        ]
        self.assertFalse(is_cand01r3_active())
        self.assertEqual(default_questions, filter_training_questions(default_questions))
        restored = restore_experimental_session(default_questions, {"question_numbers": [1, 2]})
        self.assertTrue(restored.accepted)
        self.assertEqual(2, len(restored.questions))

    def test_g3_037_default_launch_bank_hash_unchanged(self):
        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, sha256_file(DEFAULT_BANK))

    def test_inactive_context_does_not_filter_unpartitioned_bank(self):
        from cand01r3_runtime import filter_training_questions

        harness = SessionBuilderHarness(self.pool)
        self.assertEqual(3, len(harness.get_session_builder_pool()))
        self.assertEqual(3, len(filter_training_questions(self.pool)))

    def test_restore_recomputes_eligibility_and_drops_probe(self):
        from cand01r3_runtime import persistable_authority_metadata, restore_experimental_session

        self.activate()
        snapshot = {
            "cand01r3": persistable_authority_metadata(),
            "question_ids": ["train_a", "probe_a", "train_b"],
        }
        result = restore_experimental_session(self.pool, snapshot)
        self.assertTrue(result.accepted)
        self.assertEqual(["train_a", "train_b"], [row["id"] for row in result.questions])

    def test_analytics_export_redacts_unmeasured_probe_content(self):
        from cand01r3_runtime import sanitize_learner_export

        self.activate()
        payload = {
            "history": [
                {
                    "question_id": "probe_a",
                    "prompt": "secret stem",
                    "correct_texts": ["secret answer"],
                    "selected_texts": ["secret answer"],
                    "explanation": "secret explanation",
                    "correct": True,
                }
            ]
        }
        sanitized = sanitize_learner_export(payload)
        row = sanitized["history"][0]
        self.assertEqual("probe_a", row["question_id"])
        self.assertNotIn("prompt", row)
        self.assertNotIn("correct_texts", row)
        self.assertNotIn("explanation", row)
        self.assertTrue(row.get("redacted"))

    def test_all_task7_paths_are_accounted_for(self):
        from cand01r3_paths import PATH_MATRIX, required_path_ids

        expected = [f"P{index:02d}" for index in range(1, 49)]
        self.assertEqual(expected, required_path_ids())
        self.assertEqual(set(expected), {row["PATH_ID"] for row in PATH_MATRIX})
        for row in PATH_MATRIX:
            self.assertTrue(row["PATH_ID"])
            self.assertTrue(row["SOURCE"])
            self.assertTrue(row["ENFORCEMENT_LOCATION"])
            self.assertIn(row["EARLY_FILTER"], {"YES", "NO", "N/A"})
            self.assertIn(row["LATE_REVALIDATION"], {"YES", "NO", "N/A"})
            self.assertTrue(row["TEST_ID"])
            self.assertTrue(row["STATUS"])
            self.assertNotEqual("MISSING", row["STATUS"])

    def test_smart_practice_champion_is_not_rewritten(self):
        from smart_practice_core import build_smart_practice_score
        from smart_practice_profile import SMART_PRACTICE_SCORING, UTILITY_COMPONENT_BOUNDS

        self.activate(policy_id="SMART_PRACTICE_CHAMPION")
        question_row = copy.deepcopy(self.train_a)
        meta = {
            "record": {"attempts": 0, "correct_streak": 0, "wrong_count": 0, "correct_count": 0},
            "unit_key": "topic::family_train",
            "stem_style": "single_answer",
            "objective_code": "entra_authentication",
            "source_name": "Guide",
            "base_concept_key": "concept.train",
        }
        context = {
            "profile": SMART_PRACTICE_SCORING,
            "active_smart_policy": {"policy_id": "policy-a"},
            "graph_enabled": False,
            "quality_enabled": False,
            "information_enabled": False,
            "source_map": {},
            "utility_scales": {},
            "utility_bounds": UTILITY_COMPONENT_BOUNDS,
            "role_shares": {},
            "active_policy_values": {},
        }
        result = build_smart_practice_score(question_row, qnum=1, meta=meta, context=context)
        self.assertEqual("blueprint_coverage", result.primary_role)
        self.assertIn("smart_utility", result.question_updates or result.__dict__)


if __name__ == "__main__":
    unittest.main()
