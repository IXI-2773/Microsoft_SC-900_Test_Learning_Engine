from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app_constants import MODE_PRACTICE
from content_revision_authority import RevisionEdge
from content_revision_migration import ContentRevisionMigrationError, MigrationFailureReason
from question_identity import question_content_fingerprint
from runtime_persistence import RuntimePersistence
from session_store import build_session_snapshot
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
            "history": [{"question_id": "change", "question_content_fingerprint": question_content_fingerprint(self.change_source), "selected_texts": ["old"]}],
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
        self.target_progress.write_text(json.dumps({**self.progress_payload, "bank_fingerprint": "e" * 64}), encoding="utf-8")
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
            answers=[_answer(selected=["A"], answered=True, flagged=True), _answer(selected=["B"], pending=["B"], answered=False)],
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


if __name__ == "__main__":
    unittest.main()
