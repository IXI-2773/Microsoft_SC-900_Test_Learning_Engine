from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from content_fingerprint_bridge import unwrap_revision
from content_revision_correction_authority import AdmittedCorrectionRevision
from content_revision_correction_migration import (
    ContentCorrectionMigrationError,
    derive_correction_migration_id,
    migrate_correction_progress_payload,
    migrate_correction_session_payload,
)
from content_revision_explanation_authority import AdmittedExplanationRevision
from content_revision_explanation_migration import (
    ContentExplanationMigrationError,
    accepted_explanation_migration_lineage_identities,
    derive_explanation_migration_id,
    migrate_explanation_progress_payload,
    migrate_explanation_session_payload,
)
from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    accepted_migration_lineage_identities,
    derive_migration_id,
    migrate_progress_payload,
    migrate_session_payload,
)
from fingerprint_identity import FINGERPRINT_SCHEMA_VERSION, RUNTIME_FINGERPRINT_DOMAIN
from question_identity import (
    ProgressIdentityError,
    migrate_legacy_progress_keys,
    migrate_progress_content_epoch,
    registered_progress_identity_bank,
)
from storage_utils import backup_bad_json_file, load_json_or_backup, safe_write_json


def _migrate_progress_for_revision(payload, target_questions, revision, migrated_at):
    raw = unwrap_revision(revision)
    if isinstance(raw, AdmittedExplanationRevision):
        return migrate_explanation_progress_payload(payload, target_questions, revision, migrated_at)
    if isinstance(raw, AdmittedCorrectionRevision):
        return migrate_correction_progress_payload(payload, target_questions, revision, migrated_at)
    return migrate_progress_payload(payload, target_questions, revision, migrated_at)


def _migrate_session_for_revision(saved, target_questions, revision, target_bank_file, *, source_questions=None):
    raw = unwrap_revision(revision)
    if isinstance(raw, AdmittedExplanationRevision):
        return migrate_explanation_session_payload(
            saved, target_questions, revision, target_bank_file, source_questions=source_questions
        )
    if isinstance(raw, AdmittedCorrectionRevision):
        return migrate_correction_session_payload(
            saved, target_questions, revision, target_bank_file, source_questions=source_questions
        )
    return migrate_session_payload(
        saved, target_questions, revision, target_bank_file, source_questions=source_questions
    )


def _derive_migration_id_for_revision(revision) -> str:
    raw = unwrap_revision(revision)
    if isinstance(raw, AdmittedExplanationRevision):
        return derive_explanation_migration_id(revision)
    if isinstance(raw, AdmittedCorrectionRevision):
        return derive_correction_migration_id(revision)
    return derive_migration_id(revision)


def _accepted_migration_identities_for_revision(revision):
    raw = unwrap_revision(revision)
    if isinstance(raw, AdmittedExplanationRevision):
        return accepted_explanation_migration_lineage_identities(revision)
    if isinstance(raw, AdmittedCorrectionRevision):
        return frozenset(
            {
                (raw.manifest_sha256, derive_correction_migration_id(revision)),
                (raw.manifest_sha256, derive_correction_migration_id(raw)),
            }
        )
    return accepted_migration_lineage_identities(revision)


@dataclass(slots=True)
class RuntimePersistence:
    checkpoint_dir: Path
    backup_dir: Path

    def load_json_with_backup(self, path: Path):
        target = Path(path)
        if target.name.endswith("_progress.json"):
            return self.load_progress_with_identity_migration(target)
        return load_json_or_backup(target)

    def load_progress_with_identity_migration(self, path: Path, questions=None):
        target = Path(path)
        data, backup, err = load_json_or_backup(target)
        if err or not isinstance(data, dict):
            return data, backup, err

        authority = tuple(questions) if questions is not None else registered_progress_identity_bank()
        try:
            migrated, changed = migrate_legacy_progress_keys(data, authority)
            epoch_migrated, epoch_changed = migrate_progress_content_epoch(migrated, authority)
            migrated = epoch_migrated
            changed = bool(changed or epoch_changed)
        except ProgressIdentityError as exc:
            logging.warning("Progress identity migration rejected: %s", exc)
            return None, None, exc

        if not changed:
            return migrated, None, None

        try:
            migration_backup = self.backup_progress_file(target, suffix="before_identity_migration_v1")
        except OSError as exc:
            logging.warning("Progress identity migration backup failed: %s", exc)
            return None, None, exc
        if migration_backup is None:
            backup_error = OSError("Could not create pre-migration progress backup.")
            logging.warning("Progress identity migration aborted: %s", backup_error)
            return None, None, backup_error

        try:
            self.write_json(target, migrated)
        except OSError as exc:
            logging.warning("Progress identity migration write failed: %s", exc)
            return None, migration_backup, exc

        logging.info("Migrated progress identity to canonical question IDs: %s", target)
        return migrated, migration_backup, None

    def restore_progress_from_source(self, source_path: Path, destination_path: Path, questions=None):
        source = Path(source_path)
        target = Path(destination_path)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            return None, None, exc
        if not isinstance(data, dict):
            return None, None, ValueError("Restore source must be a progress JSON object.")
        if "history" in data and not isinstance(data.get("history"), list):
            return None, None, ValueError("Progress.history must be a list.")
        if "meta" in data and not isinstance(data.get("meta"), dict):
            return None, None, ValueError("Progress.meta must be a mapping.")
        authority = tuple(questions) if questions is not None else registered_progress_identity_bank()
        try:
            migrated, _changed = migrate_legacy_progress_keys(data, authority)
            migrated, _epoch_changed = migrate_progress_content_epoch(migrated, authority)
        except ProgressIdentityError as exc:
            return None, None, exc

        backup = None
        if target.exists():
            try:
                backup = self.backup_progress_file(target, suffix="before_restore")
            except OSError as exc:
                return None, None, exc
            if backup is None:
                return None, None, OSError("Could not create pre-restore progress backup.")
        try:
            self.write_json(target, migrated)
        except OSError as exc:
            return None, backup, exc
        return migrated, backup, None

    def write_json(self, path: Path, payload: Any, *, indent: int = 2) -> None:
        safe_write_json(path, payload, indent=indent)

    def copy_file(self, source: Path, destination: Path, *, label: str = "file") -> Path:
        source = Path(source)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        logging.info("Copied %s: %s -> %s", label, source, destination)
        return destination

    def migrate_runtime_file(self, legacy_path: Path, new_path: Path, *, label: str) -> bool:
        legacy_path = Path(legacy_path)
        new_path = Path(new_path)
        if new_path.exists() or not legacy_path.exists():
            return False
        self.copy_file(legacy_path, new_path, label=f"{label} migration")
        return True

    def quarantine_invalid_runtime_file(self, path: Path, *, label: str) -> Path | None:
        target = Path(path)
        if not target.exists():
            return None
        backup = backup_bad_json_file(target)
        logging.warning("Quarantined invalid %s file: %s -> %s", label, target, backup)
        return backup

    def progress_backup_path(self, progress_path: Path, suffix: str = "manual") -> Path:
        progress_path = Path(progress_path)
        if suffix == "auto_backup":
            return self.backup_dir / f"{progress_path.stem}_auto_backup.json"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.backup_dir / f"{progress_path.stem}_{suffix}_{timestamp}.json"

    def backup_progress_file(
        self,
        progress_path: Path | None,
        *,
        suffix: str = "manual",
        destination: Path | None = None,
    ) -> Path | None:
        if not progress_path:
            return None
        source = Path(progress_path)
        if not source.exists():
            return None
        target = Path(destination) if destination is not None else self.progress_backup_path(source, suffix=suffix)
        return self.copy_file(source, target, label=f"progress {suffix}")

    def write_checkpoint(self, path: Path, payload: Any) -> None:
        self.write_json(path, payload)
        logging.info("Saved checkpoint file: %s", path)

    def content_revision_archive_path(self, source_path: Path, migration_id: str, label: str) -> Path:
        return content_revision_archive_path(source_path, migration_id, label)

    def _revision_transaction_paths(self, root: Path, migration_id: str) -> tuple[Path, Path, Path]:
        root = Path(root)
        return (
            root / f".sc900_revision_{migration_id}.lock",
            root / f".sc900_revision_{migration_id}.journal.json",
            root / f".sc900_revision_{migration_id}.receipt.json",
        )

    def _transaction_file_sha256(self, path: Path) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def _transaction_payload_bytes(self, payload: Mapping[str, Any]) -> bytes:
        return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")

    def _transaction_failpoint(self, requested: str | None, point: str) -> None:
        if requested == point:
            raise RuntimeError(f"INJECTED_TRANSACTION_FAILURE:{point}")

    def _revision_transaction_identity(self, revision) -> dict[str, Any]:
        raw = unwrap_revision(revision)
        if isinstance(raw, AdmittedExplanationRevision):
            migration_family = "explanation"
        elif isinstance(raw, AdmittedCorrectionRevision):
            migration_family = "correction"
        else:
            migration_family = "equivalence"
        return {
            "migration_family": migration_family,
            "migration_id": _derive_migration_id_for_revision(revision),
            "manifest_sha256": str(raw.manifest_sha256),
            "bridge_sha256": str(getattr(revision, "bridge_sha256", "") or ""),
            "source_bank_node_id": str(getattr(getattr(revision, "source_node", None), "bank_node_id", "") or ""),
            "target_bank_node_id": str(getattr(getattr(revision, "target_node", None), "bank_node_id", "") or ""),
            "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
            "source_fingerprint_domain": RUNTIME_FINGERPRINT_DOMAIN,
            "target_fingerprint_domain": RUNTIME_FINGERPRINT_DOMAIN,
        }

    def _validate_committed_revision_receipt(
        self,
        receipt: Mapping[str, Any],
        *,
        expected_identity: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not bool(receipt.get("committed")):
            raise ValueError("Revision transaction receipt is not committed.")
        for key, expected in expected_identity.items():
            actual = receipt.get(key)
            if str(actual) != str(expected):
                raise ValueError(f"Revision transaction receipt identity mismatch: {key}")
        entries = receipt.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Revision transaction receipt has no committed entries.")
        for raw_entry in entries:
            if not isinstance(raw_entry, Mapping):
                raise ValueError("Invalid revision transaction receipt entry.")
            target = Path(str(raw_entry.get("target_path") or ""))
            expected_sha = str(raw_entry.get("target_sha256") or "")
            if not target.exists() or not expected_sha:
                raise OSError(f"Committed revision target unavailable: {target}")
            if self._transaction_file_sha256(target) != expected_sha:
                raise OSError(f"Committed revision target hash mismatch: {target}")
            source_value = str(raw_entry.get("source_path") or "")
            if source_value:
                source = Path(source_value)
                if source.resolve() != target.resolve() and source.exists():
                    raise OSError(f"Superseded revision source remains after committed receipt: {source}")
        return dict(receipt)

    def recover_revision_state_transaction(
        self,
        journal_path: Path,
        *,
        expected_identity: Mapping[str, Any] | None = None,
        failpoint: str | None = None,
    ) -> dict[str, Any]:
        journal_path = Path(journal_path)
        journal, error = self._read_json_nonmutating(journal_path)
        if error is not None or journal is None:
            raise error or ValueError("Transaction journal unavailable.")
        if expected_identity is not None:
            for key, expected in expected_identity.items():
                if str(journal.get(key)) != str(expected):
                    raise ValueError(f"Revision transaction journal identity mismatch: {key}")
        else:
            if int(journal.get("fingerprint_schema_version") or 0) != FINGERPRINT_SCHEMA_VERSION:
                raise ValueError("Revision transaction journal fingerprint schema mismatch.")
            if str(journal.get("source_fingerprint_domain") or "") != RUNTIME_FINGERPRINT_DOMAIN:
                raise ValueError("Revision transaction journal source domain mismatch.")
            if str(journal.get("target_fingerprint_domain") or "") != RUNTIME_FINGERPRINT_DOMAIN:
                raise ValueError("Revision transaction journal target domain mismatch.")
            for key in (
                "migration_family",
                "migration_id",
                "manifest_sha256",
                "bridge_sha256",
                "source_bank_node_id",
                "target_bank_node_id",
            ):
                if not str(journal.get(key) or "").strip():
                    raise ValueError(f"Revision transaction journal missing identity: {key}")
        entries = journal.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError("Transaction journal has no entries.")
        for index, raw_entry in enumerate(entries):
            if not isinstance(raw_entry, Mapping):
                raise ValueError("Invalid transaction journal entry.")
            target = Path(str(raw_entry["target_path"]))
            stage = Path(str(raw_entry["stage_path"]))
            expected = str(raw_entry["target_sha256"])
            if target.exists() and self._transaction_file_sha256(target) == expected:
                continue
            if not stage.exists() or self._transaction_file_sha256(stage) != expected:
                raise OSError(f"Cannot recover staged target: {target}")
            self._transaction_failpoint(failpoint, f"before_replace_{index}")
            os.replace(stage, target)
            self._transaction_failpoint(failpoint, f"after_replace_{index}")
        receipt_path = Path(str(journal["receipt_path"]))
        receipt = {
            "transaction_version": 1,
            "migration_family": str(journal.get("migration_family") or ""),
            "migration_id": str(journal["migration_id"]),
            "manifest_sha256": str(journal["manifest_sha256"]),
            "bridge_sha256": str(journal.get("bridge_sha256") or ""),
            "source_bank_node_id": str(journal.get("source_bank_node_id") or ""),
            "target_bank_node_id": str(journal.get("target_bank_node_id") or ""),
            "fingerprint_schema_version": int(journal.get("fingerprint_schema_version") or 0),
            "source_fingerprint_domain": str(journal.get("source_fingerprint_domain") or ""),
            "target_fingerprint_domain": str(journal.get("target_fingerprint_domain") or ""),
            "entries": [
                {
                    "source_path": str(entry["source_path"]),
                    "source_sha256": str(entry["source_sha256"]),
                    "target_path": str(entry["target_path"]),
                    "target_sha256": str(entry["target_sha256"]),
                }
                for entry in entries
                if isinstance(entry, Mapping)
            ],
            "committed": True,
        }
        self._transaction_failpoint(failpoint, "before_receipt")
        safe_write_json(receipt_path, receipt, indent=2)
        self._transaction_failpoint(failpoint, "after_receipt")
        for raw_entry in entries:
            if not isinstance(raw_entry, Mapping):
                continue
            source = Path(str(raw_entry["source_path"]))
            target = Path(str(raw_entry["target_path"]))
            if source.resolve() == target.resolve() or not source.exists():
                continue
            source_sha = str(raw_entry["source_sha256"])
            if self._transaction_file_sha256(source) != source_sha:
                raise OSError(f"Source changed during transaction: {source}")
            label = str(raw_entry.get("label") or "revision")
            self._archive_source_bytes(source, str(journal["migration_id"]), label)
            source.unlink()
        journal_path.unlink(missing_ok=True)
        return receipt

    def migrate_revision_state_transaction(
        self,
        *,
        progress_source_path: Path,
        progress_target_path: Path,
        session_pairs: Sequence[tuple[Path, Path]],
        target_questions,
        revision,
        target_bank_file: str,
        migrated_at: str,
        source_questions=None,
        failpoint: str | None = None,
    ) -> tuple[dict[str, Any] | None, Exception | None]:
        transaction_identity = self._revision_transaction_identity(revision)
        migration_id = str(transaction_identity["migration_id"])
        root = Path(progress_target_path).parent
        root.mkdir(parents=True, exist_ok=True)
        lock_path, journal_path, receipt_path = self._revision_transaction_paths(root, migration_id)
        if journal_path.exists():
            try:
                return (
                    self.recover_revision_state_transaction(
                        journal_path,
                        expected_identity=transaction_identity,
                        failpoint=failpoint,
                    ),
                    None,
                )
            except Exception as exc:
                return None, exc
        if receipt_path.exists():
            receipt, error = self._read_json_nonmutating(receipt_path)
            if error is not None or receipt is None:
                return None, error or ValueError("Revision transaction receipt unavailable.")
            try:
                return (
                    self._validate_committed_revision_receipt(
                        receipt,
                        expected_identity=transaction_identity,
                    ),
                    None,
                )
            except Exception as exc:
                return None, exc
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError as exc:
            return None, exc
        try:
            plans: list[dict[str, Any]] = []
            source_progress, error = self._read_json_nonmutating(Path(progress_source_path))
            if error is not None or source_progress is None:
                return None, error
            progress_result = _migrate_progress_for_revision(source_progress, target_questions, revision, migrated_at)
            plans.append(
                {
                    "label": "progress",
                    "source_path": str(Path(progress_source_path)),
                    "target_path": str(Path(progress_target_path)),
                    "payload": progress_result.payload,
                }
            )
            for source, target in session_pairs:
                saved, error = self._read_json_nonmutating(Path(source))
                if error is not None or saved is None:
                    return None, error
                session_result = _migrate_session_for_revision(
                    saved,
                    target_questions,
                    revision,
                    target_bank_file,
                    source_questions=source_questions,
                )
                plans.append(
                    {
                        "label": "session",
                        "source_path": str(Path(source)),
                        "target_path": str(Path(target)),
                        "payload": session_result.payload,
                    }
                )
            self._transaction_failpoint(failpoint, "after_transform")

            entries: list[dict[str, Any]] = []
            for index, plan in enumerate(plans):
                source = Path(str(plan["source_path"]))
                target = Path(str(plan["target_path"]))
                if source.resolve() == target.resolve():
                    raise ValueError("Atomic revision transaction requires distinct source and target paths.")
                if not source.exists():
                    raise FileNotFoundError(source)
                payload_bytes = self._transaction_payload_bytes(plan["payload"])
                expected_sha = hashlib.sha256(payload_bytes).hexdigest()
                if target.exists():
                    if self._transaction_file_sha256(target) != expected_sha:
                        raise OSError(f"Conflicting transaction target exists: {target}")
                    stage = target.with_name(f".{target.name}.{migration_id}.stage")
                else:
                    stage = target.with_name(f".{target.name}.{migration_id}.stage")
                    stage.parent.mkdir(parents=True, exist_ok=True)
                    stage.write_bytes(payload_bytes)
                self._transaction_failpoint(failpoint, f"after_stage_{index}")
                entries.append(
                    {
                        "label": str(plan["label"]),
                        "source_path": str(source),
                        "source_sha256": self._transaction_file_sha256(source),
                        "target_path": str(target),
                        "target_sha256": expected_sha,
                        "stage_path": str(stage),
                    }
                )
            self._transaction_failpoint(failpoint, "after_staging")
            journal = {
                "transaction_version": 1,
                **transaction_identity,
                "receipt_path": str(receipt_path),
                "entries": entries,
            }
            self._transaction_failpoint(failpoint, "before_journal")
            safe_write_json(journal_path, journal, indent=2)
            self._transaction_failpoint(failpoint, "after_journal")
            receipt = self.recover_revision_state_transaction(
                journal_path,
                expected_identity=transaction_identity,
                failpoint=failpoint,
            )
            return receipt, None
        except Exception as exc:
            return None, exc
        finally:
            lock_path.unlink(missing_ok=True)

    def _read_json_nonmutating(self, path: Path) -> tuple[dict[str, Any] | None, Exception | None]:
        target = Path(path)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except Exception as exc:
            return None, exc
        if not isinstance(payload, dict):
            return None, ValueError("JSON object required")
        return payload, None

    def _archive_source_bytes(self, source_path: Path, migration_id: str, label: str) -> Path:
        source = Path(source_path)
        archive = content_revision_archive_path(source, migration_id, label)
        source_bytes = source.read_bytes()
        if archive.exists():
            if archive.read_bytes() != source_bytes:
                raise OSError("Conflicting content-revision archive already exists.")
            return archive
        return self.copy_file(source, archive, label=f"content revision {label} archive")

    def migrate_progress_across_approved_revision(
        self,
        source_path: Path,
        target_path: Path,
        target_questions,
        revision,
        migrated_at: str,
    ) -> tuple[dict[str, Any] | None, Path | None, Exception | None]:
        source_path = Path(source_path)
        target_path = Path(target_path)
        same_path = source_path.resolve() == target_path.resolve()
        payload, error = self._read_json_nonmutating(source_path)
        if error is not None or payload is None:
            return None, None, error
        transform_source = payload
        if target_path.exists() and not same_path:
            existing, existing_error = self._read_json_nonmutating(target_path)
            if existing_error is not None or existing is None:
                return None, None, existing_error
            existing_fp = str(existing.get("bank_fingerprint") or "").strip()
            if existing_fp not in {
                revision.source_bank_content_fingerprint,
                revision.target_bank_content_fingerprint,
            }:
                return (
                    None,
                    None,
                    ContentRevisionMigrationError(
                        MigrationFailureReason.UNEXPECTED_BANK_FINGERPRINT,
                        existing_fp,
                    ),
                )
            if existing_fp == revision.source_bank_content_fingerprint:
                if json.dumps(existing, sort_keys=True) != json.dumps(payload, sort_keys=True):
                    return (
                        None,
                        None,
                        ContentRevisionMigrationError(
                            MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                            str(target_path),
                        ),
                    )
                transform_source = existing
            else:
                leftover = payload
                leftover_fp = str(leftover.get("bank_fingerprint") or "").strip()
                if leftover_fp != revision.source_bank_content_fingerprint:
                    return (
                        None,
                        None,
                        ContentRevisionMigrationError(
                            MigrationFailureReason.SOURCE_BANK_MISMATCH,
                            leftover_fp,
                        ),
                    )
                try:
                    expected = _migrate_progress_for_revision(leftover, target_questions, revision, migrated_at)
                    verified = _migrate_progress_for_revision(existing, target_questions, revision, migrated_at)
                except (
                    ContentRevisionMigrationError,
                    ContentCorrectionMigrationError,
                    ContentExplanationMigrationError,
                ) as exc:
                    return None, None, exc
                if expected.status != MigrationStatus.APPLIED:
                    return (
                        None,
                        None,
                        ContentRevisionMigrationError(
                            MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                            str(source_path),
                        ),
                    )
                if verified.status != MigrationStatus.MIGRATION_ALREADY_APPLIED:
                    return (
                        None,
                        None,
                        ContentRevisionMigrationError(
                            MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                            str(target_path),
                        ),
                    )
                if not _progress_payloads_equal_ignoring_retry_migrated_at(expected.payload, existing, revision):
                    return (
                        None,
                        None,
                        ContentRevisionMigrationError(
                            MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                            str(target_path),
                        ),
                    )
                archive = None
                if source_path.exists() and not same_path:
                    try:
                        archive = self._archive_source_bytes(source_path, verified.migration_id, "progress")
                        source_path.unlink()
                    except OSError as exc:
                        return existing, archive, exc
                return existing, archive, None
        try:
            result = _migrate_progress_for_revision(transform_source, target_questions, revision, migrated_at)
        except (
            ContentRevisionMigrationError,
            ContentCorrectionMigrationError,
            ContentExplanationMigrationError,
        ) as exc:
            return None, None, exc
        if result.status == MigrationStatus.MIGRATION_ALREADY_APPLIED:
            return result.payload, None, None
        try:
            archive = self._archive_source_bytes(
                target_path if (target_path.exists() and same_path) else source_path,
                result.migration_id,
                "progress",
            )
        except OSError as exc:
            return None, None, exc
        try:
            self.write_json(target_path, result.payload)
        except OSError as exc:
            return None, archive, exc
        reread, reread_error = self._read_json_nonmutating(target_path)
        if reread_error is not None or reread is None:
            return None, archive, reread_error
        try:
            verified = _migrate_progress_for_revision(reread, target_questions, revision, migrated_at)
        except (
            ContentRevisionMigrationError,
            ContentCorrectionMigrationError,
            ContentExplanationMigrationError,
        ) as exc:
            return None, archive, exc
        if verified.status != MigrationStatus.MIGRATION_ALREADY_APPLIED:
            return (
                None,
                archive,
                ContentRevisionMigrationError(
                    MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                    "target verification failed",
                ),
            )
        if not same_path and source_path.exists():
            try:
                if source_path.resolve() != target_path.resolve():
                    source_path.unlink()
            except OSError as exc:
                return reread, archive, exc
        return reread, archive, None

    def migrate_session_file_across_approved_revision(
        self,
        source_path: Path,
        target_path: Path,
        target_questions,
        revision,
        target_bank_file: str,
        *,
        source_questions=None,
    ) -> tuple[dict[str, Any] | None, Path | None, Exception | None]:
        source_path = Path(source_path)
        target_path = Path(target_path)
        same_path = source_path.resolve() == target_path.resolve()
        payload, error = self._read_json_nonmutating(source_path)
        if error is not None or payload is None:
            return None, None, error
        try:
            expected = _migrate_session_for_revision(
                payload,
                target_questions,
                revision,
                target_bank_file,
                source_questions=source_questions,
            )
        except (
            ContentRevisionMigrationError,
            ContentCorrectionMigrationError,
            ContentExplanationMigrationError,
        ) as exc:
            return None, None, exc
        if target_path.exists() and not same_path:
            existing, existing_error = self._read_json_nonmutating(target_path)
            if existing_error is not None or existing is None:
                return None, None, existing_error
            if json.dumps(existing, sort_keys=True) != json.dumps(expected.payload, sort_keys=True):
                return (
                    None,
                    None,
                    ContentRevisionMigrationError(
                        MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                        str(target_path),
                    ),
                )
            archive = None
            try:
                archive = self._archive_source_bytes(source_path, expected.migration_id, "session")
                source_path.unlink()
            except OSError as exc:
                return existing, archive, exc
            return existing, archive, None
        try:
            archive = self._archive_source_bytes(source_path, expected.migration_id, "session")
        except OSError as exc:
            return None, None, exc
        try:
            self.write_json(target_path, expected.payload)
        except OSError as exc:
            return None, archive, exc
        reread, reread_error = self._read_json_nonmutating(target_path)
        if reread_error is not None or reread is None:
            return None, archive, reread_error
        if json.dumps(reread, sort_keys=True) != json.dumps(expected.payload, sort_keys=True):
            return (
                None,
                archive,
                ContentRevisionMigrationError(
                    MigrationFailureReason.TARGET_PROGRESS_CONFLICT,
                    "session target verification failed",
                ),
            )
        if not same_path and source_path.exists():
            try:
                source_path.unlink()
            except OSError as exc:
                return reread, archive, exc
        return reread, archive, None


def content_revision_archive_path(source_path: Path, migration_id: str, label: str) -> Path:
    source = Path(source_path)
    return source.with_name(f"{str(migration_id).strip()}.{str(label).strip() or 'revision'}.{source.name}")


def _progress_payloads_equal_ignoring_retry_migrated_at(
    expected: dict[str, Any], existing: dict[str, Any], revision
) -> bool:
    return _payload_for_recovery_compare(expected, revision) == _payload_for_recovery_compare(existing, revision)


def _payload_for_recovery_compare(payload: dict[str, Any], revision) -> str:
    normalized = json.loads(json.dumps(payload))
    lineage = normalized.get("content_revision_lineage")
    canonical_migration_id = _derive_migration_id_for_revision(revision)
    accepted_identities = _accepted_migration_identities_for_revision(revision)
    if isinstance(lineage, list):
        for row in lineage:
            if not isinstance(row, dict):
                continue
            identity = (
                str(row.get("manifest_sha256") or ""),
                str(row.get("migration_id") or ""),
            )
            if identity in accepted_identities:
                row["manifest_sha256"] = revision.manifest_sha256
                row["migration_id"] = canonical_migration_id
                row["migrated_at"] = ""
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
