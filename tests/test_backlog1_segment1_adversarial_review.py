import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

import app as app_module
import progress_store
import question_identity
from progress_models import issue_report_from_question, normalize_progress_meta
from question_identity import (
    PROGRESS_IDENTITY_KIND,
    PROGRESS_IDENTITY_VERSION,
    ProgressIdentityError,
    register_progress_identity_bank,
)
from runtime_persistence import RuntimePersistence


def question(qid, number):
    return {
        "question_id": qid,
        "question_number": number,
        "prompt": "p",
        "choices": {"A": "a"},
        "correct": ["A"],
    }


def legacy_payload(records):
    return {
        "version": 3,
        "questions": deepcopy(records),
        "history": [],
        "created_at": "2026-09-12T00:00:00",
        "updated_at": "2026-09-12T00:00:00",
    }


def canonical_payload(records):
    payload = legacy_payload(records)
    payload["progress_identity_version"] = PROGRESS_IDENTITY_VERSION
    payload["question_identity"] = PROGRESS_IDENTITY_KIND
    return payload


def persistence(root: Path):
    return RuntimePersistence(checkpoint_dir=root / "checkpoints", backup_dir=root / "backups")


def write_progress(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FakeSaveQueue:
    def cancel(self, _key):
        return None


class Backlog1Segment1AdversarialReviewTests(unittest.TestCase):
    def test_b1r_01_bare_number_reference_is_not_a_general_progress_key(self):
        register_progress_identity_bank([question("sc900-a", 27)])
        with self.assertRaisesRegex(ValueError, "MISSING_CANONICAL_QUESTION_ID"):
            progress_store.question_key({"question_number": 27})
        self.assertEqual(question_identity.resolve_registered_question_id_from_number(27), "sc900-a")

    def test_b1r_02_explicit_future_identity_schema_fails_closed(self):
        payload = legacy_payload({"27": {"attempts": 1}})
        payload["progress_identity_version"] = PROGRESS_IDENTITY_VERSION + 1
        payload["question_identity"] = PROGRESS_IDENTITY_KIND
        with self.assertRaisesRegex(ProgressIdentityError, "PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED"):
            progress_store.migrate_legacy_progress_keys(payload, [question("sc900-a", 27)])

    def test_b1r_03_malformed_legacy_progress_record_fails_before_rewrite(self):
        payload = legacy_payload({"27": ["not", "a", "record"]})
        with self.assertRaisesRegex(ProgressIdentityError, "INVALID_PROGRESS_RECORD"):
            progress_store.migrate_legacy_progress_keys(payload, [question("sc900-a", 27)])

    def test_b1r_04_read_only_legacy_lookup_does_not_require_a_canonical_id(self):
        legacy_record = {"attempts": 2}
        records = {"27": legacy_record}
        self.assertIs(
            progress_store.progress_record_for_question(records, {"question_number": 27}),
            legacy_record,
        )
        canonical_record = {"attempts": 9}
        mixed = {"27": legacy_record, "sc900-a": canonical_record}
        self.assertIs(progress_store.progress_record_for_question(mixed, question("sc900-a", 27)), canonical_record)

    def test_b1r_05_history_matching_prefers_canonical_identity_over_reused_number(self):
        old_event = {"question_id": "sc900-old", "question_number": 27}
        self.assertFalse(question_identity.history_event_matches_question(old_event, question("sc900-new", 27)))
        self.assertTrue(question_identity.history_event_matches_question(old_event, question("sc900-old", 93)))

    def test_b1r_06_legacy_history_without_id_can_still_match_by_number(self):
        legacy_event = {"question_number": 27}
        self.assertTrue(question_identity.legacy_history_event_matches_question(legacy_event, question("sc900-a", 27)))
        self.assertFalse(question_identity.legacy_history_event_matches_question(legacy_event, question("sc900-a", 93)))
        self.assertFalse(question_identity.history_event_matches_question(legacy_event, question("sc900-a", 27)))

    def test_b1r_07_backup_failure_is_reported_without_rewriting_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bank_progress.json"
            write_progress(path, legacy_payload({"27": {"attempts": 1}}))
            before = path.read_bytes()
            store = persistence(root)
            with mock.patch.object(RuntimePersistence, "backup_progress_file", side_effect=OSError("disk full")):
                loaded, backup, err = store.load_progress_with_identity_migration(path, [question("sc900-a", 27)])
            self.assertIsNone(loaded)
            self.assertIsNone(backup)
            self.assertIsInstance(err, OSError)
            self.assertEqual(path.read_bytes(), before)

    def test_b1r_08_restore_migrates_destination_without_mutating_selected_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "selected_progress.json"
            destination = root / "active_progress.json"
            original = legacy_payload({"27": {"attempts": 3}})
            write_progress(source, original)
            write_progress(destination, canonical_payload({"sc900-z": {"attempts": 1}}))
            source_before = source.read_bytes()
            loaded, backup, err = persistence(root).restore_progress_from_source(
                source, destination, [question("sc900-a", 27)]
            )
            self.assertIsNone(err)
            self.assertIsNotNone(backup)
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(loaded["questions"], {"sc900-a": {"attempts": 3}})
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), loaded)

    def test_b1r_09_failed_application_migration_blocks_later_progress_save(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bank_progress.json"
            original = legacy_payload({"27": {"attempts": 1}})
            write_progress(path, original)
            before = path.read_bytes()
            register_progress_identity_bank([question("sc900-a", 27), question("sc900-b", 27)])
            app = app_module.TestingEngineApp.__new__(app_module.TestingEngineApp)
            app.bank_path = root / "bank.json"
            app.progress_path = path
            app.persistence = persistence(root)
            app.save_queue = FakeSaveQueue()
            app.progress_data = {}
            app.last_progress_snapshot = None
            app._progress_snapshot_payload = lambda: app.progress_data
            app.auto_backup_progress = lambda: None
            app._show_bad_json_warning = lambda *_args, **_kwargs: None
            app.migrate_runtime_file = lambda *_args, **_kwargs: False
            app._progress_meta = lambda: {}
            app.normalize_progress_repair_state = lambda: False
            app.load_progress_if_present()
            self.assertTrue(app.progress_write_blocked)
            app.progress_data["questions"] = {"sc900-a": {"attempts": 9}}
            app.last_progress_snapshot = "force-save-attempt"
            app.save_progress()
            self.assertEqual(path.read_bytes(), before)

    def test_b1r_10_issue_reports_retain_canonical_identity_across_normalization(self):
        report = issue_report_from_question(
            question("sc900-a", 27), exclude_from_scoring=True, reported_at="2026-09-12T00:00:00"
        )
        self.assertEqual(report["question_id"], "sc900-a")
        normalized = normalize_progress_meta({"issue_reports": [report]})
        self.assertEqual(normalized["issue_reports"][0]["question_id"], "sc900-a")
        self.assertEqual(normalized["issue_reports"][0]["question_number"], 27)


if __name__ == "__main__":
    unittest.main()
