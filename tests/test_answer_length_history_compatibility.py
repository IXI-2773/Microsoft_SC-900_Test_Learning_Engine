from __future__ import annotations

import unittest
from copy import deepcopy

from app_constants import MODE_PRACTICE
from question_identity import (
    CHANGED_CONTENT,
    PROGRESS_CONTENT_EPOCH_VERSION,
    PROGRESS_IDENTITY_KIND,
    PROGRESS_IDENTITY_VERSION,
    bank_content_fingerprint,
    canonical_question_id,
    migrate_progress_content_epoch,
    question_content_fingerprint,
)
from session_store import build_session_snapshot, saved_session_matches_current
from tools.bank_revision_guard import compare_bank_invariants


def make_question(
    question_id: str = "sc900-x",
    *,
    choices: dict[str, str] | None = None,
    correct: list[str] | None = None,
) -> dict:
    choice_map = dict(
        choices
        or {
            "A": "one",
            "B": "two",
            "C": "three",
            "D": "four",
        }
    )
    return {
        "id": question_id,
        "question_number": 1,
        "prompt": "Which option is correct?",
        "question_type": "single",
        "choices": choice_map,
        "correct": list(correct or ["A"]),
        "general_explanation": "Test explanation.",
        "choice_explanations": {letter: f"Explanation {letter}" for letter in choice_map},
        "domain": "microsoft_entra",
        "chapter": "Test chapter",
        "subtitle": "Test subtitle",
        "topics": ["Test topic"],
        "objective_code": "2.1",
        "study_focus": "Test focus",
        "exam_calibration_tier": "CORE",
        "exam_simulation_eligible": True,
    }


def canonical_progress_for(questions: list[dict], records: dict) -> dict:
    fingerprints = {
        canonical_question_id(question): question_content_fingerprint(question)
        for question in questions
    }
    return {
        "version": 3,
        "progress_identity_version": PROGRESS_IDENTITY_VERSION,
        "question_identity": PROGRESS_IDENTITY_KIND,
        "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
        "bank_fingerprint": bank_content_fingerprint(questions),
        "question_content_fingerprints": fingerprints,
        "questions": deepcopy(records),
        "history": [],
        "created_at": "2026-09-17T00:00:00",
        "updated_at": "2026-09-17T00:00:00",
    }


def canonical_session_for(question: dict) -> dict:
    question_id = canonical_question_id(question)
    fingerprint = bank_content_fingerprint([question])
    return build_session_snapshot(
        app_version="test",
        bank_file="sc900_bank_v8_final.json",
        mode=MODE_PRACTICE,
        builder_context={"mode": MODE_PRACTICE, "count": "1"},
        source_label="All",
        question_numbers=[1],
        restore_question_numbers=[1],
        session_base_question_count=1,
        session_question_limit=1,
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
        answers=[{}],
        bank_fingerprint=fingerprint,
        question_ids=[question_id],
        restore_question_ids=[question_id],
    )


class AnswerLengthHistoryCompatibilityTests(unittest.TestCase):
    def test_unchanged_content_preserves_bound_progress(self):
        original = make_question()
        payload = canonical_progress_for([original], {"sc900-x": {"attempts": 7}})

        migrated, changed = migrate_progress_content_epoch(payload, [deepcopy(original)])

        self.assertFalse(changed)
        self.assertEqual({"attempts": 7}, migrated["questions"]["sc900-x"])
        self.assertNotIn("sc900-x", migrated.get("quarantined_questions", {}))

    def test_wording_only_choice_edit_changes_content_fingerprint_and_quarantines_prior_state(self):
        original = make_question()
        revised = deepcopy(original)
        revised["choices"]["D"] = "a more realistic distractor"

        payload = canonical_progress_for([original], {"sc900-x": {"attempts": 7}})
        migrated, changed = migrate_progress_content_epoch(payload, [revised])

        self.assertTrue(changed)
        self.assertNotEqual(question_content_fingerprint(original), question_content_fingerprint(revised))
        self.assertNotIn("sc900-x", migrated["questions"])
        self.assertEqual(
            CHANGED_CONTENT,
            migrated["quarantined_questions"]["sc900-x"]["reason"],
        )

    def test_wording_only_choice_edit_invalidates_existing_canonical_saved_session(self):
        original = make_question()
        revised = deepcopy(original)
        revised["choices"]["D"] = "a more realistic distractor"

        old_bank_fp = bank_content_fingerprint([original])
        new_bank_fp = bank_content_fingerprint([revised])
        self.assertNotEqual(old_bank_fp, new_bank_fp)

        saved = canonical_session_for(original)
        self.assertFalse(
            saved_session_matches_current(
                saved,
                MODE_PRACTICE,
                [1],
                [1],
                bank_fingerprint=new_bank_fp,
                current_question_ids=["sc900-x"],
                restore_question_ids=["sc900-x"],
            )
        )

    def test_mechanical_invariant_guard_can_pass_while_history_compatibility_fails_closed(self):
        original = make_question()
        revised = deepcopy(original)
        revised["choices"]["D"] = "a more realistic distractor"

        self.assertEqual(
            [],
            compare_bank_invariants([original], [revised], expected_count=1),
        )

        payload = canonical_progress_for([original], {"sc900-x": {"attempts": 7}})
        migrated, changed = migrate_progress_content_epoch(payload, [revised])
        self.assertTrue(changed)
        self.assertEqual(
            CHANGED_CONTENT,
            migrated["quarantined_questions"]["sc900-x"]["reason"],
        )


if __name__ == "__main__":
    unittest.main()
