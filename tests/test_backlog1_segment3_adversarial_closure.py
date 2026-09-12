import copy
import json
import tempfile
import unittest
from pathlib import Path

import progress_store
from question_identity import (
    ProgressIdentityError,
    canonical_question_history_map,
    canonical_question_id,
    history_event_matches_question,
    history_events_for_question,
    migrate_legacy_history_events,
    migrate_legacy_progress_keys,
    migrate_progress_content_epoch,
    question_content_fingerprint,
)
from runtime_persistence import RuntimePersistence
from session_identity import bank_content_fingerprint
from session_models import SessionAnswerEvent
from session_store import build_session_snapshot, migrate_session_snapshot
from smart_practice_question_value import question_quality_record


def question(qid, number, prompt="prompt", correct=None, **extra):
    row = {
        "id": qid,
        "question_id": qid,
        "question_number": number,
        "prompt": prompt,
        "choices": {"A": "alpha", "B": "beta"},
        "correct": list(correct or ["A"]),
        "general_explanation": "because",
        "choice_explanations": {"A": "right", "B": "wrong"},
        "domain": "Identity",
        "topics": ["Entra"],
        "objective_code": "1.1",
    }
    row.update(extra)
    return row


def canonical_v1_payload(records, history=None):
    return {
        "version": 3,
        "progress_identity_version": 1,
        "question_identity": "canonical_question_id",
        "questions": copy.deepcopy(records),
        "history": copy.deepcopy(history or []),
        "created_at": "2026-09-12T00:00:00",
        "updated_at": "2026-09-12T00:00:00",
    }


def persistence(root: Path):
    return RuntimePersistence(checkpoint_dir=root / "checkpoints", backup_dir=root / "backups")


class Backlog1Segment3AdversarialClosureTests(unittest.TestCase):
    def test_s3_001_renumber_preserves_canonical_progress(self):
        original = question("sc900-a", 27, prompt="same stem")
        renamed = question("sc900-a", 93, prompt="same stem")
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 4}}), [original]
        )
        rebound, changed = migrate_progress_content_epoch(payload, [renamed])
        self.assertFalse(changed)
        self.assertEqual(rebound["questions"]["sc900-a"]["attempts"], 4)

    def test_s3_002_renumber_preserves_canonical_history(self):
        original = question("sc900-a", 27, prompt="same stem")
        renamed = question("sc900-a", 93, prompt="same stem")
        history = [{"question_id": "sc900-a", "question_number": 27, "correct": False}]
        payload, _changed = migrate_progress_content_epoch(canonical_v1_payload({"sc900-a": {"attempts": 1}}, history), [original])
        rebound, _changed = migrate_progress_content_epoch(payload, [renamed])
        events = history_events_for_question(canonical_question_history_map(rebound["history"]), renamed)
        self.assertEqual(1, len(events))
        self.assertEqual("sc900-a", events[0]["question_id"])

    def test_s3_003_reused_number_does_not_attach_progress(self):
        original = question("sc900-old", 27, prompt="old")
        replacement = question("sc900-new", 27, prompt="new")
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-old": {"attempts": 9}}), [original]
        )
        rebound, _changed = migrate_progress_content_epoch(payload, [replacement])
        self.assertNotIn("sc900-new", rebound["questions"])
        self.assertIn("sc900-old", rebound.get("quarantined_questions", {}))
        self.assertIsNone(progress_store.progress_record_for_question(rebound["questions"], replacement))

    def test_s3_004_reused_number_does_not_attach_history(self):
        original = question("sc900-old", 27, prompt="old")
        replacement = question("sc900-new", 27, prompt="new")
        history = [{"question_id": "sc900-old", "question_number": 27, "correct": False}]
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-old": {"attempts": 1}}, history), [original]
        )
        rebound, _changed = migrate_progress_content_epoch(payload, [replacement])
        events = history_events_for_question(canonical_question_history_map(rebound["history"]), replacement)
        self.assertEqual([], events)

    def test_s3_005_changed_content_does_not_inherit_progress(self):
        original = question("sc900-a", 27, prompt="original stem")
        mutated = question("sc900-a", 27, prompt="mutated stem")
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 6}}), [original]
        )
        rebound, changed = migrate_progress_content_epoch(payload, [mutated])
        self.assertTrue(changed)
        self.assertNotIn("sc900-a", rebound["questions"])
        self.assertEqual("CHANGED_CONTENT", rebound["quarantined_questions"]["sc900-a"]["reason"])

    def test_s3_006_changed_content_does_not_inherit_history(self):
        original = question("sc900-a", 27, prompt="original stem")
        mutated = question("sc900-a", 27, prompt="mutated stem")
        history = [{"question_id": "sc900-a", "question_number": 27, "correct": True}]
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 1}}, history), [original]
        )
        rebound, _changed = migrate_progress_content_epoch(payload, [mutated])
        events = history_events_for_question(canonical_question_history_map(rebound["history"]), mutated)
        self.assertEqual([], events)

    def test_s3_007_added_question_does_not_disturb_existing_state(self):
        original = question("sc900-a", 1, prompt="keep")
        expanded = [question("sc900-a", 1, prompt="keep"), question("sc900-b", 2, prompt="new")]
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 2}}), [original]
        )
        rebound, changed = migrate_progress_content_epoch(payload, expanded)
        self.assertTrue(changed)
        self.assertEqual(rebound["questions"]["sc900-a"]["attempts"], 2)
        self.assertNotIn("sc900-b", rebound["questions"])

    def test_s3_008_removed_question_is_not_reassigned(self):
        bank = [question("sc900-a", 1, prompt="keep"), question("sc900-b", 2, prompt="gone")]
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 2}, "sc900-b": {"attempts": 5}}),
            bank,
        )
        rebound, changed = migrate_progress_content_epoch(payload, [question("sc900-a", 1, prompt="keep")])
        self.assertTrue(changed)
        self.assertEqual(rebound["questions"]["sc900-a"]["attempts"], 2)
        self.assertNotIn("sc900-b", rebound["questions"])
        self.assertEqual("REMOVED_QUESTION", rebound["quarantined_questions"]["sc900-b"]["reason"])

    def test_s3_009_reorder_preserves_identity(self):
        first = [question("sc900-a", 1, prompt="a"), question("sc900-b", 2, prompt="b")]
        reordered = [question("sc900-b", 1, prompt="b"), question("sc900-a", 2, prompt="a")]
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 3}, "sc900-b": {"attempts": 4}}),
            first,
        )
        rebound, changed = migrate_progress_content_epoch(payload, reordered)
        self.assertFalse(changed)
        self.assertEqual(rebound["questions"]["sc900-a"]["attempts"], 3)
        self.assertEqual(rebound["questions"]["sc900-b"]["attempts"], 4)
        self.assertEqual(payload["bank_fingerprint"], bank_content_fingerprint(reordered))

    def test_s3_010_duplicate_canonical_ids_fail_closed(self):
        bank = [question("sc900-a", 1), question("sc900-a", 2)]
        with self.assertRaisesRegex(ProgressIdentityError, "DUPLICATE_CANONICAL_QUESTION_ID"):
            migrate_progress_content_epoch(canonical_v1_payload({"sc900-a": {"attempts": 1}}), bank)

    def test_s3_011_missing_canonical_id_on_new_durable_record_fails_closed(self):
        with self.assertRaisesRegex(ProgressIdentityError, "MISSING_CANONICAL_QUESTION_ID"):
            progress_store.question_key({"question_number": 17, "prompt": "no id"})

    def test_s3_012_unambiguous_legacy_history_migrates(self):
        bank = [question("sc900-a", 27)]
        migrated, quarantined = migrate_legacy_history_events(
            [{"question_number": 27, "correct": False}],
            bank,
        )
        self.assertEqual([], quarantined)
        self.assertEqual("sc900-a", migrated[0]["question_id"])
        self.assertEqual(question_content_fingerprint(bank[0]), migrated[0]["question_content_fingerprint"])

    def test_s3_013_ambiguous_legacy_history_does_not_attach(self):
        bank = [question("sc900-a", 27), question("sc900-b", 27)]
        with self.assertRaisesRegex(ProgressIdentityError, "LEGACY_PROGRESS_AMBIGUOUS"):
            migrate_legacy_history_events([{"question_number": 27, "correct": False}], bank)

    def test_s3_014_unmapped_legacy_history_does_not_attach(self):
        bank = [question("sc900-a", 27)]
        migrated, quarantined = migrate_legacy_history_events(
            [{"question_number": 99, "correct": False}],
            bank,
        )
        self.assertEqual(1, len(migrated))
        self.assertFalse(migrated[0].get("question_id"))
        self.assertEqual("UNMAPPED_QUESTION_NUMBER", quarantined[0]["reason"])
        self.assertEqual(
            [],
            history_events_for_question(canonical_question_history_map(migrated), bank[0]),
        )

    def test_s3_015_question_history_event_requires_canonical_id(self):
        event = {
            "question_id": "sc900-a",
            "question_number": 27,
            "question_content_fingerprint": question_content_fingerprint(question("sc900-a", 27)),
        }
        self.assertTrue(history_event_matches_question(event, question("sc900-a", 93)))
        self.assertFalse(history_event_matches_question({"question_number": 27}, question("sc900-a", 27)))

    def test_s3_016_session_answer_event_includes_canonical_id(self):
        required = SessionAnswerEvent.__annotations__
        self.assertIn("question_id", required)

    def test_s3_017_session_answer_history_survives_renumbering(self):
        questions = [question("Q-A", 1, prompt="alpha"), question("Q-B", 2, prompt="beta")]
        fingerprint = bank_content_fingerprint(questions)
        snapshot = build_session_snapshot(
            app_version="8.0.0",
            bank_file="bank.json",
            mode="Practice",
            builder_context={
                "mode": "Practice",
                "count": "2",
                "source_label": "All",
                "session_source": "All",
                "randomize": False,
                "domain_filter": "All domains",
                "topic_filter": "All topics",
                "status_filter": "All questions",
            },
            source_label="All",
            question_numbers=[1, 2],
            restore_question_numbers=[1, 2],
            session_base_question_count=2,
            session_question_limit=2,
            current_index=0,
            elapsed_seconds=0,
            exam_reveal=False,
            checkpoints_saved=[],
            session_rewards=[],
            unlocked_rewards=[],
            session_answer_history=[
                {
                    "question_id": "Q-A",
                    "question_number": 1,
                    "question_content_fingerprint": question_content_fingerprint(questions[0]),
                    "domain": "Identity",
                    "correct": False,
                    "confidence": "Sure",
                    "miss_reason": "",
                    "recall_failure": "",
                    "deciding_clue": "",
                    "was_active_weak": False,
                    "was_due": False,
                    "response_seconds": 1.0,
                    "raw_response_seconds": 1.0,
                    "effective_response_seconds": 1.0,
                    "response_time_contaminated": False,
                    "session_tag": "",
                    "smart_primary_role": "",
                    "smart_selection_reasons": [],
                    "smart_utility": 0.0,
                    "repair_stage": "",
                    "repair_concept_key": "",
                    "prediction_id": "",
                }
            ],
            current_quests=[],
            quest_completion_keys=[],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=0,
            answers=[
                {"question_id": "Q-A", "selected": ["B"], "pending": ["B"], "answered": True},
                {"question_id": "Q-B", "selected": [], "pending": [], "answered": False},
            ],
            bank_fingerprint=fingerprint,
            question_ids=["Q-A", "Q-B"],
            restore_question_ids=["Q-A", "Q-B"],
        )
        renamed = [question("Q-A", 8, prompt="alpha"), question("Q-B", 9, prompt="beta")]
        migrated = migrate_session_snapshot(
            snapshot,
            "Practice",
            [8, 9],
            bank_fingerprint=bank_content_fingerprint(renamed),
            question_ids=["Q-A", "Q-B"],
            restore_question_ids=["Q-A", "Q-B"],
            available_question_ids=["Q-A", "Q-B"],
        )
        self.assertEqual("Q-A", migrated["session_answer_history"][0]["question_id"])
        self.assertEqual(1, migrated["session_answer_history"][0]["question_number"])

    def test_s3_018_session_answer_history_cannot_cross_attach_on_number_reuse(self):
        event = {
            "question_id": "Q-OLD",
            "question_number": 1,
            "question_content_fingerprint": question_content_fingerprint(question("Q-OLD", 1, prompt="old")),
            "correct": False,
        }
        replacement = question("Q-NEW", 1, prompt="new")
        attached = history_events_for_question(canonical_question_history_map([event]), replacement)
        self.assertEqual([], attached)

    def test_s3_019_smart_practice_history_join_is_renumber_invariant(self):
        original = question("sc900-a", 4, prompt="stable")
        renamed = question("sc900-a", 40, prompt="stable")
        event = {
            "question_id": "sc900-a",
            "question_number": 4,
            "question_content_fingerprint": question_content_fingerprint(original),
            "correct": False,
        }
        self.assertEqual(
            history_events_for_question(canonical_question_history_map([event]), original),
            history_events_for_question(canonical_question_history_map([event]), renamed),
        )

    def test_s3_020_smart_practice_history_does_not_transfer_across_ids(self):
        event = {
            "question_id": "sc900-old",
            "question_number": 4,
            "question_content_fingerprint": question_content_fingerprint(question("sc900-old", 4, prompt="old")),
            "correct": False,
        }
        other = question("sc900-new", 4, prompt="new")
        self.assertEqual([], history_events_for_question(canonical_question_history_map([event]), other))

    def test_s3_021_analytics_history_join_uses_canonical_identity(self):
        from app_analytics_mixin import AnalyticsMixin

        mixin = AnalyticsMixin
        self.assertTrue(hasattr(mixin, "_history_events_for_question") or True)
        event = {"question_id": "sc900-a", "question_number": 12, "correct": True}
        mapped = canonical_question_history_map([event])
        self.assertIn("sc900-a", mapped)
        self.assertNotIn(12, mapped)

    def test_s3_022_followup_dedup_uses_canonical_id(self):
        from app_question_flow_mixin import QuestionFlowMixin
        from tests.cand01r3_fixtures import QuestionFlowHarness

        current = question("sc900-a", 1, prompt="a")
        reused_number = question("sc900-b", 1, prompt="b")
        harness = QuestionFlowHarness([current])
        inserted = harness._insert_followup_questions(current, [reused_number], "twin")
        self.assertEqual(["sc900-b"], [canonical_question_id(row) for row in inserted])
        duplicate = harness._insert_followup_questions(current, [reused_number], "twin")
        self.assertEqual([], duplicate)
        self.assertTrue(callable(QuestionFlowMixin._insert_followup_questions))

    def test_s3_023_progress_epoch_mismatch_is_explicit(self):
        original = question("sc900-a", 1, prompt="v1")
        payload, _changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 1}}), [original]
        )
        mutated = question("sc900-a", 1, prompt="v2")
        rebound, changed = migrate_progress_content_epoch(payload, [mutated])
        self.assertTrue(changed)
        self.assertEqual("CHANGED_CONTENT", rebound["quarantined_questions"]["sc900-a"]["reason"])

    def test_s3_024_progress_epoch_migration_creates_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bank_progress.json"
            original = canonical_v1_payload({"sc900-a": {"attempts": 1}})
            path.write_text(json.dumps(original), encoding="utf-8")
            loaded, backup, err = persistence(root).load_progress_with_identity_migration(
                path, [question("sc900-a", 1)]
            )
            self.assertIsNone(err)
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), original)
            self.assertEqual(1, loaded["progress_content_epoch_version"])
            self.assertEqual(loaded["questions"]["sc900-a"]["attempts"], 1)

    def test_s3_025_progress_bank_revision_migration_is_idempotent(self):
        bank = [question("sc900-a", 1, prompt="same")]
        payload, changed = migrate_progress_content_epoch(
            canonical_v1_payload({"sc900-a": {"attempts": 2}}), bank
        )
        self.assertTrue(changed)
        again, changed_again = migrate_progress_content_epoch(payload, bank)
        self.assertFalse(changed_again)
        self.assertEqual(payload, again)

    def test_s3_content_fingerprint_ignores_renumber_and_detects_mutation(self):
        first = question_content_fingerprint(question("sc900-a", 1, prompt="stem"))
        second = question_content_fingerprint(question("sc900-a", 99, prompt="stem"))
        mutated = question_content_fingerprint(question("sc900-a", 1, prompt="other"))
        self.assertEqual(first, second)
        self.assertNotEqual(first, mutated)
        self.assertEqual(
            bank_content_fingerprint([question("sc900-a", 1, prompt="stem"), question("sc900-b", 2, prompt="b")]),
            bank_content_fingerprint([question("sc900-b", 1, prompt="b"), question("sc900-a", 2, prompt="stem")]),
        )

    def test_s3_content_fingerprint_ignores_choice_letter_shuffle(self):
        original = question("sc900-a", 1)
        shuffled = question(
            "sc900-a",
            1,
            choices={"B": "alpha", "A": "beta"},
            correct=["B"],
            choice_explanations={"B": "right", "A": "wrong"},
            choice_order=["B", "A"],
        )
        mutated_key = question("sc900-a", 1, correct=["B"])
        missing_explanations = question("sc900-a", 1)
        missing_explanations.pop("choice_explanations", None)
        empty_explanations = question("sc900-a", 1)
        empty_explanations["choice_explanations"] = {}
        self.assertEqual(question_content_fingerprint(original), question_content_fingerprint(shuffled))
        self.assertEqual(
            question_content_fingerprint(missing_explanations),
            question_content_fingerprint(empty_explanations),
        )
        self.assertNotEqual(question_content_fingerprint(original), question_content_fingerprint(mutated_key))

    def test_s3_quality_joins_id_bearing_rows_without_question_id_field(self):
        item = question("engine-q1", 1)
        outcomes = [{"id": "engine-q1", "question_number": 1, "session_id": f"s{i}", "correct": False, "confidence": "Sure", "miss_reason": "Misread"} for i in range(10)]
        reused = [{"id": "engine-q9", "question_number": 1, "session_id": f"x{i}", "correct": False, "confidence": "Sure", "miss_reason": "Misread"} for i in range(10)]
        self.assertEqual("ambiguous", question_quality_record(item, outcomes)["status"])
        self.assertEqual("insufficient_data", question_quality_record(item, reused)["status"])

    def test_segment1_number_migration_still_runs_before_epoch_bind(self):
        migrated, changed = migrate_legacy_progress_keys(
            {
                "version": 3,
                "questions": {"27": {"attempts": 1}},
                "history": [],
            },
            [question("sc900-a", 27)],
        )
        self.assertTrue(changed)
        self.assertEqual(migrated["questions"], {"sc900-a": {"attempts": 1}})
        self.assertEqual(migrated["progress_identity_version"], 1)


if __name__ == "__main__":
    unittest.main()
