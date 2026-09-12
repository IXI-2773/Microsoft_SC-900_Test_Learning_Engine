import copy
import unittest

from app_constants import MODE_PRACTICE
from session_identity import (
    bank_content_fingerprint,
    canonical_session_signature,
    ordered_question_ids,
)
import session_store
from session_store import build_session_snapshot, migrate_session_snapshot, saved_session_matches_current


def _question(question_id: str, number: int, prompt: str = "Prompt", correct=None):
    return {
        "id": question_id,
        "question_number": number,
        "prompt": prompt,
        "choices": {"A": "Alpha", "B": "Beta"},
        "correct": list(correct or ["A"]),
        "general_explanation": "Because.",
        "choice_explanations": {"A": "Right", "B": "Wrong"},
        "domain": "Identity",
        "chapter": "1",
        "subtitle": "Basics",
        "question_type": "multiple_choice",
        "topics": ["Entra"],
        "objective_code": "1.1",
        "study_focus": "Core",
        "choice_order": ["A", "B"],
    }


def _blank_answer(selected=None, answered=False):
    return {
        "selected": list(selected or []),
        "pending": list(selected or []),
        "answered": bool(answered),
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


class Segment2SessionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.questions = [_question("Q-A", 1, "Alpha?"), _question("Q-B", 2, "Beta?")]
        self.fingerprint = bank_content_fingerprint(self.questions)
        self.question_ids = ordered_question_ids(self.questions)

    def _snapshot(self):
        return build_session_snapshot(
            app_version="test",
            bank_file="bank.json",
            mode=MODE_PRACTICE,
            builder_context={
                "mode": MODE_PRACTICE,
                "count": "2",
                "source_label": "Full bank",
                "session_source": "",
                "randomize": False,
                "domain_filter": "All domains",
                "topic_filter": "All topics",
                "status_filter": "All questions",
            },
            source_label="Full bank",
            question_numbers=[1, 2],
            restore_question_numbers=[1, 2],
            bank_fingerprint=self.fingerprint,
            question_ids=self.question_ids,
            restore_question_ids=self.question_ids,
            session_base_question_count=2,
            session_question_limit=2,
            current_index=0,
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
            answers=[_blank_answer(["A"], True), _blank_answer()],
        )

    def test_bank_fingerprint_ignores_reorder_and_question_number(self):
        changed = [copy.deepcopy(self.questions[1]), copy.deepcopy(self.questions[0])]
        changed[0]["question_number"] = 91
        changed[1]["question_number"] = 92
        self.assertEqual(self.fingerprint, bank_content_fingerprint(changed))

    def test_bank_fingerprint_changes_when_question_content_changes(self):
        changed = copy.deepcopy(self.questions)
        changed[0]["prompt"] = "Changed meaning?"
        self.assertNotEqual(self.fingerprint, bank_content_fingerprint(changed))

    def test_bank_fingerprint_changes_when_canonical_id_changes(self):
        changed = copy.deepcopy(self.questions)
        changed[0]["id"] = "Q-NEW"
        self.assertNotEqual(self.fingerprint, bank_content_fingerprint(changed))

    def test_bank_fingerprint_rejects_missing_or_duplicate_ids(self):
        missing = [dict(self.questions[0])]
        missing[0].pop("id")
        with self.assertRaises(ValueError):
            bank_content_fingerprint(missing)
        with self.assertRaises(ValueError):
            bank_content_fingerprint([self.questions[0], copy.deepcopy(self.questions[0])])

    def test_session_signature_is_order_sensitive_for_canonical_ids(self):
        forward = canonical_session_signature(MODE_PRACTICE, self.fingerprint, ["Q-A", "Q-B"])
        reverse = canonical_session_signature(MODE_PRACTICE, self.fingerprint, ["Q-B", "Q-A"])
        self.assertNotEqual(forward, reverse)

    def test_new_snapshot_contains_fingerprint_and_canonical_ids(self):
        snapshot = self._snapshot()
        self.assertEqual(4, snapshot["schema_version"])
        self.assertEqual(self.fingerprint, snapshot["bank_fingerprint"])
        self.assertEqual(["Q-A", "Q-B"], snapshot["question_ids"])
        self.assertEqual(["Q-A", "Q-B"], snapshot["restore_question_ids"])
        self.assertEqual(["Q-A", "Q-B"], [row["question_id"] for row in snapshot["answers"]])

    def test_matching_rejects_same_numbers_when_bank_content_changed(self):
        snapshot = self._snapshot()
        changed = copy.deepcopy(self.questions)
        changed[0]["prompt"] = "Different content"
        changed_fingerprint = bank_content_fingerprint(changed)
        self.assertFalse(
            saved_session_matches_current(
                snapshot,
                MODE_PRACTICE,
                [1, 2],
                [1, 2],
                bank_fingerprint=changed_fingerprint,
                current_question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
            )
        )

    def test_matching_survives_pure_renumber_when_ids_and_content_are_stable(self):
        snapshot = self._snapshot()
        renumbered = copy.deepcopy(self.questions)
        renumbered[0]["question_number"] = 101
        renumbered[1]["question_number"] = 102
        self.assertTrue(
            saved_session_matches_current(
                snapshot,
                MODE_PRACTICE,
                [101, 102],
                [101, 102],
                bank_fingerprint=bank_content_fingerprint(renumbered),
                current_question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
            )
        )

    def test_migration_rejects_answer_cardinality_mismatch(self):
        snapshot = self._snapshot()
        snapshot["answers"] = snapshot["answers"][:1]
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                snapshot,
                MODE_PRACTICE,
                [1, 2],
                available_question_numbers=[1, 2],
                bank_fingerprint=self.fingerprint,
                question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
                available_question_ids=["Q-A", "Q-B"],
            )

    def test_migration_rejects_duplicate_or_missing_answer_question_id(self):
        duplicate = self._snapshot()
        duplicate["answers"][1]["question_id"] = "Q-A"
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                duplicate,
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint=self.fingerprint,
                question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
                available_question_ids=["Q-A", "Q-B"],
            )
        missing = self._snapshot()
        missing["answers"][0].pop("question_id")
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                missing,
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint=self.fingerprint,
                question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
                available_question_ids=["Q-A", "Q-B"],
            )

    def test_migration_rejects_bank_fingerprint_mismatch(self):
        snapshot = self._snapshot()
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                snapshot,
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint="0" * 64,
                question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
                available_question_ids=["Q-A", "Q-B"],
            )

    def test_legacy_ordinary_snapshot_fails_closed_without_explicit_override(self):
        legacy = {
            "schema_version": 3,
            "mode": MODE_PRACTICE,
            "question_numbers": [1, 2],
            "restore_question_numbers": [1, 2],
            "answers": [_blank_answer(), _blank_answer()],
        }
        self.assertFalse(
            saved_session_matches_current(
                legacy,
                MODE_PRACTICE,
                [1, 2],
                [1, 2],
                bank_fingerprint=self.fingerprint,
                current_question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
            )
        )
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                legacy,
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint=self.fingerprint,
                question_ids=["Q-A", "Q-B"],
                restore_question_ids=["Q-A", "Q-B"],
                available_question_ids=["Q-A", "Q-B"],
            )

    def test_cand_v3_question_ids_metadata_remains_legacy_when_explicitly_allowed(self):
        legacy_cand = {
            "schema_version": 3,
            "mode": MODE_PRACTICE,
            "question_numbers": [1, 2],
            "restore_question_numbers": [1, 2],
            "question_ids": ["Q-A", "Q-B"],
            "answers": [_blank_answer(), _blank_answer()],
        }
        migrated = migrate_session_snapshot(
            legacy_cand,
            MODE_PRACTICE,
            [1, 2],
            available_question_numbers=[1, 2],
            allow_legacy=True,
        )
        self.assertEqual(3, migrated["schema_version"])
        self.assertTrue(
            saved_session_matches_current(
                legacy_cand,
                MODE_PRACTICE,
                [1, 2],
                [1, 2],
                allow_legacy=True,
            )
        )

    def test_answer_rows_are_bound_by_question_id_not_position(self):
        snapshot = self._snapshot()
        reversed_rows = [copy.deepcopy(snapshot["answers"][1]), copy.deepcopy(snapshot["answers"][0])]
        by_id = session_store.answer_states_by_question_id(reversed_rows)
        self.assertEqual([], by_id["Q-B"]["selected"])
        self.assertEqual(["A"], by_id["Q-A"]["selected"])
        self.assertTrue(by_id["Q-A"]["answered"])


if __name__ == "__main__":
    unittest.main()
