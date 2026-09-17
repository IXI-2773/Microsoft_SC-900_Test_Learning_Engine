from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app_constants import MODE_PRACTICE
from content_revision_authority import AdmissionResult, AdmissionStatus, RevisionEdge, RevisionFailureReason
from content_revision_migration import ContentRevisionMigrationError, MigrationFailureReason
from question_identity import (
    canonical_question_history_map,
    question_content_fingerprint,
    registered_progress_identity_bank,
)
from runtime_persistence import RuntimePersistence
from session_store import build_session_snapshot, progress_file_path
from tests.test_content_revision_migration import _answer, _question, _record, _revision


class ContentRevisionPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.persistence = RuntimePersistence(checkpoint_dir=root / "checkpoints", backup_dir=root / "backups")
        self.keep_source = _question("keep", number=1)
        self.keep_target = copy.deepcopy(self.keep_source)
        self.change_source = _question("change", choice_b="beta", number=2)
        self.change_target = _question("change", choice_b="beta rebalanced", number=2)
        self.source_questions = [self.keep_source, self.change_source]
        self.target_questions = [self.keep_target, self.change_target]
        self.edge = RevisionEdge(
            "change",
            question_content_fingerprint(self.change_source),
            question_content_fingerprint(self.change_target),
            "review.json",
            "d" * 64,
        )
        self.revision = _revision(self.source_questions, self.target_questions, (self.edge,))
        self.source_progress = root / "source_progress.json"
        self.target_progress = root / "target_progress.json"
        self.progress_payload = {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": self.revision.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                "keep": question_content_fingerprint(self.keep_source),
                "change": question_content_fingerprint(self.change_source),
            },
            "questions": {"keep": _record(), "change": _record()},
            "history": [
                {
                    "question_id": "change",
                    "question_content_fingerprint": question_content_fingerprint(self.change_source),
                    "selected_texts": ["old"],
                }
            ],
            "quarantined_questions": {"gone": {"reason": "CHANGED_CONTENT", "record": {"attempts": 9}}},
        }
        self.source_progress.write_text(json.dumps(self.progress_payload, indent=2), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_progress_success_archives_and_writes_target(self) -> None:
        payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(error)
        self.assertIsNotNone(payload)
        self.assertIsNotNone(archive)
        assert payload is not None and archive is not None
        self.assertEqual(self.revision.target_bank_content_fingerprint, payload["bank_fingerprint"])
        self.assertFalse(self.source_progress.exists())
        self.assertTrue(self.target_progress.exists())
        self.assertTrue(archive.exists())

    def test_progress_already_applied_no_new_backup(self) -> None:
        first = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(first[2])
        second_payload, second_archive, second_error = self.persistence.migrate_progress_across_approved_revision(
            self.target_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-18T00:00:00",
        )
        self.assertIsNone(second_error)
        self.assertIsNone(second_archive)
        self.assertEqual(first[0]["content_revision_lineage"], second_payload["content_revision_lineage"])

    def test_progress_archive_failure_preserves_source(self) -> None:
        original = self.source_progress.read_bytes()
        with mock.patch.object(RuntimePersistence, "copy_file", side_effect=OSError("archive failed")):
            payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
                self.source_progress,
                self.target_progress,
                self.target_questions,
                self.revision,
                "2026-09-17T00:00:00",
            )
        self.assertIsNone(payload)
        self.assertIsNone(archive)
        self.assertIsInstance(error, OSError)
        self.assertEqual(original, self.source_progress.read_bytes())
        self.assertFalse(self.target_progress.exists())

    def test_progress_write_failure_preserves_source(self) -> None:
        original = self.source_progress.read_bytes()
        with mock.patch.object(RuntimePersistence, "write_json", side_effect=OSError("write failed")):
            payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
                self.source_progress,
                self.target_progress,
                self.target_questions,
                self.revision,
                "2026-09-17T00:00:00",
            )
        self.assertIsNone(payload)
        self.assertIsNotNone(archive)
        self.assertIsInstance(error, OSError)
        self.assertEqual(original, self.source_progress.read_bytes())
        self.assertFalse(self.target_progress.exists())

    def test_progress_same_path_archives_before_replacement(self) -> None:
        payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.source_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(error)
        self.assertTrue(self.source_progress.exists())
        self.assertIsNotNone(archive)
        assert archive is not None and payload is not None
        self.assertTrue(archive.exists())
        self.assertEqual(self.revision.target_bank_content_fingerprint, payload["bank_fingerprint"])
        archived = json.loads(archive.read_text(encoding="utf-8"))
        self.assertEqual(self.revision.source_bank_content_fingerprint, archived["bank_fingerprint"])

    def test_progress_unexpected_target_bank_fp(self) -> None:
        self.target_progress.write_text(
            json.dumps({**self.progress_payload, "bank_fingerprint": "e" * 64}), encoding="utf-8"
        )
        original_source = self.source_progress.read_bytes()
        original_target = self.target_progress.read_bytes()
        payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(payload)
        self.assertIsNone(archive)
        self.assertIsInstance(error, ContentRevisionMigrationError)
        self.assertEqual(MigrationFailureReason.UNEXPECTED_BANK_FINGERPRINT, error.reason)
        self.assertEqual(original_source, self.source_progress.read_bytes())
        self.assertEqual(original_target, self.target_progress.read_bytes())

    def test_progress_conflicting_target_preserved(self) -> None:
        other = copy.deepcopy(self.progress_payload)
        other["questions"]["keep"] = {**_record(), "attempts": 99}
        self.target_progress.write_text(json.dumps(other, indent=2), encoding="utf-8")
        original_source = self.source_progress.read_bytes()
        original_target = self.target_progress.read_bytes()
        payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(payload)
        self.assertIsInstance(error, ContentRevisionMigrationError)
        self.assertEqual(original_source, self.source_progress.read_bytes())
        self.assertEqual(original_target, self.target_progress.read_bytes())

    def test_malformed_progress_source_remains_unchanged(self) -> None:
        self.source_progress.write_bytes(b"{not json")
        original = self.source_progress.read_bytes()
        payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(payload)
        self.assertIsNone(archive)
        self.assertIsNotNone(error)
        self.assertEqual(original, self.source_progress.read_bytes())
        self.assertTrue(self.source_progress.exists())
        self.assertFalse(self.target_progress.exists())

    def test_malformed_parseable_progress_source_bytes_unchanged(self) -> None:
        broken = copy.deepcopy(self.progress_payload)
        broken["history"] = {"0": broken["history"][0]}
        self.source_progress.write_text(json.dumps(broken), encoding="utf-8")
        original = self.source_progress.read_bytes()
        payload, archive, error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(payload)
        self.assertIsNone(archive)
        self.assertIsInstance(error, ContentRevisionMigrationError)
        self.assertEqual(MigrationFailureReason.INVALID_PROGRESS_PAYLOAD, error.reason)
        self.assertEqual(original, self.source_progress.read_bytes())
        self.assertEqual(self.source_progress, Path(self.source_progress))
        self.assertFalse(self.target_progress.exists())

    def test_crash_retry_verified_target_does_not_require_matching_timestamp(self) -> None:
        original_source = self.source_progress.read_bytes()
        first_payload, first_archive, first_error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-17T00:00:00",
        )
        self.assertIsNone(first_error)
        self.assertIsNotNone(first_payload)
        self.assertIsNotNone(first_archive)
        self.assertFalse(self.source_progress.exists())
        self.source_progress.write_bytes(original_source)
        original_target = self.target_progress.read_bytes()
        retry_payload, retry_archive, retry_error = self.persistence.migrate_progress_across_approved_revision(
            self.source_progress,
            self.target_progress,
            self.target_questions,
            self.revision,
            "2026-09-18T12:00:00",
        )
        self.assertIsNone(retry_error)
        self.assertIsNotNone(retry_payload)
        self.assertFalse(self.source_progress.exists())
        self.assertEqual(original_target, self.target_progress.read_bytes())
        assert first_payload is not None and retry_payload is not None
        self.assertEqual(first_payload["content_revision_lineage"], retry_payload["content_revision_lineage"])
        self.assertEqual("2026-09-17T00:00:00", retry_payload["content_revision_lineage"][0]["migrated_at"])
        self.assertEqual(1, len(retry_payload["content_revision_lineage"]))
        self.assertIsNotNone(retry_archive)
        assert retry_archive is not None
        self.assertTrue(retry_archive.exists())


class ContentRevisionSessionPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.persistence = RuntimePersistence(checkpoint_dir=root / "checkpoints", backup_dir=root / "backups")
        keep_source = _question("keep", number=1)
        keep_target = copy.deepcopy(keep_source)
        change_source = _question("change", choice_b="beta", number=2)
        change_target = _question("change", choice_b="beta rebalanced", number=2)
        self.source_questions = [keep_source, change_source]
        self.target_questions = [keep_target, change_target]
        edge = RevisionEdge(
            "change",
            question_content_fingerprint(change_source),
            question_content_fingerprint(change_target),
            "review.json",
            "d" * 64,
        )
        self.revision = _revision(self.source_questions, self.target_questions, (edge,))
        self.snapshot = build_session_snapshot(
            app_version="test",
            bank_file="source_bank.json",
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
            bank_fingerprint=self.revision.source_bank_content_fingerprint,
            question_ids=["keep", "change"],
            restore_question_ids=["keep", "change"],
            session_base_question_count=2,
            session_question_limit=2,
            current_index=1,
            elapsed_seconds=42,
            exam_reveal=True,
            checkpoints_saved=["cp1"],
            session_rewards=["r1"],
            unlocked_rewards=["u1"],
            session_answer_history=[],
            current_quests=[],
            quest_completion_keys=["q1"],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=7,
            answers=[
                _answer(selected=["A"], answered=True, flagged=True),
                _answer(selected=["B"], pending=["B"], answered=False),
            ],
        )
        self.source_path = root / "source.session.json"
        self.target_path = root / "target.session.json"
        self.source_path.write_text(json.dumps(self.snapshot, indent=2), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _migrate(self, source=None, target=None):
        return self.persistence.migrate_session_file_across_approved_revision(
            source or self.source_path,
            target or self.target_path,
            self.target_questions,
            self.revision,
            "target_bank.json",
            source_questions=self.source_questions,
        )

    def test_session_success_source_not_target(self) -> None:
        payload, archive, error = self._migrate()
        self.assertIsNone(error)
        self.assertIsNotNone(payload)
        self.assertFalse(self.source_path.exists())
        self.assertTrue(self.target_path.exists())
        self.assertIsNotNone(archive)
        assert archive is not None
        self.assertTrue(archive.exists())

    def test_session_archive_failure_before_target_write(self) -> None:
        original = self.source_path.read_bytes()
        with mock.patch.object(RuntimePersistence, "copy_file", side_effect=OSError("archive failed")):
            payload, archive, error = self._migrate()
        self.assertIsNone(payload)
        self.assertIsInstance(error, OSError)
        self.assertEqual(original, self.source_path.read_bytes())
        self.assertFalse(self.target_path.exists())

    def test_session_write_failure_preserves_source(self) -> None:
        original = self.source_path.read_bytes()
        with mock.patch.object(RuntimePersistence, "write_json", side_effect=OSError("write failed")):
            payload, archive, error = self._migrate()
        self.assertIsNone(payload)
        self.assertIsNotNone(archive)
        self.assertIsInstance(error, OSError)
        self.assertEqual(original, self.source_path.read_bytes())
        self.assertFalse(self.target_path.exists())

    def test_session_cleanup_failure_after_verified_target_is_recoverable(self) -> None:
        with mock.patch.object(Path, "unlink", side_effect=OSError("cleanup failed")):
            payload, archive, error = self._migrate()
        self.assertIsNotNone(payload)
        self.assertIsNotNone(archive)
        self.assertIsInstance(error, OSError)
        self.assertTrue(self.target_path.exists())

    def test_session_restart_with_exact_expected_target_finishes_cleanup(self) -> None:
        first_payload, _archive, _error = self._migrate()
        self.assertIsNone(_error)
        self.source_path.write_text(json.dumps(self.snapshot, indent=2), encoding="utf-8")
        payload, archive, error = self._migrate()
        self.assertIsNone(error)
        self.assertEqual(json.dumps(first_payload, sort_keys=True), json.dumps(payload, sort_keys=True))
        self.assertFalse(self.source_path.exists())

    def test_session_existing_differing_target_preserves_both(self) -> None:
        other = copy.deepcopy(self.snapshot)
        other["elapsed_seconds"] = 999
        self.target_path.write_text(json.dumps(other, indent=2), encoding="utf-8")
        original_source = self.source_path.read_bytes()
        original_target = self.target_path.read_bytes()
        payload, archive, error = self._migrate()
        self.assertIsNone(payload)
        self.assertIsInstance(error, ContentRevisionMigrationError)
        self.assertEqual(original_source, self.source_path.read_bytes())
        self.assertEqual(original_target, self.target_path.read_bytes())

    def test_session_same_path_safety(self) -> None:
        payload, archive, error = self._migrate(target=self.source_path)
        self.assertIsNone(error)
        self.assertTrue(self.source_path.exists())
        self.assertIsNotNone(archive)
        assert archive is not None
        self.assertTrue(archive.exists())
        self.assertEqual("target_bank.json", payload["bank_file"])

    def test_malformed_session_source_remains_unchanged(self) -> None:
        self.source_path.write_bytes(b"{bad")
        original = self.source_path.read_bytes()
        payload, archive, error = self._migrate()
        self.assertIsNone(payload)
        self.assertIsNotNone(error)
        self.assertEqual(original, self.source_path.read_bytes())
        self.assertTrue(self.source_path.exists())


class ContentRevisionAppIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.user_data = self.root / "user_data"
        self.user_data.mkdir()
        self.keep_source = _question("keep", number=1)
        self.keep_target = copy.deepcopy(self.keep_source)
        self.change_source = _question("change", choice_b="beta", number=2)
        self.change_target = _question("change", choice_b="beta rebalanced", number=2)
        self.source_questions = [self.keep_source, self.change_source]
        self.target_questions = [self.keep_target, self.change_target]
        self.edge = RevisionEdge(
            "change",
            question_content_fingerprint(self.change_source),
            question_content_fingerprint(self.change_target),
            "review.json",
            "d" * 64,
        )
        self.revision = _revision(self.source_questions, self.target_questions, (self.edge,))
        self.source_bank = self.root / "source_bank.json"
        self.target_bank = self.root / "target_bank.json"
        self.source_bank.write_text(json.dumps({"title": "s", "questions": self.source_questions}), encoding="utf-8")
        self.target_bank.write_text(json.dumps({"title": "t", "questions": self.target_questions}), encoding="utf-8")
        import app as app_module

        self.app_module = app_module
        engine = app_module.TestingEngineApp.__new__(app_module.TestingEngineApp)
        engine.user_data_dir = self.user_data
        engine.persistence = RuntimePersistence(
            checkpoint_dir=self.root / "checkpoints", backup_dir=self.root / "backups"
        )
        engine.bank_path = self.target_bank
        engine.progress_path = progress_file_path(self.user_data, self.target_bank)
        engine.data = {"questions": self.target_questions}
        engine.master_questions = self.target_questions
        engine.questions = self.target_questions
        engine.content_revision_authority = None
        engine.progress_write_blocked = False
        engine.progress_data = {"history": []}
        engine.active_session_mode = MODE_PRACTICE
        self.engine = engine

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _progress_payload(self, questions, bank_fp):
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": bank_fp,
            "question_content_fingerprints": {
                question["id"]: question_content_fingerprint(question) for question in questions
            },
            "questions": {question["id"]: _record() for question in questions},
            "history": [
                {
                    "question_id": "change",
                    "question_content_fingerprint": question_content_fingerprint(self.change_source),
                    "selected_texts": ["old wording"],
                    "correct_texts": ["alpha"],
                    "correct": True,
                }
            ],
        }

    def test_empty_registry_preserves_ordinary_load_path(self) -> None:
        self.assertIsNone(self.engine.content_revision_authority)
        self.assertFalse(self.engine._apply_registered_content_revision(self.target_bank))
        self.assertIsNone(self.engine.content_revision_authority)
        self.assertFalse(self.engine.progress_write_blocked)

    def test_failed_admission_does_not_leak_into_authority(self) -> None:
        result = AdmissionResult(AdmissionStatus.FAIL, (RevisionFailureReason.SCHEMA_UNSUPPORTED,), None)
        bound = self.engine._bind_content_revision_authority(result)
        self.assertIsNone(bound)
        self.assertIsNone(self.engine.content_revision_authority)
        self.assertTrue(self.engine.progress_write_blocked)

    def test_failed_registered_admission_does_not_invoke_load_progress_if_present(self) -> None:
        fail = AdmissionResult(AdmissionStatus.FAIL, (RevisionFailureReason.REGISTRY_HASH_MISMATCH,), None)
        target_progress = progress_file_path(self.user_data, self.target_bank)
        target_progress.write_text(json.dumps(self._progress_payload(self.target_questions, "e" * 64)), encoding="utf-8")
        original = target_progress.read_bytes()
        self.engine.domain_combo = mock.MagicMock()
        self.engine.topic_combo = mock.MagicMock()
        self.engine.status_combo = mock.MagicMock()
        self.engine.status_combo.__contains__.return_value = True
        self.engine.domain_combo.__getitem__.return_value = ["All domains"]
        self.engine.topic_combo.__getitem__.return_value = ["All topics"]
        self.engine.status_combo.__getitem__.return_value = ["All questions"]
        self.engine.domain_filter_var = mock.MagicMock()
        self.engine.topic_filter_var = mock.MagicMock()
        self.engine.status_filter_var = mock.MagicMock()
        self.engine.session_source_var = mock.MagicMock()
        self.engine.config = {}
        self.engine.root = mock.MagicMock()
        self.engine.normalize_status_filter = mock.Mock(return_value="All questions")
        self.engine.normalize_session_source = mock.Mock(return_value="Full bank")
        with (
            mock.patch.object(self.app_module, "load_bank", return_value={"questions": self.target_questions}),
            mock.patch.object(self.app_module, "resolve_registered_revision_for_target", return_value=fail),
            mock.patch.object(self.engine, "load_progress_if_present") as load_progress,
            mock.patch.object(self.engine, "_clone_questions", return_value=self.target_questions),
            mock.patch.object(self.engine, "_reset_runtime_question_state"),
            mock.patch.object(self.engine, "_rebuild_followup_candidate_index"),
            mock.patch.object(self.engine, "clear_active_session"),
            mock.patch.object(self.engine, "invalidate_learning_state"),
            mock.patch.object(self.engine, "_progress_snapshot_payload", return_value={"questions": {}, "history": []}),
        ):
            self.engine.load_from_path(self.target_bank)
        load_progress.assert_not_called()
        self.assertIsNone(self.engine.content_revision_authority)
        self.assertTrue(self.engine.progress_write_blocked)
        self.assertEqual(original, target_progress.read_bytes())

    def test_incomplete_target_fingerprint_is_verified_not_skipped(self) -> None:
        target_progress = progress_file_path(self.user_data, self.target_bank)
        payload = self._progress_payload(self.source_questions, self.revision.target_bank_content_fingerprint)
        target_progress.write_text(json.dumps(payload), encoding="utf-8")
        original = target_progress.read_bytes()
        skipped = self.engine._migrate_progress_for_admitted_revision(self.revision)
        self.assertTrue(skipped)
        self.assertTrue(self.engine.progress_write_blocked)
        self.assertEqual(original, target_progress.read_bytes())

    def test_crash_retry_app_cleanup_at_different_timestamp(self) -> None:
        source_progress = progress_file_path(self.user_data, self.source_bank)
        target_progress = progress_file_path(self.user_data, self.target_bank)
        source_progress.write_text(
            json.dumps(self._progress_payload(self.source_questions, self.revision.source_bank_content_fingerprint)),
            encoding="utf-8",
        )
        self.engine.content_revision_authority = self.revision
        with mock.patch.object(self.app_module, "now_iso", return_value="2026-09-17T00:00:00"):
            self.assertFalse(self.engine._migrate_progress_for_admitted_revision(self.revision))
        original_source = json.dumps(
            self._progress_payload(self.source_questions, self.revision.source_bank_content_fingerprint)
        ).encode("utf-8")
        source_progress.write_bytes(original_source)
        target_before_retry = target_progress.read_bytes()
        with mock.patch.object(self.app_module, "now_iso", return_value="2026-09-18T12:00:00"):
            skipped = self.engine._migrate_progress_for_admitted_revision(self.revision)
        self.assertFalse(skipped)
        self.assertFalse(self.engine.progress_write_blocked)
        self.assertFalse(source_progress.exists())
        self.assertEqual(target_before_retry, target_progress.read_bytes())
        loaded = json.loads(target_progress.read_text(encoding="utf-8"))
        self.assertEqual(1, len(loaded["content_revision_lineage"]))
        self.assertEqual("2026-09-17T00:00:00", loaded["content_revision_lineage"][0]["migrated_at"])

    def test_different_filenames_migrate_source_progress(self) -> None:
        source_progress = progress_file_path(self.user_data, self.source_bank)
        source_progress.write_text(
            json.dumps(self._progress_payload(self.source_questions, self.revision.source_bank_content_fingerprint)),
            encoding="utf-8",
        )
        original = source_progress.read_bytes()
        self.engine.content_revision_authority = self.revision
        skipped = self.engine._migrate_progress_for_admitted_revision(self.revision)
        self.assertFalse(skipped)
        self.assertFalse(self.engine.progress_write_blocked)
        self.assertFalse(source_progress.exists())
        target_progress = progress_file_path(self.user_data, self.target_bank)
        self.assertTrue(target_progress.exists())
        loaded = json.loads(target_progress.read_text(encoding="utf-8"))
        self.assertEqual(self.revision.target_bank_content_fingerprint, loaded["bank_fingerprint"])
        self.assertEqual(["old wording"], loaded["history"][0]["selected_texts"])
        archive_dir_files = list(source_progress.parent.glob(f"*{source_progress.name}"))
        self.assertTrue(archive_dir_files or original)

    def test_same_path_progress_archives_before_replacement(self) -> None:
        target_progress = progress_file_path(self.user_data, self.target_bank)
        target_progress.write_text(
            json.dumps(self._progress_payload(self.source_questions, self.revision.source_bank_content_fingerprint)),
            encoding="utf-8",
        )
        skipped = self.engine._migrate_progress_for_admitted_revision(self.revision)
        self.assertFalse(skipped)
        loaded = json.loads(target_progress.read_text(encoding="utf-8"))
        self.assertEqual(self.revision.target_bank_content_fingerprint, loaded["bank_fingerprint"])
        archives = [path for path in target_progress.parent.glob(f"*.progress.{target_progress.name}")]
        self.assertTrue(archives)

    def test_unexpected_target_progress_fails_closed(self) -> None:
        target_progress = progress_file_path(self.user_data, self.target_bank)
        payload = self._progress_payload(self.source_questions, "e" * 64)
        target_progress.write_text(json.dumps(payload), encoding="utf-8")
        original = target_progress.read_bytes()
        skipped = self.engine._migrate_progress_for_admitted_revision(self.revision)
        self.assertTrue(skipped)
        self.assertTrue(self.engine.progress_write_blocked)
        self.assertEqual(original, target_progress.read_bytes())

    def test_conflicting_source_and_target_progress_preserved(self) -> None:
        source_progress = progress_file_path(self.user_data, self.source_bank)
        target_progress = progress_file_path(self.user_data, self.target_bank)
        source_payload = self._progress_payload(self.source_questions, self.revision.source_bank_content_fingerprint)
        target_payload = self._progress_payload(self.source_questions, self.revision.source_bank_content_fingerprint)
        target_payload["questions"]["keep"] = {**_record(), "attempts": 99}
        source_progress.write_text(json.dumps(source_payload), encoding="utf-8")
        target_progress.write_text(json.dumps(target_payload), encoding="utf-8")
        original_source = source_progress.read_bytes()
        original_target = target_progress.read_bytes()
        skipped = self.engine._migrate_progress_for_admitted_revision(self.revision)
        self.assertTrue(skipped)
        self.assertEqual(original_source, source_progress.read_bytes())
        self.assertEqual(original_target, target_progress.read_bytes())

    def test_target_registration_restored_after_resolution(self) -> None:
        from question_bank import load_bank
        from question_identity import canonical_question_id

        load_bank(self.target_bank)
        target_ids = [canonical_question_id(row) for row in registered_progress_identity_bank()]
        with mock.patch(
            "app.resolve_registered_revision_for_target",
            return_value=AdmissionResult(AdmissionStatus.PASS, (), self.revision),
        ):
            self.engine._apply_registered_content_revision(self.target_bank)
        restored_ids = [canonical_question_id(row) for row in registered_progress_identity_bank()]
        self.assertEqual(target_ids, restored_ids)

    def test_history_consumers_use_approved_lineage(self) -> None:
        self.engine.progress_data = {
            "history": [
                {
                    "question_id": "change",
                    "question_content_fingerprint": question_content_fingerprint(self.change_source),
                    "selected_texts": ["old wording"],
                    "correct": True,
                }
            ]
        }
        mapped = canonical_question_history_map(self.engine.progress_data["history"])
        without_authority = self.engine.revision_aware_history_events(mapped, self.change_target)
        self.assertEqual([], without_authority)
        self.engine.content_revision_authority = self.revision
        with_authority = self.engine.revision_aware_history_events(mapped, self.change_target)
        self.assertEqual(["old wording"], with_authority[0]["selected_texts"])
        volatility = self.engine.question_volatility(self.change_target)
        self.assertGreaterEqual(volatility["attempts"], 1)

    def test_source_session_discovered_only_with_authority(self) -> None:
        self.engine.content_revision_authority = None
        patterns = self.engine._session_discovery_glob_patterns(MODE_PRACTICE)
        self.assertEqual(1, len(patterns))
        self.engine.content_revision_authority = self.revision
        patterns = self.engine._session_discovery_glob_patterns(MODE_PRACTICE)
        self.assertEqual(2, len(patterns))

    def test_successful_session_migration_returns_target_path(self) -> None:
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file="source_bank.json",
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
            bank_fingerprint=self.revision.source_bank_content_fingerprint,
            question_ids=["keep", "change"],
            restore_question_ids=["keep", "change"],
            session_base_question_count=2,
            session_question_limit=2,
            current_index=0,
            elapsed_seconds=1,
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
            answers=[_answer(selected=["A"], answered=True), _answer()],
        )
        source_session = self.user_data / "source_bank_practice_session_abc.json"
        source_session.write_text(json.dumps(snapshot), encoding="utf-8")
        self.engine.content_revision_authority = self.revision
        saved, target_path, error = self.engine._maybe_migrate_authorized_session(source_session, snapshot)
        self.assertIsNone(error)
        self.assertIsNotNone(saved)
        self.assertNotEqual(source_session, target_path)
        self.assertTrue(target_path.exists())
        self.assertFalse(source_session.exists())
        self.assertEqual(self.revision.target_bank_content_fingerprint, saved["bank_fingerprint"])

    def test_session_migration_failure_preserves_source_without_quarantine(self) -> None:
        snapshot = {
            "bank_fingerprint": self.revision.source_bank_content_fingerprint,
            "mode": MODE_PRACTICE,
            "question_ids": ["keep", "change"],
            "question_numbers": [1, 2],
        }
        source_session = self.user_data / "source_bank_practice_session_bad.json"
        source_session.write_text(json.dumps(snapshot), encoding="utf-8")
        original = source_session.read_bytes()
        self.engine.content_revision_authority = self.revision
        saved, path, error = self.engine._maybe_migrate_authorized_session(source_session, snapshot)
        self.assertIsNotNone(error)
        self.assertIsNone(saved)
        self.assertEqual(original, source_session.read_bytes())
        self.assertTrue(source_session.exists())
        self.assertFalse(list(self.user_data.glob("*.bad.json")))


if __name__ == "__main__":
    unittest.main()
