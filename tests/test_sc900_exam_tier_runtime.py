from __future__ import annotations

import json
import logging
import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import app as app_module
from app_constants import MODE_EXAM, MODE_PRACTICE, MODE_SMART_PRACTICE
from progress_store import normalize_progress_record
from question_bank import load_bank
from question_identity import bank_content_fingerprint, canonical_question_id
from session_identity import ordered_question_ids
from session_store import build_session_snapshot
from tools.sc900_exam_calibration import (
    APPLIED,
    CALIBRATED_BANK_SHA256,
    CALIBRATION_VERSION,
    COMPILED_BANK_PATH,
    CORE,
    DEFAULT_BANK,
    EXPECTED_DEFAULT_BANK_SHA256,
    STRETCH,
    VALID_TIERS,
    sha256_file,
)

CORE_ID = "core-q"
APPLIED_ID = "applied-q"
STRETCH_ID = "stretch-q"
INELIGIBLE_ID = "ineligible-q"
LEGACY_ID = "legacy-q"


def _question(
    question_id: str,
    number: int,
    *,
    domain: str,
    topics: list[str],
    exam_simulation_eligible=None,
    exam_calibration_tier: str | None = None,
):
    payload = {
        "id": question_id,
        "question_number": number,
        "prompt": f"Prompt for {question_id}",
        "choices": {"A": "Correct", "B": "Wrong"},
        "correct": ["A"],
        "general_explanation": "Because.",
        "choice_explanations": {"A": "Right", "B": "Wrong"},
        "domain": domain,
        "chapter": "1",
        "subtitle": "Basics",
        "question_type": "multiple_choice",
        "topics": list(topics),
        "objective_code": "1.1",
        "study_focus": "Core",
        "choice_order": ["A", "B"],
        "source_name": "Synthetic",
    }
    if exam_calibration_tier is not None:
        payload["exam_calibration_tier"] = exam_calibration_tier
        payload["reasoning_steps"] = 2 if exam_calibration_tier == STRETCH else 1
        payload["calibration_version"] = CALIBRATION_VERSION
    if exam_simulation_eligible is not None:
        payload["exam_simulation_eligible"] = exam_simulation_eligible
    return payload


def _blank_answer():
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


def synthetic_questions():
    return [
        _question(
            STRETCH_ID,
            1,
            domain="Identity",
            topics=["Entra"],
            exam_simulation_eligible=False,
            exam_calibration_tier=STRETCH,
        ),
        _question(
            CORE_ID,
            2,
            domain="Identity",
            topics=["Entra"],
            exam_simulation_eligible=True,
            exam_calibration_tier=CORE,
        ),
        _question(
            APPLIED_ID,
            3,
            domain="Compliance",
            topics=["DLP"],
            exam_simulation_eligible=True,
            exam_calibration_tier=APPLIED,
        ),
        _question(
            INELIGIBLE_ID,
            4,
            domain="Security",
            topics=["Sentinel"],
            exam_simulation_eligible=False,
            exam_calibration_tier=STRETCH,
        ),
        _question(LEGACY_ID, 5, domain="Security", topics=["Sentinel"]),
    ]


class ExamTierRuntimeTests(unittest.TestCase):
    def make_app(self, questions=None):
        self.tmpdir_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir_ctx.cleanup)
        tmpdir = Path(self.tmpdir_ctx.name)
        user_data = tmpdir / "user_data"
        checkpoints = user_data / "checkpoints"
        backups = user_data / "backups"
        logs = user_data / "logs"
        for folder in (user_data, checkpoints, backups, logs):
            folder.mkdir(parents=True, exist_ok=True)
        bank_path = tmpdir / "exam_tier_bank.json"
        bank_path.write_text(
            json.dumps({"title": "Exam Tier Bank", "questions": questions or synthetic_questions()}),
            encoding="utf-8",
        )
        patches = [
            mock.patch.object(app_module, "APP_DIR", tmpdir),
            mock.patch.object(app_module, "USER_DATA_DIR", user_data),
            mock.patch.object(app_module, "CHECKPOINT_DIR", checkpoints),
            mock.patch.object(app_module, "BACKUP_DIR", backups),
            mock.patch.object(app_module, "CONFIG_PATH", user_data / "config.json"),
            mock.patch.object(app_module, "DEFAULT_BANK", bank_path),
            mock.patch.object(app_module.TestingEngineApp, "_tick", lambda self: None),
            mock.patch.object(
                app_module.TestingEngineApp,
                "_collect_answer_feedback",
                lambda self, q, is_correct: {"confidence": "Sure", "miss_reason": ""},
            ),
            mock.patch.object(app_module.messagebox, "showwarning", return_value=None),
            mock.patch.object(app_module.messagebox, "showerror", return_value=None),
            mock.patch.object(app_module.messagebox, "showinfo", return_value=None),
            mock.patch.object(app_module.messagebox, "askyesno", return_value=True),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        try:
            root = app_module.tk.Tk()
        except app_module.tk.TclError as exc:
            self.skipTest(f"Tk unavailable: {exc}")
        self.addCleanup(root.destroy)
        root.withdraw()
        root_logger = logging.getLogger()
        previous_handlers = list(root_logger.handlers)
        previous_level = root_logger.level
        storage_logger = logging.getLogger("storage_utils")
        previous_propagate = storage_logger.propagate

        def restore_logging():
            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)
                handler.close()
            for handler in previous_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(previous_level)
            storage_logger.propagate = previous_propagate

        self.addCleanup(restore_logging)
        return app_module.TestingEngineApp(root)

    def session_ids(self, app):
        return [canonical_question_id(question) for question in app.questions]

    def start_mode(self, app, mode, *, count="All visible", randomize=False, source="All", domain=None, topic=None):
        app.session_mode_var.set(mode)
        app.session_count_var.set(count)
        app.session_random_var.set(randomize)
        app.session_source_var.set(source)
        app.domain_filter_var.set(domain or "All domains")
        app.topic_filter_var.set(topic or "All topics")
        app.status_filter_var.set("All questions")
        app.start_custom_session()

    def by_id(self, app, question_id):
        return next(question for question in app.master_questions if canonical_question_id(question) == question_id)

    def test_r1_new_exam_excludes_explicit_ineligible_question(self):
        app = self.make_app()
        original_master = [canonical_question_id(question) for question in app.master_questions]
        self.start_mode(app, MODE_EXAM, count="1", randomize=False)
        ids = self.session_ids(app)
        self.assertNotIn(STRETCH_ID, ids)
        self.assertNotIn(INELIGIBLE_ID, ids)
        self.assertEqual([CORE_ID], ids)
        self.assertEqual(original_master, [canonical_question_id(question) for question in app.master_questions])
        self.assertFalse(self.by_id(app, STRETCH_ID).get("exam_simulation_eligible"))

    def test_r2_practice_retains_ineligible_question(self):
        app = self.make_app()
        self.start_mode(app, MODE_PRACTICE, count="All visible", randomize=False)
        ids = self.session_ids(app)
        self.assertEqual([STRETCH_ID, CORE_ID, APPLIED_ID, INELIGIBLE_ID, LEGACY_ID], ids)

    def test_r3_smart_practice_keeps_ineligible_in_candidate_population(self):
        app = self.make_app()
        app.session_mode_var.set(MODE_SMART_PRACTICE)
        candidate_ids = [canonical_question_id(question) for question in app.get_filtered_master_pool()]
        self.assertIn(STRETCH_ID, candidate_ids)
        self.assertIn(INELIGIBLE_ID, candidate_ids)
        self.start_mode(app, MODE_SMART_PRACTICE, count="All visible", randomize=False)
        self.assertIn(STRETCH_ID, [canonical_question_id(question) for question in app.get_filtered_master_pool()])

    def test_r4_missing_exam_simulation_eligible_remains_exam_usable(self):
        app = self.make_app()
        self.assertNotIn("exam_simulation_eligible", self.by_id(app, LEGACY_ID))
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False)
        ids = self.session_ids(app)
        self.assertIn(LEGACY_ID, ids)
        self.assertIn(CORE_ID, ids)
        self.assertIn(APPLIED_ID, ids)
        self.assertNotIn(STRETCH_ID, ids)
        self.assertNotIn(INELIGIBLE_ID, ids)

    def test_r5_persisted_exam_with_stretch_restores_saved_identity_order(self):
        app = self.make_app()
        historical = [
            self.by_id(app, STRETCH_ID),
            self.by_id(app, CORE_ID),
            self.by_id(app, INELIGIBLE_ID),
        ]
        builder = {
            "mode": MODE_EXAM,
            "count": "All visible",
            "source_label": "All",
            "session_source": "All",
            "randomize": False,
            "domain_filter": "All domains",
            "topic_filter": "All topics",
            "status_filter": "All questions",
        }
        ids = ordered_question_ids(historical)
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=app.bank_path.name,
            mode=MODE_EXAM,
            builder_context=builder,
            source_label="All",
            question_numbers=[question["question_number"] for question in historical],
            restore_question_numbers=[question["question_number"] for question in historical],
            session_base_question_count=len(historical),
            session_question_limit=len(historical),
            current_index=1,
            elapsed_seconds=12,
            exam_reveal=False,
            checkpoints_saved=[],
            session_rewards=[],
            unlocked_rewards=[],
            session_answer_history=[],
            current_quests=[],
            quest_completion_keys=[],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=0,
            answers=[_blank_answer() for _ in historical],
            bank_fingerprint=bank_content_fingerprint(app.master_questions),
            question_ids=ids,
            restore_question_ids=ids,
        )
        path = app.session_file_for_bank(
            app.bank_path,
            mode=MODE_EXAM,
            questions=historical,
            builder_context=builder,
        )
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False)
        self.assertEqual([STRETCH_ID, CORE_ID, INELIGIBLE_ID], self.session_ids(app))
        self.assertEqual(1, app.index)

    def test_new_exam_ordered_and_randomized_exclude_stretch(self):
        app = self.make_app()
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False)
        ordered_ids = self.session_ids(app)
        self.assertEqual([CORE_ID, APPLIED_ID, LEGACY_ID], ordered_ids)
        random.seed(7)
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=True)
        randomized_ids = self.session_ids(app)
        self.assertEqual(set(ordered_ids), set(randomized_ids))
        self.assertNotIn(STRETCH_ID, randomized_ids)
        self.assertNotIn(INELIGIBLE_ID, randomized_ids)

    def test_exam_domain_and_topic_filters_compose_without_stretch_backfill(self):
        app = self.make_app()
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False, domain="Identity")
        self.assertEqual([CORE_ID], self.session_ids(app))
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False, topic="Entra")
        self.assertEqual([CORE_ID], self.session_ids(app))

    def test_exam_history_source_filter_and_count_clamp(self):
        app = self.make_app()
        core = self.by_id(app, CORE_ID)
        app._progress_questions()[app._question_key(core)] = normalize_progress_record({"attempts": 1})
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False, source="Unseen")
        unseen_ids = self.session_ids(app)
        self.assertEqual([APPLIED_ID, LEGACY_ID], unseen_ids)
        self.start_mode(app, MODE_EXAM, count="10", randomize=False)
        self.assertEqual([CORE_ID, APPLIED_ID, LEGACY_ID], self.session_ids(app))
        self.start_mode(app, MODE_EXAM, count="2", randomize=False)
        self.assertEqual([CORE_ID, APPLIED_ID], self.session_ids(app))

    def test_default_bank_missing_eligibility_field_loads_for_exam(self):
        questions = load_bank(DEFAULT_BANK)["questions"]
        self.assertEqual(8, len(questions))
        self.assertTrue(all("exam_simulation_eligible" not in question for question in questions))
        app = self.make_app(questions=questions)
        self.start_mode(app, MODE_EXAM, count="All visible", randomize=False)
        self.assertEqual(8, len(app.questions))
        self.assertEqual(
            [canonical_question_id(question) for question in app.master_questions],
            self.session_ids(app),
        )


class ExamTierCalibratedBankContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = load_bank(COMPILED_BANK_PATH)["questions"]

    def test_calibrated_and_default_bank_hashes_are_frozen(self):
        self.assertEqual(sha256_file(COMPILED_BANK_PATH), CALIBRATED_BANK_SHA256)
        self.assertEqual(sha256_file(DEFAULT_BANK), EXPECTED_DEFAULT_BANK_SHA256)

    def test_calibrated_bank_tier_and_exam_eligibility_counts(self):
        self.assertEqual(454, len(self.questions))
        tiers = Counter(row["exam_calibration_tier"] for row in self.questions)
        self.assertEqual(301, tiers[CORE])
        self.assertEqual(130, tiers[APPLIED])
        self.assertEqual(23, tiers[STRETCH])
        eligible = [row for row in self.questions if row.get("exam_simulation_eligible") is True]
        ineligible = [row for row in self.questions if row.get("exam_simulation_eligible") is False]
        self.assertEqual(431, len(eligible))
        self.assertEqual(23, len(ineligible))
        missing = [
            row["id"]
            for row in self.questions
            if row.get("exam_calibration_tier") not in VALID_TIERS
            or "reasoning_steps" not in row
            or "exam_simulation_eligible" not in row
            or row.get("calibration_version") != CALIBRATION_VERSION
        ]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
