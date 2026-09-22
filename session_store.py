import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from app_constants import MODE_EXAM, MODE_PRACTICE, MODE_SMART_PRACTICE
from builder_identity import canonical_builder_identity as canonical_builder_identity
from builder_identity import normalize_builder_context as normalize_builder_context
from builder_identity import resolve_builder_identity_from_snapshot as resolve_builder_identity_from_snapshot
from fingerprint_identity import (
    FINGERPRINT_ALGORITHM,
    FINGERPRINT_SCHEMA_VERSION,
    RUNTIME_FINGERPRINT_DOMAIN,
    RUNTIME_LOADER_CONTRACT_VERSION,
    progress_runtime_identity_metadata,
)
from session_identity import (
    SESSION_IDENTITY_KIND,
    SESSION_IDENTITY_VERSION,
    canonical_session_signature,
)
from session_models import (
    AnswerState,
    BuilderContext,
    QuestProgressState,
    SessionAnswerEvent,
    SessionAnswerState,
    SessionSnapshot,
    answer_state_from_question,
)

SESSION_SCHEMA_VERSION = 5
PREVIOUS_CANONICAL_SESSION_SCHEMA_VERSION = 4
LEGACY_SESSION_SCHEMA_VERSION = 3
SUPPORTED_SESSION_MODES = {MODE_PRACTICE, MODE_SMART_PRACTICE, MODE_EXAM}


def _runtime_identity_metadata(bank_fingerprint: str) -> dict[str, Any]:
    bank_node_id = ""
    try:
        from content_fingerprint_bridge import runtime_bank_node_id_for_fingerprint

        bank_node_id = runtime_bank_node_id_for_fingerprint(bank_fingerprint)
    except Exception:
        pass
    return progress_runtime_identity_metadata(bank_fingerprint, bank_node_id=bank_node_id)


def _validate_session_fingerprint_metadata(payload: Mapping[str, Any]) -> None:
    if int(payload.get("fingerprint_schema_version") or 0) != FINGERPRINT_SCHEMA_VERSION:
        raise ValueError("Unsupported fingerprint schema version.")
    if str(payload.get("fingerprint_domain") or "").strip() != RUNTIME_FINGERPRINT_DOMAIN:
        raise ValueError("Unsupported fingerprint domain.")
    if str(payload.get("fingerprint_algorithm") or "").strip() != FINGERPRINT_ALGORITHM:
        raise ValueError("Unsupported fingerprint algorithm.")
    if int(payload.get("loader_contract_version") or 0) != RUNTIME_LOADER_CONTRACT_VERSION:
        raise ValueError("Unsupported runtime loader contract version.")


def calculate_session_question_limit(base_count: int) -> int:
    try:
        base = max(0, int(base_count or 0))
    except (TypeError, ValueError):
        base = 0
    return base


def session_signature(mode: str, question_numbers: list[Any]) -> str:
    raw = f"{str(mode or '').strip()}|{'/'.join(str(qnum) for qnum in question_numbers)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def runtime_bank_stem(bank_path: Path) -> str:
    stem = bank_path.stem
    for suffix in ("_clean", "_plus_studyguide"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def session_file_path(
    user_data_dir: Path,
    bank_path: Path,
    mode: str,
    question_numbers: list[Any],
    *,
    bank_fingerprint: str | None = None,
    question_ids: list[str] | None = None,
    builder_context_fingerprint: str | None = None,
) -> Path:
    safe_mode = str(mode or "").lower().replace(" ", "_").replace("/", "_")
    if bank_fingerprint is None and question_ids is None:
        count = len(question_numbers)
        signature = session_signature(mode, question_numbers)
        return user_data_dir / f"{runtime_bank_stem(bank_path)}_{safe_mode}_session_{count}_{signature}.json"
    if bank_fingerprint and question_ids:
        count = len(question_ids)
        signature = canonical_session_signature(mode, bank_fingerprint, question_ids)
        name = f"{runtime_bank_stem(bank_path)}_{safe_mode}_session_{count}_{signature}"
        if builder_context_fingerprint is not None:
            fingerprint = str(builder_context_fingerprint).strip()
            if not fingerprint:
                raise ValueError("Builder context fingerprint cannot be blank when provided.")
            name = f"{name}_{fingerprint[:12]}"
        return user_data_dir / f"{name}.json"
    raise ValueError("Canonical session file identity requires fingerprint and question IDs together.")


def checkpoint_file_path(checkpoint_dir: Path, bank_path: Path, mode: str, answered_count: int) -> Path:
    safe_mode = str(mode or "").lower().replace(" ", "_")
    return checkpoint_dir / f"{runtime_bank_stem(bank_path)}_{safe_mode}_checkpoint_{answered_count}.json"


def progress_file_path(user_data_dir: Path, bank_path: Path) -> Path:
    return user_data_dir / f"{runtime_bank_stem(bank_path)}_progress.json"


def legacy_session_file_path(bank_path: Path, mode: str) -> Path:
    safe_mode = str(mode or "").lower().replace(" ", "_").replace("/", "_")
    return bank_path.with_name(f"{runtime_bank_stem(bank_path)}_{safe_mode}_session.json")


def legacy_progress_file_path(bank_path: Path) -> Path:
    return bank_path.with_name(f"{runtime_bank_stem(bank_path)}_progress.json")


def serialize_answer_state(question: Mapping[str, Any]) -> AnswerState:
    return answer_state_from_question(question)


def _snapshot_builder_identity(
    payload: Mapping[str, Any] | None,
    *,
    saved_mode: str,
    source_label: str,
    question_count: Any,
    builder_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if builder_context is not None:
        raw = dict(builder_context)
        if not raw.get("mode"):
            raw["mode"] = saved_mode
        if not raw.get("source_label"):
            raw["source_label"] = source_label
        identity = canonical_builder_identity(raw)
        return dict(identity)
    return dict(
        resolve_builder_identity_from_snapshot(
            payload,
            saved_mode=saved_mode,
            source_label=source_label,
            question_count=question_count,
        )
    )


def _coerce_int(value: Any, *, field: str, default: int = 0, minimum: int | None = None) -> int:
    if value in (None, ""):
        number = default
    else:
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid integer for {field}: {value!r}") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"Invalid integer for {field}: {number!r}")
    return number


def _coerce_str_list(value: Any, *, field: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"Invalid list for {field}")
    return [str(item) for item in value]


def _coerce_int_list(value: Any, *, field: str, minimum: int = 0) -> list[int]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"Invalid list for {field}")
    return [_coerce_int(item, field=field, minimum=minimum) for item in value]


def _coerce_canonical_id_list(value: Any, *, field: str, required: bool = False) -> list[str]:
    if value in (None, ""):
        if required:
            raise ValueError(f"Missing canonical question IDs for {field}.")
        return []
    if not isinstance(value, list):
        raise ValueError(f"Invalid list for {field}")
    ids = [str(item or "").strip() for item in value]
    if required and (not ids or any(not item for item in ids)):
        raise ValueError(f"Missing canonical question IDs for {field}.")
    if any(not item for item in ids):
        raise ValueError(f"Blank canonical question ID in {field}.")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate canonical question ID in {field}.")
    return ids


def answer_states_by_question_id(answers: list[Mapping[str, Any]]) -> dict[str, SessionAnswerState]:
    by_id: dict[str, SessionAnswerState] = {}
    for answer in answers:
        if not isinstance(answer, Mapping):
            raise ValueError("Session answer row must be a mapping.")
        row = cast(SessionAnswerState, dict(answer))
        question_id = str(row.get("question_id") or "").strip()
        if not question_id:
            raise ValueError("Canonical session answer row is missing question_id.")
        if question_id in by_id:
            raise ValueError("Duplicate canonical question ID in session answers.")
        by_id[question_id] = row
    return by_id


def migrate_session_snapshot(
    saved: Mapping[str, Any] | None,
    mode: str,
    question_numbers: list[Any],
    *,
    available_question_numbers: list[Any] | None = None,
    bank_fingerprint: str | None = None,
    question_ids: list[str] | None = None,
    restore_question_ids: list[str] | None = None,
    available_question_ids: list[str] | None = None,
    allow_legacy: bool = False,
) -> SessionSnapshot:
    payload = dict(saved or {})
    current_qnums = [
        _coerce_int(qnum, field="question_numbers", minimum=1) for qnum in question_numbers if str(qnum).strip()
    ]
    saved_mode = str(payload.get("mode") or mode or "")
    if saved_mode not in SUPPORTED_SESSION_MODES:
        raise ValueError(f"Unsupported session mode: {saved_mode!r}")

    schema_version = _coerce_int(
        payload.get("schema_version") or 1,
        field="schema_version",
        default=1,
        minimum=1,
    )
    if schema_version > SESSION_SCHEMA_VERSION:
        raise ValueError(f"Unsupported future session schema: {schema_version}")
    canonical_snapshot = schema_version >= PREVIOUS_CANONICAL_SESSION_SCHEMA_VERSION or any(
        key in payload
        for key in (
            "bank_fingerprint",
            "restore_question_ids",
            "session_identity",
            "session_identity_version",
        )
    )
    if not canonical_snapshot and not allow_legacy:
        raise ValueError("Legacy ordinary session lacks canonical bank/question identity authority.")

    raw_saved_qnums = payload.get("question_numbers", [])
    if raw_saved_qnums not in (None, "") and not isinstance(raw_saved_qnums, list):
        raise ValueError("Session question_numbers must be a list.")
    saved_qnums = [
        _coerce_int(qnum, field="question_numbers", minimum=1) for qnum in raw_saved_qnums if str(qnum).strip()
    ]
    raw_restore_qnums = payload.get("restore_question_numbers", [])
    if raw_restore_qnums not in (None, "") and not isinstance(raw_restore_qnums, list):
        raise ValueError("Session restore_question_numbers must be a list.")
    restore_qnums = (
        [
            _coerce_int(qnum, field="restore_question_numbers", minimum=1)
            for qnum in raw_restore_qnums
            if str(qnum).strip()
        ]
        or saved_qnums
        or current_qnums
    )

    saved_ids: list[str] = []
    saved_restore_ids: list[str] = []
    saved_fingerprint = ""
    if canonical_snapshot:
        if schema_version not in {PREVIOUS_CANONICAL_SESSION_SCHEMA_VERSION, SESSION_SCHEMA_VERSION}:
            raise ValueError(
                f"Canonical session must use schema {PREVIOUS_CANONICAL_SESSION_SCHEMA_VERSION} or {SESSION_SCHEMA_VERSION}."
            )
        if schema_version == SESSION_SCHEMA_VERSION:
            _validate_session_fingerprint_metadata(payload)
        if (
            _coerce_int(
                payload.get("session_identity_version") or 0,
                field="session_identity_version",
                minimum=1,
            )
            != SESSION_IDENTITY_VERSION
        ):
            raise ValueError("Unsupported session identity version.")
        if str(payload.get("session_identity") or "").strip() != SESSION_IDENTITY_KIND:
            raise ValueError("Unsupported session identity kind.")
        saved_fingerprint = str(payload.get("bank_fingerprint") or "").strip()
        if not saved_fingerprint:
            raise ValueError("Canonical session is missing bank_fingerprint.")
        if bank_fingerprint is not None and saved_fingerprint != str(bank_fingerprint).strip():
            raise ValueError("Session bank fingerprint does not match the loaded bank.")
        saved_ids = _coerce_canonical_id_list(payload.get("question_ids"), field="question_ids", required=True)
        saved_restore_ids = _coerce_canonical_id_list(
            payload.get("restore_question_ids"),
            field="restore_question_ids",
            required=True,
        )
        if available_question_ids is not None:
            available_ids = _coerce_canonical_id_list(
                list(available_question_ids),
                field="available_question_ids",
                required=True,
            )
            available_set = set(available_ids)
            for question_id in saved_ids + saved_restore_ids:
                if question_id not in available_set:
                    raise ValueError(f"Unknown canonical question reference in session snapshot: {question_id}")
        if question_ids is not None:
            _coerce_canonical_id_list(list(question_ids), field="current_question_ids", required=True)
        if restore_question_ids is not None:
            _coerce_canonical_id_list(
                list(restore_question_ids),
                field="current_restore_question_ids",
                required=True,
            )
        expected_session_signature = canonical_session_signature(saved_mode, saved_fingerprint, saved_ids)
        expected_restore_signature = canonical_session_signature(saved_mode, saved_fingerprint, saved_restore_ids)
        if str(payload.get("session_signature") or "").strip() != expected_session_signature:
            raise ValueError("Canonical session signature is invalid.")
        if str(payload.get("restore_signature") or "").strip() != expected_restore_signature:
            raise ValueError("Canonical restore signature is invalid.")
    else:
        known_source = (
            current_qnums
            if available_question_numbers is None
            else [
                _coerce_int(qnum, field="question_numbers", minimum=1)
                for qnum in available_question_numbers
                if str(qnum).strip()
            ]
        )
        if known_source:
            available_qnums = set(known_source)
            for qnum in saved_qnums + restore_qnums:
                if qnum not in available_qnums:
                    raise ValueError(f"Unknown question reference in session snapshot: {qnum}")

    base_count = _coerce_int(
        payload.get("session_base_question_count")
        or len(saved_restore_ids)
        or len(restore_qnums)
        or len(saved_ids)
        or len(saved_qnums)
        or len(current_qnums),
        field="session_base_question_count",
        minimum=0,
    )
    limit = payload.get("session_question_limit")
    try:
        session_limit = int(limit or 0)
    except (TypeError, ValueError):
        session_limit = 0
    if session_limit <= 0:
        session_limit = calculate_session_question_limit(base_count)

    raw_answers = payload.get("answers", [])
    raw_answer_history = payload.get("session_answer_history", [])
    raw_quests = payload.get("current_quests", [])
    if raw_answers not in (None, "") and not isinstance(raw_answers, list):
        raise ValueError("Session answers must be a list.")
    if raw_answer_history not in (None, "") and not isinstance(raw_answer_history, list):
        raise ValueError("Session session_answer_history must be a list.")
    if raw_quests not in (None, "") and not isinstance(raw_quests, list):
        raise ValueError("Session current_quests must be a list.")

    answers: list[SessionAnswerState] = []
    answer_ids: list[str] = []
    for answer in raw_answers if isinstance(raw_answers, list) else []:
        if not isinstance(answer, Mapping):
            raise ValueError("Session answer row must be a mapping.")
        row = cast(SessionAnswerState, dict(answer))
        if canonical_snapshot:
            answer_id = str(row.get("question_id") or "").strip()
            if not answer_id:
                raise ValueError("Canonical session answer row is missing question_id.")
            answer_ids.append(answer_id)
        answers.append(row)
    if canonical_snapshot:
        if len(answers) != len(saved_ids):
            raise ValueError("Session answer cardinality does not match canonical question cardinality.")
        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError("Duplicate canonical question ID in session answers.")
        if set(answer_ids) != set(saved_ids):
            raise ValueError("Session answer question IDs do not match canonical session question IDs.")

    answer_history: list[SessionAnswerEvent] = []
    number_to_id: dict[int, str] = {}
    if canonical_snapshot:
        for qnum, question_id in zip(saved_qnums, saved_ids, strict=False):
            number_to_id[int(qnum)] = str(question_id)
    for event in raw_answer_history if isinstance(raw_answer_history, list) else []:
        if not isinstance(event, Mapping):
            raise ValueError("Session answer history row must be a mapping.")
        history_row = dict(event)
        if canonical_snapshot:
            event_id = str(history_row.get("question_id") or "").strip()
            if not event_id:
                raw_number = history_row.get("question_number")
                try:
                    event_id = str(number_to_id.get(int(str(raw_number))) or "").strip()
                except (TypeError, ValueError):
                    event_id = ""
                if event_id:
                    history_row["question_id"] = event_id
            if not str(history_row.get("question_id") or "").strip() and history_row:
                raise ValueError("Canonical session answer history row is missing question_id.")
        answer_history.append(cast(SessionAnswerEvent, history_row))
    quests = []
    for quest in raw_quests if isinstance(raw_quests, list) else []:
        if not isinstance(quest, Mapping):
            raise ValueError("Session quest row must be a mapping.")
        quests.append(cast(QuestProgressState, dict(quest)))

    builder_identity = _snapshot_builder_identity(
        payload,
        saved_mode=saved_mode,
        source_label=str(payload.get("source_label") or ""),
        question_count=base_count,
    )
    builder_context = builder_identity["builder_context"]
    current_index = _coerce_int(payload.get("current_index", 0), field="current_index", minimum=0)
    identity_count = len(saved_ids) if canonical_snapshot else len(saved_qnums or current_qnums)
    max_index = max(0, identity_count - 1)
    if current_index > max_index:
        raise ValueError(f"Session current_index is out of bounds: {current_index}")
    elapsed_seconds = _coerce_int(payload.get("elapsed_seconds", 0), field="elapsed_seconds", minimum=0)

    result: SessionSnapshot = {
        "schema_version": schema_version,
        "app_version": str(payload.get("app_version") or ""),
        "bank_file": str(payload.get("bank_file") or ""),
        "mode": saved_mode,
        "builder_context": builder_context,
        "builder_identity": str(builder_identity["builder_identity"]),
        "builder_identity_version": int(builder_identity["builder_identity_version"]),
        "builder_context_fingerprint": str(builder_identity["builder_context_fingerprint"]),
        "builder_identity_status": str(builder_identity["builder_identity_status"]),
        "source_label": str(payload.get("source_label") or ""),
        "question_count": _coerce_int(
            payload.get("question_count") or identity_count,
            field="question_count",
            minimum=0,
        ),
        "question_numbers": saved_qnums or current_qnums,
        "restore_question_numbers": restore_qnums,
        "session_base_question_count": base_count,
        "session_question_limit": session_limit,
        "restore_signature": str(payload.get("restore_signature") or session_signature(mode, restore_qnums)),
        "session_signature": str(
            payload.get("session_signature") or session_signature(mode, saved_qnums or current_qnums)
        ),
        "current_index": current_index,
        "elapsed_seconds": elapsed_seconds,
        "exam_reveal": bool(payload.get("exam_reveal", mode != "Exam")),
        "checkpoints_saved": _coerce_str_list(payload.get("checkpoints_saved", []), field="checkpoints_saved"),
        "session_rewards": _coerce_str_list(payload.get("session_rewards", []), field="session_rewards"),
        "unlocked_rewards": _coerce_str_list(payload.get("unlocked_rewards", []), field="unlocked_rewards"),
        "session_answer_history": answer_history,
        "current_quests": quests,
        "quest_completion_keys": _coerce_str_list(
            payload.get("quest_completion_keys", []), field="quest_completion_keys"
        ),
        "session_boss_markers": _coerce_int_list(
            payload.get("session_boss_markers", []), field="session_boss_markers", minimum=0
        ),
        "session_stealth_markers": _coerce_int_list(
            payload.get("session_stealth_markers", []), field="session_stealth_markers", minimum=0
        ),
        "session_xp_gained": _coerce_int(payload.get("session_xp_gained", 0), field="session_xp_gained", minimum=0),
        "answers": answers,
    }
    if canonical_snapshot:
        result["schema_version"] = SESSION_SCHEMA_VERSION
        result["session_identity_version"] = SESSION_IDENTITY_VERSION
        result["session_identity"] = SESSION_IDENTITY_KIND
        result["bank_fingerprint"] = saved_fingerprint
        result["question_ids"] = saved_ids
        result["restore_question_ids"] = saved_restore_ids
        identity_metadata = _runtime_identity_metadata(saved_fingerprint)
        result["fingerprint_schema_version"] = int(identity_metadata["fingerprint_schema_version"])
        result["fingerprint_domain"] = str(identity_metadata["fingerprint_domain"])
        result["fingerprint_algorithm"] = str(identity_metadata["fingerprint_algorithm"])
        result["loader_contract_version"] = int(identity_metadata["loader_contract_version"])
        if identity_metadata.get("bank_node_id"):
            result["bank_node_id"] = str(identity_metadata["bank_node_id"])
    return result


def build_session_snapshot(
    *,
    app_version: str,
    bank_file: str,
    mode: str,
    builder_context: BuilderContext,
    source_label: str,
    question_numbers: list[int],
    restore_question_numbers: list[int],
    session_base_question_count: int,
    session_question_limit: int,
    current_index: int,
    elapsed_seconds: int,
    exam_reveal: bool,
    checkpoints_saved: list[str],
    session_rewards: list[str],
    unlocked_rewards: list[str],
    session_answer_history: list[SessionAnswerEvent],
    current_quests: list[QuestProgressState],
    quest_completion_keys: list[str],
    session_boss_markers: list[int],
    session_stealth_markers: list[int],
    session_xp_gained: int,
    answers: list[AnswerState],
    bank_fingerprint: str | None = None,
    question_ids: list[str] | None = None,
    restore_question_ids: list[str] | None = None,
) -> SessionSnapshot:
    canonical_requested = any(value is not None for value in (bank_fingerprint, question_ids, restore_question_ids))
    if canonical_requested and not (bank_fingerprint and question_ids and restore_question_ids):
        raise ValueError("Canonical session snapshot requires fingerprint and question IDs together.")

    identity = _snapshot_builder_identity(
        None,
        saved_mode=mode,
        source_label=source_label,
        question_count=session_base_question_count,
        builder_context=builder_context,
    )

    if canonical_requested:
        canonical_ids = _coerce_canonical_id_list(question_ids, field="question_ids", required=True)
        canonical_restore_ids = _coerce_canonical_id_list(
            restore_question_ids,
            field="restore_question_ids",
            required=True,
        )
        if len(canonical_ids) != len(question_numbers):
            raise ValueError("Canonical question IDs must match session question cardinality.")
        if len(canonical_restore_ids) != len(restore_question_numbers):
            raise ValueError("Canonical restore IDs must match restore question cardinality.")
        if len(answers) != len(canonical_ids):
            raise ValueError("Session answer cardinality must match canonical question cardinality.")
        bound_answers: list[SessionAnswerState] = []
        for question_id, answer in zip(canonical_ids, answers, strict=True):
            row = cast(SessionAnswerState, dict(answer))
            row["question_id"] = question_id
            bound_answers.append(row)
        fingerprint_metadata = _runtime_identity_metadata(str(bank_fingerprint))
        snapshot: SessionSnapshot = {
            "schema_version": SESSION_SCHEMA_VERSION,
            "app_version": app_version,
            "bank_file": bank_file,
            "session_identity_version": SESSION_IDENTITY_VERSION,
            "session_identity": SESSION_IDENTITY_KIND,
            "bank_fingerprint": str(bank_fingerprint),
            "fingerprint_schema_version": fingerprint_metadata["fingerprint_schema_version"],
            "fingerprint_domain": fingerprint_metadata["fingerprint_domain"],
            "fingerprint_algorithm": fingerprint_metadata["fingerprint_algorithm"],
            "loader_contract_version": fingerprint_metadata["loader_contract_version"],
            "question_ids": canonical_ids,
            "restore_question_ids": canonical_restore_ids,
            "mode": mode,
            "builder_context": identity["builder_context"],
            "builder_identity": identity["builder_identity"],
            "builder_identity_version": identity["builder_identity_version"],
            "builder_context_fingerprint": identity["builder_context_fingerprint"],
            "builder_identity_status": identity["builder_identity_status"],
            "source_label": source_label,
            "question_count": len(canonical_ids),
            "question_numbers": list(question_numbers),
            "restore_question_numbers": list(restore_question_numbers),
            "session_base_question_count": int(session_base_question_count),
            "session_question_limit": int(session_question_limit),
            "restore_signature": canonical_session_signature(mode, str(bank_fingerprint), canonical_restore_ids),
            "session_signature": canonical_session_signature(mode, str(bank_fingerprint), canonical_ids),
            "current_index": int(current_index),
            "elapsed_seconds": int(elapsed_seconds),
            "exam_reveal": bool(exam_reveal),
            "checkpoints_saved": list(checkpoints_saved),
            "session_rewards": list(session_rewards),
            "unlocked_rewards": list(unlocked_rewards),
            "session_answer_history": list(session_answer_history),
            "current_quests": list(current_quests),
            "quest_completion_keys": list(quest_completion_keys),
            "session_boss_markers": list(session_boss_markers),
            "session_stealth_markers": list(session_stealth_markers),
            "session_xp_gained": int(session_xp_gained),
            "answers": bound_answers,
        }
        if fingerprint_metadata.get("bank_node_id"):
            snapshot["bank_node_id"] = str(fingerprint_metadata["bank_node_id"])
        return snapshot

    legacy_answers = [cast(SessionAnswerState, dict(answer)) for answer in answers]
    return {
        "schema_version": LEGACY_SESSION_SCHEMA_VERSION,
        "app_version": app_version,
        "bank_file": bank_file,
        "mode": mode,
        "builder_context": identity["builder_context"],
        "builder_identity": identity["builder_identity"],
        "builder_identity_version": identity["builder_identity_version"],
        "builder_context_fingerprint": identity["builder_context_fingerprint"],
        "builder_identity_status": identity["builder_identity_status"],
        "source_label": source_label,
        "question_count": len(question_numbers),
        "question_numbers": list(question_numbers),
        "restore_question_numbers": list(restore_question_numbers),
        "session_base_question_count": int(session_base_question_count),
        "session_question_limit": int(session_question_limit),
        "restore_signature": session_signature(mode, restore_question_numbers),
        "session_signature": session_signature(mode, question_numbers),
        "current_index": int(current_index),
        "elapsed_seconds": int(elapsed_seconds),
        "exam_reveal": bool(exam_reveal),
        "checkpoints_saved": list(checkpoints_saved),
        "session_rewards": list(session_rewards),
        "unlocked_rewards": list(unlocked_rewards),
        "session_answer_history": list(session_answer_history),
        "current_quests": list(current_quests),
        "quest_completion_keys": list(quest_completion_keys),
        "session_boss_markers": list(session_boss_markers),
        "session_stealth_markers": list(session_stealth_markers),
        "session_xp_gained": int(session_xp_gained),
        "answers": legacy_answers,
    }


def saved_session_matches_current(
    saved: Mapping[str, Any] | None,
    mode: str,
    current_question_numbers: list[Any],
    restore_question_numbers: list[Any],
    *,
    bank_fingerprint: str | None = None,
    current_question_ids: list[str] | None = None,
    restore_question_ids: list[str] | None = None,
    allow_legacy: bool = False,
) -> bool:
    if not isinstance(saved, Mapping):
        return False
    try:
        schema_version = _coerce_int(saved.get("schema_version") or 1, field="schema_version", default=1, minimum=1)
    except ValueError:
        return False
    canonical_snapshot = schema_version >= PREVIOUS_CANONICAL_SESSION_SCHEMA_VERSION or any(
        key in saved
        for key in (
            "bank_fingerprint",
            "restore_question_ids",
            "session_identity",
            "session_identity_version",
        )
    )
    if canonical_snapshot:
        if schema_version not in {PREVIOUS_CANONICAL_SESSION_SCHEMA_VERSION, SESSION_SCHEMA_VERSION}:
            return False
        if schema_version == SESSION_SCHEMA_VERSION:
            try:
                _validate_session_fingerprint_metadata(saved)
            except ValueError:
                return False
        expected_fingerprint = str(bank_fingerprint or "").strip()
        if not expected_fingerprint or str(saved.get("bank_fingerprint") or "").strip() != expected_fingerprint:
            return False
        try:
            saved_ids = _coerce_canonical_id_list(saved.get("question_ids"), field="question_ids", required=True)
            saved_restore_ids = _coerce_canonical_id_list(
                saved.get("restore_question_ids"),
                field="restore_question_ids",
                required=True,
            )
            current_ids = _coerce_canonical_id_list(
                list(current_question_ids or []),
                field="current_question_ids",
                required=True,
            )
            current_restore_ids = _coerce_canonical_id_list(
                list(restore_question_ids or []),
                field="current_restore_question_ids",
                required=True,
            )
        except ValueError:
            return False
        if saved_restore_ids != current_restore_ids:
            return False
        if saved_ids != current_ids and saved_restore_ids != current_ids:
            return False
        expected_session_signature = canonical_session_signature(mode, expected_fingerprint, saved_ids)
        expected_restore_signature = canonical_session_signature(mode, expected_fingerprint, saved_restore_ids)
        return (
            str(saved.get("session_signature") or "").strip() == expected_session_signature
            and str(saved.get("restore_signature") or "").strip() == expected_restore_signature
        )

    if not allow_legacy:
        return False
    raw_restore_signature = str(saved.get("restore_signature") or "").strip()
    if raw_restore_signature:
        return raw_restore_signature == session_signature(mode, list(restore_question_numbers))
    raw_session_signature = str(saved.get("session_signature") or "").strip()
    if raw_session_signature:
        return raw_session_signature == session_signature(mode, list(current_question_numbers))
    try:
        saved_qnums = [
            _coerce_int(qnum, field="question_numbers", minimum=1)
            for qnum in saved.get("question_numbers", [])
            if str(qnum).strip()
        ]
        current_qnums = [
            _coerce_int(qnum, field="current_question_numbers", minimum=1) for qnum in current_question_numbers
        ]
    except (TypeError, ValueError):
        return False
    return bool(saved_qnums) and saved_qnums == current_qnums
