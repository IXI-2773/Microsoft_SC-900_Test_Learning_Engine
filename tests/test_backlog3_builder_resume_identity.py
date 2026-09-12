import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app_constants import MODE_EXAM, MODE_PRACTICE
from app_session_persistence_mixin import SessionPersistenceMixin
from question_identity import canonical_question_id
from runtime_persistence import RuntimePersistence
from session_identity import bank_content_fingerprint, canonical_session_signature, ordered_question_ids
from session_store import (
    SESSION_SCHEMA_VERSION,
    build_session_snapshot,
    migrate_session_snapshot,
    session_file_path,
)


def _question(question_id: str, number: int, prompt: str = "Prompt", domain="Identity", topics=None):
    return {
        "id": question_id,
        "question_number": number,
        "prompt": prompt,
        "choices": {"A": "Alpha", "B": "Beta"},
        "correct": ["A"],
        "general_explanation": "Because.",
        "choice_explanations": {"A": "Right", "B": "Wrong"},
        "domain": domain,
        "chapter": "1",
        "subtitle": "Basics",
        "question_type": "multiple_choice",
        "topics": list(topics or ["Entra"]),
        "objective_code": "1.1",
        "study_focus": "Core",
        "choice_order": ["A", "B"],
    }


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


def _builder(
    *,
    mode=MODE_PRACTICE,
    count="50",
    source_label="Full bank",
    session_source="All",
    randomize=False,
    domain_filter="All domains",
    topic_filter="All topics",
    status_filter="All questions",
):
    return {
        "mode": mode,
        "count": count,
        "source_label": source_label,
        "session_source": session_source,
        "randomize": randomize,
        "domain_filter": domain_filter,
        "topic_filter": topic_filter,
        "status_filter": status_filter,
    }


class LabelStub:
    def configure(self, **kwargs):
        self.kwargs = kwargs


class VarStub:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeSessionApp(SessionPersistenceMixin):
    def _clone_questions(self, source):
        return copy.deepcopy(list(source or []))

    def _show_bad_json_warning(self, *args, **kwargs):
        self.warnings.append(args)

    def _progress_record(self, q, create=False):
        return None

    def _progress_questions(self):
        return {}

    def _progress_meta(self):
        return {"session_history": list(getattr(self, "session_history_entries", []) or [])}

    def _question_key(self, q):
        return canonical_question_id(q)

    def _question_correct(self, q):
        return list(q.get("correct") or [])

    def save_progress(self):
        return None

    def refresh_session_quests(self):
        return None

    def refresh_reward_badges(self):
        return None

    def set_flag_by_question_number(self, *args, **kwargs):
        return None

    def set_suspended_by_question_number(self, *args, **kwargs):
        return None

    def flush_scheduled_session_save(self):
        return None

    def flush_scheduled_progress_save(self):
        return None

    def _apply_adaptive_answer_order(self, pool):
        return list(pool)

    def choose_session_quests(self):
        return None

    def clear_reward_banner(self):
        return None

    def set_sidebar_visible(self, visible):
        return None

    def render_question(self):
        return None

    def get_session_builder_pool(self):
        return list(self.master_questions)

    def normalize_session_source(self, value):
        return str(value or "All") or "All"

    def normalize_status_filter(self, value):
        return str(value or "All questions") or "All questions"

    def current_builder_source_label(self, mode=None):
        return str(getattr(self, "active_source_label", "") or "Full bank")


def _make_app(root: Path, questions, *, builder=None):
    bank_path = root / "bank.json"
    if not bank_path.exists():
        bank_path.write_text("{}", encoding="utf-8")
    app = FakeSessionApp()
    app.user_data_dir = root
    app.bank_path = bank_path
    app.active_session_mode = MODE_PRACTICE
    app.active_source_label = "Full bank"
    app.questions = copy.deepcopy(questions)
    app.master_questions = copy.deepcopy(questions)
    app.session_restore_question_numbers = [q["question_number"] for q in app.questions]
    app.session_restore_question_ids = ordered_question_ids(app.questions)
    app.persistence = RuntimePersistence(
        checkpoint_dir=root / "checkpoints",
        backup_dir=root / "backups",
    )
    app.persistence.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    app.persistence.backup_dir.mkdir(parents=True, exist_ok=True)
    app.session_label = LabelStub()
    app.checkpoint_label = LabelStub()
    app.warnings = []
    app.index = 0
    app.elapsed_base = 0
    app.clock_started_at = 0
    app.checkpoints_saved = set()
    app.exam_reveal = True
    app.session_rewards = []
    app.unlocked_rewards = set()
    app.session_answer_history = []
    app.current_quests = []
    app.quest_completion_keys = set()
    app.session_boss_markers = set()
    app.session_stealth_markers = set()
    app.session_xp_gained = 0
    app.current_builder_context_data = dict(builder or {})
    app.session_base_question_count = len(app.questions)
    app.session_question_limit = len(app.questions)
    app.last_session_snapshot = None
    app.session_path = root / "session.json"
    app.session_history_entries = []
    app.answer_order_epoch = 0
    app.smart_practice_prewarm = None
    app.session_mode_var = VarStub(MODE_PRACTICE)
    app.session_count_var = VarStub("50")
    app.session_source_var = VarStub("All")
    app.session_random_var = VarStub(False)
    app.domain_filter_var = VarStub("All domains")
    app.topic_filter_var = VarStub("All topics")
    app.status_filter_var = VarStub("All questions")
    return app


def _snapshot_for(questions, builder, *, answers=None, **overrides):
    ids = ordered_question_ids(questions)
    fingerprint = bank_content_fingerprint(questions)
    payload = dict(
        app_version="test",
        bank_file="bank.json",
        mode=builder["mode"],
        builder_context=builder,
        source_label=builder["source_label"],
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
        answers=list(answers or [_blank_answer() for _ in questions]),
    )
    payload.update(overrides)
    return build_session_snapshot(**payload)


class Backlog3CanonicalIdentityTests(unittest.TestCase):
    def test_b3_001_identical_builder_requests_normalize_identically(self):
        from builder_identity import normalize_builder_context

        first = normalize_builder_context(None, **_builder())
        second = normalize_builder_context(dict(_builder()), mode=MODE_PRACTICE, count="50")
        self.assertEqual(first, second)

    def test_b3_002_randomize_true_survives_wrapper_normalization(self):
        questions = [_question("Q-A", 1), _question("Q-B", 2)]
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), questions)
            ctx = app.normalize_builder_context(_builder(randomize=False), randomize=True)
        self.assertTrue(ctx["randomize"])

    def test_b3_003_randomize_false_survives_wrapper_normalization(self):
        questions = [_question("Q-A", 1), _question("Q-B", 2)]
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), questions)
            ctx = app.normalize_builder_context(_builder(randomize=True), randomize=False)
        self.assertFalse(ctx["randomize"])

    def test_b3_004_randomize_true_and_false_produce_different_canonical_contexts(self):
        from builder_identity import normalize_builder_context

        true_ctx = normalize_builder_context(None, **_builder(randomize=True))
        false_ctx = normalize_builder_context(None, **_builder(randomize=False))
        self.assertNotEqual(true_ctx, false_ctx)
        self.assertTrue(true_ctx["randomize"])
        self.assertFalse(false_ctx["randomize"])

    def test_b3_005_randomize_true_and_false_produce_different_builder_fingerprints(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        true_fp = builder_context_fingerprint(normalize_builder_context(None, **_builder(randomize=True)))
        false_fp = builder_context_fingerprint(normalize_builder_context(None, **_builder(randomize=False)))
        self.assertNotEqual(true_fp, false_fp)

    def test_b3_006_explicit_false_is_not_overwritten_by_truthiness(self):
        from builder_identity import normalize_builder_context

        ctx = normalize_builder_context({"randomize": True, "mode": MODE_PRACTICE, "count": "50"}, randomize=False)
        self.assertFalse(ctx["randomize"])

    def test_b3_007_to_b3_013_material_fields_change_fingerprint(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        base = builder_context_fingerprint(normalize_builder_context(None, **_builder()))
        variants = {
            "mode": _builder(mode=MODE_EXAM),
            "count": _builder(count="25"),
            "source_label": _builder(source_label="Previously wrong"),
            "session_source": _builder(session_source="Unseen"),
            "domain_filter": _builder(domain_filter="Compliance"),
            "topic_filter": _builder(topic_filter="Identity"),
            "status_filter": _builder(status_filter="Flagged"),
        }
        for field, payload in variants.items():
            with self.subTest(field=field):
                changed = builder_context_fingerprint(normalize_builder_context(None, **payload))
                self.assertNotEqual(base, changed)

    def test_b3_008_all_visible_does_not_collapse_to_matching_numeric_count(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        all_visible = builder_context_fingerprint(normalize_builder_context(None, **_builder(count="All visible")))
        fifty = builder_context_fingerprint(normalize_builder_context(None, **_builder(count="50")))
        self.assertNotEqual(all_visible, fifty)

    def test_b3_014_semantically_identical_normalized_input_is_stable(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        messy = normalize_builder_context(
            {
                "mode": " Practice ",
                "count": "050",
                "source_label": " Full bank ",
                "session_source": "All visible",
                "randomize": "false",
                "domain_filter": "all domains",
                "topic_filter": "  All topics ",
                "status_filter": "All questions",
            }
        )
        clean = normalize_builder_context(None, **_builder(randomize=False, count="50"))
        self.assertEqual(messy, clean)
        self.assertEqual(builder_context_fingerprint(messy), builder_context_fingerprint(clean))

    def test_b3_015_builder_fingerprint_is_deterministic_across_repeated_calls(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        ctx = normalize_builder_context(None, **_builder(randomize=True, count="All visible"))
        fingerprints = [builder_context_fingerprint(ctx) for _ in range(5)]
        self.assertEqual(1, len(set(fingerprints)))
        self.assertEqual(64, len(fingerprints[0]))


class Backlog3SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.questions = [_question("Q-A", 1, "Alpha?"), _question("Q-B", 2, "Beta?")]

    def test_b3_016_017_018_snapshot_persists_canonical_builder_identity(self):
        from builder_identity import (
            BUILDER_IDENTITY_KIND,
            BUILDER_IDENTITY_VERSION,
            builder_context_fingerprint,
            normalize_builder_context,
        )

        builder = _builder(randomize=True, count="All visible")
        snapshot = _snapshot_for(self.questions, builder)
        canonical = normalize_builder_context(None, **builder)
        self.assertEqual(canonical, snapshot["builder_context"])
        self.assertEqual(BUILDER_IDENTITY_VERSION, snapshot["builder_identity_version"])
        self.assertEqual(BUILDER_IDENTITY_KIND, snapshot["builder_identity"])
        self.assertEqual(builder_context_fingerprint(canonical), snapshot["builder_context_fingerprint"])
        self.assertEqual(SESSION_SCHEMA_VERSION, snapshot["schema_version"])

    def test_b3_019_snapshot_fingerprint_validates_against_stored_context(self):
        snapshot = _snapshot_for(self.questions, _builder(randomize=True))
        migrated = migrate_session_snapshot(
            snapshot,
            MODE_PRACTICE,
            [1, 2],
            bank_fingerprint=snapshot["bank_fingerprint"],
            available_question_ids=snapshot["question_ids"],
        )
        self.assertEqual(snapshot["builder_context_fingerprint"], migrated["builder_context_fingerprint"])

    def test_b3_020_tampered_builder_context_with_unchanged_fingerprint_fails_closed(self):
        snapshot = _snapshot_for(self.questions, _builder(randomize=False))
        snapshot["builder_context"] = dict(snapshot["builder_context"], randomize=True)
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                snapshot,
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint=snapshot["bank_fingerprint"],
                available_question_ids=snapshot["question_ids"],
            )

    def test_b3_021_tampered_fingerprint_fails_closed(self):
        snapshot = _snapshot_for(self.questions, _builder(randomize=False))
        snapshot["builder_context_fingerprint"] = "0" * 64
        with self.assertRaises(ValueError):
            migrate_session_snapshot(
                snapshot,
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint=snapshot["bank_fingerprint"],
                available_question_ids=snapshot["question_ids"],
            )


class Backlog3ResumeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.questions = [_question("Q-A", 1, "Alpha?"), _question("Q-B", 2, "Beta?")]

    def _write_resumable(self, app, builder, *, name=None, mtime=None):
        snapshot = _snapshot_for(self.questions, builder)
        path = app.session_file_for_bank(
            app.bank_path,
            mode=builder["mode"],
            questions=self.questions,
            builder_context=builder,
        )
        if name:
            path = app.user_data_dir / name
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path, snapshot

    def test_b3_022_randomized_request_cannot_resume_ordered_snapshot(self):
        app = _make_app(self.root, self.questions)
        self._write_resumable(app, _builder(randomize=False))
        self.assertIsNone(app.find_resumable_session_for_builder(_builder(randomize=True)))

    def test_b3_023_ordered_request_cannot_resume_randomized_snapshot(self):
        app = _make_app(self.root, self.questions)
        self._write_resumable(app, _builder(randomize=True))
        self.assertIsNone(app.find_resumable_session_for_builder(_builder(randomize=False)))

    def test_b3_024_to_b3_029_cross_field_resume_isolation(self):
        app = _make_app(self.root, self.questions)
        saved = _builder(randomize=False)
        self._write_resumable(app, saved)
        mismatches = [
            _builder(domain_filter="Compliance"),
            _builder(topic_filter="Governance"),
            _builder(status_filter="Flagged"),
            _builder(source_label="Unseen", session_source="Unseen"),
            _builder(mode=MODE_EXAM),
            _builder(count="25"),
        ]
        for request in mismatches:
            with self.subTest(request=request):
                self.assertIsNone(app.find_resumable_session_for_builder(request))

    def test_b3_030_ordered_cleanup_does_not_delete_randomized_resumable(self):
        app = _make_app(self.root, self.questions)
        path, _snapshot = self._write_resumable(app, _builder(randomize=True))
        removed = app.clear_resumable_sessions_for_builder(_builder(randomize=False))
        self.assertEqual(0, removed)
        self.assertTrue(path.exists())

    def test_b3_031_randomized_cleanup_does_not_delete_ordered_resumable(self):
        app = _make_app(self.root, self.questions)
        path, _snapshot = self._write_resumable(app, _builder(randomize=False))
        removed = app.clear_resumable_sessions_for_builder(_builder(randomize=True))
        self.assertEqual(0, removed)
        self.assertTrue(path.exists())

    def test_b3_032_to_b3_037_cleanup_isolation(self):
        app = _make_app(self.root, self.questions)
        saved = _builder(randomize=False)
        path, _snapshot = self._write_resumable(app, saved)
        cleanups = [
            _builder(domain_filter="Compliance"),
            _builder(topic_filter="Governance"),
            _builder(status_filter="Flagged"),
            _builder(source_label="Unseen", session_source="Unseen"),
            _builder(mode=MODE_EXAM),
            _builder(count="25"),
        ]
        for request in cleanups:
            with self.subTest(request=request):
                removed = app.clear_resumable_sessions_for_builder(request)
                self.assertEqual(0, removed)
                self.assertTrue(path.exists())

    def test_b3_038_mtime_ignored_across_different_builder_identities(self):
        app = _make_app(self.root, self.questions)
        older, _snapshot = self._write_resumable(
            app,
            _builder(randomize=False),
            name=f"{app.runtime_bank_stem(app.bank_path)}_practice_session_2_old.json",
            mtime=1_700_000_000,
        )
        newer, _snapshot = self._write_resumable(
            app,
            _builder(randomize=True),
            name=f"{app.runtime_bank_stem(app.bank_path)}_practice_session_2_new.json",
            mtime=1_800_000_000,
        )
        found = app.find_resumable_session_for_builder(_builder(randomize=False))
        self.assertEqual(older.resolve(), found.resolve())
        self.assertNotEqual(newer.resolve(), found.resolve())

    def test_b3_039_mtime_selects_newest_only_among_equivalent_identities(self):
        app = _make_app(self.root, self.questions)
        older, _snapshot = self._write_resumable(
            app,
            _builder(randomize=True),
            name=f"{app.runtime_bank_stem(app.bank_path)}_practice_session_2_older.json",
            mtime=1_700_000_000,
        )
        newer, _snapshot = self._write_resumable(
            app,
            _builder(randomize=True),
            name=f"{app.runtime_bank_stem(app.bank_path)}_practice_session_2_newer.json",
            mtime=1_800_000_000,
        )
        found = app.find_resumable_session_for_builder(_builder(randomize=True))
        self.assertEqual(newer.resolve(), found.resolve())
        self.assertNotEqual(older.resolve(), found.resolve())


class Backlog3LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.questions = [_question("Q-A", 1, "Alpha?"), _question("Q-B", 2, "Beta?")]
        self.fingerprint = bank_content_fingerprint(self.questions)
        self.ids = ordered_question_ids(self.questions)

    def _legacy_canonical(self, builder_context):
        return {
            "schema_version": 4,
            "app_version": "test",
            "bank_file": "bank.json",
            "session_identity_version": 1,
            "session_identity": "canonical_question_id+bank_fingerprint",
            "bank_fingerprint": self.fingerprint,
            "question_ids": self.ids,
            "restore_question_ids": self.ids,
            "mode": MODE_PRACTICE,
            "builder_context": builder_context,
            "source_label": "Full bank",
            "question_count": 2,
            "question_numbers": [1, 2],
            "restore_question_numbers": [1, 2],
            "session_base_question_count": 2,
            "session_question_limit": 2,
            "restore_signature": canonical_session_signature(MODE_PRACTICE, self.fingerprint, self.ids),
            "session_signature": canonical_session_signature(MODE_PRACTICE, self.fingerprint, self.ids),
            "current_index": 0,
            "elapsed_seconds": 0,
            "exam_reveal": True,
            "checkpoints_saved": [],
            "session_rewards": [],
            "unlocked_rewards": [],
            "session_answer_history": [],
            "current_quests": [],
            "quest_completion_keys": [],
            "session_boss_markers": [],
            "session_stealth_markers": [],
            "session_xp_gained": 0,
            "answers": [
                dict(_blank_answer(), question_id="Q-A"),
                dict(_blank_answer(), question_id="Q-B"),
            ],
        }

    def test_b3_040_legacy_complete_builder_context_migrates_deterministically(self):
        from builder_identity import BUILDER_IDENTITY_MIGRATED, builder_context_fingerprint, normalize_builder_context

        raw = self._legacy_canonical(_builder(randomize=True))
        migrated = migrate_session_snapshot(
            raw,
            MODE_PRACTICE,
            [1, 2],
            bank_fingerprint=self.fingerprint,
            available_question_ids=self.ids,
        )
        canonical = normalize_builder_context(None, **_builder(randomize=True))
        self.assertEqual(canonical, migrated["builder_context"])
        self.assertEqual(builder_context_fingerprint(canonical), migrated["builder_context_fingerprint"])
        self.assertEqual(BUILDER_IDENTITY_MIGRATED, migrated["builder_identity_status"])

    def test_b3_041_legacy_explicit_randomize_true_preserves_true(self):
        raw = self._legacy_canonical(_builder(randomize=True))
        migrated = migrate_session_snapshot(
            raw,
            MODE_PRACTICE,
            [1, 2],
            bank_fingerprint=self.fingerprint,
            available_question_ids=self.ids,
        )
        self.assertTrue(migrated["builder_context"]["randomize"])

    def test_b3_042_legacy_explicit_randomize_false_preserves_false(self):
        raw = self._legacy_canonical(_builder(randomize=False))
        migrated = migrate_session_snapshot(
            raw,
            MODE_PRACTICE,
            [1, 2],
            bank_fingerprint=self.fingerprint,
            available_question_ids=self.ids,
        )
        self.assertFalse(migrated["builder_context"]["randomize"])

    def test_b3_043_legacy_missing_randomize_defaults_to_false(self):
        from builder_identity import BUILDER_IDENTITY_LEGACY_DEFAULTED

        builder = _builder(randomize=False)
        builder.pop("randomize")
        raw = self._legacy_canonical(builder)
        migrated = migrate_session_snapshot(
            raw,
            MODE_PRACTICE,
            [1, 2],
            bank_fingerprint=self.fingerprint,
            available_question_ids=self.ids,
        )
        self.assertFalse(migrated["builder_context"]["randomize"])
        self.assertEqual(BUILDER_IDENTITY_LEGACY_DEFAULTED, migrated["builder_identity_status"])

    def test_b3_044_ambiguous_legacy_builder_identity_does_not_cross_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), self.questions)
            raw = self._legacy_canonical(None)
            raw.pop("builder_context", None)
            path = app.user_data_dir / f"{app.runtime_bank_stem(app.bank_path)}_practice_session_2_ambiguous.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            self.assertIsNone(app.find_resumable_session_for_builder(_builder(randomize=False)))
            self.assertIsNone(app.find_resumable_session_for_builder(_builder(randomize=True)))
            self.assertTrue(path.exists())

    def test_b3_045_ambiguous_legacy_is_not_deleted_by_unrelated_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), self.questions)
            raw = self._legacy_canonical(None)
            raw.pop("builder_context", None)
            path = app.user_data_dir / f"{app.runtime_bank_stem(app.bank_path)}_practice_session_2_ambiguous.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            removed = app.clear_resumable_sessions_for_builder(_builder(randomize=False))
            self.assertEqual(0, removed)
            self.assertTrue(path.exists())


class Backlog3UiAndCoexistenceTests(unittest.TestCase):
    def setUp(self):
        self.questions = [_question("Q-A", 1, "Alpha?"), _question("Q-B", 2, "Beta?")]

    def test_b3_046_047_builder_ui_round_trip_preserves_randomize_and_filters(self):
        from builder_identity import builder_ui_state_from_context, normalize_builder_context

        canonical = normalize_builder_context(
            None,
            **_builder(
                randomize=True,
                count="All visible",
                domain_filter="Compliance",
                topic_filter="Governance",
                status_filter="Flagged",
                session_source="Unseen",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), self.questions)
            app.restore_builder_ui_from_context(canonical)
            self.assertTrue(app.session_random_var.get())
            self.assertEqual("All visible", app.session_count_var.get())
            self.assertEqual("Compliance", app.domain_filter_var.get())
            self.assertEqual("Governance", app.topic_filter_var.get())
            self.assertEqual("Flagged", app.status_filter_var.get())
            self.assertEqual("Unseen", app.session_source_var.get())
        state = builder_ui_state_from_context(canonical)
        self.assertTrue(state["randomize"])
        self.assertEqual("Compliance", state["domain_filter"])

    def test_b3_048_049_builder_identity_coexists_with_backlog1_authorities(self):
        snapshot = _snapshot_for(self.questions, _builder(randomize=True))
        self.assertTrue(snapshot["bank_fingerprint"])
        self.assertEqual(["Q-A", "Q-B"], snapshot["question_ids"])
        self.assertTrue(snapshot["builder_context_fingerprint"])
        self.assertNotEqual(snapshot["bank_fingerprint"], snapshot["builder_context_fingerprint"])
        self.assertNotEqual(snapshot["session_signature"], snapshot["builder_context_fingerprint"][:24])

    def test_b3_050_question_number_changes_are_not_builder_identity(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        ctx = normalize_builder_context(None, **_builder())
        fingerprint = builder_context_fingerprint(ctx)
        self.assertNotIn("question_number", ctx)
        self.assertEqual(fingerprint, builder_context_fingerprint(dict(ctx)))

    def test_b3_051_restore_with_valid_builder_bank_and_question_identity_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), self.questions, builder=_builder(randomize=True))
            snapshot = _snapshot_for(self.questions, _builder(randomize=True))
            app.session_path.write_text(json.dumps(snapshot), encoding="utf-8")
            app.load_session_if_present()
            self.assertEqual(["Q-A", "Q-B"], ordered_question_ids(app.questions))
            self.assertTrue(app.current_builder_context_data["randomize"])

    def test_b3_052_builder_identity_cannot_override_bank_fingerprint_mismatch(self):
        snapshot = _snapshot_for(self.questions, _builder(randomize=True))
        changed = copy.deepcopy(self.questions)
        changed[0]["prompt"] = "Different content"
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), changed, builder=_builder(randomize=True))
            app.session_path.write_text(json.dumps(snapshot), encoding="utf-8")
            before = ordered_question_ids(app.questions)
            app.load_session_if_present()
            self.assertEqual(before, ordered_question_ids(app.questions))

    def test_b3_053_builder_identity_cannot_override_question_identity_mismatch(self):
        snapshot = _snapshot_for(self.questions, _builder(randomize=True))
        other = [_question("Q-C", 1, "Gamma?"), _question("Q-D", 2, "Delta?")]
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), other, builder=_builder(randomize=True))
            app.session_path.write_text(json.dumps(snapshot), encoding="utf-8")
            app.load_session_if_present()
            self.assertEqual(["Q-C", "Q-D"], ordered_question_ids(app.questions))

    def test_b3_054_same_question_set_different_builder_remains_distinct(self):
        from builder_identity import builder_context_fingerprint, normalize_builder_context

        ordered = normalize_builder_context(None, **_builder(randomize=False, domain_filter="All domains"))
        filtered = normalize_builder_context(None, **_builder(randomize=False, domain_filter="Identity"))
        self.assertNotEqual(builder_context_fingerprint(ordered), builder_context_fingerprint(filtered))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ordered_path = session_file_path(
                root,
                root / "bank.json",
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint="abc",
                question_ids=["Q-A", "Q-B"],
                builder_context_fingerprint=builder_context_fingerprint(ordered),
            )
            filtered_path = session_file_path(
                root,
                root / "bank.json",
                MODE_PRACTICE,
                [1, 2],
                bank_fingerprint="abc",
                question_ids=["Q-A", "Q-B"],
                builder_context_fingerprint=builder_context_fingerprint(filtered),
            )
            self.assertNotEqual(ordered_path.name, filtered_path.name)
            self.assertIn(builder_context_fingerprint(ordered)[:12], ordered_path.name)

    def test_b3_061_cand_path_keeps_question_number_file_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), self.questions, builder=_builder(randomize=True))
            with mock.patch("app_session_persistence_mixin.is_cand01r3_active", return_value=True):
                path = app.session_file_for_bank(app.bank_path, mode=MODE_PRACTICE, questions=self.questions)
            self.assertNotIn("_" + "0" * 12, path.name)
            from builder_identity import builder_context_fingerprint, normalize_builder_context

            fingerprint = builder_context_fingerprint(normalize_builder_context(None, **_builder(randomize=True)))
            self.assertNotIn(fingerprint[:12], path.name)

    def test_b3_062_cand_active_path_does_not_inherit_ordinary_randomize_identity(self):
        from builder_identity import canonical_builder_identity

        identity = canonical_builder_identity(None, **_builder(randomize=True))
        self.assertTrue(identity["builder_context"]["randomize"])
        with tempfile.TemporaryDirectory() as tmp:
            app = _make_app(Path(tmp), self.questions)
            with mock.patch("app_session_persistence_mixin.is_cand01r3_active", return_value=True):
                path = app.session_file_for_bank(app.bank_path, mode=MODE_PRACTICE, questions=self.questions)
            self.assertNotIn(identity["builder_context_fingerprint"][:12], path.name)

    def test_b3_063_pr13_artifacts_remain_absent(self):
        root = Path(__file__).resolve().parents[1]
        forbidden_names = (
            "measurement_day1.py",
            "cand01r3_day1.py",
            "start_day1.py",
        )
        for name in forbidden_names:
            self.assertFalse((root / name).exists(), name)
        runtime = (root / "cand01r3_runtime.py").read_text(encoding="utf-8")
        self.assertNotIn("DAY1_STARTED", runtime)
        self.assertNotIn("begin_day_1", runtime)


if __name__ == "__main__":
    unittest.main()
