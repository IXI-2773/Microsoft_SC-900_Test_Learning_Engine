from __future__ import annotations

import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from content_revision_authority import AdmittedRevision, RevisionEdge
from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    derive_migration_id,
    migrate_progress_payload,
)
from question_identity import question_content_fingerprint
from runtime_persistence import RuntimePersistence
from tests.test_content_revision_migration import _question, _record


T1_CONTENT_FINGERPRINT = "e0b4394b6faa8d0f9053291521b2dd83983e84990f1a169a25ab745694a7aabb"
T2_CONTENT_FINGERPRINT = "34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b"
T3_CONTENT_FINGERPRINT = "83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2"

T1_FILE_SHA256 = "45ee43c9ced0d50c790c4b637ddc3d585526830a3dec32251b904d9d06e4c7e8"
T2_OLD_FILE_SHA256 = "9c208309483aba1f1881e33a2be85a175548498c51854ef9c04adc075b760800"
T2_FILE_SHA256 = "c53ba19ee26992643969d546a73da5aa8396041ebe4e138f6b30db637756aa65"
T3_OLD_FILE_SHA256 = "d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b"
T3_FILE_SHA256 = "0b0cdf3bf4c8b7885acf0b3b19381dd9f19ee38944fc6af6934b11b5b14588bd"

T2_OLD_MANIFEST_SHA256 = "2f04ae1d2d22bdea1a8b96d470691700d59ea119bf34fb02d686d423b93bc571"
T2_MANIFEST_SHA256 = "646ad8ba5a7ccb0ae7f369b019b482fcd3212495ff0ce893aaecf0ceb5237cbe"
T3_OLD_MANIFEST_SHA256 = "d89a6708b08f2afc5bfc3a30cbd4c5708b6022acbacdb3a91db360d12c18c2ea"
T3_MANIFEST_SHA256 = "4b9eab410da68bd348b4ae40946cf54a45b1da98bf04d68baaf6a57e3de15338"

T2_OLD_MIGRATION_ID = "24d7b56a36067bd74f000d15c2cf74810c1f575ba248a522b934450408ca6458"
T2_MIGRATION_ID = "c8f581bca9c94fdeb08f0bab3af83ae4cdeb6693d11b4a6869b220b555c367a5"
T3_OLD_MIGRATION_ID = "7dd60b6dc130e4c8a16d3c117c832da737c0293957a350f3027826ababe268e2"
T3_MIGRATION_ID = "1fdc1cb04f142124506d57da5ef40cc8ab7949dc7908cfabbe43f7584f96757e"

T1_FILENAME = "sc900_bank_v8_length_rebalanced_t1.json"
T2_FILENAME = "sc900_bank_v8_length_rebalanced_t2.json"
T3_FILENAME = "sc900_bank_v8_length_rebalanced_t3.json"


class PackageBLineageCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_question = _question("change", choice_b="beta")
        self.target_question = _question("change", choice_b="beta rebalanced")
        self.target_questions = [self.target_question]
        self.edge = RevisionEdge(
            "change",
            question_content_fingerprint(self.source_question),
            question_content_fingerprint(self.target_question),
            "review.json",
            "d" * 64,
        )
        self.t2_old = self._revision(
            T2_OLD_MANIFEST_SHA256,
            T1_FILENAME,
            T1_FILE_SHA256,
            T1_CONTENT_FINGERPRINT,
            T2_FILENAME,
            T2_OLD_FILE_SHA256,
            T2_CONTENT_FINGERPRINT,
        )
        self.t2_repaired = self._revision(
            T2_MANIFEST_SHA256,
            T1_FILENAME,
            T1_FILE_SHA256,
            T1_CONTENT_FINGERPRINT,
            T2_FILENAME,
            T2_FILE_SHA256,
            T2_CONTENT_FINGERPRINT,
        )
        self.t3_old = self._revision(
            T3_OLD_MANIFEST_SHA256,
            T2_FILENAME,
            T2_OLD_FILE_SHA256,
            T2_CONTENT_FINGERPRINT,
            T3_FILENAME,
            T3_OLD_FILE_SHA256,
            T3_CONTENT_FINGERPRINT,
        )
        self.t3_repaired = self._revision(
            T3_MANIFEST_SHA256,
            T2_FILENAME,
            T2_FILE_SHA256,
            T2_CONTENT_FINGERPRINT,
            T3_FILENAME,
            T3_FILE_SHA256,
            T3_CONTENT_FINGERPRINT,
        )

    def _revision(
        self,
        manifest_sha256: str,
        source_filename: str,
        source_file_sha256: str,
        source_content_fingerprint: str,
        target_filename: str,
        target_file_sha256: str,
        target_content_fingerprint: str,
    ) -> AdmittedRevision:
        return AdmittedRevision(
            manifest_sha256=manifest_sha256,
            source_bank_filename=source_filename,
            source_bank_file_sha256=source_file_sha256,
            source_bank_content_fingerprint=source_content_fingerprint,
            target_bank_filename=target_filename,
            target_bank_file_sha256=target_file_sha256,
            target_bank_content_fingerprint=target_content_fingerprint,
            edges=(self.edge,),
        )

    def _source_payload(self, revision: AdmittedRevision) -> dict:
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": revision.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                "change": question_content_fingerprint(self.source_question),
            },
            "questions": {"change": _record()},
            "history": [],
        }

    def _target_payload(self, revision: AdmittedRevision) -> dict:
        return migrate_progress_payload(
            self._source_payload(revision),
            self.target_questions,
            revision,
            "2026-09-17T00:00:00",
        ).payload

    def _assert_target_conflict(self, payload: dict, revision: AdmittedRevision) -> None:
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(
                payload,
                self.target_questions,
                revision,
                "2026-09-18T00:00:00",
            )
        self.assertEqual(
            MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
            ctx.exception.reason,
        )

    def test_exact_migration_ids_pin_old_and_repaired_lineages(self) -> None:
        cases = (
            (self.t2_old, T2_OLD_MIGRATION_ID),
            (self.t2_repaired, T2_MIGRATION_ID),
            (self.t3_old, T3_OLD_MIGRATION_ID),
            (self.t3_repaired, T3_MIGRATION_ID),
        )
        for revision, expected in cases:
            with self.subTest(manifest=revision.manifest_sha256):
                self.assertEqual(expected, derive_migration_id(revision))

    def test_old_t2_lineage_is_already_applied_under_repaired_t2_manifest(self) -> None:
        payload = self._target_payload(self.t2_old)
        lineage_before = copy.deepcopy(payload["content_revision_lineage"])

        result = migrate_progress_payload(
            payload,
            self.target_questions,
            self.t2_repaired,
            "2026-09-18T00:00:00",
        )

        self.assertEqual(MigrationStatus.MIGRATION_ALREADY_APPLIED, result.status)
        self.assertFalse(result.changed)
        self.assertEqual(T2_MIGRATION_ID, result.migration_id)
        self.assertEqual(lineage_before, result.payload["content_revision_lineage"])
        self.assertEqual(1, len(result.payload["content_revision_lineage"]))

    def test_old_t3_lineage_is_already_applied_under_repaired_t3_manifest(self) -> None:
        payload = self._target_payload(self.t3_old)
        lineage_before = copy.deepcopy(payload["content_revision_lineage"])

        result = migrate_progress_payload(
            payload,
            self.target_questions,
            self.t3_repaired,
            "2026-09-18T00:00:00",
        )

        self.assertEqual(MigrationStatus.MIGRATION_ALREADY_APPLIED, result.status)
        self.assertFalse(result.changed)
        self.assertEqual(T3_MIGRATION_ID, result.migration_id)
        self.assertEqual(lineage_before, result.payload["content_revision_lineage"])
        self.assertEqual(1, len(result.payload["content_revision_lineage"]))

    def test_repaired_lineage_repeats_idempotently_without_duplication(self) -> None:
        for revision in (self.t2_repaired, self.t3_repaired):
            with self.subTest(manifest=revision.manifest_sha256):
                first = migrate_progress_payload(
                    self._source_payload(revision),
                    self.target_questions,
                    revision,
                    "2026-09-17T00:00:00",
                )
                second = migrate_progress_payload(
                    first.payload,
                    self.target_questions,
                    revision,
                    "2026-09-18T00:00:00",
                )
                self.assertEqual(MigrationStatus.APPLIED, first.status)
                self.assertEqual(
                    MigrationStatus.MIGRATION_ALREADY_APPLIED,
                    second.status,
                )
                self.assertFalse(second.changed)
                self.assertEqual(
                    first.payload["content_revision_lineage"],
                    second.payload["content_revision_lineage"],
                )
                self.assertEqual(1, len(second.payload["content_revision_lineage"]))

    def test_new_migrations_emit_only_repaired_canonical_identity(self) -> None:
        cases = (
            (self.t2_repaired, T2_MANIFEST_SHA256, T2_MIGRATION_ID),
            (self.t3_repaired, T3_MANIFEST_SHA256, T3_MIGRATION_ID),
        )
        for revision, manifest_sha256, migration_id in cases:
            with self.subTest(manifest=manifest_sha256):
                result = migrate_progress_payload(
                    self._source_payload(revision),
                    self.target_questions,
                    revision,
                    "2026-09-18T00:00:00",
                )
                self.assertEqual(MigrationStatus.APPLIED, result.status)
                self.assertEqual(1, len(result.payload["content_revision_lineage"]))
                row = result.payload["content_revision_lineage"][0]
                self.assertEqual(manifest_sha256, row["manifest_sha256"])
                self.assertEqual(migration_id, row["migration_id"])

    def test_unknown_migration_id_still_fails_closed(self) -> None:
        for revision in (self.t2_repaired, self.t3_repaired):
            with self.subTest(manifest=revision.manifest_sha256):
                payload = self._target_payload(revision)
                payload["content_revision_lineage"][0]["migration_id"] = "f" * 64
                self._assert_target_conflict(payload, revision)

    def test_same_target_fingerprint_with_arbitrary_lineage_is_rejected(self) -> None:
        payload = self._target_payload(self.t2_repaired)
        row = payload["content_revision_lineage"][0]
        row["manifest_sha256"] = "e" * 64
        row["migration_id"] = "f" * 64
        self._assert_target_conflict(payload, self.t2_repaired)

    def test_corrupted_target_question_fingerprint_is_rejected(self) -> None:
        payload = self._target_payload(self.t2_old)
        payload["question_content_fingerprints"]["change"] = "e" * 64
        self._assert_target_conflict(payload, self.t2_repaired)

    def test_wrong_target_bank_is_rejected(self) -> None:
        payload = self._target_payload(self.t2_old)
        payload["bank_fingerprint"] = "f" * 64
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(
                payload,
                self.target_questions,
                self.t2_repaired,
                "2026-09-18T00:00:00",
            )
        self.assertEqual(MigrationFailureReason.SOURCE_BANK_MISMATCH, ctx.exception.reason)

    def test_missing_lineage_is_rejected(self) -> None:
        payload = self._target_payload(self.t2_old)
        payload["content_revision_lineage"] = []
        self._assert_target_conflict(payload, self.t2_repaired)

    def test_tampered_lineage_fields_are_rejected(self) -> None:
        payload = self._target_payload(self.t2_old)
        payload["content_revision_lineage"][0]["to_fingerprint"] = "e" * 64
        self._assert_target_conflict(payload, self.t2_repaired)

    def test_future_unknown_manifest_rebinding_is_not_implicitly_accepted(self) -> None:
        payload = self._target_payload(self.t2_old)
        unknown = replace(self.t2_repaired, manifest_sha256="1" * 64)
        self._assert_target_conflict(payload, unknown)

    def test_alias_requires_exact_current_source_semantics(self) -> None:
        payload = self._target_payload(self.t2_old)
        wrong_source = replace(
            self.t2_repaired,
            source_bank_content_fingerprint="1" * 64,
        )
        self._assert_target_conflict(payload, wrong_source)

    def test_alias_requires_exact_current_bank_file_binding(self) -> None:
        payload = self._target_payload(self.t2_old)
        wrong_file = replace(
            self.t2_repaired,
            target_bank_file_sha256="f" * 64,
        )
        self._assert_target_conflict(payload, wrong_file)

    def test_crash_retry_accepts_old_lineage_without_rewriting_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            persistence = RuntimePersistence(
                checkpoint_dir=root / "checkpoints",
                backup_dir=root / "backups",
            )
            source_path = root / "t1_progress.json"
            target_path = root / "t2_progress.json"
            source_path.write_text(
                json.dumps(self._source_payload(self.t2_repaired), indent=2),
                encoding="utf-8",
            )
            target_path.write_text(
                json.dumps(self._target_payload(self.t2_old), indent=2),
                encoding="utf-8",
            )
            target_before = target_path.read_bytes()

            payload, archive, error = persistence.migrate_progress_across_approved_revision(
                source_path,
                target_path,
                self.target_questions,
                self.t2_repaired,
                "2026-09-18T12:00:00",
            )

            self.assertIsNone(error)
            self.assertIsNotNone(payload)
            self.assertIsNotNone(archive)
            self.assertFalse(source_path.exists())
            self.assertEqual(target_before, target_path.read_bytes())
            assert payload is not None
            self.assertEqual(
                T2_OLD_MIGRATION_ID,
                payload["content_revision_lineage"][0]["migration_id"],
            )
            self.assertEqual(1, len(payload["content_revision_lineage"]))


if __name__ == "__main__":
    unittest.main()
