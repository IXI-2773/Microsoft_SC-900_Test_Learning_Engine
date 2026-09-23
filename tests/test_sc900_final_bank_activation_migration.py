from __future__ import annotations

import json
import logging
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

import app as app_module
import cert_config
from app_constants import MODE_EXAM, MODE_PRACTICE
from exam_runtime_eligibility import exam_runtime_eligible, filter_new_exam_pool
from question_bank import load_bank
from question_identity import (
    PROGRESS_CONTENT_EPOCH_VERSION,
    PROGRESS_IDENTITY_KIND,
    PROGRESS_IDENTITY_VERSION,
    REMOVED_QUESTION,
    bank_content_fingerprint,
    canonical_question_id,
    migrate_progress_content_epoch,
    question_content_fingerprint,
)
from session_identity import ordered_question_ids
from session_store import (
    build_session_snapshot,
    migrate_session_snapshot,
    progress_file_path,
    runtime_bank_stem,
    saved_session_matches_current,
    session_file_path,
)

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_BASELINE_BANK = ROOT / "sc900_bank_v8_baseline.json"
ACTIVE_RUNTIME_BANK_FILENAME = "sc900_bank_v8_final.json"
EXPECTED_ACTIVE_COUNT = 454
EXPECTED_EXAM_ELIGIBLE_COUNT = 431
STRETCH = "STRETCH"


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


def _canonical_progress(records: dict, questions: list[dict], history: list | None = None) -> dict:
    fingerprints = {
        canonical_question_id(question): question_content_fingerprint(question) for question in questions
    }
    return {
        "version": 3,
        "progress_identity_version": PROGRESS_IDENTITY_VERSION,
        "question_identity": PROGRESS_IDENTITY_KIND,
        "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
        "bank_fingerprint": bank_content_fingerprint(questions),
        "question_content_fingerprints": fingerprints,
        "questions": deepcopy(records),
        "history": deepcopy(history or []),
        "created_at": "2026-09-12T00:00:00",
        "updated_at": "2026-09-12T00:00:00",
    }


class FinalBankActivationMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.active_path = ROOT / cert_config.QUESTION_BANK_FILENAME
        cls.baseline_questions = load_bank(HISTORICAL_BASELINE_BANK)["questions"]
        cls.active_questions = load_bank(cls.active_path)["questions"]
        cls.baseline_fingerprint = bank_content_fingerprint(cls.baseline_questions)
        cls.active_fingerprint = bank_content_fingerprint(cls.active_questions)
        cls.baseline_ids = [canonical_question_id(row) for row in cls.baseline_questions]
        cls.active_ids = [canonical_question_id(row) for row in cls.active_questions]

    def test_runtime_stems_isolate_baseline_progress_and_sessions(self):
        self.assertEqual(cert_config.QUESTION_BANK_FILENAME, self.active_path.name)
        self.assertNotEqual(runtime_bank_stem(HISTORICAL_BASELINE_BANK), runtime_bank_stem(self.active_path))
        user_data = Path("C:/tmp-activation-isolation")
        self.assertNotEqual(
            progress_file_path(user_data, HISTORICAL_BASELINE_BANK),
            progress_file_path(user_data, self.active_path),
        )
        baseline_session = session_file_path(
            user_data,
            HISTORICAL_BASELINE_BANK,
            MODE_PRACTICE,
            [row["question_number"] for row in self.baseline_questions],
            bank_fingerprint=self.baseline_fingerprint,
            question_ids=self.baseline_ids,
        )
        active_session = session_file_path(
            user_data,
            self.active_path,
            MODE_PRACTICE,
            [row["question_number"] for row in self.active_questions[:8]],
            bank_fingerprint=self.active_fingerprint,
            question_ids=self.active_ids[:8],
        )
        self.assertNotEqual(baseline_session.name, active_session.name)
        self.assertIn("sc900_bank_v8_baseline", baseline_session.name)
        self.assertIn("sc900_bank_v8_final_content_correction_002", active_session.name)

    def test_bank_fingerprint_mismatch_fails_closed(self):
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=HISTORICAL_BASELINE_BANK.name,
            mode=MODE_PRACTICE,
            builder_context={"mode": MODE_PRACTICE, "count": "8"},
            source_label="All",
            question_numbers=[row["question_number"] for row in self.baseline_questions],
            restore_question_numbers=[row["question_number"] for row in self.baseline_questions],
            session_base_question_count=8,
            session_question_limit=8,
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
            answers=[_blank_answer() for _ in self.baseline_questions],
            bank_fingerprint=self.baseline_fingerprint,
            question_ids=self.baseline_ids,
            restore_question_ids=self.baseline_ids,
        )
        self.assertFalse(
            saved_session_matches_current(
                snapshot,
                MODE_PRACTICE,
                [row["question_number"] for row in self.active_questions[:8]],
                [row["question_number"] for row in self.active_questions[:8]],
                bank_fingerprint=self.active_fingerprint,
                current_question_ids=self.active_ids[:8],
                restore_question_ids=self.active_ids[:8],
            )
        )
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                snapshot,
                MODE_PRACTICE,
                [row["question_number"] for row in self.baseline_questions],
                bank_fingerprint=self.active_fingerprint,
                question_ids=self.baseline_ids,
                restore_question_ids=self.baseline_ids,
                available_question_ids=self.active_ids,
            )

    def test_placeholder_progress_is_not_mapped_onto_final_bank_ids(self):
        self.assertTrue(set(self.baseline_ids).isdisjoint(self.active_ids))
        baseline_progress = _canonical_progress(
            {self.baseline_ids[0]: {"attempts": 9, "wrong_count": 2}},
            self.baseline_questions,
            history=[{"question_id": self.baseline_ids[0], "question_number": 1, "correct": False}],
        )
        original = json.dumps(baseline_progress, sort_keys=True)
        migrated, changed = migrate_progress_content_epoch(baseline_progress, self.active_questions)
        self.assertTrue(changed)
        self.assertEqual({}, migrated["questions"])
        quarantined = migrated["quarantined_questions"]
        self.assertIn(self.baseline_ids[0], quarantined)
        self.assertEqual(REMOVED_QUESTION, quarantined[self.baseline_ids[0]]["reason"])
        self.assertNotIn(self.active_ids[0], migrated["questions"])
        self.assertEqual(original, json.dumps(baseline_progress, sort_keys=True))

    def test_final_bank_session_round_trip_and_stretch_exam_resume(self):
        stretch = [row for row in self.active_questions if row.get("exam_calibration_tier") == STRETCH]
        core_like = [row for row in self.active_questions if exam_runtime_eligible(row)][:2]
        historical_exam = [stretch[0], core_like[0], stretch[1]]
        ids = ordered_question_ids(historical_exam)
        fingerprint = self.active_fingerprint
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=self.active_path.name,
            mode=MODE_EXAM,
            builder_context={"mode": MODE_EXAM, "count": "3", "source_label": "All"},
            source_label="All",
            question_numbers=[row["question_number"] for row in historical_exam],
            restore_question_numbers=[row["question_number"] for row in historical_exam],
            session_base_question_count=3,
            session_question_limit=3,
            current_index=1,
            elapsed_seconds=9,
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
            answers=[_blank_answer() for _ in historical_exam],
            bank_fingerprint=fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
        )
        migrated = migrate_session_snapshot(
            snapshot,
            MODE_EXAM,
            [row["question_number"] for row in historical_exam],
            bank_fingerprint=fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
            available_question_ids=self.active_ids,
        )
        self.assertEqual(ids, migrated["question_ids"])
        self.assertEqual(1, migrated["current_index"])
        self.assertEqual(fingerprint, migrated["bank_fingerprint"])
        self.assertEqual(EXPECTED_EXAM_ELIGIBLE_COUNT, len(filter_new_exam_pool(self.active_questions)))
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(self.active_questions))

    def test_application_starts_with_final_bank_and_leaves_baseline_progress_untouched(self):
        active_path = ROOT / cert_config.QUESTION_BANK_FILENAME
        self.assertEqual("sc900_bank_v8_final_content_correction_002.json", active_path.name)
        tmpdir_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir_ctx.cleanup)
        tmpdir = Path(tmpdir_ctx.name)
        user_data = tmpdir / "user_data"
        checkpoints = user_data / "checkpoints"
        backups = user_data / "backups"
        for folder in (user_data, checkpoints, backups, user_data / "logs"):
            folder.mkdir(parents=True, exist_ok=True)
        baseline_progress_path = progress_file_path(user_data, HISTORICAL_BASELINE_BANK)
        baseline_payload = _canonical_progress(
            {self.baseline_ids[0]: {"attempts": 4}},
            self.baseline_questions,
        )
        baseline_progress_path.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")
        original_bytes = baseline_progress_path.read_bytes()
        patches = [
            mock.patch.object(app_module, "APP_DIR", tmpdir),
            mock.patch.object(app_module, "USER_DATA_DIR", user_data),
            mock.patch.object(app_module, "CHECKPOINT_DIR", checkpoints),
            mock.patch.object(app_module, "BACKUP_DIR", backups),
            mock.patch.object(app_module, "CONFIG_PATH", user_data / "config.json"),
            mock.patch.object(app_module, "DEFAULT_BANK", active_path),
            mock.patch.object(app_module.TestingEngineApp, "_tick", lambda self: None),
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

        def restore_logging():
            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)
                handler.close()
            for handler in previous_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(previous_level)

        self.addCleanup(restore_logging)
        engine = app_module.TestingEngineApp(root)
        self.assertEqual(EXPECTED_ACTIVE_COUNT, len(engine.master_questions))
        self.assertEqual(active_path.resolve(), Path(engine.bank_path).resolve())
        self.assertEqual(original_bytes, baseline_progress_path.read_bytes())
        self.assertNotEqual(
            progress_file_path(user_data, HISTORICAL_BASELINE_BANK),
            progress_file_path(user_data, Path(engine.bank_path)),
        )
        loaded_ids = {canonical_question_id(row) for row in engine.master_questions}
        self.assertTrue(set(self.baseline_ids).isdisjoint(loaded_ids))
        engine.start_session_from_pool(
            engine.master_questions[:5],
            mode=MODE_PRACTICE,
            count="5",
            randomize=False,
            reset_clock=True,
            preserve_if_saved=False,
            source_label="All",
            builder_context={
                "mode": MODE_PRACTICE,
                "count": "5",
                "source_label": "All",
                "session_source": "All",
                "randomize": False,
                "domain_filter": "All domains",
                "topic_filter": "All topics",
                "status_filter": "All questions",
            },
        )
        self.assertEqual(5, len(engine.questions))
        engine.save_session()
        session_path = Path(engine.session_path)
        self.assertTrue(session_path.is_file())
        saved = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual(self.active_fingerprint, saved["bank_fingerprint"])
        restored = migrate_session_snapshot(
            saved,
            MODE_PRACTICE,
            [row["question_number"] for row in engine.questions],
            bank_fingerprint=engine.current_bank_fingerprint(),
            question_ids=ordered_question_ids(engine.questions),
            restore_question_ids=ordered_question_ids(engine.questions),
            available_question_ids=self.active_ids,
        )
        self.assertEqual(ordered_question_ids(engine.questions), restored["question_ids"])
        self.assertEqual(original_bytes, baseline_progress_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
