import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import progress_store
from cand01r3_partition import canonical_question_id as cand01r3_canonical_question_id
from progress_store import aggregate_concept_memory, blank_progress, question_key
from question_bank import load_bank
from question_identity import (
    PROGRESS_IDENTITY_KIND,
    PROGRESS_IDENTITY_VERSION,
    ProgressIdentityError,
    canonical_question_id,
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


class Backlog1ProgressIdentityMigrationTests(unittest.TestCase):
    def test_b1_01_same_number_different_id_does_not_inherit_progress(self):
        records = {question_key(question("sc900-a", 27)): {"attempts": 4}}
        self.assertIsNone(records.get(question_key(question("sc900-b", 27))))

    def test_b1_02_stable_id_survives_renumbering(self):
        self.assertEqual(question_key(question("sc900-a", 27)), "sc900-a")
        self.assertEqual(question_key(question("sc900-a", 93)), "sc900-a")

    def test_b1_03_unique_legacy_number_migrates_to_canonical_id(self):
        migrated = progress_store.migrate_legacy_progress_keys(
            legacy_payload({"27": {"attempts": 1}}), [question("sc900-a", 27)]
        )
        self.assertEqual(migrated["questions"], {"sc900-a": {"attempts": 1}})
        self.assertEqual(migrated["progress_identity_version"], PROGRESS_IDENTITY_VERSION)
        self.assertEqual(migrated["question_identity"], PROGRESS_IDENTITY_KIND)

    def test_b1_04_migration_preserves_learner_record_contents(self):
        record = {"attempts": 3, "wrong_count": 1, "custom": {"keep": True}}
        migrated = progress_store.migrate_legacy_progress_keys(
            legacy_payload({"27": record}), [question("sc900-a", 27)]
        )
        self.assertEqual(migrated["questions"]["sc900-a"], record)

    def test_b1_05_already_canonical_progress_is_idempotent(self):
        payload = canonical_payload({"sc900-a": {"attempts": 3}})
        first = progress_store.migrate_legacy_progress_keys(payload, [question("sc900-a", 27)])
        second = progress_store.migrate_legacy_progress_keys(first, [question("sc900-a", 93)])
        self.assertEqual(first, payload)
        self.assertEqual(second, payload)

    def test_b1_06_ambiguous_legacy_number_mapping_fails_closed(self):
        bank = [question("sc900-a", 27), question("sc900-b", 27)]
        with self.assertRaisesRegex(ProgressIdentityError, "LEGACY_PROGRESS_AMBIGUOUS"):
            progress_store.migrate_legacy_progress_keys(legacy_payload({"27": {"attempts": 1}}), bank)

    def test_b1_07_duplicate_canonical_question_ids_fail_closed(self):
        bank = [question("sc900-a", 27), question("sc900-a", 93)]
        with self.assertRaisesRegex(ProgressIdentityError, "DUPLICATE_CANONICAL_QUESTION_ID"):
            progress_store.migrate_legacy_progress_keys(legacy_payload({"27": {"attempts": 1}}), bank)

    def test_b1_08_two_legacy_keys_colliding_into_one_canonical_id_fail_closed(self):
        payload = legacy_payload({"027": {"attempts": 1}, "27": {"attempts": 2}})
        with self.assertRaisesRegex(ProgressIdentityError, "LEGACY_PROGRESS_COLLISION"):
            progress_store.migrate_legacy_progress_keys(payload, [question("sc900-a", 27)])

    def test_b1_09_unmapped_legacy_question_number_fails_closed(self):
        with self.assertRaisesRegex(ProgressIdentityError, "LEGACY_PROGRESS_UNMAPPED"):
            progress_store.migrate_legacy_progress_keys(
                legacy_payload({"999": {"attempts": 1}}), [question("sc900-a", 27)]
            )

    def test_b1_10_persistent_migration_failure_leaves_original_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bank_progress.json"
            original = legacy_payload({"27": {"attempts": 1}})
            write_progress(path, original)
            before = path.read_bytes()
            loaded, backup, err = persistence(root).load_progress_with_identity_migration(
                path, [question("sc900-a", 27), question("sc900-b", 27)]
            )
            self.assertIsNone(loaded)
            self.assertIsNone(backup)
            self.assertIsInstance(err, ProgressIdentityError)
            self.assertEqual(path.read_bytes(), before)

    def test_b1_11_successful_migration_backs_up_original_before_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bank_progress.json"
            original = legacy_payload({"27": {"attempts": 1}})
            write_progress(path, original)
            loaded, backup, err = persistence(root).load_progress_with_identity_migration(
                path, [question("sc900-a", 27)]
            )
            self.assertIsNone(err)
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertTrue(backup.exists())
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), original)
            self.assertEqual(loaded, json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual(loaded["questions"], {"sc900-a": {"attempts": 1}})

    def test_b1_12_new_progress_writes_use_canonical_question_id(self):
        self.assertEqual(question_key(question("sc900-a", 27)), "sc900-a")

    def test_b1_13_missing_canonical_id_never_falls_back_to_question_number(self):
        with self.assertRaisesRegex(ValueError, "MISSING_CANONICAL_QUESTION_ID"):
            question_key({"question_number": 27})

    def test_b1_14_renumbering_does_not_orphan_canonical_progress(self):
        record = {"attempts": 9}
        records = {question_key(question("sc900-a", 27)): record}
        self.assertIs(records[question_key(question("sc900-a", 93))], record)

    def test_b1_15_blank_progress_declares_canonical_identity_schema(self):
        payload = blank_progress("bank.json", "8.0.0")
        self.assertEqual(payload["progress_identity_version"], PROGRESS_IDENTITY_VERSION)
        self.assertEqual(payload["question_identity"], PROGRESS_IDENTITY_KIND)
        self.assertEqual(payload["questions"], {})

    def test_b1_16_default_sc900_bank_keeps_stable_canonical_ids(self):
        root = Path(__file__).resolve().parents[1]
        bank = load_bank(root / "sc900_bank_v8_baseline.json")
        self.assertTrue(bank["questions"])
        self.assertTrue(all(question_key(item) for item in bank["questions"]))
        self.assertEqual(question_key(bank["questions"][0]), "SC900-PH-001")

    def test_b1_17_cand01r3_canonical_identity_semantics_remain_equivalent(self):
        samples = [
            "  direct-id  ",
            {"id": " top-id ", "question_id": "other"},
            {"question_id": " qid "},
            {"canonical_question_id": " canonical "},
            {"metadata": {"question_id": " meta-qid "}},
            {"metadata": {"canonical_question_id": " meta-canonical "}},
            {"question_number": 27},
            None,
        ]
        self.assertEqual(
            [canonical_question_id(value) for value in samples],
            [cand01r3_canonical_question_id(value) for value in samples],
        )

    def test_b1_18_canonical_concept_aggregation_survives_renumbering(self):
        record = {"attempts": 1, "learner_memory": {"retrievability": 0.5, "stability": 0.4}}
        q = question("sc900-a", 93)
        q["objective_code"] = "1.1"
        result = aggregate_concept_memory({"sc900-a": record}, [q])
        self.assertEqual(result["Objective::1.1"]["supporting_question_count"], 1)
        self.assertEqual(result["Objective::1.1"]["stability"], 0.4)

    def test_b1_19_persistent_migration_is_idempotent_without_extra_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bank_progress.json"
            write_progress(path, legacy_payload({"27": {"attempts": 1}}))
            store = persistence(root)
            first, first_backup, first_err = store.load_progress_with_identity_migration(
                path, [question("sc900-a", 27)]
            )
            self.assertIsNone(first_err)
            self.assertIsNotNone(first_backup)
            backup_count = len(list((root / "backups").glob("*.json")))
            second, second_backup, second_err = store.load_progress_with_identity_migration(
                path, [question("sc900-a", 93)]
            )
            self.assertIsNone(second_err)
            self.assertIsNone(second_backup)
            self.assertEqual(second, first)
            self.assertEqual(len(list((root / "backups").glob("*.json"))), backup_count)

    def test_b1_20_unversioned_non_numeric_progress_keys_are_not_guessed(self):
        payload = legacy_payload({"unknown-id": {"attempts": 1}})
        with self.assertRaisesRegex(ProgressIdentityError, "PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS"):
            progress_store.migrate_legacy_progress_keys(payload, [question("sc900-a", 27)])


if __name__ == "__main__":
    unittest.main()
