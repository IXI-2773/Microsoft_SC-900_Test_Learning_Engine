import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from app_constants import MODE_EXAM
from progress_store import (
    infer_review_grade,
    normalize_confidence,
    update_learner_memory,
    update_progress_record,
)
from session_models import apply_answer_state, clear_runtime_answer_state


def _question(qid="engine-q1", number=1, question_type="single", correct=None):
    correct = list(correct or ["A"])
    return {
        "id": qid,
        "question_id": qid,
        "question_number": number,
        "prompt": "Which control?",
        "choices": {"A": "Correct", "B": "Wrong", "C": "Also wrong"},
        "correct": correct,
        "question_type": question_type,
        "domain": "Identity",
        "topics": ["Entra"],
        "objective_code": "1.1",
        "general_explanation": "Because.",
        "choice_explanations": {"A": "Right", "B": "No", "C": "No"},
        "selected": [],
        "pending": [],
        "answered": False,
        "flagged": False,
        "suspended": False,
        "last_confidence": "",
        "last_miss_reason": "",
        "recall_ready": False,
        "session_tag": "",
    }


class Backlog2NormalizeAndDiagnosisTests(unittest.TestCase):
    def test_b2_003_observed_sure_remains_sure(self):
        self.assertEqual("Sure", normalize_confidence("Sure"))

    def test_b2_031_legacy_explicit_sure_remains_sure(self):
        rec = update_progress_record({}, ["A"], True, seen_on="2026-09-12", confidence="Sure")
        self.assertEqual("Sure", rec["last_confidence"])

    def test_b2_032_legacy_explicit_unsure_remains_unsure(self):
        rec = update_progress_record({}, ["A"], True, seen_on="2026-09-12", confidence="Unsure")
        self.assertEqual("Unsure", rec["last_confidence"])

    def test_b2_033_legacy_explicit_guessed_remains_guessed(self):
        rec = update_progress_record({}, ["A"], True, seen_on="2026-09-12", confidence="Guessed")
        self.assertEqual("Guessed", rec["last_confidence"])

    def test_b2_004_missing_confidence_never_silently_becomes_sure(self):
        self.assertEqual("Unknown", normalize_confidence(None))
        self.assertEqual("Unknown", normalize_confidence(""))
        rec = update_progress_record({}, ["A"], True, seen_on="2026-09-12")
        self.assertEqual("Unknown", rec["last_confidence"])
        self.assertNotEqual("Sure", rec["last_confidence"])

    def test_b2_005_invalid_confidence_never_silently_becomes_sure(self):
        self.assertEqual("Unknown", normalize_confidence("bogus"))
        self.assertEqual("Unknown", normalize_confidence("maybe"))
        rec = update_progress_record({}, ["B"], False, seen_on="2026-09-12", confidence="nope")
        self.assertEqual("Unknown", rec["last_confidence"])

    def test_b2_034_legacy_missing_confidence_becomes_unknown_not_sure(self):
        rec = update_progress_record({}, ["B"], False, seen_on="2026-09-12", confidence="")
        self.assertEqual("Unknown", rec["last_confidence"])
        self.assertEqual("", rec["last_miss_reason"])

    def test_b2_008_wrong_guessed_is_ignorance_blank_recall(self):
        from confidence_epistemics import classify_recall_failure, infer_miss_reason_from_confidence

        self.assertEqual("Did not know", infer_miss_reason_from_confidence("Guessed", False))
        self.assertEqual(
            "Blank recall",
            classify_recall_failure(False, "Guessed", "Did not know"),
        )
        self.assertEqual("lapse", infer_review_grade(False, confidence="Guessed", miss_reason="Did not know"))

    def test_b2_009_wrong_unsure_is_interference(self):
        from confidence_epistemics import classify_recall_failure, infer_miss_reason_from_confidence

        self.assertEqual("Narrowed to two", infer_miss_reason_from_confidence("Unsure", False))
        self.assertEqual(
            "Concept interference",
            classify_recall_failure(False, "Unsure", "Narrowed to two"),
        )

    def test_b2_010_wrong_sure_is_confident_miss(self):
        from confidence_epistemics import classify_recall_failure, infer_miss_reason_from_confidence

        self.assertEqual("Misread", infer_miss_reason_from_confidence("Sure", False))
        self.assertEqual("Cue / wording miss", classify_recall_failure(False, "Sure", "Misread"))
        self.assertEqual("lapse_strong", infer_review_grade(False, confidence="Sure", miss_reason="Misread"))

    def test_b2_011_wrong_unknown_does_not_masquerade_as_confident_miss(self):
        from confidence_epistemics import classify_recall_failure, infer_miss_reason_from_confidence

        self.assertEqual("", infer_miss_reason_from_confidence("Unknown", False))
        self.assertEqual("", infer_miss_reason_from_confidence(None, False))
        self.assertEqual("Unclassified miss", classify_recall_failure(False, "Unknown", ""))
        self.assertEqual("lapse", infer_review_grade(False, confidence="Unknown"))
        self.assertNotEqual("lapse_strong", infer_review_grade(False, confidence="Unknown"))

    def test_b2_012_correct_guessed_is_recognition(self):
        from confidence_epistemics import classify_recall_failure

        self.assertEqual("Recognition without recall", classify_recall_failure(True, "Guessed", ""))
        self.assertEqual("recognition", infer_review_grade(True, confidence="Guessed"))

    def test_b2_013_correct_unsure_is_partial_fragile(self):
        from confidence_epistemics import classify_recall_failure

        self.assertEqual("Fragile retrieval", classify_recall_failure(True, "Unsure", ""))
        self.assertEqual("partial", infer_review_grade(True, confidence="Unsure"))

    def test_b2_014_correct_sure_is_confident(self):
        from confidence_epistemics import classify_recall_failure

        self.assertEqual("", classify_recall_failure(True, "Sure", ""))
        self.assertEqual("confident", infer_review_grade(True, confidence="Sure"))
        self.assertNotEqual("confident", infer_review_grade(True, confidence="Unknown"))

    def test_b2_015_new_answer_event_id_is_stable_and_unique(self):
        from confidence_epistemics import new_answer_event_id

        first = new_answer_event_id()
        second = new_answer_event_id()
        self.assertTrue(str(first).startswith("ae:"))
        self.assertNotEqual(first, second)

    def test_b2_035_legacy_event_id_migration_is_deterministic(self):
        from confidence_epistemics import deterministic_legacy_answer_event_id

        first = deterministic_legacy_answer_event_id(
            question_id="Q-A",
            at="2026-09-12T10:00:00",
            selected=["A"],
            correct=True,
            ordinal=0,
        )
        second = deterministic_legacy_answer_event_id(
            question_id="Q-A",
            at="2026-09-12T10:00:00",
            selected=["A"],
            correct=True,
            ordinal=0,
        )
        other = deterministic_legacy_answer_event_id(
            question_id="Q-A",
            at="2026-09-12T10:00:00",
            selected=["B"],
            correct=False,
            ordinal=0,
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("ae:"))

    def test_b2_036_ambiguous_legacy_answer_event_pairing_does_not_silently_bind(self):
        from confidence_epistemics import bind_legacy_answer_event_ids

        runtime = [
            {
                "id": "Q-A",
                "answered": True,
                "selected": ["A"],
                "last_confidence": "Guessed",
            }
        ]
        session_history = [
            {"question_id": "Q-A", "confidence": "Guessed", "correct": True, "selected": ["A"]},
            {"question_id": "Q-A", "confidence": "Sure", "correct": False, "selected": ["B"]},
        ]
        progress_history = [
            {"question_id": "Q-A", "confidence": "Guessed", "correct": True, "at": "2026-09-12T10:00:00"},
            {"question_id": "Q-A", "confidence": "Sure", "correct": False, "at": "2026-09-12T11:00:00"},
        ]
        result = bind_legacy_answer_event_ids(
            runtime_questions=runtime,
            session_history=session_history,
            progress_history=progress_history,
        )
        self.assertIsNone(runtime[0].get("answer_event_id") or None)
        self.assertFalse(session_history[0].get("answer_event_id"))
        self.assertFalse(progress_history[0].get("answer_event_id"))
        self.assertTrue(result["ambiguous"])

    def test_b2_025_learner_memory_rebuild_is_deterministic(self):
        from confidence_epistemics import rebuild_learner_memory_from_history

        events = [
            {
                "at": "2026-09-12T10:00:00",
                "day": "2026-09-12",
                "correct": False,
                "confidence": "Guessed",
                "miss_reason": "Did not know",
                "recall_failure": "Blank recall",
                "effective_response_seconds": 8.0,
                "session_tag": "",
            },
            {
                "at": "2026-09-12T11:00:00",
                "day": "2026-09-12",
                "correct": True,
                "confidence": "Sure",
                "miss_reason": "",
                "recall_failure": "",
                "effective_response_seconds": 6.0,
                "session_tag": "",
            },
        ]
        first = rebuild_learner_memory_from_history(events)
        second = rebuild_learner_memory_from_history(events)
        self.assertEqual(first, second)
        guessed_only = rebuild_learner_memory_from_history(events[:1])
        unknown_wrong = rebuild_learner_memory_from_history(
            [{**events[0], "confidence": "Unknown", "miss_reason": "", "recall_failure": "Unclassified miss"}]
        )
        sure_wrong = update_learner_memory(None, False, confidence="Sure", miss_reason="Misread", seen_on="2026-09-12")
        self.assertNotEqual(guessed_only, unknown_wrong)
        self.assertNotEqual(unknown_wrong.get("last_grade"), sure_wrong.get("last_grade"))


class Backlog2AppLifecycleTests(unittest.TestCase):
    def make_app(self, start_session=True):
        tmpdir = Path(tempfile.mkdtemp())
        user_data = tmpdir / "user_data"
        checkpoints = tmpdir / "checkpoints"
        backups = tmpdir / "backups"
        bank_path = tmpdir / "bank.json"
        source_bank = Path(app_module.DEFAULT_BANK)
        if source_bank.exists():
            bank_path.write_bytes(source_bank.read_bytes())
        else:
            bank_path.write_text("{}", encoding="utf-8")
        user_data.mkdir()
        checkpoints.mkdir()
        backups.mkdir()
        patches = [
            mock.patch.object(app_module, "APP_DIR", tmpdir),
            mock.patch.object(app_module, "USER_DATA_DIR", user_data),
            mock.patch.object(app_module, "CHECKPOINT_DIR", checkpoints),
            mock.patch.object(app_module, "BACKUP_DIR", backups),
            mock.patch.object(app_module, "CONFIG_PATH", user_data / "config.json"),
            mock.patch.object(app_module, "DEFAULT_BANK", bank_path),
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
        app = app_module.TestingEngineApp(root)
        if start_session:
            app.restore_full_bank()
        return app

    def _stage_and_commit(self, app, letter, confidence, *, wrong=False):
        q = app.current_question()
        if wrong:
            letter = next(choice for choice in q["choices"] if choice not in q["correct"])
        if q.get("question_type") == "multi":
            app.toggle_choice(letter)
            app.submit_answer()
        else:
            app.toggle_choice(letter)
        self.assertIsNotNone(getattr(app, "pending_feedback_request", None))
        self.assertFalse(q.get("answered"))
        app._complete_feedback_choice(confidence)
        return app.current_question()

    def test_b2_001_ordinary_single_choice_guessed_persists_guessed(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Guessed")
        self.assertTrue(q["answered"])
        self.assertEqual("Guessed", q["last_confidence"])
        self.assertEqual("Guessed", app.session_answer_history[-1]["confidence"])
        rec = app._progress_record(q)
        self.assertEqual("Guessed", rec["last_confidence"])
        history = [event for event in app._progress_history() if event.get("question_id") == app._question_key(q)]
        self.assertEqual("Guessed", history[-1]["confidence"])

    def test_b2_002_ordinary_single_choice_unsure_persists_unsure(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Unsure")
        self.assertEqual("Unsure", q["last_confidence"])
        self.assertEqual("Unsure", app.session_answer_history[-1]["confidence"])

    def test_b2_003_ordinary_single_choice_sure_persists_sure(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Sure")
        self.assertEqual("Sure", q["last_confidence"])
        self.assertEqual("Sure", app.session_answer_history[-1]["confidence"])

    def test_b2_006_ordinary_multi_choice_uses_same_confidence_capture_lifecycle(self):
        app = self.make_app()
        q = app.current_question()
        q["question_type"] = "multi"
        app.toggle_choice("A")
        self.assertFalse(q.get("answered"))
        self.assertIsNone(getattr(app, "pending_feedback_request", None))
        app.submit_answer()
        self.assertFalse(q.get("answered"))
        self.assertIsNotNone(app.pending_feedback_request)
        app._complete_feedback_choice("Unsure")
        self.assertTrue(q["answered"])
        self.assertEqual("Unsure", q["last_confidence"])
        self.assertEqual("Unsure", app.session_answer_history[-1]["confidence"])

    def test_b2_007_keyboard_submission_cannot_bypass_confidence_capture(self):
        app = self.make_app()
        q = app.current_question()
        q["pending"] = [q["correct"][0]]
        app.handle_return_key()
        self.assertFalse(q.get("answered"))
        self.assertIsNotNone(app.pending_feedback_request)
        self.assertNotEqual("Sure", q.get("last_confidence"))
        app.handle_return_key()
        self.assertFalse(q.get("answered"))
        self.assertEqual("Unknown", normalize_confidence(q.get("last_confidence")))
        self.assertNotEqual("Sure", q.get("last_confidence") or "Unknown")

    def test_b2_016_persistent_and_session_history_share_answer_event_id(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Guessed")
        event_id = q.get("answer_event_id")
        self.assertTrue(event_id)
        self.assertEqual(event_id, app.session_answer_history[-1]["answer_event_id"])
        history = [event for event in app._progress_history() if event.get("question_id") == app._question_key(q)]
        self.assertEqual(event_id, history[-1]["answer_event_id"])

    def test_b2_039_single_and_multi_choice_events_are_structurally_equivalent(self):
        app = self.make_app()
        single = self._stage_and_commit(app, "A", "Sure")
        single_event = dict(app.session_answer_history[-1])
        app._set_current_index(1)
        q = app.current_question()
        q["question_type"] = "multi"
        app.toggle_choice(q["correct"][0])
        app.submit_answer()
        app._complete_feedback_choice("Sure")
        multi_event = dict(app.session_answer_history[-1])
        required = {
            "answer_event_id",
            "question_id",
            "confidence",
            "miss_reason",
            "recall_failure",
            "correct",
        }
        self.assertTrue(required.issubset(single_event))
        self.assertTrue(required.issubset(multi_event))
        self.assertNotEqual(single_event["answer_event_id"], multi_event["answer_event_id"])
        self.assertEqual(single.get("answer_event_id"), single_event["answer_event_id"])

    def _retag_app(self, from_conf="Guessed", to_conf="Sure", *, wrong=False):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", from_conf, wrong=wrong)
        event_id = q["answer_event_id"]
        original_signal = app._smart_practice_signal_key()
        app._set_current_index(0)
        app.retag_current_answer_confidence(to_conf)
        app._set_current_index(0)
        return app, app.current_question(), event_id, original_signal

    def test_b2_017_retag_by_event_id_updates_runtime_state(self):
        app, q, event_id, _signal = self._retag_app()
        self.assertEqual(event_id, q["answer_event_id"])
        self.assertEqual("Sure", q["last_confidence"])

    def test_b2_018_retag_by_event_id_updates_progress_record(self):
        app, q, _event_id, _signal = self._retag_app()
        rec = app._progress_record(q)
        self.assertEqual("Sure", rec["last_confidence"])

    def test_b2_019_retag_by_event_id_updates_persistent_progress_history(self):
        app, q, event_id, _signal = self._retag_app()
        history = [event for event in app._progress_history() if event.get("answer_event_id") == event_id]
        self.assertEqual(1, len(history))
        self.assertEqual("Sure", history[0]["confidence"])

    def test_b2_020_retag_by_event_id_updates_session_answer_history(self):
        app, _q, event_id, _signal = self._retag_app()
        matching = [event for event in app.session_answer_history if event.get("answer_event_id") == event_id]
        self.assertEqual(1, len(matching))
        self.assertEqual("Sure", matching[0]["confidence"])

    def test_b2_021_retag_recomputes_miss_reason(self):
        app, q, event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Sure", wrong=True)
        self.assertEqual("Misread", q["last_miss_reason"])
        event = next(item for item in app.session_answer_history if item.get("answer_event_id") == event_id)
        self.assertEqual("Misread", event["miss_reason"])

    def test_b2_022_retag_recomputes_recall_failure(self):
        app, _q, event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Sure", wrong=True)
        event = next(item for item in app.session_answer_history if item.get("answer_event_id") == event_id)
        self.assertEqual("Cue / wording miss", event["recall_failure"])

    def test_b2_023_retag_reconciles_confidence_counters(self):
        app, q, _event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Unsure")
        rec = app._progress_record(q)
        self.assertEqual(0, int(rec["confidence_counts"].get("Guessed", 0)))
        self.assertEqual(1, int(rec["confidence_counts"].get("Unsure", 0)))

    def test_b2_024_retag_reconciles_miss_reason_counters(self):
        app, q, _event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Unsure", wrong=True)
        rec = app._progress_record(q)
        self.assertEqual(0, int(rec["miss_reason_counts"].get("Did not know", 0)))
        self.assertEqual(1, int(rec["miss_reason_counts"].get("Narrowed to two", 0)))

    def test_b2_025_retag_reconciles_learner_memory(self):
        app, q, _event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Sure", wrong=True)
        rec = app._progress_record(q)
        self.assertEqual("lapse_strong", rec["learner_memory"]["last_grade"])

    def test_b2_026_retag_invalidates_smart_practice_signal_identity(self):
        app, _q, _event_id, original_signal = self._retag_app(from_conf="Guessed", to_conf="Sure")
        self.assertNotEqual(original_signal, app._smart_practice_signal_key())

    def test_b2_027_rewards_consume_corrected_session_confidence(self):
        app, _q, event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Sure")
        sure_correct = sum(
            1
            for entry in app.session_answer_history
            if entry.get("correct") and entry.get("confidence") == "Sure" and entry.get("answer_event_id") == event_id
        )
        self.assertEqual(1, sure_correct)
        app.current_quests = [
            {
                "key": "sure_3",
                "title": "Sure Start",
                "kind": "sure_correct",
                "target": 3,
                "progress": 0,
                "completed": False,
            }
        ]
        app.refresh_session_quests()
        self.assertEqual(1, app.current_quests[0]["progress"])

    def test_b2_028_analytics_consume_corrected_confidence(self):
        app, q, event_id, _signal = self._retag_app(from_conf="Guessed", to_conf="Unsure")
        self.assertIsNone(app.analytics_cache_payload)
        weight = app._confidence_weight("Unknown")
        self.assertNotEqual(app._confidence_weight("Sure"), weight)
        event = next(item for item in app._progress_history() if item.get("answer_event_id") == event_id)
        self.assertEqual("Unsure", event["confidence"])
        self.assertEqual("Unsure", app._progress_record(q)["last_confidence"])

    def test_b2_029_super_confident_uses_canonical_event_synchronization(self):
        app = self.make_app()
        q = self._stage_and_commit(app, app.current_question()["correct"][0], "Guessed")
        event_id = q["answer_event_id"]
        app._set_current_index(0)
        app.mark_current_question_super_confident()
        app._set_current_index(0)
        q = app.current_question()
        rec = app._progress_record(q)
        event = next(item for item in app.session_answer_history if item.get("answer_event_id") == event_id)
        history = next(item for item in app._progress_history() if item.get("answer_event_id") == event_id)
        self.assertEqual("Sure", q["last_confidence"])
        self.assertEqual("Sure", rec["last_confidence"])
        self.assertEqual("Sure", event["confidence"])
        self.assertEqual("Sure", history["confidence"])
        self.assertTrue(str(rec.get("super_confident_until") or ""))

    def test_b2_030_restart_resume_preserves_answer_event_id_and_corrected_confidence(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Guessed")
        event_id = q["answer_event_id"]
        app._set_current_index(0)
        app.retag_current_answer_confidence("Unsure")
        app.save_session()
        snapshot = json.loads(Path(app.session_path).read_text(encoding="utf-8"))
        restored = next(item for item in snapshot["session_answer_history"] if item.get("answer_event_id") == event_id)
        self.assertEqual("Unsure", restored["confidence"])
        runtime_conf = snapshot["answers"][0].get("last_confidence")
        runtime_event = snapshot["answers"][0].get("answer_event_id")
        self.assertEqual(event_id, runtime_event)
        self.assertEqual("Unsure", runtime_conf)

    def test_b2_037_redo_creates_a_new_answer_event_id(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Guessed")
        first_id = q["answer_event_id"]
        app._set_current_index(0)
        app.redo_question()
        q = app.current_question()
        self.assertFalse(q.get("answered"))
        self.assertFalse(q.get("answer_event_id"))
        q = self._stage_and_commit(app, "A", "Sure")
        self.assertNotEqual(first_id, q["answer_event_id"])
        ids = [event["answer_event_id"] for event in app.session_answer_history]
        self.assertEqual(2, len(ids))
        self.assertEqual({first_id, q["answer_event_id"]}, set(ids))

    def test_b2_038_retagging_latest_attempt_does_not_mutate_previous_attempt(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Guessed")
        first_id = q["answer_event_id"]
        app._set_current_index(0)
        app.redo_question()
        q = self._stage_and_commit(app, "A", "Unsure")
        second_id = q["answer_event_id"]
        app._set_current_index(0)
        app.retag_current_answer_confidence("Sure")
        first = next(item for item in app.session_answer_history if item["answer_event_id"] == first_id)
        second = next(item for item in app.session_answer_history if item["answer_event_id"] == second_id)
        self.assertEqual("Guessed", first["confidence"])
        self.assertEqual("Sure", second["confidence"])

    def test_b2_040_restored_session_correction_targets_correct_event(self):
        app = self.make_app()
        q = self._stage_and_commit(app, "A", "Guessed")
        event_id = q["answer_event_id"]
        apply_answer_state(
            q,
            {
                **{key: q.get(key) for key in ("selected", "pending", "answered", "flagged", "suspended")},
                "last_confidence": "Guessed",
                "last_miss_reason": q.get("last_miss_reason") or "",
                "recall_ready": False,
                "session_tag": "",
                "answer_event_id": event_id,
            },
        )
        app.correct_answer_event_confidence(event_id, "Unsure")
        self.assertEqual("Unsure", app.current_question()["last_confidence"])
        matching = [event for event in app.session_answer_history if event["answer_event_id"] == event_id]
        self.assertEqual(["Unsure"], [event["confidence"] for event in matching])

    def test_b2_041_exam_mode_does_not_reveal_correctness_through_confidence_capture(self):
        app = self.make_app()
        app.active_session_mode = MODE_EXAM
        app.exam_reveal = False
        q = app.current_question()
        letter = q["correct"][0]
        app.toggle_choice(letter)
        self.assertTrue(q["answered"])
        self.assertEqual("Unknown", q["last_confidence"])
        self.assertIsNone(getattr(app, "pending_feedback_request", None) or None)
        self.assertFalse(app._feedback_popover_active())
        app.render_question()
        self.assertNotIn("Correct", str(app.status_label.cget("text")))

    def test_b2_042_gate3_train_probe_isolation_helper_unchanged(self):
        from cand01r3_runtime import ROLE_PROBE, sanitize_history_event

        event = {"question_id": "probe-x", "confidence": "Unknown", "prompt": "secret", "selected_texts": ["x"]}
        with (
            mock.patch("cand01r3_runtime.is_cand01r3_active", return_value=True),
            mock.patch("cand01r3_runtime._is_probe_question", return_value=True),
        ):
            sanitized = sanitize_history_event(event)
        self.assertTrue(sanitized.get("redacted"))
        self.assertNotIn("prompt", sanitized)
        self.assertEqual(ROLE_PROBE, "PROBE")

    def test_b2_043_experimental_suppressed_confidence_records_unknown(self):
        app = self.make_app()
        q = app.current_question()
        with mock.patch.object(app, "_should_suppress_confidence_capture", return_value=True):
            app.toggle_choice(q["correct"][0])
        self.assertTrue(q["answered"])
        self.assertEqual("Unknown", q["last_confidence"])
        self.assertEqual("Unknown", app.session_answer_history[-1]["confidence"])
        self.assertNotEqual("Sure", q["last_confidence"])

    def test_b2_047_collect_answer_feedback_does_not_manufacture_sure(self):
        app = self.make_app()
        q = app.current_question()
        feedback = app._collect_answer_feedback(q, True)
        self.assertEqual("Unknown", feedback["confidence"])
        self.assertNotEqual("Sure", feedback["confidence"])


class Backlog2ClearRedoStateTests(unittest.TestCase):
    def test_redo_clears_runtime_answer_event_id(self):
        q = _question()
        q["answered"] = True
        q["answer_event_id"] = "ae:test"
        q["last_confidence"] = "Sure"
        clear_runtime_answer_state(q)
        self.assertFalse(q.get("answered"))
        self.assertEqual("", q.get("answer_event_id") or "")
        self.assertEqual("", q.get("last_confidence") or "")
