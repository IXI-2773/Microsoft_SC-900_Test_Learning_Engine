from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    migrate_progress_payload,
    migrate_session_payload,
)
from question_identity import (
    ProgressIdentityError,
    migrate_legacy_progress_keys,
    migrate_progress_content_epoch,
    registered_progress_identity_bank,
)
from storage_utils import backup_bad_json_file, load_json_or_backup, safe_write_json


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
                    expected = migrate_progress_payload(leftover, target_questions, revision, migrated_at)
                    verified = migrate_progress_payload(existing, target_questions, revision, migrated_at)
                except ContentRevisionMigrationError as exc:
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
                if not _progress_payloads_equal_ignoring_retry_migrated_at(
                    expected.payload, existing, expected.migration_id
                ):
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
            result = migrate_progress_payload(transform_source, target_questions, revision, migrated_at)
        except ContentRevisionMigrationError as exc:
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
            verified = migrate_progress_payload(reread, target_questions, revision, migrated_at)
        except ContentRevisionMigrationError as exc:
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
            expected = migrate_session_payload(
                payload,
                target_questions,
                revision,
                target_bank_file,
                source_questions=source_questions,
            )
        except ContentRevisionMigrationError as exc:
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
    expected: dict[str, Any], existing: dict[str, Any], migration_id: str
) -> bool:
    return _payload_for_recovery_compare(expected, migration_id) == _payload_for_recovery_compare(
        existing, migration_id
    )


def _payload_for_recovery_compare(payload: dict[str, Any], migration_id: str) -> str:
    normalized = json.loads(json.dumps(payload))
    lineage = normalized.get("content_revision_lineage")
    if isinstance(lineage, list):
        for row in lineage:
            if isinstance(row, dict) and str(row.get("migration_id") or "") == migration_id:
                row["migrated_at"] = ""
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
