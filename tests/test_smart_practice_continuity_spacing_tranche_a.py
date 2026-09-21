import json
import logging
import random
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as app_module  # noqa: E402
from app_constants import MODE_SMART_PRACTICE, QUESTION_TAG_STREAK_RESCUE_PREFIX  # noqa: E402
from progress_store import update_progress_record  # noqa: E402
from question_identity import canonical_question_id  # noqa: E402
from session_identity import canonical_session_signature  # noqa: E402
from smart_practice_core import (  # noqa: E402
    EXPOSURE_INVALID,
    EXPOSURE_NEVER,
    EXPOSURE_NORMAL,
    EXPOSURE_RECENT,
    SmartPracticeCandidate,
    apply_target6_suppression,
    build_smart_practice_selection,
    local_smart_practice_rng,
    order_recent_exact_fallback,
    smart_practice_ordering_seed,
    summarize_exact_exposure,
)
from smart_practice_policy import (  # noqa: E402
    cross_session_spacing_threshold_hours,
    default_policy_values,
    make_policy,
    normalize_governance,
    policy_checksum,
    validate_policy,
    validate_policy_values,
)
from smart_practice_profile import SMART_PRACTICE_SCORING  # noqa: E402
from smart_practice_worker import build_detached_pool  # noqa: E402

EVAL = datetime(2026, 9, 21, 12, 0, 0)


def _question(question_id, number, *, domain="Domain A", topic="Concept", objective="1.1", role="blueprint_coverage"):
    return {
        "id": question_id,
        "question_number": number,
        "prompt": f"Prompt {question_id}",
        "choices": {"A": "Right", "B": "Wrong"},
        "correct": ["A"],
        "domain": domain,
        "topics": [topic],
        "source_name": "Source",
        "source_label": "Source",
        "objective_code": objective,
        "smart_primary_role": role,
    }


def _summary(question, events, evaluation_time=EVAL, threshold=72):
    return summarize_exact_exposure(
        question,
        evaluation_time=evaluation_time,
        threshold_hours=threshold,
        matching_events=events,
    )


def _at(delta):
    return (EVAL + delta).isoformat()


class SmartPracticeSpacingPureTests(unittest.TestCase):
    def test_spa_001_never_exposed_is_normally_eligible(self):
        summary = _summary(_question("q-new", 1), [])
        self.assertEqual(EXPOSURE_NEVER, summary.status)
        self.assertTrue(summary.normally_eligible)
        self.assertEqual(0, summary.exact_exposure_count)

    def test_spa_002_just_under_72_hours_is_excluded(self):
        question = _question("q-recent", 1)
        summary = _summary(
            question, [{"at": _at(-timedelta(hours=71, minutes=59, seconds=59)), "question_id": "q-recent"}]
        )
        self.assertEqual(EXPOSURE_RECENT, summary.status)
        self.assertFalse(summary.normally_eligible)

    def test_spa_003_exactly_72_hours_is_eligible(self):
        summary = _summary(_question("q-72", 1), [{"at": _at(-timedelta(hours=72)), "question_id": "q-72"}])
        self.assertEqual(EXPOSURE_NORMAL, summary.status)
        self.assertTrue(summary.normally_eligible)

    def test_spa_004_beyond_72_hours_is_eligible(self):
        summary = _summary(
            _question("q-old", 1), [{"at": _at(-timedelta(hours=72, seconds=1)), "question_id": "q-old"}]
        )
        self.assertEqual(EXPOSURE_NORMAL, summary.status)
        self.assertTrue(summary.normally_eligible)

    def test_spa_005_future_timestamp_fails_closed(self):
        summary = _summary(_question("q-future", 1), [{"at": _at(timedelta(seconds=1)), "question_id": "q-future"}])
        self.assertEqual(EXPOSURE_INVALID, summary.status)
        self.assertFalse(summary.normally_eligible)

    def test_spa_006_malformed_timestamp_fails_closed(self):
        summary = _summary(_question("q-bad", 1), [{"at": "not-a-timestamp", "question_id": "q-bad"}])
        self.assertEqual(EXPOSURE_INVALID, summary.status)
        self.assertFalse(summary.normally_eligible)

    def test_spa_007_unusable_chronology_is_not_never_exposed(self):
        summary = _summary(_question("q-bad", 1), [{"at": "", "question_id": "q-bad"}, {"question_id": "q-bad"}])
        self.assertNotEqual(EXPOSURE_NEVER, summary.status)
        self.assertEqual(2, summary.exact_exposure_count)
        self.assertFalse(summary.normally_eligible)

    def test_spa_008_distinct_canonical_id_is_independent(self):
        shared_events = [{"at": _at(-timedelta(hours=1)), "question_id": "q-a"}]
        recent = _summary(_question("q-a", 1, topic="Shared"), shared_events)
        other = _summary(_question("q-b", 2, topic="Shared"), [])
        self.assertFalse(recent.normally_eligible)
        self.assertTrue(other.normally_eligible)

    def test_spa_012_through_015_and_039_fallback_order(self):
        older = _summary(_question("q-older", 1), [{"at": _at(-timedelta(hours=30)), "question_id": "q-older"}])
        fewer = _summary(
            _question("q-fewer", 2),
            [{"at": _at(-timedelta(hours=10)), "question_id": "q-fewer"}],
        )
        more = _summary(
            _question("q-more", 3),
            [
                {"at": _at(-timedelta(hours=40)), "question_id": "q-more"},
                {"at": _at(-timedelta(hours=10)), "question_id": "q-more"},
            ],
        )
        higher = _summary(_question("q-higher", 4), [{"at": _at(-timedelta(hours=10)), "question_id": "q-higher"}])
        lower_id = _summary(_question("q-a", 5), [{"at": _at(-timedelta(hours=10)), "question_id": "q-a"}])
        higher_id = _summary(_question("q-b", 6), [{"at": _at(-timedelta(hours=10)), "question_id": "q-b"}])
        invalid = _summary(_question("q-invalid", 7), [{"at": "bad", "question_id": "q-invalid"}])
        future = _summary(_question("q-future", 8), [{"at": _at(timedelta(hours=1)), "question_id": "q-future"}])
        questions = [
            _question("q-b", 6),
            _question("q-future", 8),
            _question("q-more", 3),
            _question("q-older", 1),
            _question("q-invalid", 7),
            _question("q-a", 5),
            _question("q-fewer", 2),
            _question("q-higher", 4),
        ]
        summaries = {
            "q-older": older,
            "q-fewer": fewer,
            "q-more": more,
            "q-higher": higher,
            "q-a": lower_id,
            "q-b": higher_id,
            "q-invalid": invalid,
            "q-future": future,
        }
        scores = {
            "q-older": 1.0,
            "q-fewer": 1.0,
            "q-more": 50.0,
            "q-higher": 20.0,
            "q-a": 5.0,
            "q-b": 5.0,
            "q-invalid": 100.0,
            "q-future": 100.0,
        }
        ordered = [
            canonical_question_id(question)
            for question in order_recent_exact_fallback(questions, summaries, lambda question: scores[question["id"]])
        ]
        self.assertEqual(
            ["q-older", "q-higher", "q-a", "q-b", "q-fewer", "q-more", "q-future", "q-invalid"],
            ordered,
        )
        self.assertLess(ordered.index("q-older"), ordered.index("q-higher"))
        self.assertLess(ordered.index("q-fewer"), ordered.index("q-more"))
        self.assertLess(ordered.index("q-higher"), ordered.index("q-fewer"))
        self.assertLess(ordered.index("q-a"), ordered.index("q-b"))
        self.assertLess(ordered.index("q-b"), ordered.index("q-future"))
        self.assertLess(ordered.index("q-b"), ordered.index("q-invalid"))

    def test_spa_016_selection_rejects_duplicate_canonical_id(self):
        def candidate(number, canonical_id, role, priority):
            question = _question(canonical_id, number, role=role)
            return SmartPracticeCandidate(
                question=question,
                qnum=number,
                priority=priority,
                selection_bonus=0.0,
                primary_role=role,
                objective_code="1.1",
                source_label="Source",
                primary_topic="Concept",
                normalized_domain="domain a",
                raw_domain="Domain A",
                canonical_id=canonical_id,
                exposure_status=EXPOSURE_NEVER,
                spacing_order_active=True,
            )

        result = build_smart_practice_selection(
            [
                candidate(1, "same", "weak_repair", 90),
                candidate(2, "same", "due_retention", 80),
                candidate(3, "other", "blueprint_coverage", 70),
            ],
            [],
            target=3,
            role_shares={},
            objective_cap=3,
            profile=SMART_PRACTICE_SCORING,
            high_signal_qnums=set(),
            freshness_map={},
        )
        ids = [canonical_question_id(question) for question in result.ordered_questions]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotEqual(ids.count("same"), 2)

    def test_spa_019_and_021_local_rng_is_deterministic_and_isolated(self):
        material = {
            "builder_context_fingerprint": "builder-a",
            "bank_content_fingerprint": "bank-a",
            "policy_id": "policy-a",
            "policy_version": "v1",
            "policy_checksum": "checksum-a",
            "learner_state_revision": ("rev", 1),
        }
        before = random.getstate()
        first = local_smart_practice_rng(material)
        second = local_smart_practice_rng(material)
        other = local_smart_practice_rng({**material, "builder_context_fingerprint": "builder-b"})
        left = ["a", "b", "c", "d", "e"]
        right = list(left)
        altered = list(left)
        first.shuffle(left)
        second.shuffle(right)
        other.shuffle(altered)
        self.assertEqual(left, right)
        self.assertNotEqual(left, altered)
        self.assertEqual(before, random.getstate())
        self.assertNotEqual(
            smart_practice_ordering_seed(material),
            smart_practice_ordering_seed({**material, "policy_checksum": "checksum-b"}),
        )

    def test_spa_023_through_025_target6_suppression_order(self):
        pool = [_question(f"q{number}", number) for number in range(1, 5)]
        joint = apply_target6_suppression(pool, {1}, {2}, target=2)
        self.assertEqual([3, 4], [question["question_number"] for question in joint])
        super_only = apply_target6_suppression(pool, {1}, {2, 3, 4}, target=2)
        self.assertEqual([2, 3, 4], [question["question_number"] for question in super_only])
        full = apply_target6_suppression(pool, {1, 2}, {3, 4}, target=3)
        self.assertEqual([1, 2, 3, 4], [question["question_number"] for question in full])

    def test_legacy_policy_without_spacing_field_stays_valid(self):
        values = default_policy_values()
        self.assertEqual(72, values["cross_session_spacing_threshold_hours"])
        del values["cross_session_spacing_threshold_hours"]
        ok, reasons = validate_policy_values(values)
        self.assertTrue(ok, reasons)
        policy = make_policy(
            policy_id="policy-legacy",
            policy_version="v1",
            policy_name="Legacy",
            status="active",
            created_at="2026-01-01T00:00:00",
            created_by="test",
            policy_values=values,
        )
        stored_checksum = policy["checksum"]
        self.assertNotIn("cross_session_spacing_threshold_hours", policy["policy_values"])
        self.assertEqual(stored_checksum, policy_checksum(policy))
        self.assertEqual(72.0, cross_session_spacing_threshold_hours(policy["policy_values"]))
        governance = {
            "schema_version": 1,
            "active_policy_id": policy["policy_id"],
            "policies": {policy["policy_id"]: policy},
            "candidates": {},
            "shadow_decisions": {},
            "challenger_evaluations": {},
            "drift_reports": {},
            "recovery_snapshots": {},
            "audit_log": [],
            "invalid_data_count": 0,
            "last_updated_at": "2026-01-01T00:00:00",
        }
        normalized = normalize_governance(governance, created_at="2026-01-01T00:00:00")
        active = normalized["policies"][policy["policy_id"]]
        self.assertEqual(stored_checksum, active["checksum"])
        self.assertNotIn("cross_session_spacing_threshold_hours", active["policy_values"])
        self.assertTrue(validate_policy(active)[0])

    def test_authoritative_event_is_list_order_not_timestamp_order(self):
        question = _question("q-order", 1)
        events = [
            {"at": _at(-timedelta(hours=1)), "question_id": "q-order"},
            {"at": "malformed", "question_id": "q-order"},
        ]
        summary = _summary(question, events)
        self.assertEqual(EXPOSURE_INVALID, summary.status)
        self.assertEqual(2, summary.exact_exposure_count)


class SmartPracticeSpacingAppTests(unittest.TestCase):
    def make_app(self, start_session=False):
        self.tmpdir_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir_ctx.cleanup)
        tmpdir = Path(self.tmpdir_ctx.name)
        user_data = tmpdir / "user_data"
        checkpoints = user_data / "checkpoints"
        backups = user_data / "backups"
        logs = user_data / "logs"
        for folder in (user_data, checkpoints, backups, logs):
            folder.mkdir(parents=True, exist_ok=True)
        bank_path = tmpdir / "mini_bank.json"
        bank_payload = {
            "title": "Mini Bank",
            "questions": [
                _question("mini-q1", 1),
                _question("mini-q2", 2, domain="Domain B", topic="Other"),
                _question("mini-q3", 3, domain="Domain C", topic="Third"),
            ],
        }
        bank_path.write_text(json.dumps(bank_payload), encoding="utf-8")
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

        def restore_logging():
            for handler in list(root_logger.handlers):
                root_logger.removeHandler(handler)
                handler.close()
            for handler in previous_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(previous_level)

        self.addCleanup(restore_logging)
        app = app_module.TestingEngineApp(root)
        app._show_feedback_popover = lambda q, selected, anchor_widget=None: app._record_answer(
            q, selected, feedback_override={"confidence": "Sure", "miss_reason": ""}
        )
        if start_session:
            app.restore_full_bank()
        return app

    def _install(self, app, questions, history=None):
        app.master_questions = questions
        app._reset_runtime_question_state(app.master_questions)
        app.progress_data["history"] = list(history or [])
        app.smart_practice_evaluation_time = EVAL
        app.smart_practice_pool_cache = {}
        app.smart_practice_signal_cache_key = None
        app.smart_practice_signal_cache_payload = None

    def _event(self, question_id, number, at):
        return {"at": at, "question_id": question_id, "question_number": number, "correct": True}

    def test_spa_009_and_010_recent_exact_does_not_bypass_when_alternative_exists(self):
        app = self.make_app()
        questions = [
            _question("weak-recent", 1, role="weak_repair"),
            _question("weak-alt", 2, domain="Domain B", topic="Other", objective="2.1", role="weak_repair"),
            _question("due-recent", 3, domain="Domain C", topic="Due", objective="3.1", role="due_retention"),
            _question("due-alt", 4, domain="Domain D", topic="Due Alt", objective="4.1", role="due_retention"),
        ]
        self._install(
            app,
            questions[:2],
            [self._event("weak-recent", 1, _at(-timedelta(hours=2)))],
        )
        weak_pool = app.build_smart_practice_pool("1", randomize=False)
        self.assertEqual(["weak-alt"], [question["id"] for question in weak_pool])
        self._install(
            app,
            questions[2:],
            [self._event("due-recent", 3, _at(-timedelta(hours=2)))],
        )
        due_pool = app.build_smart_practice_pool("1", randomize=False)
        self.assertEqual(["due-alt"], [question["id"] for question in due_pool])

    def test_spa_011_fallback_only_when_normal_pool_cannot_fill(self):
        app = self.make_app()
        questions = [
            _question("spaced", 1),
            _question("recent", 2, domain="Domain B", topic="Other", objective="2.1"),
        ]
        history = [self._event("recent", 2, _at(-timedelta(hours=3)))]
        self._install(app, questions, history)
        one = app.build_smart_practice_pool("1", randomize=False)
        self.assertEqual(["spaced"], [question["id"] for question in one])
        app.smart_practice_pool_cache = {}
        app.smart_practice_signal_cache_key = None
        both = app.build_smart_practice_pool("2", randomize=False)
        self.assertEqual(["spaced", "recent"], [question["id"] for question in both])

    def test_spa_012_builder_fallback_prefers_older_exposure(self):
        app = self.make_app()
        questions = [
            _question("newer", 1, domain="Domain A", topic="A", objective="1.1"),
            _question("older", 2, domain="Domain B", topic="B", objective="2.1"),
        ]
        history = [
            self._event("newer", 1, _at(-timedelta(hours=5))),
            self._event("older", 2, _at(-timedelta(hours=40))),
        ]
        self._install(app, questions, history)
        pool = app.build_smart_practice_pool("1", randomize=False)
        self.assertEqual(["older"], [question["id"] for question in pool])

    def test_spa_016_and_017_session_insertion_cannot_duplicate_canonical_id(self):
        app = self.make_app()
        questions = [
            _question("keep", 1, domain="Shared"),
            _question("already", 2, domain="Shared"),
            _question("fresh", 3, domain="Shared", topic="Other"),
        ]
        self._install(app, questions, [self._event("already", 2, _at(-timedelta(hours=1)))])
        app.start_session_from_pool(
            [dict(questions[0]), dict(questions[1])],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=False,
            preserve_if_saved=False,
        )
        app.session_answer_history = [
            {"question_id": "keep", "question_number": 1, "domain": "Shared", "correct": False},
            {"question_id": "keep", "question_number": 1, "domain": "Shared", "correct": False},
        ]
        inserted = app.maybe_trigger_streak_rescue(app.questions[0])
        ids = [canonical_question_id(question) for question in app.questions]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("already", [canonical_question_id(question) for question in inserted])
        self.assertIn("fresh", [canonical_question_id(question) for question in inserted])

    def test_spa_018_and_019_repeated_builds_match(self):
        app = self.make_app()
        questions = [
            _question(f"q{number}", number, domain=f"Domain {number}", topic=f"Topic {number}", objective=f"1.{number}")
            for number in range(1, 6)
        ]
        self._install(app, questions)
        first = [question["id"] for question in app.build_smart_practice_pool("4", randomize=False)]
        second = [question["id"] for question in app.build_smart_practice_pool("4", randomize=False)]
        self.assertEqual(first, second)
        app.smart_practice_pool_cache = {}
        app.smart_practice_signal_cache_key = None
        random_first = [question["id"] for question in app.build_smart_practice_pool("4", randomize=True)]
        random_second = [question["id"] for question in app.build_smart_practice_pool("4", randomize=True)]
        self.assertEqual(random_first, random_second)
        self.assertEqual(set(first), set(random_first))

    def test_spa_020_seed_change_does_not_change_membership(self):
        app = self.make_app()
        questions = [
            _question(
                f"q{number}", number, domain=f"Domain {number % 3}", topic=f"Topic {number}", objective=f"1.{number}"
            )
            for number in range(1, 7)
        ]
        self._install(app, questions)
        app.smart_practice_builder_context_fingerprint = "builder-a"
        app.smart_practice_bank_content_fingerprint = app.current_bank_fingerprint()
        first = app.build_smart_practice_pool("5", randomize=True)
        app.smart_practice_pool_cache = {}
        app.smart_practice_signal_cache_key = None
        app.smart_practice_builder_context_fingerprint = "builder-b"
        second = app.build_smart_practice_pool("5", randomize=True)
        self.assertEqual({question["id"] for question in first}, {question["id"] for question in second})

    def test_spa_021_randomized_build_does_not_touch_global_rng(self):
        app = self.make_app()
        self._install(
            app,
            [
                _question(f"q{number}", number, domain=f"D{number}", topic=f"T{number}", objective=f"1.{number}")
                for number in range(1, 5)
            ],
        )
        before = random.getstate()
        app.build_smart_practice_pool("3", randomize=True)
        self.assertEqual(before, random.getstate())

    def test_spa_022_foreground_and_worker_match(self):
        app = self.make_app()
        self._install(
            app,
            [
                _question(f"q{number}", number, domain=f"D{number}", topic=f"T{number}", objective=f"1.{number}")
                for number in range(1, 6)
            ],
        )
        app.smart_practice_builder_context_fingerprint = "builder-frozen"
        app.smart_practice_bank_content_fingerprint = app.current_bank_fingerprint()
        base = list(app.master_questions)
        snapshot = app._smart_practice_worker_snapshot(base_pool=base)
        foreground = [question["id"] for question in app.build_smart_practice_pool("4", randomize=True, base_pool=base)]
        detached = build_detached_pool(
            type(app),
            snapshot,
            count="4",
            randomize=True,
            base_pool=base,
        )
        self.assertEqual(foreground, [question["id"] for question in detached])

    def test_spa_026_through_032_exact_restore_and_rescue_reconstruction(self):
        app = self.make_app()
        questions = [
            _question("third", 3, domain="Rescue A"),
            _question("first", 1, domain="Rescue B"),
            _question("second", 2, domain="Plain"),
        ]
        self._install(app, questions, [self._event("other-session", 9, _at(-timedelta(days=1)))])
        app.progress_data["history"].append(
            {
                "at": _at(-timedelta(days=2)),
                "question_id": "third",
                "question_number": 3,
                "session_tag": f"{QUESTION_TAG_STREAK_RESCUE_PREFIX}Unrelated",
                "correct": False,
            }
        )
        app.start_session_from_pool(
            [dict(questions[0]), dict(questions[1]), dict(questions[2])],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=False,
            preserve_if_saved=False,
        )
        app.questions[0]["session_tag"] = f"{QUESTION_TAG_STREAK_RESCUE_PREFIX}Rescue A"
        app.questions[0]["answered"] = True
        app.questions[0]["selected"] = ["A"]
        app.index = 1
        app.session_answer_history = [
            {
                "question_id": "third",
                "question_number": 3,
                "domain": "Rescue A",
                "session_tag": f"{QUESTION_TAG_STREAK_RESCUE_PREFIX}Rescue A",
                "correct": False,
            },
            {
                "question_id": "first",
                "question_number": 1,
                "domain": "Rescue B",
                "session_tag": f"{QUESTION_TAG_STREAK_RESCUE_PREFIX}Rescue B",
                "correct": False,
            },
        ]
        saved_ids = [canonical_question_id(question) for question in app.questions]
        app.save_session()
        app.questions = []
        app.index = 0
        app.rescue_domains_triggered = set()
        app.load_session_if_present(skip_identity_check=True)
        self.assertEqual(saved_ids, [canonical_question_id(question) for question in app.questions])
        self.assertEqual(1, app.index)
        self.assertTrue(app.questions[0]["answered"])
        self.assertFalse(app.questions[1]["answered"])
        self.assertEqual({"Rescue A", "Rescue B"}, set(app.rescue_domains_triggered))
        again = set(app.rescue_domains_triggered)
        app._reconstruct_rescue_domains_triggered()
        self.assertEqual(again, set(app.rescue_domains_triggered))

    def test_spa_033_and_034_cache_admits_newly_eligible_candidate(self):
        app = self.make_app()
        questions = [
            _question("becomes-eligible", 1, domain="Domain A", topic="A", objective="1.1"),
            _question("always", 2, domain="Domain B", topic="B", objective="2.1"),
        ]
        early = EVAL
        exposed = (early - timedelta(hours=71, minutes=59, seconds=59)).isoformat()
        self._install(app, questions, [self._event("becomes-eligible", 1, exposed)])
        app._progress_questions()["becomes-eligible"] = update_progress_record(
            {}, ["B"], False, confidence="Sure", miss_reason="Did not know"
        )
        app.smart_practice_evaluation_time = early
        first = [question["id"] for question in app.build_smart_practice_pool("1", randomize=False)]
        self.assertEqual(["always"], first)
        app.smart_practice_evaluation_time = early + timedelta(hours=72)
        second = [question["id"] for question in app.build_smart_practice_pool("1", randomize=False)]
        self.assertIn("becomes-eligible", second)
        snapshot = app._smart_practice_worker_snapshot()
        detached = build_detached_pool(type(app), snapshot, count="1", randomize=False, base_pool=list(questions))
        self.assertEqual(second, [question["id"] for question in detached])

    def test_spa_035_manual_redo_is_not_spacing_restricted(self):
        app = self.make_app()
        question = _question("redo-me", 1)
        self._install(
            app,
            [question, _question("other", 2, domain="Domain B", topic="Other")],
            [self._event("redo-me", 1, _at(-timedelta(minutes=5)))],
        )
        app.start_session_from_pool(
            [dict(question)],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=False,
            preserve_if_saved=False,
        )
        app.questions[0]["answered"] = True
        app.questions[0]["selected"] = ["B"]
        app.redo_question()
        self.assertFalse(app.questions[0].get("answered"))
        self.assertEqual(["redo-me"], [item["id"] for item in app.questions])

    def test_spa_036_through_038_no_tranche_b_replacement(self):
        app = self.make_app()
        questions = [
            _question(f"q{number}", number, domain=f"Domain {number}", topic=f"Topic {number}", objective=f"{number}.1")
            for number in range(1, 4)
        ]
        self._install(app, questions)
        app.start_session_from_pool(
            [dict(question) for question in questions],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=False,
            preserve_if_saved=False,
        )
        before = [question["id"] for question in app.questions]
        app._record_answer(app.questions[0], ["A"], feedback_override={"confidence": "Sure", "miss_reason": ""})
        after = [question["id"] for question in app.questions]
        self.assertEqual(before, after[: len(before)])
        builder = Path(ROOT, "app_session_builder_mixin.py").read_text(encoding="utf-8")
        core = Path(ROOT, "smart_practice_core.py").read_text(encoding="utf-8")
        self.assertNotIn("MINIMUM_SCORE_DELTA_FOR_REPLACEMENT", builder + core)
        self.assertNotIn("MAX_REPLACEMENTS_PER_ANSWER", builder + core)

    def test_spa_040_restore_keeps_order_and_later_insert_dedupes(self):
        with self.assertRaises(ValueError):
            canonical_session_signature(MODE_SMART_PRACTICE, "bank", ["same", "same"])
        app = self.make_app()
        questions = [
            _question("c", 3),
            _question("a", 1, domain="Domain B", topic="B"),
            _question("b", 2, domain="Domain C", topic="C"),
        ]
        self._install(app, questions)
        app.start_session_from_pool(
            [dict(questions[0]), dict(questions[1]), dict(questions[2])],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=False,
            preserve_if_saved=False,
        )
        app.save_session()
        app.questions = list(reversed(app.questions))
        app.load_session_if_present(skip_identity_check=True)
        self.assertEqual(["c", "a", "b"], [question["id"] for question in app.questions])
        inserted = app._insert_followup_questions(app.questions[0], [dict(questions[1]), dict(questions[0])], "repair")
        self.assertEqual([], inserted)
        self.assertEqual(["c", "a", "b"], [question["id"] for question in app.questions])

    def _weak_record(self):
        return {
            "attempts": 2,
            "wrong_count": 2,
            "correct_count": 0,
            "last_correct": False,
            "correct_streak": 0,
        }

    def _open_single(self, app, questions):
        app.start_session_from_pool(
            [dict(questions[0])],
            mode=MODE_SMART_PRACTICE,
            count="All visible",
            randomize=False,
            reset_clock=False,
            preserve_if_saved=False,
        )
        app.session_question_limit = 12
        return app.questions[0]

    def _capture_followup_class(self, app, invoke):
        captured = {}
        original = app._prepare_spaced_followups

        def spy(candidates, tag, maximum=None):
            captured["ids"] = [candidate.get("id") for candidate in candidates]
            captured["maximum"] = maximum
            return original(candidates, tag, maximum=maximum)

        app._prepare_spaced_followups = spy
        try:
            inserted = invoke()
        finally:
            app._prepare_spaced_followups = original
        return captured, inserted

    def _assert_normal_survives_pretruncation(self, app, invoke, recent_ids, normal_id):
        captured, inserted = self._capture_followup_class(app, invoke)
        ids = captured["ids"]
        self.assertIn(normal_id, ids)
        for recent_id in recent_ids:
            self.assertIn(recent_id, ids)
            self.assertLess(ids.index(recent_id), ids.index(normal_id))
        self.assertEqual([normal_id], [item["id"] for item in inserted])
        self.assertNotIn(normal_id, recent_ids)

    def test_repair_a_twins_prefer_normal_candidate_hidden_by_old_limit(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("recent-a", 2, domain="Shared", topic="Shared Topic"),
            _question("recent-b", 3, domain="Shared", topic="Shared Topic"),
            _question("normal", 4, domain="Shared", topic="Shared Topic"),
        ]
        self._install(
            app,
            questions,
            [
                self._event("recent-a", 2, _at(-timedelta(hours=2))),
                self._event("recent-b", 3, _at(-timedelta(hours=3))),
            ],
        )
        records = app._progress_questions()
        records["recent-a"] = self._weak_record()
        records["recent-b"] = self._weak_record()
        self._open_single(app, questions)
        window = [item["id"] for item in app.find_question_twins(app.questions[0], limit=2)]
        self.assertEqual(["recent-a", "recent-b"], window)
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_queue_question_twins(app.questions[0]),
            ["recent-a", "recent-b"],
            "normal",
        )

    def test_repair_b_wrong_answer_memory_prefers_normal_candidate(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("recent", 2, domain="Shared", topic="Shared Topic"),
            _question("normal", 3, domain="Shared", topic="Shared Topic"),
        ]
        for question in questions:
            question["choices"] = {"A": "Approved (RIGHT)", "B": "Rejected (WRONG)"}
            question["prompt"] = f"{question['prompt']} RIGHT WRONG"
        self._install(app, questions, [self._event("recent", 2, _at(-timedelta(hours=2)))])
        recent_record = self._weak_record()
        recent_record["wrong_count"] = 8
        app._progress_questions()["recent"] = recent_record
        current = self._open_single(app, questions)
        wrong_letter = next(letter for letter in current["choices"] if letter not in set(current.get("correct") or []))
        current["selected"] = [wrong_letter]
        window = [item["id"] for item in app.find_wrong_answer_memory_candidates(current, limit=1)]
        self.assertEqual(["recent"], window)
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_queue_wrong_answer_memory(current),
            ["recent"],
            "normal",
        )

    def test_repair_c_confusion_pair_prefers_normal_candidate(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("recent", 2, domain="Shared", topic="Shared Topic"),
            _question("normal", 3, domain="Shared", topic="Shared Topic"),
        ]
        for question in questions:
            question["choices"] = {"A": "Approved (RIGHT)", "B": "Rejected (WRONG)"}
            question["prompt"] = f"{question['prompt']} RIGHT WRONG"
        self._install(app, questions, [self._event("recent", 2, _at(-timedelta(hours=2)))])
        app._progress_questions()["recent"] = self._weak_record()
        current = self._open_single(app, questions)
        wrong_letter = next(letter for letter in current["choices"] if letter not in set(current.get("correct") or []))
        current["selected"] = [wrong_letter]
        window = [item["id"] for item in app.find_confusion_pair_candidates(current, limit=1)]
        self.assertEqual(["recent"], window)
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_queue_confusion_pair_drill(current),
            ["recent"],
            "normal",
        )

    def test_repair_d_delayed_recall_prefers_normal_candidate(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic", objective="1.1"),
            _question("recent", 2, domain="Shared", topic="Shared Topic", objective="1.1"),
            _question("normal", 3, domain="Shared", topic="Shared Topic", objective="1.1"),
        ]
        self._install(app, questions, [self._event("recent", 2, _at(-timedelta(hours=2)))])
        app._progress_questions()["normal"] = {
            "attempts": 6,
            "wrong_count": 0,
            "correct_count": 6,
            "last_correct": True,
            "correct_streak": 6,
        }
        current = self._open_single(app, questions)
        current["last_confidence"] = "Sure"
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_queue_delayed_recall_probe(current),
            ["recent"],
            "normal",
        )

    def test_repair_e_memory_ramp_prefers_normal_candidate(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic", objective="1.1"),
            _question("recent", 2, domain="Shared", topic="Shared Topic", objective="1.1"),
            _question("normal", 3, domain="Shared", topic="Shared Topic", objective="1.1"),
        ]
        self._install(
            app,
            questions,
            [
                self._event("current", 1, _at(-timedelta(days=10))),
                self._event("current", 1, _at(-timedelta(days=9))),
                self._event("recent", 2, _at(-timedelta(hours=2))),
            ],
        )
        for event in app.progress_data["history"]:
            event["correct"] = False
        app._progress_questions()["normal"] = {
            "attempts": 5,
            "wrong_count": 0,
            "correct_count": 5,
            "last_correct": True,
            "correct_streak": 5,
        }
        current = self._open_single(app, questions)
        tag, window = app.find_memory_ramp_candidates(current, limit=1)
        self.assertTrue(tag)
        self.assertEqual(["recent"], [item["id"] for item in window])
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_queue_memory_ramp(current),
            ["recent"],
            "normal",
        )

    def test_repair_f_misconception_repair_prefers_normal_candidate(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("recent", 2, domain="Shared", topic="Shared Topic"),
            _question("normal", 3, domain="Shared", topic="Shared Topic"),
        ]
        for question in questions:
            question["choices"] = {"A": "Approved (RIGHT)", "B": "Rejected (WRONG)"}
            question["prompt"] = f"{question['prompt']} RIGHT WRONG"
        self._install(app, questions, [self._event("recent", 2, _at(-timedelta(hours=2)))])
        app._progress_questions()["recent"] = self._weak_record()
        current = self._open_single(app, questions)
        wrong_letter = next(letter for letter in current["choices"] if letter not in set(current.get("correct") or []))
        current["selected"] = [wrong_letter]
        current["smart_root_cause"] = "concept_confusion"
        inserted_box = {}

        def invoke():
            inserted_box["items"] = app.plan_misconception_repair(current, is_correct=False)
            return inserted_box["items"]

        self._assert_normal_survives_pretruncation(app, invoke, ["recent"], "normal")
        self.assertEqual("contrast", inserted_box["items"][0]["repair_stage"])
        self.assertEqual("Confusion pair drill", inserted_box["items"][0]["session_tag"])

    def test_repair_g_streak_rescue_still_spaces_before_limit(self):
        app = self.make_app()
        questions = [_question("current", 1, domain="Shared", topic="Shared Topic")]
        questions.extend(
            _question(f"recent-{index}", index + 1, domain="Shared", topic=f"Topic {index}") for index in range(1, 4)
        )
        questions.append(_question("normal", 5, domain="Shared", topic="Other"))
        history = [self._event(f"recent-{index}", index + 1, _at(-timedelta(hours=2))) for index in range(1, 4)]
        self._install(app, questions, history)
        records = app._progress_questions()
        for index in range(1, 4):
            records[f"recent-{index}"] = {
                "attempts": 4,
                "wrong_count": 5 - index,
                "correct_count": 0,
                "last_correct": False,
                "correct_streak": 0,
            }
        current = self._open_single(app, questions)
        app.session_answer_history = [
            {"question_id": "current", "question_number": 1, "domain": "Shared", "correct": False},
            {"question_id": "current", "question_number": 1, "domain": "Shared", "correct": False},
        ]
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_trigger_streak_rescue(current),
            ["recent-1", "recent-2", "recent-3"],
            "normal",
        )

    def test_repair_h_non_insertable_normal_does_not_block_fallback(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("blocked-normal", 2, domain="Shared", topic="Shared Topic"),
            _question("legal-recent", 3, domain="Shared", topic="Shared Topic"),
        ]
        self._install(app, questions, [self._event("legal-recent", 3, _at(-timedelta(hours=2)))])
        app._progress_questions()["blocked-normal"] = self._weak_record()
        current = self._open_single(app, questions)

        def fake_revalidate(question, action="RENDER"):
            role = "NOT_ELIGIBLE" if question.get("id") == "blocked-normal" else "TRAIN"
            return type("EligibilityDecision", (), {"role": role})()

        with mock.patch("app_question_flow_mixin.revalidate_training_question", side_effect=fake_revalidate):
            captured, inserted = self._capture_followup_class(app, lambda: app.maybe_queue_question_twins(current))
        self.assertLess(captured["ids"].index("blocked-normal"), captured["ids"].index("legal-recent"))
        self.assertEqual(["legal-recent"], [item["id"] for item in inserted])

    def _target6_questions(self):
        return [
            _question("kept", 1, domain="Domain A", topic="A", objective="1.1"),
            _question("recent", 2, domain="Domain B", topic="B", objective="2.1"),
            _question("relaxed", 3, domain="Domain C", topic="C", objective="3.1"),
        ]

    def test_repair_i_target6_uses_next_tier_instead_of_recent_fallback(self):
        app = self.make_app()
        questions = self._target6_questions()
        moment = datetime.now().replace(microsecond=0)
        self._install(app, questions, [self._event("recent", 2, (moment - timedelta(hours=24)).isoformat())])
        app.smart_practice_evaluation_time = moment
        records = app._progress_questions()
        records["recent"] = self._weak_record()
        records["relaxed"] = {"attempts": 0, "last_seen": (date.today() + timedelta(days=1)).isoformat()}
        pool = [question["id"] for question in app.build_smart_practice_pool("2", randomize=False)]
        self.assertEqual({"kept", "relaxed"}, set(pool))
        self.assertNotIn("recent", pool)
        app.smart_practice_builder_context_fingerprint = "builder-frozen"
        app.smart_practice_bank_content_fingerprint = app.current_bank_fingerprint()
        app.smart_practice_pool_cache = {}
        app.smart_practice_signal_cache_key = None
        snapshot = app._smart_practice_worker_snapshot(base_pool=list(questions))
        foreground = [
            question["id"]
            for question in app.build_smart_practice_pool("2", randomize=False, base_pool=list(questions))
        ]
        detached = build_detached_pool(type(app), snapshot, count="2", randomize=False, base_pool=list(questions))
        self.assertEqual(foreground, [question["id"] for question in detached])
        self.assertEqual({"kept", "relaxed"}, set(foreground))

    def test_repair_j_target6_respects_downstream_membership_constraint(self):
        app = self.make_app()
        questions = [
            _question("dup", 1, domain="Domain A", topic="A", objective="1.1"),
            _question("dup", 2, domain="Domain B", topic="B", objective="2.1"),
            _question("other", 3, domain="Domain C", topic="C", objective="3.1"),
            _question("recent", 4, domain="Domain D", topic="D", objective="4.1"),
        ]
        moment = datetime.now().replace(microsecond=0)
        self._install(app, questions, [self._event("recent", 4, (moment - timedelta(hours=24)).isoformat())])
        app.smart_practice_evaluation_time = moment
        records = app._progress_questions()
        records["recent"] = self._weak_record()
        records["other"] = {"attempts": 0, "last_seen": (date.today() + timedelta(days=1)).isoformat()}
        pool = [question["id"] for question in app.build_smart_practice_pool("2", randomize=False)]
        self.assertEqual(["dup", "other"], pool)
        self.assertNotIn("recent", pool)

    def test_repair_k_target6_fallback_only_after_full_tier_shortfall(self):
        app = self.make_app()
        questions = [
            _question("kept", 1, domain="Domain A", topic="A", objective="1.1"),
            _question("newer", 2, domain="Domain B", topic="B", objective="2.1"),
            _question("older", 3, domain="Domain C", topic="C", objective="3.1"),
        ]
        moment = datetime.now().replace(microsecond=0)
        self._install(
            app,
            questions,
            [
                self._event("newer", 2, (moment - timedelta(hours=5)).isoformat()),
                self._event("older", 3, (moment - timedelta(hours=40)).isoformat()),
            ],
        )
        app.smart_practice_evaluation_time = moment
        app._progress_questions()["newer"] = self._weak_record()
        pool = [question["id"] for question in app.build_smart_practice_pool("2", randomize=False)]
        self.assertEqual(["kept", "older"], pool)

    def test_repair_l_invalid_chronology_stays_fail_closed(self):
        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("invalid-a", 2, domain="Shared", topic="Shared Topic"),
            _question("invalid-b", 3, domain="Shared", topic="Shared Topic"),
            _question("normal", 4, domain="Shared", topic="Shared Topic"),
        ]
        self._install(
            app,
            questions,
            [
                self._event("invalid-a", 2, "not-a-timestamp"),
                self._event("invalid-b", 3, "also-bad"),
            ],
        )
        records = app._progress_questions()
        records["invalid-a"] = self._weak_record()
        records["invalid-b"] = self._weak_record()
        current = self._open_single(app, questions)
        self._assert_normal_survives_pretruncation(
            app,
            lambda: app.maybe_queue_question_twins(current),
            ["invalid-a", "invalid-b"],
            "normal",
        )
        summary = _summary(questions[1], [{"at": "not-a-timestamp", "question_id": "invalid-a"}])
        self.assertEqual(EXPOSURE_INVALID, summary.status)
        self.assertNotEqual(EXPOSURE_NEVER, summary.status)

        app = self.make_app()
        questions = [
            _question("current", 1, domain="Shared", topic="Shared Topic"),
            _question("invalid", 2, domain="Shared", topic="Shared Topic"),
            _question("recent", 3, domain="Shared", topic="Shared Topic"),
        ]
        for question in questions:
            question["choices"] = {"A": "Approved (RIGHT)", "B": "Rejected (WRONG)"}
            question["prompt"] = f"{question['prompt']} RIGHT WRONG"
        self._install(
            app,
            questions,
            [
                self._event("invalid", 2, "not-a-timestamp"),
                self._event("recent", 3, _at(-timedelta(hours=10))),
            ],
        )
        app._progress_questions()["invalid"] = self._weak_record()
        current = self._open_single(app, questions)
        wrong_letter = next(letter for letter in current["choices"] if letter not in set(current.get("correct") or []))
        current["selected"] = [wrong_letter]
        captured, inserted = self._capture_followup_class(app, lambda: app.maybe_queue_confusion_pair_drill(current))
        self.assertLess(captured["ids"].index("invalid"), captured["ids"].index("recent"))
        self.assertEqual(["recent"], [item["id"] for item in inserted])

        app = self.make_app()
        questions = [
            _question("kept", 1, domain="Domain A", topic="A", objective="1.1"),
            _question("invalid", 2, domain="Domain B", topic="B", objective="2.1"),
            _question("relaxed", 3, domain="Domain C", topic="C", objective="3.1"),
        ]
        self._install(app, questions, [self._event("invalid", 2, "not-a-timestamp")])
        app._progress_questions()["relaxed"] = {
            "attempts": 0,
            "last_seen": (date.today() + timedelta(days=1)).isoformat(),
        }
        pool = [question["id"] for question in app.build_smart_practice_pool("2", randomize=False)]
        self.assertEqual({"kept", "relaxed"}, set(pool))
        self.assertNotIn("invalid", pool)

    def test_repair_m_repaired_paths_are_deterministic(self):
        def twin_ids():
            app = self.make_app()
            questions = [
                _question("current", 1, domain="Shared", topic="Shared Topic"),
                _question("recent-a", 2, domain="Shared", topic="Shared Topic"),
                _question("recent-b", 3, domain="Shared", topic="Shared Topic"),
                _question("normal", 4, domain="Shared", topic="Shared Topic"),
            ]
            self._install(
                app,
                questions,
                [
                    self._event("recent-a", 2, _at(-timedelta(hours=2))),
                    self._event("recent-b", 3, _at(-timedelta(hours=3))),
                ],
            )
            records = app._progress_questions()
            records["recent-a"] = self._weak_record()
            records["recent-b"] = self._weak_record()
            self._open_single(app, questions)
            return [item["id"] for item in app.maybe_queue_question_twins(app.questions[0])]

        self.assertEqual(twin_ids(), twin_ids())

        def pool_ids():
            app = self.make_app()
            questions = self._target6_questions()
            moment = datetime.now().replace(microsecond=0)
            self._install(app, questions, [self._event("recent", 2, (moment - timedelta(hours=24)).isoformat())])
            app.smart_practice_evaluation_time = moment
            records = app._progress_questions()
            records["recent"] = self._weak_record()
            records["relaxed"] = {"attempts": 0, "last_seen": (date.today() + timedelta(days=1)).isoformat()}
            first = [question["id"] for question in app.build_smart_practice_pool("2", randomize=False)]
            second = [question["id"] for question in app.build_smart_practice_pool("2", randomize=False)]
            return first, second

        first, second = pool_ids()
        self.assertEqual(first, second)
        self.assertEqual({"kept", "relaxed"}, set(first))


if __name__ == "__main__":
    unittest.main()
