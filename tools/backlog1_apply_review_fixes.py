from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_one(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str, minimum: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count < minimum:
        raise RuntimeError(f"{path}: expected >= {minimum} matches, found {count}: {old[:80]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")


# ---------------------------------------------------------------------------
# Canonical identity authority: strict durable key boundary + schema/history.
# ---------------------------------------------------------------------------
replace_one(
    "question_identity.py",
    'PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS = "PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS"\n',
    'PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS = "PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS"\n'
    'PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED = "PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED"\n'
    'INVALID_PROGRESS_RECORD = "INVALID_PROGRESS_RECORD"\n',
)
replace_one(
    "question_identity.py",
    '''def require_canonical_question_id(question: Mapping[str, Any] | str | None) -> str:\n    value = canonical_question_id(question)\n    if value:\n        return value\n    if isinstance(question, Mapping) and set(question) == {"question_number"}:\n        return resolve_registered_question_id_from_number(question.get("question_number"))\n    raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID)\n''',
    '''def require_canonical_question_id(question: Mapping[str, Any] | str | None) -> str:\n    value = canonical_question_id(question)\n    if value:\n        return value\n    raise ProgressIdentityError(MISSING_CANONICAL_QUESTION_ID)\n''',
)
replace_one(
    "question_identity.py",
    '''def classify_progress_identity_schema(payload: Mapping[str, Any]) -> str:\n    version = payload.get("progress_identity_version")\n    kind = str(payload.get("question_identity") or "").strip()\n    if version == PROGRESS_IDENTITY_VERSION and kind == PROGRESS_IDENTITY_KIND:\n        return "canonical"\n    questions = payload.get("questions")\n''',
    '''def classify_progress_identity_schema(payload: Mapping[str, Any]) -> str:\n    version_present = "progress_identity_version" in payload\n    kind_present = "question_identity" in payload\n    version = payload.get("progress_identity_version")\n    kind = str(payload.get("question_identity") or "").strip()\n    if version == PROGRESS_IDENTITY_VERSION and kind == PROGRESS_IDENTITY_KIND:\n        return "canonical"\n    if version_present or kind_present:\n        raise ProgressIdentityError(\n            PROGRESS_IDENTITY_SCHEMA_UNSUPPORTED,\n            f"version={version!r}, kind={kind!r}",\n        )\n    questions = payload.get("questions")\n''',
)
replace_one(
    "question_identity.py",
    '''def migrate_legacy_progress_keys(\n    payload: Mapping[str, Any],\n    questions: Iterable[Mapping[str, Any]],\n) -> tuple[dict[str, Any], bool]:\n    schema = classify_progress_identity_schema(payload)\n    if schema == "canonical":\n        return copy.deepcopy(dict(payload)), False\n\n    legacy_questions = payload.get("questions")\n''',
    '''def _validate_progress_records(records: Mapping[Any, Any]) -> None:\n    for key, record in records.items():\n        if not isinstance(record, Mapping):\n            raise ProgressIdentityError(INVALID_PROGRESS_RECORD, str(key))\n\n\ndef migrate_legacy_progress_keys(\n    payload: Mapping[str, Any],\n    questions: Iterable[Mapping[str, Any]],\n) -> tuple[dict[str, Any], bool]:\n    schema = classify_progress_identity_schema(payload)\n    payload_questions = payload.get("questions")\n    if not isinstance(payload_questions, Mapping):\n        raise ProgressIdentityError(PROGRESS_IDENTITY_SCHEMA_AMBIGUOUS, "questions must be a mapping")\n    _validate_progress_records(payload_questions)\n    if schema == "canonical":\n        return copy.deepcopy(dict(payload)), False\n\n    legacy_questions = payload_questions\n''',
)
replace_one(
    "question_identity.py",
    '''\n_registered_bank_questions: tuple[Mapping[str, Any], ...] = ()\n''',
    '''\ndef history_event_question_id(event: Mapping[str, Any] | None) -> str:\n    if not isinstance(event, Mapping):\n        return ""\n    for key in ("question_id", "canonical_question_id"):\n        value = str(event.get(key) or "").strip()\n        if value:\n            return value\n    return ""\n\n\ndef history_event_matches_question(\n    event: Mapping[str, Any] | None, question: Mapping[str, Any] | None\n) -> bool:\n    if not isinstance(event, Mapping) or not isinstance(question, Mapping):\n        return False\n    event_id = history_event_question_id(event)\n    question_id = canonical_question_id(question)\n    if event_id:\n        return bool(question_id) and event_id == question_id\n    try:\n        return int(event.get("question_number")) == int(question.get("question_number"))\n    except (TypeError, ValueError):\n        return False\n\n\ndef question_for_history_event(\n    event: Mapping[str, Any] | None, questions: Iterable[Mapping[str, Any]]\n) -> Mapping[str, Any] | None:\n    matches = [question for question in questions if history_event_matches_question(event, question)]\n    return matches[0] if len(matches) == 1 else None\n\n\n_registered_bank_questions: tuple[Mapping[str, Any], ...] = ()\n''',
)

# ---------------------------------------------------------------------------
# Progress reads may consume legacy numeric state; every durable write remains
# strict canonical-ID-only through question_key().
# ---------------------------------------------------------------------------
replace_one(
    "progress_store.py",
    '''    migrate_legacy_progress_keys as _migrate_legacy_progress_keys,\n    require_canonical_question_id,\n)\n''',
    '''    canonical_question_id,\n    migrate_legacy_progress_keys as _migrate_legacy_progress_keys,\n    require_canonical_question_id,\n)\n''',
)
replace_one(
    "progress_store.py",
    '''def aggregate_concept_memory(records: Mapping[str, Mapping[str, Any]], questions) -> dict[str, dict[str, Any]]:\n    aggregates: dict[str, dict[str, Any]] = {}\n    for question in questions:\n        progress_key = question_key(question)\n''',
    '''def progress_record_for_question(\n    records: Mapping[str, Mapping[str, Any]], question: Mapping[str, Any]\n) -> Mapping[str, Any] | None:\n    question_id = canonical_question_id(question)\n    if question_id:\n        canonical_record = records.get(question_id)\n        if isinstance(canonical_record, Mapping):\n            return canonical_record\n    try:\n        legacy_key = str(int(question.get("question_number")))\n    except (TypeError, ValueError):\n        return None\n    legacy_record = records.get(legacy_key)\n    return legacy_record if isinstance(legacy_record, Mapping) else None\n\n\ndef aggregate_concept_memory(records: Mapping[str, Mapping[str, Any]], questions) -> dict[str, dict[str, Any]]:\n    aggregates: dict[str, dict[str, Any]] = {}\n    for question in questions:\n''',
)
replace_one(
    "progress_store.py",
    '''        rec = normalize_progress_record(records.get(progress_key, {}))\n''',
    '''        rec = normalize_progress_record(progress_record_for_question(records, question) or {})\n''',
)
replace_all(
    "progress_store.py",
    '''records.get(question_key(q), {})''',
    '''progress_record_for_question(records, q) or {}''',
    minimum=3,
)

# ---------------------------------------------------------------------------
# Persistence: catch backup failure and restore from an immutable source.
# ---------------------------------------------------------------------------
replace_one("runtime_persistence.py", "import logging\n", "import json\nimport logging\n")
replace_one(
    "runtime_persistence.py",
    '''        migration_backup = self.backup_progress_file(target, suffix="before_identity_migration_v1")\n        if migration_backup is None:\n            exc = OSError("Could not create pre-migration progress backup.")\n            logging.warning("Progress identity migration aborted: %s", exc)\n            return None, None, exc\n''',
    '''        try:\n            migration_backup = self.backup_progress_file(target, suffix="before_identity_migration_v1")\n        except OSError as exc:\n            logging.warning("Progress identity migration backup failed: %s", exc)\n            return None, None, exc\n        if migration_backup is None:\n            exc = OSError("Could not create pre-migration progress backup.")\n            logging.warning("Progress identity migration aborted: %s", exc)\n            return None, None, exc\n''',
)
replace_one(
    "runtime_persistence.py",
    '''    def write_json(self, path: Path, payload: Any, *, indent: int = 2) -> None:\n        safe_write_json(path, payload, indent=indent)\n''',
    '''    def restore_progress_from_source(self, source_path: Path, destination_path: Path, questions=None):\n        source = Path(source_path)\n        target = Path(destination_path)\n        try:\n            data = json.loads(source.read_text(encoding="utf-8"))\n        except (OSError, UnicodeError, json.JSONDecodeError) as exc:\n            return None, None, exc\n        if not isinstance(data, dict):\n            return None, None, ValueError("Restore source must be a progress JSON object.")\n        if "history" in data and not isinstance(data.get("history"), list):\n            return None, None, ValueError("Progress.history must be a list.")\n        if "meta" in data and not isinstance(data.get("meta"), dict):\n            return None, None, ValueError("Progress.meta must be a mapping.")\n        authority = tuple(questions) if questions is not None else registered_progress_identity_bank()\n        try:\n            migrated, _changed = migrate_legacy_progress_keys(data, authority)\n        except ProgressIdentityError as exc:\n            return None, None, exc\n\n        backup = None\n        if target.exists():\n            try:\n                backup = self.backup_progress_file(target, suffix="before_restore")\n            except OSError as exc:\n                return None, None, exc\n            if backup is None:\n                return None, None, OSError("Could not create pre-restore progress backup.")\n        try:\n            self.write_json(target, migrated)\n        except OSError as exc:\n            return None, backup, exc\n        return migrated, backup, None\n\n    def write_json(self, path: Path, payload: Any, *, indent: int = 2) -> None:\n        safe_write_json(path, payload, indent=indent)\n''',
)

# ---------------------------------------------------------------------------
# Progress metadata: new issue reports carry canonical ID, legacy reports remain
# readable by number.
# ---------------------------------------------------------------------------
replace_one(
    "progress_models.py",
    '''from typing import Any, NotRequired, TypedDict, cast\n''',
    '''from typing import Any, NotRequired, TypedDict, cast\n\nfrom question_identity import canonical_question_id\n''',
)
replace_one(
    "progress_models.py",
    '''class IssueReport(TypedDict):\n    question_number: int\n''',
    '''class IssueReport(TypedDict):\n    question_id: NotRequired[str]\n    question_number: int\n''',
)
replace_one(
    "progress_models.py",
    '''        issue_reports.append(\n            {\n                "question_number": _coerce_int(\n''',
    '''        issue_reports.append(\n            {\n                "question_id": str(row.get("question_id") or "").strip(),\n                "question_number": _coerce_int(\n''',
)
replace_one(
    "progress_models.py",
    '''    return {\n        "question_number": int(question.get("question_number", 0) or 0),\n''',
    '''    return {\n        "question_id": canonical_question_id(question),\n        "question_number": int(question.get("question_number", 0) or 0),\n''',
)

# ---------------------------------------------------------------------------
# History typing and application lifecycle integration.
# ---------------------------------------------------------------------------
replace_one(
    "session_models.py",
    '''class QuestionHistoryEvent(TypedDict):\n    at: str\n    day: str\n    question_number: int\n''',
    '''class QuestionHistoryEvent(TypedDict):\n    at: str\n    day: str\n    question_id: str\n    question_number: int\n''',
)
replace_one(
    "app.py",
    '''    normalize_progress_record,\n    now_iso,\n    question_key,\n''',
    '''    normalize_progress_record,\n    now_iso,\n    progress_record_for_question,\n    question_key,\n''',
)
replace_one(
    "app.py",
    '''from question_bank import adaptive_shuffle_question, load_bank, stable_shuffle_question\n''',
    '''from question_bank import adaptive_shuffle_question, load_bank, stable_shuffle_question\nfrom question_identity import (\n    canonical_question_id,\n    history_event_matches_question,\n    resolve_registered_question_id_from_number,\n)\n''',
)
replace_one(
    "app.py",
    '''        self.progress_data = blank_progress(app_version=APP_VERSION)\n        self.data: QuestionBankData | None = None\n''',
    '''        self.progress_data = blank_progress(app_version=APP_VERSION)\n        self.progress_write_blocked = False\n        self.data: QuestionBankData | None = None\n''',
)
replace_one(
    "app.py",
    '''    def _open_issue_reports_for_question(self, qnum):\n        try:\n            target_qnum = int(qnum or 0)\n        except (TypeError, ValueError):\n            return []\n        issue_reports = self._issue_reports()\n        cached_reports = getattr(self, "_open_issue_reports_cache_source", None)\n        indexed_reports = getattr(self, "_open_issue_reports_cache_value", None)\n        if issue_reports is not cached_reports or indexed_reports is None:\n            indexed_reports = {}\n            for report in issue_reports:\n                if str(report.get("status") or "open") != "open":\n                    continue\n                try:\n                    report_qnum = int(report.get("question_number", 0) or 0)\n                except (TypeError, ValueError):\n                    continue\n                indexed_reports.setdefault(report_qnum, []).append(report)\n            self._open_issue_reports_cache_source = issue_reports\n            self._open_issue_reports_cache_value = indexed_reports\n        return list(indexed_reports.get(target_qnum, []))\n\n    def question_has_open_issue_report(self, q):\n        return bool(self._open_issue_reports_for_question(q.get("question_number")))\n''',
    '''    def _open_issue_reports_for_question(self, qnum, question_id=""):\n        try:\n            target_qnum = int(qnum or 0)\n        except (TypeError, ValueError):\n            return []\n        target_id = str(question_id or "").strip()\n        out = []\n        for report in self._issue_reports():\n            if str(report.get("status") or "open") != "open":\n                continue\n            report_id = str(report.get("question_id") or "").strip()\n            if report_id and target_id:\n                if report_id == target_id:\n                    out.append(report)\n                continue\n            try:\n                report_qnum = int(report.get("question_number", 0) or 0)\n            except (TypeError, ValueError):\n                continue\n            if report_qnum == target_qnum:\n                out.append(report)\n        return out\n\n    def question_has_open_issue_report(self, q):\n        return bool(\n            self._open_issue_reports_for_question(\n                q.get("question_number"), canonical_question_id(q)\n            )\n        )\n''',
)
replace_one(
    "app.py",
    '''        for report in self._open_issue_reports_for_question(q.get("question_number")):\n''',
    '''        for report in self._open_issue_reports_for_question(\n            q.get("question_number"), canonical_question_id(q)\n        ):\n''',
)
replace_one(
    "app.py",
    '''    def set_question_suspended_state(self, qnum, suspended):\n        temp_q = {"question_number": qnum}\n        rec = self._progress_record(temp_q, create=True)\n        rec = set_progress_suspended(rec, suspended)\n        self._progress_questions()[self._question_key(temp_q)] = rec\n''',
    '''    def set_question_suspended_state(self, qnum, suspended):\n        key = resolve_registered_question_id_from_number(qnum)\n        records = self._progress_questions()\n        rec = set_progress_suspended(records.get(key), suspended)\n        records[key] = rec\n''',
)
replace_one(
    "app.py",
    '''        qnum = report.get("question_number")\n        if restore_scoring and report.get("exclude_from_scoring"):\n            self.set_question_suspended_state(qnum, False)\n''',
    '''        qnum = report.get("question_number")\n        report_id = str(report.get("question_id") or "").strip()\n        if report_id:\n            current = next(\n                (q for q in self.master_questions if canonical_question_id(q) == report_id),\n                None,\n            )\n            if current is not None:\n                qnum = current.get("question_number")\n        if restore_scoring and report.get("exclude_from_scoring"):\n            self.set_question_suspended_state(qnum, False)\n''',
)
replace_one(
    "app.py",
    '''    def _progress_record(self, q, create=False) -> ProgressRecord | None:\n        key = self._question_key(q)\n        records = self._progress_questions()\n        if create and key not in records:\n            records[key] = default_progress_record()\n        record = records.get(key)\n        if record is None:\n            return None\n        return cast(ProgressRecord, record)\n''',
    '''    def _progress_record(self, q, create=False) -> ProgressRecord | None:\n        records = self._progress_questions()\n        if create:\n            key = self._question_key(q)\n            if key not in records:\n                records[key] = default_progress_record()\n            return cast(ProgressRecord, records[key])\n        record = progress_record_for_question(records, q)\n        return cast(ProgressRecord, record) if record is not None else None\n''',
)
replace_one(
    "app.py",
    '''    def load_progress_if_present(self):\n        self.progress_data = blank_progress(self.bank_path.name if self.bank_path else "", app_version=APP_VERSION)\n''',
    '''    def load_progress_if_present(self):\n        self.progress_write_blocked = False\n        self.progress_data = blank_progress(self.bank_path.name if self.bank_path else "", app_version=APP_VERSION)\n''',
)
replace_one(
    "app.py",
    '''        if err:\n            logging.warning("Progress file reset after read failure: %s", self.progress_path)\n            self._show_bad_json_warning("Progress", self.progress_path, backup, err)\n            return\n''',
    '''        if err:\n            if self.progress_path and self.progress_path.exists():\n                self.progress_write_blocked = True\n                logging.warning("Progress load blocked; preserved source unchanged: %s", self.progress_path)\n                if hasattr(self, "root"):\n                    messagebox.showwarning(\n                        "Progress migration blocked",\n                        "Existing progress could not be migrated safely and was left unchanged. "\n                        "Progress saving is disabled for this bank until the conflict is resolved.\\n\\n"\n                        f"{err}",\n                    )\n            else:\n                logging.warning("Progress file reset after read failure: %s", self.progress_path)\n                self._show_bad_json_warning("Progress", self.progress_path, backup, err)\n            return\n''',
)
replace_one(
    "app.py",
    '''    def save_progress(self):\n        if not self.progress_path:\n            return\n''',
    '''    def save_progress(self):\n        if not self.progress_path or getattr(self, "progress_write_blocked", False):\n            if getattr(self, "progress_write_blocked", False):\n                logging.warning("Progress save blocked to preserve unresolved source: %s", self.progress_path)\n            return\n''',
)
replace_one(
    "app.py",
    '''        data, backup, err = self.persistence.load_json_with_backup(restore_path)\n        if err:\n            logging.warning("Restore progress source was unreadable: %s", restore_path)\n            self._show_bad_json_warning("Restore progress", restore_path, backup, err)\n            return\n        if not isinstance(data, dict) or not isinstance(data.get("questions"), dict):\n            messagebox.showerror("Restore progress", "That file is not a valid progress JSON file.")\n            return\n        if self.progress_path.exists():\n            self.auto_backup_progress()\n        self.persistence.copy_file(restore_path, self.progress_path, label="restored progress")\n        self.load_progress_if_present()\n''',
    '''        questions = self.data["questions"] if self.data else None\n        _data, _backup, err = self.persistence.restore_progress_from_source(\n            restore_path, self.progress_path, questions\n        )\n        if err:\n            logging.warning("Restore progress rejected without modifying source: %s", restore_path)\n            messagebox.showerror("Restore progress", f"Could not restore progress safely:\\n{err}")\n            return\n        self.load_progress_if_present()\n''',
)
replace_one(
    "app.py",
    '''        records = self._progress_questions()\n        for q in questions:\n            rec = records.get(self._question_key(q))\n''',
    '''        records = self._progress_questions()\n        for q in questions:\n            rec = progress_record_for_question(records, q)\n''',
)
replace_one(
    "app.py",
    '''            "day": str(rec.get("last_seen") or ""),\n            "question_number": int(q.get("question_number") or 0),\n''',
    '''            "day": str(rec.get("last_seen") or ""),\n            "question_id": self._question_key(q),\n            "question_number": int(q.get("question_number") or 0),\n''',
)
replace_one(
    "app.py",
    '''    def question_volatility(self, q):\n        qnum = int((q or {}).get("question_number") or 0)\n        events = [event for event in self._progress_history() if int(event.get("question_number") or 0) == qnum]\n''',
    '''    def question_volatility(self, q):\n        events = [\n            event for event in self._progress_history() if history_event_matches_question(event, q)\n        ]\n''',
)

# ---------------------------------------------------------------------------
# Existing history consumers: canonical ID when available; numeric fallback is
# retained only for legacy events that predate Segment 1.
# ---------------------------------------------------------------------------
replace_one(
    "app_question_flow_mixin.py",
    '''from progress_store import (\n''',
    '''from question_identity import history_event_matches_question, question_for_history_event\nfrom progress_store import (\n''',
)
replace_all(
    "app_question_flow_mixin.py",
    '''if int(event.get("question_number") or 0) == int(q.get("question_number") or 0):''',
    '''if history_event_matches_question(event, q):''',
    minimum=1,
)
replace_one(
    "app_question_flow_mixin.py",
    '''        history_map: dict[int, list[dict[str, Any]]] = {}\n        for event in self._progress_history():\n            qnum = int(event.get("question_number") or 0)\n            if qnum not in concept_qnums:\n                continue\n            history_map.setdefault(qnum, []).append(event)\n''',
    '''        history_map: dict[int, list[dict[str, Any]]] = {}\n        for event in self._progress_history():\n            matched = question_for_history_event(event, concept_questions)\n            if matched is None:\n                continue\n            qnum = int(matched.get("question_number") or 0)\n            if qnum in concept_qnums:\n                history_map.setdefault(qnum, []).append(event)\n''',
)
replace_one(
    "app_game_mixin.py",
    '''from progress_store import''',
    '''from question_identity import history_event_matches_question\nfrom progress_store import''',
)
replace_one(
    "app_game_mixin.py",
    '''            qnum: [event for event in self._recent_history(28) if int(event.get("question_number") or 0) == qnum]\n''',
    '''            qnum: [event for event in self._recent_history(28) if history_event_matches_question(event, current_q)]\n''',
)

# Smart-practice measurement same-question correlation now refuses ID conflict.
replace_one(
    "smart_practice_measurement.py",
    '''from progress_store import now_iso\n''',
    '''from progress_store import now_iso\nfrom question_identity import canonical_question_id, history_event_question_id\n''',
)
replace_one(
    "smart_practice_measurement.py",
    '''def same_concept(prediction: Mapping[str, Any], event: Mapping[str, Any]) -> tuple[bool, str]:\n    if int(prediction.get("question_number") or 0) == int(event.get("question_number") or 0):\n        return True, "same_question"\n''',
    '''def same_concept(prediction: Mapping[str, Any], event: Mapping[str, Any]) -> tuple[bool, str]:\n    prediction_id = canonical_question_id(prediction)\n    event_id = history_event_question_id(event)\n    if prediction_id and event_id:\n        if prediction_id == event_id:\n            return True, "same_question"\n    elif int(prediction.get("question_number") or 0) == int(event.get("question_number") or 0):\n        return True, "same_question"\n''',
)

print("Applied BACKLOG-1 Segment-1 adversarial review repair package.")
