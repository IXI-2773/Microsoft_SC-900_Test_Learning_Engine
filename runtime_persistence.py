from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from question_identity import (
    ProgressIdentityError,
    migrate_legacy_progress_keys,
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
