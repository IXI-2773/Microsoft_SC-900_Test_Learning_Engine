import copy
import tempfile
import unittest
from pathlib import Path

from app_constants import MODE_PRACTICE
from app_session_persistence_mixin import SessionPersistenceMixin
from session_identity import bank_content_fingerprint, ordered_question_ids
from session_store import build_session_snapshot


def question(question_id: str, number: int, prompt: str):
    return {
        "id": question_id,
        "question_number": number,
        "prompt": prompt,
        "choices": {"A": "Alpha", "B": "Beta"},
        "correct": ["A"],
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


def blank_answer():
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


class FakeSessionApp(SessionPersistenceMixin):
    pass


class Segment2SessionAppIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bank_path = self.root / "bank.json"
        self.bank_path.write_text("{}", encoding="utf-8")
        self.questions = [question("Q-A", 1, "Alpha?"), question("Q-B", 2, "Beta?")]

    def make_app(self, questions=None):
        app = FakeSessionApp()
        app.user_data_dir = self.root
        app.bank_path = self.bank_path
        app.active_session_mode = MODE_PRACTICE
        app.questions = copy.deepcopy(questions or self.questions)
        app.master_questions = copy.deepcopy(questions or self.questions)
        app.session_restore_question_numbers = [q["question_number"] for q in app.questions]
        app.session_restore_question_ids = ordered_question_ids(app.questions)
        return app

    def snapshot_for(self, questions=None):
        questions = copy.deepcopy(questions or self.questions)
        ids = ordered_question_ids(questions)
        fingerprint = bank_content_fingerprint(questions)
        return build_session_snapshot(
            app_version="test",
            bank_file=self.bank_path.name,
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
            question_numbers=[q["question_number"] for q in questions],
            restore_question_numbers=[q["question_number"] for q in questions],
            bank_fingerprint=fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
            session_base_question_count=len(questions),
            session_question_limit=len(questions),
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
            answers=[blank_answer() for _ in questions],
        )

    def test_app_identity_match_survives_pure_renumber(self):
        saved = self.snapshot_for(self.questions)
        renumbered = copy.deepcopy(self.questions)
        renumbered[0]["question_number"] = 101
        renumbered[1]["question_number"] = 102
        app = self.make_app(renumbered)
        self.assertTrue(app._saved_session_matches_current(saved))

    def test_app_identity_match_rejects_same_numbers_when_content_changes(self):
        saved = self.snapshot_for(self.questions)
        changed = copy.deepcopy(self.questions)
        changed[0]["prompt"] = "Different content"
        app = self.make_app(changed)
        self.assertFalse(app._saved_session_matches_current(saved))

    def test_ordinary_session_filename_changes_with_bank_content(self):
        original = self.make_app(self.questions)
        changed_questions = copy.deepcopy(self.questions)
        changed_questions[0]["prompt"] = "Different content"
        changed = self.make_app(changed_questions)
        original_path = original.session_file_for_bank(
            self.bank_path,
            mode=MODE_PRACTICE,
            questions=original.questions,
        )
        changed_path = changed.session_file_for_bank(
            self.bank_path,
            mode=MODE_PRACTICE,
            questions=changed.questions,
        )
        self.assertNotEqual(original_path.name, changed_path.name)


if __name__ == "__main__":
    unittest.main()
