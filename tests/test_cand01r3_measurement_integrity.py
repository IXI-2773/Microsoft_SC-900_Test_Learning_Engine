from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from cand01r3_fixtures import (
    DEFAULT_BANK,
    EXPECTED_AUDIT_SHA256,
    EXPECTED_COMPILED_SHA256,
    EXPECTED_DEFAULT_BANK_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_STORE_SHA256,
    LEARNER_ID,
    progress_record,
    question,
    sha256_file,
)

EXPECTED_PROTOCOL_SHA256 = "51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72"


class _Var:
    def __init__(self, value=False):
        self.value = value

    def get(self):
        return self.value


class _Root:
    def __init__(self):
        self.after_calls = []

    def after(self, delay, callback):
        token = f"after-{len(self.after_calls) + 1}"
        self.after_calls.append((delay, callback, token))
        return token

    def after_cancel(self, token):
        self.after_calls = [row for row in self.after_calls if row[2] != token]


class MeasurementFlowHarness:
    def __init__(self, q):
        from app_question_flow_mixin import QuestionFlowMixin

        self._flow = QuestionFlowMixin
        self.questions = [copy.deepcopy(q)]
        self.master_questions = copy.deepcopy(self.questions)
        self.index = 0
        self.record = progress_record()
        self.progress_data = {"questions": {}, "meta": {}, "history": []}
        self.session_answer_history = []
        self.active_session_mode = "Practice"
        self.active_question_started_qnum = self.questions[0].get("question_number")
        self.active_question_started_at = time.time() - 1.0
        self.auto_next_correct_var = _Var(True)
        self.auto_next_after_id = None
        self.root = _Root()
        self.update_progress_calls = 0
        self.xp_calls = 0
        self.misconception_calls = 0
        self.memory_ramp_calls = 0
        self.delayed_recall_calls = 0
        self.reward_calls = 0
        self.quest_calls = 0
        self.feedback_chip_calls = 0
        self.prewarm_calls = 0
        self.progress_save_calls = 0
        self.session_save_calls = 0
        self.checkpoint_calls = 0
        self.boss_calls = 0
        self.stealth_calls = 0
        self.render_calls = 0
        self.auto_next_calls = 0

    def current_question(self):
        return self.questions[self.index]

    def _progress_record(self, q, create=False):
        return self.record

    def _progress_history(self):
        return self.progress_data.setdefault("history", [])

    def _progress_questions(self):
        return self.progress_data.setdefault("questions", {})

    def _question_key(self, q):
        return str(q.get("id") or q.get("question_id") or q.get("question_number"))

    def mark_question_list_dirty(self):
        return None

    def _collect_answer_feedback(self, q, correct):
        return {"confidence": "Sure", "miss_reason": "", "correct": bool(correct)}

    def _question_correct(self, q):
        return sorted(q.get("selected", [])) == sorted(q.get("correct", []))

    def classify_recall_failure(self, q, is_correct, feedback):
        return "" if is_correct else "retrieval"

    def deciding_clue_for_question(self, q):
        return ""

    def update_progress_for_answer(self, q, feedback=None):
        self.update_progress_calls += 1
        self.record["attempts"] = int(self.record.get("attempts") or 0) + 1
        self.record["next_review"] = "2099-01-01"
        self.record["smart_utility"] = 0.0

    def _apply_xp_for_answer(self, q, is_correct, feedback, was_active_weak=False, was_due=False):
        self.xp_calls += 1
        return 10

    def plan_misconception_repair(self, q, is_correct):
        self.misconception_calls += 1
        return []

    def maybe_trigger_stealth_checkpoint(self, q):
        self.stealth_calls += 1

    def maybe_queue_memory_ramp(self, q):
        self.memory_ramp_calls += 1
        return []

    def maybe_queue_delayed_recall_probe(self, q):
        self.delayed_recall_calls += 1
        return []

    def schedule_progress_save(self):
        self.progress_save_calls += 1

    def maybe_trigger_boss_round(self, q):
        self.boss_calls += 1

    def refresh_session_quests(self):
        self.quest_calls += 1

    def _unlock_quest_rewards(self):
        self.reward_calls += 1

    def schedule_session_save(self, delay_ms=250):
        self.session_save_calls += 1

    def maybe_save_checkpoint(self):
        self.checkpoint_calls += 1

    def unlock_session_rewards(self):
        self.reward_calls += 1

    def render_question(self):
        self.render_calls += 1

    def _render_current_view(self, save_session=True):
        self.render_calls += 1

    def show_answer_feedback_chip(self, q, is_correct, xp_gained, was_active_weak=False, was_due=False):
        self.feedback_chip_calls += 1

    def maybe_finish_session(self, force=False):
        return None

    def maybe_auto_next_after_answer(self, q):
        self.auto_next_calls += 1

    def schedule_smart_practice_prewarm(self, delay_ms=0):
        self.prewarm_calls += 1

    def cancel_auto_next_after_answer(self):
        self.auto_next_after_id = None

    def _auto_next_after_answer(self):
        self.auto_next_calls += 1


class Cand01R3MeasurementIntegrityTests(unittest.TestCase):
    def setUp(self):
        from cand01r3_protocol import reset_measurement_session
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()
        reset_measurement_session()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.tmpdir.name) / "epoch.jsonl"

    def tearDown(self):
        from cand01r3_protocol import reset_measurement_session
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_measurement_session()
        reset_cand01r3_runtime()
        self.tmpdir.cleanup()

    def _begin(self):
        from cand01r3_protocol import begin_cand01r3_measurement

        return begin_cand01r3_measurement(
            learner_id=LEARNER_ID,
            measurement_epoch="cand01r3-measurement-001",
            schedule_version="cand01r3-probe-schedule-v1",
            policy_sequence_version="cand01r3-alt-crossover-v1",
            manifest_sha256=EXPECTED_MANIFEST_SHA256,
            store_sha256=EXPECTED_STORE_SHA256,
            semantic_audit_sha256=EXPECTED_AUDIT_SHA256,
            compiled_sha256=EXPECTED_COMPILED_SHA256,
            candidate_bank_identity=EXPECTED_COMPILED_SHA256,
            ledger_path=self.ledger_path,
        )

    def _restart(self):
        from cand01r3_protocol import reset_measurement_session
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_measurement_session()
        reset_cand01r3_runtime()
        return self._begin()

    def _train_ids(self, count=20):
        from cand01r3_partition import ROLE_TRAIN, load_runtime_authority

        ids = sorted(qid for qid, item in load_runtime_authority().items.items() if item.get("role") == ROLE_TRAIN)
        return ids[:count]

    def _probe_ids(self, day):
        from cand01r3_protocol import build_protocol

        return [
            str(row["question_id"])
            for row in build_protocol()["schedule"]
            if int(row.get("scheduled_day") or 0) == int(day)
        ]

    def _complete_train(self, day):
        from cand01r3_protocol import allocated_policy_for_day, record_train_exposure, train_budget_for_day

        policy = allocated_policy_for_day(day)
        budget = train_budget_for_day(day, policy)
        for qid in self._train_ids(budget):
            result = record_train_exposure(
                policy_id=policy,
                question_id=qid,
                semantic_family_id="family_train",
                domain="microsoft_entra",
                objective="entra_authentication",
                service_class="COVERAGE",
                scheduled_day=day,
            )
            self.assertTrue(result["counted"], result)

    def _enter_measurement(self, day=1):
        from cand01r3_protocol import begin_todays_probe_measurement, set_measurement_day

        set_measurement_day(day)
        self._complete_train(day)
        begin_todays_probe_measurement()

    def _finish_day(self, day):
        from cand01r3_protocol import begin_todays_probe_measurement, record_measurement_event, set_measurement_day

        set_measurement_day(day)
        self._complete_train(day)
        begin_todays_probe_measurement()
        for qid in self._probe_ids(day):
            result = record_measurement_event(question(qid, role_hint="PROBE"), selected=["A"], correct=True)
            self.assertEqual("PRIMARY", result.status)

    def _flow_answer(self, qid, selected=None):
        from app_question_flow_mixin import QuestionFlowMixin

        harness = MeasurementFlowHarness(question(qid, role_hint="PROBE"))
        QuestionFlowMixin._record_answer(harness, harness.current_question(), list(selected or ["A"]))
        return harness

    def test_r2_001_probe_eligibility_validated_before_normal_progress_mutation(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(2)[0])
        self.assertEqual(0, harness.update_progress_calls)
        self.assertFalse(harness.current_question().get("answered", False))

    def test_r2_002_probe_does_not_increment_normal_attempt_count(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(1)[0])
        self.assertEqual(0, harness.record["attempts"])

    def test_r2_003_probe_does_not_alter_weak_or_due_state(self):
        self._begin()
        self._enter_measurement(1)
        harness = MeasurementFlowHarness(question(self._probe_ids(1)[0], role_hint="PROBE"))
        before = copy.deepcopy(harness.record)
        from app_question_flow_mixin import QuestionFlowMixin

        QuestionFlowMixin._record_answer(harness, harness.current_question(), ["A"])
        self.assertEqual(before, harness.record)

    def test_r2_004_probe_does_not_alter_smart_practice_state(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(1)[0])
        self.assertEqual(0, harness.prewarm_calls)

    def test_r2_005_probe_does_not_alter_rrc1_scheduler_state(self):
        self._begin()
        self._enter_measurement(1)
        harness = MeasurementFlowHarness(question(self._probe_ids(1)[0], role_hint="PROBE"))
        harness.record["rrc1_queue_age"] = 7
        before = copy.deepcopy(harness.record)
        from app_question_flow_mixin import QuestionFlowMixin

        QuestionFlowMixin._record_answer(harness, harness.current_question(), ["A"])
        self.assertEqual(before, harness.record)

    def test_r2_006_probe_does_not_trigger_misconception_repair(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(1)[0])
        self.assertEqual(0, harness.misconception_calls)

    def test_r2_007_probe_does_not_create_memory_or_delayed_recall_followups(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(1)[0])
        self.assertEqual(0, harness.memory_ramp_calls)
        self.assertEqual(0, harness.delayed_recall_calls)

    def test_r2_008_probe_does_not_award_xp_reward_or_quest_progress(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(1)[0])
        self.assertEqual(0, harness.xp_calls)
        self.assertEqual(0, harness.reward_calls)
        self.assertEqual(0, harness.quest_calls)

    def test_r2_009_feedback_does_not_reveal_correctness(self):
        self._begin()
        self._enter_measurement(1)
        harness = self._flow_answer(self._probe_ids(1)[0])
        self.assertEqual(0, harness.feedback_chip_calls)

    def test_r2_010_feedback_does_not_reveal_explanation(self):
        from app_question_render_mixin import QuestionRenderMixin

        self._begin()
        self._enter_measurement(1)
        q = question(self._probe_ids(1)[0], role_hint="PROBE", answered=True, selected=["B"])
        _letter, explanation = QuestionRenderMixin._inline_explanation_for_question(object(), q, True)
        self.assertEqual("", explanation)

    def test_r2_011_feedback_does_not_reveal_keyed_option(self):
        from app_question_flow_mixin import QuestionFlowMixin

        self._begin()
        self._enter_measurement(1)
        q = question(self._probe_ids(1)[0], role_hint="PROBE", answered=True, selected=[])
        rendered = QuestionFlowMixin.format_choice_explanations(object(), q)
        self.assertNotIn("Keyed answer", rendered)
        self.assertNotIn("[correct]", rendered)

    def test_r2_012_auto_next_behavior_is_correctness_independent(self):
        from app_question_flow_mixin import QuestionFlowMixin

        self._begin()
        self._enter_measurement(1)
        qid = self._probe_ids(1)[0]
        correct = MeasurementFlowHarness(question(qid, role_hint="PROBE", answered=True, selected=["A"]))
        wrong = MeasurementFlowHarness(question(qid, role_hint="PROBE", answered=True, selected=["B"]))
        correct.questions.append(question(self._train_ids(1)[0], role_hint="TRAIN"))
        wrong.questions.append(question(self._train_ids(1)[0], role_hint="TRAIN"))
        QuestionFlowMixin.maybe_auto_next_after_answer(correct, correct.current_question())
        QuestionFlowMixin.maybe_auto_next_after_answer(wrong, wrong.current_question())
        self.assertEqual(0, len(correct.root.after_calls))
        self.assertEqual(0, len(wrong.root.after_calls))

    def test_r2_013_redo_disabled_for_measured_probe(self):
        from app_question_flow_mixin import QuestionFlowMixin

        self._begin()
        self._enter_measurement(1)
        harness = MeasurementFlowHarness(
            question(self._probe_ids(1)[0], role_hint="PROBE", answered=True, selected=[], pending=[])
        )
        QuestionFlowMixin.redo_question(harness)
        self.assertTrue(harness.current_question().get("answered"))

    def test_r2_014_retry_cannot_become_primary(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        self._enter_measurement(1)
        result = record_measurement_event(
            question(self._probe_ids(1)[0], role_hint="PROBE"), selected=["A"], correct=True, kind="RETRY"
        )
        self.assertNotEqual("PRIMARY", result.status)

    def test_r2_015_flag_does_not_terminally_resolve_measurement(self):
        from app_question_flow_mixin import QuestionFlowMixin

        self._begin()
        self._enter_measurement(1)
        q = question(self._probe_ids(1)[0], role_hint="PROBE", answered=False, flagged=True, suspended=False)
        self.assertFalse(QuestionFlowMixin._question_resolved_for_finish(object(), q))

    def test_r2_016_suspend_does_not_terminally_resolve_measurement(self):
        from app_question_flow_mixin import QuestionFlowMixin

        self._begin()
        self._enter_measurement(1)
        q = question(self._probe_ids(1)[0], role_hint="PROBE", answered=False, flagged=False, suspended=True)
        self.assertFalse(QuestionFlowMixin._question_resolved_for_finish(object(), q))

    def test_r2_017_unobserved_then_scored_cannot_become_primary(self):
        from cand01r3_protocol import record_measurement_event, record_unobserved

        self._begin()
        self._enter_measurement(1)
        qid = self._probe_ids(1)[0]
        first = record_unobserved(qid, reason="MISSED")
        self.assertEqual("UNOBSERVED", first.status)
        late = record_measurement_event(question(qid, role_hint="PROBE"), selected=["A"], correct=True)
        self.assertNotEqual("PRIMARY", late.status)

    def test_r2_018_primary_then_unobserved_is_rejected(self):
        from cand01r3_protocol import record_measurement_event, record_unobserved

        self._begin()
        self._enter_measurement(1)
        qid = self._probe_ids(1)[0]
        first = record_measurement_event(question(qid, role_hint="PROBE"), selected=["A"], correct=True)
        self.assertEqual("PRIMARY", first.status)
        late = record_unobserved(qid, reason="MISSED")
        self.assertNotEqual("UNOBSERVED", late.status)

    def test_r2_019_contaminated_then_scored_stays_non_primary(self):
        from cand01r3_protocol import record_contamination, record_measurement_event

        self._begin()
        self._enter_measurement(1)
        qid = self._probe_ids(1)[0]
        record_contamination(qid, "EXPOSED")
        later = record_measurement_event(question(qid, role_hint="PROBE"), selected=["A"], correct=True)
        self.assertEqual("CONTAMINATED", later.status)
        self.assertFalse(later.counts_toward_primary)

    def test_r2_020_malformed_empirical_ledger_fails_closed(self):
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write("{malformed-json\n")
        with self.assertRaises(Cand01R3AuthorityError) as raised:
            self._restart()
        self.assertIn("EMPIRICAL_LEDGER_CORRUPT", str(raised.exception))

    def test_r2_021_valid_ledger_resumes(self):
        self._begin()
        session = self._restart()
        self.assertEqual("cand01r3-measurement-001-v2", session.protocol_version)

    def test_r2_022_correct_none_is_rejected(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        self._enter_measurement(1)
        result = record_measurement_event(question(self._probe_ids(1)[0], role_hint="PROBE"), selected=["A"], correct=None)
        self.assertNotEqual("PRIMARY", result.status)
        self.assertEqual("INVALID_MEASUREMENT_SCORE", result.reason)

    def test_r2_023_non_boolean_score_is_rejected(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        self._enter_measurement(1)
        result = record_measurement_event(
            question(self._probe_ids(1)[0], role_hint="PROBE"), selected=["A"], correct="yes"
        )
        self.assertNotEqual("PRIMARY", result.status)
        self.assertEqual("INVALID_MEASUREMENT_SCORE", result.reason)

    def test_r2_024_day2_rejected_on_day1_calendar_date(self):
        from cand01r3_protocol import set_measurement_day
        from cand01r3_runtime import Cand01R3AuthorityError

        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-12", create=True):
            self._begin()
            self._finish_day(1)
            with self.assertRaises(Cand01R3AuthorityError) as raised:
                set_measurement_day(2)
        self.assertEqual("MEASUREMENT_DAY_TOO_EARLY", str(raised.exception))

    def test_r2_025_day_n_cannot_start_before_day1_plus_n_minus_1(self):
        from cand01r3_protocol import set_measurement_day
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-12", create=True):
            self._finish_day(1)
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-13", create=True):
            self._finish_day(2)
            with self.assertRaises(Cand01R3AuthorityError) as raised:
                set_measurement_day(3)
        self.assertEqual("MEASUREMENT_DAY_TOO_EARLY", str(raised.exception))

    def test_r2_026_late_day_retains_original_scheduled_day(self):
        from cand01r3_protocol import begin_todays_probe_measurement, record_measurement_event, set_measurement_day

        self._begin()
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-12", create=True):
            self._finish_day(1)
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-15", create=True):
            set_measurement_day(2)
            self._complete_train(2)
            begin_todays_probe_measurement()
            result = record_measurement_event(
                question(self._probe_ids(2)[0], role_hint="PROBE"), selected=["A"], correct=True
            )
        self.assertEqual(2, result.payload["scheduled_day"])
        self.assertEqual("2026-09-15", result.payload.get("calendar_local_date"))

    def test_r2_027_day1_calendar_anchor_survives_restart(self):
        from cand01r3_protocol import set_measurement_day

        self._begin()
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-12", create=True):
            set_measurement_day(1)
        session = self._restart()
        self.assertEqual("2026-09-12", getattr(session, "day1_local_date", ""))

    def test_r2_028_learner_export_hides_probe_selected_options(self):
        from cand01r3_runtime import sanitize_learner_export

        self._begin()
        qid = self._probe_ids(1)[0]
        sanitized = sanitize_learner_export(
            {"history": [{"question_id": qid, "selected": ["A"], "selected_option_ids": ["A"], "correct": True}]}
        )
        row = sanitized["history"][0]
        self.assertNotIn("selected", row)
        self.assertNotIn("selected_option_ids", row)
        self.assertTrue(row["redacted"])

    def test_r2_029_learner_export_hides_probe_correctness(self):
        from cand01r3_runtime import sanitize_learner_export

        self._begin()
        qid = self._probe_ids(1)[0]
        sanitized = sanitize_learner_export(
            {"history": [{"question_id": qid, "correct": True, "answer_key": ["A"], "explanation": "secret"}]}
        )
        row = sanitized["history"][0]
        self.assertNotIn("correct", row)
        self.assertNotIn("answer_key", row)
        self.assertNotIn("explanation", row)

    def test_r2_030_ordinary_mastery_analytics_exclude_probe_result(self):
        self._begin()
        self._enter_measurement(1)
        harness = MeasurementFlowHarness(question(self._probe_ids(1)[0], role_hint="PROBE"))
        before = copy.deepcopy(harness.progress_data)
        from app_question_flow_mixin import QuestionFlowMixin

        QuestionFlowMixin._record_answer(harness, harness.current_question(), ["A"])
        self.assertEqual(before, harness.progress_data)
        self.assertEqual(0, harness.update_progress_calls)

    def test_r2_031_measurement_pool_contains_today_only_probes(self):
        from cand01r3_runtime import filter_training_questions
        from cand01r3_partition import canonical_question_id

        self._begin()
        self._enter_measurement(1)
        day1 = self._probe_ids(1)
        day2 = self._probe_ids(2)
        pool = [question(qid, role_hint="PROBE") for qid in day2 + day1] + [question(self._train_ids(1)[0])]
        filtered = filter_training_questions(pool, stage="MEASUREMENT")
        self.assertEqual(set(day1), {canonical_question_id(q) for q in filtered})

    def test_r2_032_measurement_sequence_equals_frozen_day_order(self):
        from cand01r3_runtime import filter_training_questions
        from cand01r3_partition import canonical_question_id

        self._begin()
        self._enter_measurement(1)
        expected = self._probe_ids(1)
        pool = [question(qid, role_hint="PROBE") for qid in reversed(expected)]
        filtered = filter_training_questions(pool, stage="MEASUREMENT")
        self.assertEqual(expected, [canonical_question_id(q) for q in filtered])

    def test_r2_033_future_day_probe_is_excluded(self):
        from cand01r3_runtime import filter_training_questions
        from cand01r3_partition import canonical_question_id

        self._begin()
        self._enter_measurement(1)
        future = self._probe_ids(2)[0]
        today = self._probe_ids(1)[0]
        filtered = filter_training_questions(
            [question(future, role_hint="PROBE"), question(today, role_hint="PROBE")], stage="MEASUREMENT"
        )
        self.assertEqual([today], [canonical_question_id(q) for q in filtered])

    def test_r2_034_past_day_probe_is_excluded(self):
        from cand01r3_protocol import begin_todays_probe_measurement, set_measurement_day
        from cand01r3_runtime import filter_training_questions
        from cand01r3_partition import canonical_question_id

        self._begin()
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-12", create=True):
            self._finish_day(1)
        with mock.patch("cand01r3_protocol._current_experiment_local_date", return_value="2026-09-13", create=True):
            set_measurement_day(2)
            self._complete_train(2)
            begin_todays_probe_measurement()
        past = self._probe_ids(1)[0]
        today = self._probe_ids(2)[0]
        filtered = filter_training_questions(
            [question(past, role_hint="PROBE"), question(today, role_hint="PROBE")], stage="MEASUREMENT"
        )
        self.assertEqual([today], [canonical_question_id(q) for q in filtered])

    def test_r2_035_post_hoc_contamination_survives_restart(self):
        from cand01r3_protocol import clean_primary_events, current_measurement_session, record_contamination, record_measurement_event

        self._begin()
        self._enter_measurement(1)
        qid = self._probe_ids(1)[0]
        first = record_measurement_event(question(qid, role_hint="PROBE"), selected=["A"], correct=True)
        self.assertEqual("PRIMARY", first.status)
        record_contamination(qid, "POST_HOC_EXPOSURE")
        self._restart()
        self.assertTrue(current_measurement_session().ledger.is_contaminated(qid))
        self.assertNotIn(qid, [row.get("question_id") for row in clean_primary_events()])

    def test_r2_036_normal_train_behavior_remains_unchanged(self):
        from app_question_flow_mixin import QuestionFlowMixin
        from cand01r3_protocol import set_measurement_day

        self._begin()
        set_measurement_day(1)
        harness = MeasurementFlowHarness(question(self._train_ids(1)[0], role_hint="TRAIN"))
        QuestionFlowMixin._record_answer(harness, harness.current_question(), ["A"])
        self.assertEqual(1, harness.update_progress_calls)
        self.assertEqual(1, harness.xp_calls)

    def test_r2_037_default_launch_bank_remains_unchanged(self):
        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, sha256_file(DEFAULT_BANK))

    def test_r2_038_protocol_sha_remains_unchanged(self):
        from cand01r3_protocol import build_protocol

        self.assertEqual(EXPECTED_PROTOCOL_SHA256, build_protocol()["protocol_sha256"])

    def test_r2_039_real_observations_remain_zero_in_pre_run_repository_state(self):
        from cand01r3_protocol import load_committed_protocol

        protocol = load_committed_protocol()
        self.assertEqual(0, int(protocol.get("real_observations") or 0))

    def test_r2_040_no_empirical_winner_is_declared(self):
        from cand01r3_protocol import load_committed_protocol

        protocol = load_committed_protocol()
        self.assertEqual("NOT_YET_AVAILABLE", protocol.get("empirical_result"))
        self.assertEqual("NO", protocol.get("deployment_authorized"))


if __name__ == "__main__":
    unittest.main()
