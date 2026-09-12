from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"repair anchor not found in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Measurement ledger: strict Boolean scoring and mutually exclusive terminality.
# ---------------------------------------------------------------------------
replace_once(
    "cand01r3_measurement.py",
    '''        existing = self._observations.get(question_id)\n        if existing is not None or kind in DUPLICATE_KINDS:\n''',
    '''        if question_id in self._unobserved:\n            return MeasurementObservation(\n                status=STATUS_DUPLICATE,\n                reason="LATE_NOT_PRIMARY",\n                question_id=question_id,\n                correct=None,\n                evaluation_identity=identity,\n            )\n        existing = self._observations.get(question_id)\n        if existing is not None or kind in DUPLICATE_KINDS:\n''',
)
replace_once(
    "cand01r3_measurement.py",
    '''            return observation\n        payload = {\n            "status": STATUS_PRIMARY,\n''',
    '''            return observation\n        if type(correct) is not bool:\n            return MeasurementObservation(\n                status=STATUS_NOT_ELIGIBLE,\n                reason="INVALID_MEASUREMENT_SCORE",\n                question_id=question_id,\n                correct=None,\n                evaluation_identity=identity,\n            )\n        payload = {\n            "status": STATUS_PRIMARY,\n''',
)
replace_once("cand01r3_measurement.py", '            "correct": bool(correct),\n', '            "correct": correct,\n')
replace_once("cand01r3_measurement.py", '                    "correct": bool(correct),\n', '                    "correct": correct,\n')
replace_once(
    "cand01r3_measurement.py",
    '''            correct=bool(correct),\n            evaluation_identity=identity,\n        )\n\n    def record_unobserved''',
    '''            correct=correct,\n            evaluation_identity=identity,\n        )\n\n    def record_unobserved''',
)
replace_once(
    "cand01r3_measurement.py",
    '''        qid = canonical_question_id(question_id)\n        identity = self._identity(qid)\n        payload = {\n''',
    '''        qid = canonical_question_id(question_id)\n        identity = self._identity(qid)\n        if self.is_contaminated(qid):\n            return MeasurementObservation(\n                status=STATUS_CONTAMINATED,\n                reason=self._contaminated[qid][0],\n                question_id=qid,\n                correct=None,\n                evaluation_identity=identity,\n            )\n        if qid in self._observations:\n            return MeasurementObservation(\n                status=STATUS_DUPLICATE,\n                reason="PRIMARY_ALREADY_TERMINAL",\n                question_id=qid,\n                correct=None,\n                evaluation_identity=identity,\n            )\n        if qid in self._unobserved:\n            return MeasurementObservation(\n                status=STATUS_DUPLICATE,\n                reason="UNOBSERVED_ALREADY_TERMINAL",\n                question_id=qid,\n                correct=None,\n                evaluation_identity=identity,\n            )\n        payload = {\n''',
)

# ---------------------------------------------------------------------------
# Protocol: fail-closed evidence parsing, stable local calendar, strict payloads.
# ---------------------------------------------------------------------------
replace_once(
    "cand01r3_protocol.py",
    "from datetime import UTC, datetime\n",
    "from datetime import UTC, date, datetime, timedelta\n",
)
replace_once(
    "cand01r3_protocol.py",
    '''    events: list[dict[str, Any]] = []\n    day_state: str = STATE_DAY_NOT_STARTED\n''',
    '''    events: list[dict[str, Any]] = []\n    day_state: str = STATE_DAY_NOT_STARTED\n    day1_local_date: str = ""\n    calendar_utc_offset_minutes: int | None = None\n    last_local_date: str = ""\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def _read_ledger_events(path: Path | None) -> list[dict[str, Any]]:\n    if path is None or not path.exists() or path.stat().st_size == 0:\n        return []\n    events: list[dict[str, Any]] = []\n    for line in path.read_text(encoding="utf-8").splitlines():\n        if not line.strip():\n            continue\n        try:\n            payload = json.loads(line)\n        except json.JSONDecodeError:\n            continue\n        if isinstance(payload, dict):\n            events.append(payload)\n    return events\n''',
    '''def _read_ledger_events(path: Path | None) -> list[dict[str, Any]]:\n    if path is None or not path.exists() or path.stat().st_size == 0:\n        return []\n    events: list[dict[str, Any]] = []\n    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):\n        if not line.strip():\n            continue\n        try:\n            payload = json.loads(line)\n        except json.JSONDecodeError as exc:\n            raise Cand01R3AuthorityError("EMPIRICAL_LEDGER_CORRUPT") from exc\n        if not isinstance(payload, dict):\n            raise Cand01R3AuthorityError("EMPIRICAL_LEDGER_CORRUPT")\n        events.append(payload)\n    return events\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def scheduled_probe_ids_for_day(scheduled_day: int) -> set[str]:\n    protocol = _SESSION.protocol or build_protocol()\n    return {\n        str(row["question_id"])\n        for row in protocol.get("schedule") or []\n        if int(row.get("scheduled_day") or 0) == int(scheduled_day)\n    }\n\n\ndef todays_scheduled_probe_ids() -> set[str]:\n''',
    '''def ordered_scheduled_probe_ids_for_day(scheduled_day: int) -> list[str]:\n    protocol = _SESSION.protocol or build_protocol()\n    return [\n        str(row["question_id"])\n        for row in protocol.get("schedule") or []\n        if int(row.get("scheduled_day") or 0) == int(scheduled_day)\n    ]\n\n\ndef scheduled_probe_ids_for_day(scheduled_day: int) -> set[str]:\n    return set(ordered_scheduled_probe_ids_for_day(scheduled_day))\n\n\ndef todays_scheduled_probe_ids() -> set[str]:\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def _restore_ledger_from_events(ledger: MeasurementLedger, events: Sequence[Mapping[str, Any]]) -> None:\n    for event in events:\n        question_id = canonical_question_id(str(event.get("question_id") or ""))\n        if not question_id:\n            continue\n        status = str(event.get("status") or "")\n        if status == STATUS_PRIMARY:\n            identity_raw = event.get("evaluation_id") or []\n            identity = (\n                tuple(str(part) for part in identity_raw)\n                if isinstance(identity_raw, list) and len(identity_raw) == 4\n                else ledger._identity(question_id)\n            )\n            ledger._observations[question_id] = {\n                "status": STATUS_PRIMARY,\n                "reason": event.get("reason") or "OK",\n                "question_id": question_id,\n                "correct": event.get("correct"),\n                "selected_option_ids": list(event.get("selected_option_ids") or []),\n                "evaluation_identity": identity,\n            }\n        elif status == STATUS_UNOBSERVED:\n            ledger._unobserved[question_id] = {\n                "status": STATUS_UNOBSERVED,\n                "reason": event.get("reason") or "UNOBSERVED",\n                "question_id": question_id,\n                "correct": None,\n            }\n        elif status == STATUS_CONTAMINATED or event.get("contaminated"):\n            ledger.record_contamination(\n                question_id, str(event.get("contamination_reason") or event.get("reason") or "CONTAMINATED")\n            )\n''',
    '''def _restore_ledger_from_events(ledger: MeasurementLedger, events: Sequence[Mapping[str, Any]]) -> None:\n    for event in events:\n        question_id = canonical_question_id(str(event.get("question_id") or ""))\n        if not question_id:\n            continue\n        status = str(event.get("status") or "")\n        if status == STATUS_CONTAMINATED or event.get("contaminated"):\n            ledger.record_contamination(\n                question_id, str(event.get("contamination_reason") or event.get("reason") or "CONTAMINATED")\n            )\n            continue\n        if status == STATUS_PRIMARY:\n            if question_id in ledger._unobserved or ledger.is_contaminated(question_id):\n                continue\n            if question_id in ledger._observations:\n                continue\n            if type(event.get("correct")) is not bool:\n                raise Cand01R3AuthorityError("INVALID_MEASUREMENT_SCORE")\n            identity_raw = event.get("evaluation_id") or []\n            identity = (\n                tuple(str(part) for part in identity_raw)\n                if isinstance(identity_raw, list) and len(identity_raw) == 4\n                else ledger._identity(question_id)\n            )\n            ledger._observations[question_id] = {\n                "status": STATUS_PRIMARY,\n                "reason": event.get("reason") or "OK",\n                "question_id": question_id,\n                "correct": event.get("correct"),\n                "selected_option_ids": list(event.get("selected_option_ids") or []),\n                "evaluation_identity": identity,\n            }\n        elif status == STATUS_UNOBSERVED:\n            if question_id in ledger._observations or ledger.is_contaminated(question_id) or question_id in ledger._unobserved:\n                continue\n            ledger._unobserved[question_id] = {\n                "status": STATUS_UNOBSERVED,\n                "reason": event.get("reason") or "UNOBSERVED",\n                "question_id": question_id,\n                "correct": None,\n            }\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def _restore_session_from_events(events: Sequence[Mapping[str, Any]]) -> None:\n    train_log: list[dict[str, Any]] = []\n    restored_events: list[dict[str, Any]] = []\n    current_day: int | None = None\n    for event in events:\n''',
    '''def _restore_session_from_events(events: Sequence[Mapping[str, Any]]) -> None:\n    train_log: list[dict[str, Any]] = []\n    restored_events: list[dict[str, Any]] = []\n    current_day: int | None = None\n    day1_local_date = ""\n    calendar_utc_offset_minutes: int | None = None\n    last_local_date = ""\n    for event in events:\n        event_day1 = str(event.get("day1_local_date") or "")\n        if event_day1 and not day1_local_date:\n            day1_local_date = event_day1\n        if event.get("calendar_utc_offset_minutes") is not None and calendar_utc_offset_minutes is None:\n            calendar_utc_offset_minutes = int(event.get("calendar_utc_offset_minutes"))\n        event_local_date = str(event.get("calendar_local_date") or "")\n        if event_local_date and (not last_local_date or event_local_date > last_local_date):\n            last_local_date = event_local_date\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''    _SESSION.current_scheduled_day = current_day\n    if _SESSION.ledger is not None:\n''',
    '''    _SESSION.current_scheduled_day = current_day\n    _SESSION.day1_local_date = day1_local_date\n    _SESSION.calendar_utc_offset_minutes = calendar_utc_offset_minutes\n    _SESSION.last_local_date = last_local_date\n    if _SESSION.ledger is not None:\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def _observation_from_payload(payload: Mapping[str, Any], status: str, reason: str) -> MeasurementObservation:\n''',
    '''def _current_experiment_local_date() -> str:\n    if _SESSION.calendar_utc_offset_minutes is not None:\n        local_now = datetime.now(UTC) + timedelta(minutes=int(_SESSION.calendar_utc_offset_minutes))\n        return local_now.date().isoformat()\n    return datetime.now().astimezone().date().isoformat()\n\n\ndef _current_utc_offset_minutes() -> int:\n    offset = datetime.now().astimezone().utcoffset()\n    return int((offset.total_seconds() if offset is not None else 0) // 60)\n\n\ndef _calendar_fields() -> dict[str, Any]:\n    return {\n        "calendar_local_date": _current_experiment_local_date(),\n        "day1_local_date": _SESSION.day1_local_date,\n        "calendar_utc_offset_minutes": _SESSION.calendar_utc_offset_minutes,\n    }\n\n\ndef _observation_from_payload(payload: Mapping[str, Any], status: str, reason: str) -> MeasurementObservation:\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''        correct=None if correct is None else bool(correct),\n''',
    '''        correct=correct if type(correct) is bool else None,\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''        correct=correct if status == STATUS_PRIMARY else (bool(correct) if correct is not None else None),\n''',
    '''        correct=correct if type(correct) is bool else None,\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''        "calendar_timestamp": calendar_timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),\n        "scheduled_day": scheduled_day,\n''',
    '''        "calendar_timestamp": calendar_timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),\n        **_calendar_fields(),\n        "scheduled_day": scheduled_day,\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''    observation = _SESSION.ledger.record_unobserved(qid, reason=reason)\n    payload = _event_payload(\n        question_id=qid,\n        status=STATUS_UNOBSERVED,\n        reason=reason,\n''',
    '''    observation = _SESSION.ledger.record_unobserved(qid, reason=reason)\n    payload = _event_payload(\n        question_id=qid,\n        status=observation.status,\n        reason=observation.reason,\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''    _append_ledger(payload, Path(ledger_path) if ledger_path else _SESSION.ledger_path)\n    _SESSION.events.append(payload)\n    _lock_if_real(payload)\n    result = _observation_from_payload(payload, STATUS_UNOBSERVED, reason)\n    result.correct = None\n    result.counts_toward_primary = False\n    measurement_runtime_state()\n    return result\n''',
    '''    _append_ledger(payload, Path(ledger_path) if ledger_path else _SESSION.ledger_path)\n    _SESSION.events.append(payload)\n    _lock_if_real(payload)\n    result = _observation_from_payload(payload, observation.status, observation.reason)\n    result.correct = None\n    result.counts_toward_primary = False\n    measurement_runtime_state()\n    return result\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def set_measurement_day(scheduled_day: int) -> str:\n    new_day = int(scheduled_day)\n    _policy_row(new_day)\n    current = _SESSION.current_scheduled_day\n    if _SESSION.active:\n        if current is not None and int(current) != new_day and not _day_is_complete(int(current)):\n            raise Cand01R3AuthorityError("PREVIOUS_DAY_INCOMPLETE")\n        for prior in range(1, new_day):\n            if not _day_is_complete(prior):\n                raise Cand01R3AuthorityError("PREVIOUS_DAY_INCOMPLETE")\n    policy_id = allocated_policy_for_day(new_day)\n    _SESSION.current_scheduled_day = new_day\n''',
    '''def set_measurement_day(scheduled_day: int) -> str:\n    new_day = int(scheduled_day)\n    _policy_row(new_day)\n    current = _SESSION.current_scheduled_day\n    local_date = _current_experiment_local_date()\n    if _SESSION.active:\n        if current is not None and int(current) != new_day and not _day_is_complete(int(current)):\n            raise Cand01R3AuthorityError("PREVIOUS_DAY_INCOMPLETE")\n        for prior in range(1, new_day):\n            if not _day_is_complete(prior):\n                raise Cand01R3AuthorityError("PREVIOUS_DAY_INCOMPLETE")\n        if _SESSION.last_local_date and local_date < _SESSION.last_local_date:\n            raise Cand01R3AuthorityError("MEASUREMENT_CLOCK_REGRESSION")\n        if not _SESSION.day1_local_date:\n            if new_day != 1:\n                raise Cand01R3AuthorityError("DAY1_CALENDAR_ANCHOR_MISSING")\n            _SESSION.day1_local_date = local_date\n            _SESSION.calendar_utc_offset_minutes = _current_utc_offset_minutes()\n        anchor = date.fromisoformat(_SESSION.day1_local_date)\n        earliest = anchor + timedelta(days=new_day - 1)\n        if date.fromisoformat(local_date) < earliest:\n            raise Cand01R3AuthorityError("MEASUREMENT_DAY_TOO_EARLY")\n        _SESSION.last_local_date = local_date\n    policy_id = allocated_policy_for_day(new_day)\n    _SESSION.current_scheduled_day = new_day\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''            "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),\n            "counted": False,\n            **_session_identity_fields(),\n''',
    '''            "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),\n            **_calendar_fields(),\n            "counted": False,\n            **_session_identity_fields(),\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),\n        "counted": False,\n        **_session_identity_fields(),\n''',
    '''        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),\n        **_calendar_fields(),\n        "counted": False,\n        **_session_identity_fields(),\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''        "probe_ids": sorted(todays_scheduled_probe_ids()),\n''',
    '''        "probe_ids": ordered_scheduled_probe_ids_for_day(int(day)),\n''',
)
replace_once(
    "cand01r3_protocol.py",
    '''def notify_scored_attempt(\n''',
    '''def score_measurement_probe_answer(question: Mapping[str, Any], selected: Sequence[str] | None = None) -> bool:\n    correct = question.get("correct")\n    if not isinstance(correct, (list, tuple, set)) or not correct:\n        raise Cand01R3AuthorityError("INVALID_MEASUREMENT_ANSWER_KEY")\n    selected_ids = {str(value) for value in (selected or [])}\n    correct_ids = {str(value) for value in correct}\n    return selected_ids == correct_ids\n\n\ndef record_measurement_probe_answer(\n    question: Mapping[str, Any],\n    *,\n    selected: Sequence[str] | None = None,\n) -> MeasurementObservation:\n    correct = score_measurement_probe_answer(question, selected)\n    return record_measurement_event(question, selected=list(selected or []), correct=correct, kind="SCORED")\n\n\ndef notify_scored_attempt(\n''',
)

# ---------------------------------------------------------------------------
# Runtime: frozen probe order, restore revalidation, and learner-facing redaction.
# ---------------------------------------------------------------------------
replace_once(
    "cand01r3_runtime.py",
    '''def _todays_measurement_probe_ids() -> set[str] | None:\n''',
    '''def is_measurement_answer_mode() -> bool:\n    return bool(is_cand01r3_active() and get_context().intended_use == INTENDED_USE_MEASUREMENT)\n\n\ndef _todays_measurement_probe_ids() -> set[str] | None:\n''',
)
replace_once(
    "cand01r3_runtime.py",
    '''    return todays_scheduled_probe_ids()\n\n\ndef filter_training_questions''',
    '''    return todays_scheduled_probe_ids()\n\n\ndef _todays_measurement_probe_order() -> list[str] | None:\n    try:\n        from cand01r3_protocol import current_measurement_session, ordered_scheduled_probe_ids_for_day\n    except ImportError:\n        return None\n    session = current_measurement_session()\n    if not is_measurement_answer_mode() or session.current_scheduled_day is None:\n        return None\n    return ordered_scheduled_probe_ids_for_day(int(session.current_scheduled_day))\n\n\ndef filter_training_questions''',
)
replace_once(
    "cand01r3_runtime.py",
    '''    if measurement_ids is not None and intended == INTENDED_USE_MEASUREMENT:\n        probes = filter_questions(pool, INTENDED_USE_MEASUREMENT, current_authority())\n        return [question for question in probes if canonical_question_id(question) in measurement_ids]\n''',
    '''    if measurement_ids is not None and intended == INTENDED_USE_MEASUREMENT:\n        probes = filter_questions(pool, INTENDED_USE_MEASUREMENT, current_authority())\n        by_id = {canonical_question_id(question): question for question in probes}\n        order = _todays_measurement_probe_order() or sorted(measurement_ids)\n        return [by_id[question_id] for question_id in order if question_id in by_id]\n''',
)
replace_once(
    "cand01r3_runtime.py",
    '''    eligible = filter_questions(source, context.intended_use or INTENDED_USE_TRAINING, current_authority())\n    return RestoreResult(accepted=True, reason="REVALIDATED", questions=eligible)\n''',
    '''    if context.intended_use == INTENDED_USE_MEASUREMENT:\n        eligible = filter_training_questions(pool, stage="MEASUREMENT")\n        expected_ids = [canonical_question_id(question) for question in eligible]\n        if requested_ids and requested_ids != expected_ids:\n            return RestoreResult(accepted=False, reason="STALE_MEASUREMENT_SESSION", questions=[])\n        return RestoreResult(accepted=True, reason="REVALIDATED_MEASUREMENT", questions=eligible)\n    eligible = filter_questions(source, context.intended_use or INTENDED_USE_TRAINING, current_authority())\n    return RestoreResult(accepted=True, reason="REVALIDATED", questions=eligible)\n''',
)
replace_once(
    "cand01r3_runtime.py",
    '''def _is_probe_question(question_id: str) -> bool:\n''',
    '''def _is_probe_question(question_id: str) -> bool:\n''',
)
replace_once(
    "cand01r3_runtime.py",
    '''    return item.get("role") == ROLE_PROBE\n\n\ndef sanitize_learner_export''',
    '''    return item.get("role") == ROLE_PROBE\n\n\ndef is_measurement_probe_question(question: Mapping[str, Any] | str) -> bool:\n    return _is_probe_question(canonical_question_id(question))\n\n\ndef _redacted_probe_row(row: Mapping[str, Any], question_id: str) -> dict[str, Any]:\n    status = str(row.get("measurement_status") or row.get("status") or ("RECORDED" if row.get("answered") else "PENDING"))\n    return {\n        "question_id": question_id,\n        "scheduled_day": row.get("scheduled_day"),\n        "status": status,\n        "observed": bool(row.get("observed", row.get("answered", status == "RECORDED"))),\n        "redacted": True,\n    }\n\n\ndef sanitize_learner_export''',
)
replace_once(
    "cand01r3_runtime.py",
    '''            kept = {\n                "question_id": question_id,\n                "selected_option_ids": list(row.get("selected") or row.get("selected_option_ids") or []),\n                "correct": row.get("correct"),\n                "redacted": True,\n            }\n            redacted_rows.append(kept)\n''',
    '''            redacted_rows.append(_redacted_probe_row(row, question_id))\n''',
)
replace_once(
    "cand01r3_runtime.py",
    '''    payload["question_id"] = question_id\n    payload.pop("selected_texts", None)\n    payload.pop("correct_texts", None)\n    payload.pop("prompt", None)\n    payload.pop("explanation", None)\n    payload["redacted"] = True\n    return payload\n''',
    '''    return _redacted_probe_row(payload, question_id)\n\n\ndef sanitize_measurement_answer_state(question: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:\n    payload = dict(state)\n    if not is_cand01r3_active() or not is_measurement_probe_question(question):\n        return payload\n    return {\n        "answered": bool(payload.get("answered")),\n        "selected": [],\n        "pending": [],\n        "flagged": bool(payload.get("flagged")),\n        "suspended": bool(payload.get("suspended")),\n        "last_confidence": "",\n        "last_miss_reason": "",\n        "measurement_status": str(question.get("measurement_status") or ("RECORDED" if payload.get("answered") else "PENDING")),\n        "redacted": True,\n    }\n''',
)

# ---------------------------------------------------------------------------
# Question flow: reject/record PROBE before any learner-state mutation.
# ---------------------------------------------------------------------------
replace_once(
    "app_question_flow_mixin.py",
    '''    is_cand01r3_active,\n    partition_cache_identity,\n''',
    '''    is_cand01r3_active,\n    is_measurement_answer_mode,\n    partition_cache_identity,\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def _record_answer(\n''',
    '''    def _record_measurement_probe_answer(self, q: QuestionRuntimeState, selected: list[str]):\n        from cand01r3_protocol import record_measurement_probe_answer\n\n        observation = record_measurement_probe_answer(q, selected=list(selected))\n        if observation.status in {"PRIMARY", "CONTAMINATED", "DUPLICATE_NOT_PRIMARY"}:\n            q["selected"] = []\n            q["pending"] = []\n            q["answered"] = True\n            q["recall_ready"] = False\n            q["last_confidence"] = ""\n            q["last_miss_reason"] = ""\n            q["measurement_status"] = observation.status\n            q["measurement_recorded"] = True\n            self.active_question_started_qnum = None\n            self.active_question_started_at = None\n            self.mark_question_list_dirty()\n            self.schedule_session_save(delay_ms=125)\n            self.render_question()\n        return observation\n\n    def _record_answer(\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    ):\n        rec_before = self._progress_record(q, create=False)\n''',
    '''    ):\n        if is_measurement_answer_mode():\n            return self._record_measurement_probe_answer(q, selected)\n        rec_before = self._progress_record(q, create=False)\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''        if s == "Correct in session" and (not q.get("answered") or not self._question_correct(q)):\n            return False\n        if s == "Wrong in session" and (not q.get("answered") or self._question_correct(q)):\n            return False\n''',
    '''        if is_measurement_answer_mode() and s in {"Correct in session", "Wrong in session"}:\n            return False\n        if s == "Correct in session" and (not q.get("answered") or not self._question_correct(q)):\n            return False\n        if s == "Wrong in session" and (not q.get("answered") or self._question_correct(q)):\n            return False\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''            if q.get("answered"):\n                status = "OK" if self._question_correct(q) else "X"\n                if self.active_session_mode == MODE_EXAM and not self.exam_reveal:\n                    status = "R"\n''',
    '''            if q.get("answered"):\n                if is_measurement_answer_mode():\n                    status = "R"\n                else:\n                    status = "OK" if self._question_correct(q) else "X"\n                    if self.active_session_mode == MODE_EXAM and not self.exam_reveal:\n                        status = "R"\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def retag_current_answer_confidence(self, confidence):\n        if not self.questions:\n''',
    '''    def retag_current_answer_confidence(self, confidence):\n        if is_measurement_answer_mode():\n            return\n        if not self.questions:\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def mark_current_question_super_confident(self):\n        if not self.questions:\n''',
    '''    def mark_current_question_super_confident(self):\n        if is_measurement_answer_mode():\n            return\n        if not self.questions:\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def _question_resolved_for_finish(self, q):\n        return bool(q.get("answered") or q.get("flagged") or q.get("suspended"))\n''',
    '''    def _question_resolved_for_finish(self, q):\n        if is_measurement_answer_mode():\n            return bool(q.get("answered"))\n        return bool(q.get("answered") or q.get("flagged") or q.get("suspended"))\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def finish_exam(self):\n        if self.active_session_mode != MODE_EXAM:\n''',
    '''    def finish_exam(self):\n        if is_measurement_answer_mode():\n            if not self._all_session_questions_resolved_for_finish():\n                messagebox.showinfo("Finish measurement", "Record a response for every scheduled PROBE before finishing.")\n                return\n            self.schedule_session_save(delay_ms=0)\n            self.render_question()\n            return\n        if self.active_session_mode != MODE_EXAM:\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def toggle_flag(self):\n        q = self.current_question()\n        q["flagged"] = not q.get("flagged", False)\n        self.update_progress_for_flag(q)\n''',
    '''    def toggle_flag(self):\n        q = self.current_question()\n        q["flagged"] = not q.get("flagged", False)\n        if is_measurement_answer_mode():\n            self.mark_question_list_dirty()\n            self.schedule_session_save()\n            self._render_current_view(save_session=False)\n            return\n        self.update_progress_for_flag(q)\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def toggle_suspend(self):\n        q = self.current_question()\n        q["suspended"] = not q.get("suspended", False)\n        self.update_progress_for_suspended(q)\n''',
    '''    def toggle_suspend(self):\n        q = self.current_question()\n        q["suspended"] = not q.get("suspended", False)\n        if is_measurement_answer_mode():\n            self.mark_question_list_dirty()\n            self.schedule_session_save()\n            self._render_current_view(save_session=False)\n            return\n        self.update_progress_for_suspended(q)\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def redo_question(self):\n        if not self.questions:\n''',
    '''    def redo_question(self):\n        if is_measurement_answer_mode():\n            return\n        if not self.questions:\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def maybe_auto_next_after_answer(self, q):\n        if not self.auto_next_correct_var.get():\n''',
    '''    def maybe_auto_next_after_answer(self, q):\n        if is_measurement_answer_mode():\n            return\n        if not self.auto_next_correct_var.get():\n''',
)
replace_once(
    "app_question_flow_mixin.py",
    '''    def format_choice_explanations(self, q):\n        selected = sorted(q.get("selected", []))\n''',
    '''    def format_choice_explanations(self, q):\n        if is_measurement_answer_mode():\n            return "Response recorded."\n        selected = sorted(q.get("selected", []))\n''',
)

# ---------------------------------------------------------------------------
# Rendering: correctness-blind neutral measurement UI.
# ---------------------------------------------------------------------------
replace_once(
    "app_question_render_mixin.py",
    '''from cand01r3_runtime import get_context, is_cand01r3_active, revalidate_training_question\n''',
    '''from cand01r3_runtime import get_context, is_cand01r3_active, is_measurement_answer_mode, revalidate_training_question\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''    def _question_answer_meta(self, q, ladder_stage):\n        answer_meta = []\n''',
    '''    def _question_answer_meta(self, q, ladder_stage):\n        if is_measurement_answer_mode():\n            return []\n        answer_meta = []\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''    def _inline_explanation_for_question(self, q, show_exam_feedback):\n        inline_explanation_text = ''\n''',
    '''    def _inline_explanation_for_question(self, q, show_exam_feedback):\n        if is_measurement_answer_mode():\n            return None, ''\n        inline_explanation_text = ''\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''        self.redo_btn.configure(state='normal' if q.get('answered') and (self.active_session_mode != MODE_EXAM or self.exam_reveal) else 'disabled')\n''',
    '''        self.redo_btn.configure(state='disabled' if is_measurement_answer_mode() else ('normal' if q.get('answered') and (self.active_session_mode != MODE_EXAM or self.exam_reveal) else 'disabled'))\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''            if not show_exam_feedback:\n                self.status_label.configure(text='Answer recorded', bg='#eef4fb', fg=BLUE)\n''',
    '''            if not show_exam_feedback:\n                self.status_label.configure(text=('Response recorded.' if is_measurement_answer_mode() else 'Answer recorded'), bg='#eef4fb', fg=BLUE)\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''        show_exam_feedback = not (self.active_session_mode == MODE_EXAM and not self.exam_reveal)\n''',
    '''        show_exam_feedback = False if is_measurement_answer_mode() else not (self.active_session_mode == MODE_EXAM and not self.exam_reveal)\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''            correct=bool(self._question_correct(q)),\n''',
    '''            correct=(False if is_measurement_answer_mode() else bool(self._question_correct(q))),\n''',
)
replace_once(
    "app_question_render_mixin.py",
    '''        self.refresh_analytics_window()\n        if self.scroll_to_top_on_render:\n''',
    '''        if not is_measurement_answer_mode():\n            self.refresh_analytics_window()\n        if self.scroll_to_top_on_render:\n''',
)

# ---------------------------------------------------------------------------
# Session/checkpoint custody: exact probe order and redacted answer state.
# ---------------------------------------------------------------------------
replace_once(
    "app_session_persistence_mixin.py",
    '''    filter_training_questions,\n    is_cand01r3_active,\n    persistable_authority_metadata,\n''',
    '''    filter_training_questions,\n    is_cand01r3_active,\n    is_measurement_answer_mode,\n    persistable_authority_metadata,\n    sanitize_measurement_answer_state,\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''        if is_cand01r3_active():\n            pool = filter_training_questions(pool)\n            if not pool:\n                return\n        if count != 'All visible':\n''',
    '''        if is_cand01r3_active():\n            pool = filter_training_questions(pool)\n            if not pool:\n                return\n        measurement_mode = is_measurement_answer_mode()\n        if measurement_mode:\n            count = 'All visible'\n            randomize = False\n        if count != 'All visible':\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''        pool = self._clone_questions(pool)\n        self.answer_order_epoch += 1\n        pool = self._apply_adaptive_answer_order(pool)\n        if randomize:\n''',
    '''        pool = self._clone_questions(pool)\n        self.answer_order_epoch += 1\n        if not measurement_mode:\n            pool = self._apply_adaptive_answer_order(pool)\n        if randomize:\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''        self.session_answer_history = list(migrated.get('session_answer_history', []))\n''',
    '''        self.session_answer_history = [] if is_measurement_answer_mode() else list(migrated.get('session_answer_history', []))\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''        if saved_qnums and saved_qnums != current_qnums:\n''',
    '''        if saved_qnums and saved_qnums != current_qnums and not is_measurement_answer_mode():\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''            existing = self._progress_record(q, create=False)\n            if q.get('answered') and not int((existing or {}).get('attempts', 0)):\n''',
    '''            existing = self._progress_record(q, create=False)\n            if is_measurement_answer_mode():\n                continue\n            if q.get('answered') and not int((existing or {}).get('attempts', 0)):\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''            session_answer_history=list(self.session_answer_history),\n''',
    '''            session_answer_history=([] if is_measurement_answer_mode() else list(self.session_answer_history)),\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''            answers=[serialize_answer_state(q) for q in self.questions],\n''',
    '''            answers=[sanitize_measurement_answer_state(q, serialize_answer_state(q)) for q in self.questions],\n''',
)
replace_once(
    "app_session_persistence_mixin.py",
    '''                    'answers': [serialize_answer_state(q) for q in self.questions],\n''',
    '''                    'answers': [sanitize_measurement_answer_state(q, serialize_answer_state(q)) for q in self.questions],\n''',
)

print("CAND-01R3 measurement-integrity repair applied")
