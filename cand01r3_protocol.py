from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from cand01r3_measurement import (
    DUPLICATE_KINDS,
    STATUS_CONTAMINATED,
    STATUS_DUPLICATE,
    STATUS_NOT_ELIGIBLE,
    STATUS_PRIMARY,
    STATUS_UNOBSERVED,
    MeasurementLedger,
    MeasurementObservation,
)
from cand01r3_partition import (
    COMPILED_PATH,
    EXAM_ID,
    EXPECTED_COMPILED_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_SEMANTIC_AUDIT_SHA256,
    EXPECTED_STORE_SHA256,
    INTENDED_USE_MEASUREMENT,
    INTENDED_USE_TRAINING,
    PARTITION_EPOCH,
    ROLE_PROBE,
    ROLE_TRAIN,
    RuntimeAuthority,
    canonical_question_id,
    load_runtime_authority,
)
from cand01r3_runtime import (
    DEFAULT_LEARNER_ID,
    POLICY_MEASUREMENT,
    POLICY_RRC1,
    POLICY_SMART_PRACTICE,
    Cand01R3AuthorityError,
    Cand01R3RuntimeContext,
    activate_cand01r3_experiment,
    get_context,
    is_cand01r3_active,
    reset_cand01r3_runtime,
)
from cert_config import USER_DATA_DIRNAME

ROOT = Path(__file__).resolve().parent
PROTOCOL_PATH = ROOT / "content" / "sc900" / "measurement" / "cand01r3_protocol.json"
DEFAULT_LAUNCH_BANK_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"

PROTOCOL_VERSION = "cand01r3-measurement-001-v2"
SUPERSEDED_PROTOCOL_VERSION = "cand01r3-measurement-001-v1"
SUPERSEDED_PROTOCOL_SHA256 = "493b371d6200c88fe51428953947fac864fae8535667374e38050198b018e081"
MEASUREMENT_EPOCH = "cand01r3-measurement-001"
SCHEDULE_VERSION = "cand01r3-probe-schedule-v1"
POLICY_SEQUENCE_VERSION = "cand01r3-alt-crossover-v1"
ANALYSIS_VERSION = "cand01r3-analysis-plan-v1"
PRIMARY_DAILY_TRAIN_BUDGET = 20
DAY7_BLOCK_TRAIN_BUDGET = 10
SUPERSESSION_REASON = "PRIMARY_DAYS_TRAINING_DOSE_WAS_UNBOUNDED"
CANDIDATE = "CAND-01R3"
PRIMARY_ENDPOINT = "7-day first-attempt correctness on CLEAN HELD-OUT SC-900 PROBE items"
STOPPING_RULE = (
    "Complete the scheduled 7-day protocol, or terminate the epoch on a protocol-invalidating event. "
    "Do not stop early because one policy looks ahead. Do not extend because a desired result has not appeared."
)
MISSINGNESS_RULE = (
    "A missed scheduled PROBE is UNOBSERVED. It is not coerced to incorrect, correct, or zero, and it is not dropped."
)
CONTAMINATION_RULE = (
    "Improper PROBE exposure is recorded as contaminated, excluded from the clean primary endpoint, "
    "and not silently replaced. Contamination is monotonic. No post-hoc replacement rule exists."
)
FIRST_ATTEMPT_RULE = (
    "Only the earliest valid clean scored PROBE attempt for "
    "(learner_id, SC-900, partition_epoch, question_id) is primary. "
    "Retry, redo, restored duplicates, and imported duplicates are excluded."
)
DAY_CAPACITIES = (4, 4, 4, 4, 4, 4, 5)
EXPECTED_PROBE_FAMILIES = (
    "azure_key_vault",
    "entra_roles_rbac",
    "multifactor_authentication",
    "privileged_identity_management",
    "purview_portal",
    "shared_responsibility_model",
    "zero_trust_and_identity_perimeter",
)
OUTSIDE_STUDY_CODES = (
    "NONE",
    "MICROSOFT_LEARN",
    "BOOK",
    "VIDEO_COURSE",
    "PRACTICE_TEST",
    "OTHER",
)
SYNTHETIC_MARKERS = {"TEST_ONLY", "SYNTHETIC"}
HASH_EXCLUDED = {"protocol_sha256"}
STATUS_DEVIATION = "PROTOCOL_DEVIATION"
STATUS_OUTSIDE_STUDY = "OUTSIDE_STUDY"
STATUS_TRAIN_EXPOSURE = "TRAIN_EXPOSURE"
EVENT_EPOCH_BEGIN = "EPOCH_BEGIN"
EVENT_DAY_STATE = "DAY_STATE"
EVENT_MEASUREMENT_TRANSITION = "MEASUREMENT_TRANSITION"
STATE_DAY_NOT_STARTED = "DAY_NOT_STARTED"
STATE_TRAINING = "TRAINING"
STATE_TRAINING_COMPLETE = "TRAINING_COMPLETE"
STATE_MEASUREMENT = "MEASUREMENT"
STATE_DAY_COMPLETE = "DAY_COMPLETE"
STATE_SMART_PRACTICE_TRAINING = "SMART_PRACTICE_TRAINING"
STATE_SMART_PRACTICE_COMPLETE = "SMART_PRACTICE_COMPLETE"
STATE_RRC1_TRAINING = "RRC1_TRAINING"
STATE_RRC1_COMPLETE = "RRC1_COMPLETE"
TERMINAL_PROBE_STATUSES = {STATUS_PRIMARY, STATUS_UNOBSERVED, STATUS_CONTAMINATED}
REAL_OBSERVATION_STATUSES = {STATUS_PRIMARY, STATUS_UNOBSERVED, STATUS_CONTAMINATED, STATUS_DUPLICATE}
POLICY_DAY7 = "DAY7_BALANCED_MEASUREMENT"
RUNTIME_POLICY_MAP = {
    "SMART_PRACTICE": POLICY_SMART_PRACTICE,
    "RRC_1": POLICY_RRC1,
    POLICY_DAY7: POLICY_MEASUREMENT,
}

POLICY_SEQUENCE: list[dict[str, Any]] = [
    {
        "scheduled_day": 1,
        "policy_id": "SMART_PRACTICE",
        "training": True,
        "measurement": True,
        "primary_policy_contrast": True,
        "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "training_blocks": [{"policy_id": "SMART_PRACTICE", "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET}],
    },
    {
        "scheduled_day": 2,
        "policy_id": "RRC_1",
        "training": True,
        "measurement": True,
        "primary_policy_contrast": True,
        "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "training_blocks": [{"policy_id": "RRC_1", "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET}],
    },
    {
        "scheduled_day": 3,
        "policy_id": "SMART_PRACTICE",
        "training": True,
        "measurement": True,
        "primary_policy_contrast": True,
        "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "training_blocks": [{"policy_id": "SMART_PRACTICE", "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET}],
    },
    {
        "scheduled_day": 4,
        "policy_id": "RRC_1",
        "training": True,
        "measurement": True,
        "primary_policy_contrast": True,
        "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "training_blocks": [{"policy_id": "RRC_1", "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET}],
    },
    {
        "scheduled_day": 5,
        "policy_id": "SMART_PRACTICE",
        "training": True,
        "measurement": True,
        "primary_policy_contrast": True,
        "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "training_blocks": [{"policy_id": "SMART_PRACTICE", "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET}],
    },
    {
        "scheduled_day": 6,
        "policy_id": "RRC_1",
        "training": True,
        "measurement": True,
        "primary_policy_contrast": True,
        "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "training_blocks": [{"policy_id": "RRC_1", "train_item_budget": PRIMARY_DAILY_TRAIN_BUDGET}],
    },
    {
        "scheduled_day": 7,
        "policy_id": POLICY_DAY7,
        "training": True,
        "measurement": True,
        "primary_policy_contrast": False,
        "train_item_budget": None,
        "training_blocks": [
            {"policy_id": "SMART_PRACTICE", "train_item_budget": DAY7_BLOCK_TRAIN_BUDGET},
            {"policy_id": "RRC_1", "train_item_budget": DAY7_BLOCK_TRAIN_BUDGET},
        ],
    },
]


def _empty_policy_exposure() -> dict[str, Any]:
    return {
        "train_questions_seen": 0,
        "unique_train_questions_seen": 0,
        "semantic_families_seen": [],
        "domain_counts": {},
        "objective_counts": {},
        "REPAIR_service_count": 0,
        "REVIEW_service_count": 0,
        "COVERAGE_service_count": 0,
        "session_duration_seconds": None,
        "rrc1_fairness": {
            "MAX_SERVICE_DELAY": None,
            "OVERDUE_RATE": None,
            "STARVATION_RATE": None,
            "QUEUE_AGE": None,
            "COVERAGE_DEBT": None,
            "DOMAIN_SERVICE_BALANCE": {},
            "OBJECTIVE_SERVICE_BALANCE": {},
            "CLASS_SERVICE_SHARE": {},
            "BACKLOG_SIZE": None,
            "SESSION_CLASS_DOMINANCE": None,
        },
    }


@dataclass
class MeasurementSession:
    active: bool = False
    learner_id: str = DEFAULT_LEARNER_ID
    measurement_epoch: str = ""
    schedule_version: str = ""
    policy_sequence_version: str = ""
    protocol_version: str = ""
    protocol_sha256: str = ""
    candidate_bank_identity: str = ""
    partition_epoch: str = PARTITION_EPOCH
    ledger_path: Path | None = None
    allow_synthetic: bool = False
    protocol_locked: bool = False
    current_scheduled_day: int | None = None
    protocol: dict[str, Any] = field(default_factory=dict)
    schedule_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    train_ids: set[str] = field(default_factory=set)
    probe_ids: set[str] = field(default_factory=set)
    ledger: MeasurementLedger | None = None
    train_log: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    day_state: str = STATE_DAY_NOT_STARTED
    day1_local_date: str = ""
    calendar_utc_offset_minutes: int | None = None
    last_local_date: str = ""


_SESSION = MeasurementSession()


def reset_measurement_session() -> None:
    global _SESSION
    _SESSION = MeasurementSession()


def current_measurement_session() -> MeasurementSession:
    return _SESSION


def is_measurement_active() -> bool:
    return bool(_SESSION.active)


def canonical_protocol_dumps(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key not in HASH_EXCLUDED}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def protocol_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_protocol_dumps(payload).encode("utf-8")).hexdigest()


def _compiled_metadata() -> dict[str, dict[str, Any]]:
    if not COMPILED_PATH.exists():
        return {}
    raw = json.loads(COMPILED_PATH.read_text(encoding="utf-8"))
    questions = raw.get("questions") if isinstance(raw, Mapping) else raw
    if isinstance(raw, Mapping) and not questions:
        questions = raw.get("items") or []
    index: dict[str, dict[str, Any]] = {}
    for row in questions or []:
        if not isinstance(row, Mapping):
            continue
        question_id = canonical_question_id(row)
        if not question_id:
            continue
        index[question_id] = {
            "domain": str(row.get("domain") or ""),
            "objective": str(row.get("objective") or row.get("objective_code") or ""),
            "semantic_family_id": str(row.get("semantic_family_id") or ""),
        }
    return index


def build_probe_schedule(authority: RuntimeAuthority | None = None) -> list[dict[str, Any]]:
    loaded = authority if authority is not None else load_runtime_authority()
    compiled = _compiled_metadata()
    families: list[tuple[str, list[str]]] = []
    for family_id in EXPECTED_PROBE_FAMILIES:
        family = loaded.families.get(family_id) or {}
        members = sorted(str(member) for member in family.get("member_ids") or [])
        families.append((family_id, members))
    families.sort(key=lambda item: (-len(item[1]), item[0]))
    remaining = {family_id: list(members) for family_id, members in families}
    queue: list[tuple[str, str]] = []
    while any(remaining[family_id] for family_id, _members in families):
        progressed = False
        for family_id, _members in families:
            if remaining[family_id]:
                queue.append((family_id, remaining[family_id].pop(0)))
                progressed = True
        if not progressed:
            break
    day_rows: list[list[dict[str, Any]]] = [[] for _ in DAY_CAPACITIES]
    family_on_day: list[set[str]] = [set() for _ in DAY_CAPACITIES]

    def pack(index: int) -> bool:
        if index >= len(queue):
            return True
        family_id, question_id = queue[index]
        for day_index, capacity in enumerate(DAY_CAPACITIES):
            if family_id in family_on_day[day_index] or len(day_rows[day_index]) >= capacity:
                continue
            meta = compiled.get(question_id) or {}
            item = loaded.items.get(question_id) or {}
            family_name = str(item.get("semantic_family_id") or family_id)
            row = {
                "question_id": question_id,
                "semantic_family_id": family_name,
                "scheduled_day": day_index + 1,
                "domain": meta.get("domain") or "",
                "objective": meta.get("objective") or "",
                "policy_id": POLICY_SEQUENCE[day_index]["policy_id"],
                "primary_policy_contrast": bool(POLICY_SEQUENCE[day_index]["primary_policy_contrast"]),
            }
            day_rows[day_index].append(row)
            family_on_day[day_index].add(family_name)
            if pack(index + 1):
                return True
            day_rows[day_index].pop()
            family_on_day[day_index].remove(family_name)
        return False

    if not pack(0):
        raise RuntimeError("PROBE schedule overflow")
    schedule: list[dict[str, Any]] = []
    sequence_position = 0
    for _day_index, rows in enumerate(day_rows):
        ordered = sorted(rows, key=lambda row: (row["semantic_family_id"], row["question_id"]))
        for day_position, row in enumerate(ordered, start=1):
            sequence_position += 1
            payload = dict(row)
            payload["day_position"] = day_position
            payload["sequence_position"] = sequence_position
            schedule.append(payload)
    return schedule


def build_protocol(authority: RuntimeAuthority | None = None) -> dict[str, Any]:
    loaded = authority if authority is not None else load_runtime_authority()
    if not loaded.valid:
        raise Cand01R3AuthorityError(loaded.reason)
    schedule = build_probe_schedule(loaded)
    protocol = {
        "protocol_version": PROTOCOL_VERSION,
        "measurement_epoch": MEASUREMENT_EPOCH,
        "exam": EXAM_ID,
        "candidate": CANDIDATE,
        "primary_endpoint": PRIMARY_ENDPOINT,
        "question_count": 200,
        "train_question_count": 171,
        "probe_question_count": 29,
        "probe_family_count": 7,
        "independent_probe_families": list(EXPECTED_PROBE_FAMILIES),
        "schedule_version": SCHEDULE_VERSION,
        "policy_sequence_version": POLICY_SEQUENCE_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "partition_epoch": loaded.partition_epoch or PARTITION_EPOCH,
        "schedule": schedule,
        "policy_sequence": copy_policy_sequence(),
        "frozen_artifact_hashes": {
            "semantic_audit_sha256": EXPECTED_SEMANTIC_AUDIT_SHA256,
            "store_sha256": EXPECTED_STORE_SHA256,
            "compiled_sha256": EXPECTED_COMPILED_SHA256,
            "train_probe_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "default_launch_bank_sha256": DEFAULT_LAUNCH_BANK_SHA256,
        },
        "missingness_rule": MISSINGNESS_RULE,
        "contamination_rule": CONTAMINATION_RULE,
        "first_attempt_rule": FIRST_ATTEMPT_RULE,
        "stopping_rule": STOPPING_RULE,
        "real_observations": 0,
        "empirical_result": "NOT_YET_AVAILABLE",
        "deployment_authorized": "NO",
        "default_bank_unchanged": "YES",
        "primary_daily_train_budget": PRIMARY_DAILY_TRAIN_BUDGET,
        "primary_train_exposure_totals": primary_train_exposure_totals(),
        "supersession": {
            "superseded_protocol_version": SUPERSEDED_PROTOCOL_VERSION,
            "superseded_protocol_sha256": SUPERSEDED_PROTOCOL_SHA256,
            "V1_SUPERSEDED_BEFORE_EMPIRICAL_RUN": "YES",
            "SUPERSESSION_REASON": SUPERSESSION_REASON,
            "REAL_OBSERVATIONS_AT_SUPERSESSION": 0,
            "EMPIRICAL_DATA_INVALIDATED": "NO",
        },
    }
    protocol["protocol_sha256"] = protocol_sha256(protocol)
    return protocol


def copy_policy_sequence() -> list[dict[str, Any]]:
    return json.loads(json.dumps(POLICY_SEQUENCE))


def primary_train_exposure_totals() -> dict[str, int]:
    smart = 0
    rrc = 0
    for row in POLICY_SEQUENCE:
        if not row.get("primary_policy_contrast"):
            continue
        budget = int(row.get("train_item_budget") or 0)
        if row["policy_id"] == "SMART_PRACTICE":
            smart += budget
        elif row["policy_id"] == "RRC_1":
            rrc += budget
    return {
        "SMART_PRACTICE": smart,
        "RRC_1": rrc,
        "PRIMARY_TRAIN_EXPOSURE_DIFFERENCE": abs(smart - rrc),
    }


def allow_v2_supersession(real_observations: int) -> dict[str, Any]:
    count = int(real_observations)
    if count == 0:
        return {
            "allowed": True,
            "REAL_OBSERVATIONS_AT_SUPERSESSION": 0,
            "SUPERSESSION_REASON": SUPERSESSION_REASON,
            "EMPIRICAL_DATA_INVALIDATED": "NO",
        }
    return {
        "allowed": False,
        "reason": "NEW_MEASUREMENT_EPOCH_REQUIRED",
        "REAL_OBSERVATIONS_AT_SUPERSESSION": count,
    }


def require_train_capacity(*, expected_budget: int, actual_eligible: int, policy_id: str = "") -> dict[str, Any]:
    if int(actual_eligible) < int(expected_budget):
        result = {
            "status": "INSUFFICIENT_TRAIN_CAPACITY",
            "policy_id": policy_id,
            "expected_budget": int(expected_budget),
            "actual_exposures": int(actual_eligible),
            "filled_with_probe": False,
        }
        if _SESSION.active:
            payload = {
                "event_id": str(uuid.uuid4()),
                "event_type": STATUS_DEVIATION,
                "status": STATUS_DEVIATION,
                "reason": "INSUFFICIENT_TRAIN_CAPACITY",
                "counted": False,
                "policy_id": policy_id,
                "scheduled_day": _SESSION.current_scheduled_day,
                "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                **_session_identity_fields(),
            }
            _persist_event(payload)
        return result
    return {
        "status": "OK",
        "policy_id": policy_id,
        "expected_budget": int(expected_budget),
        "actual_exposures": int(actual_eligible),
        "filled_with_probe": False,
    }


def _ledger_real_observation_count(path: Path) -> int:
    count = 0
    for payload in _read_ledger_events(path):
        if payload.get("synthetic") or str(payload.get("marker") or "") in SYNTHETIC_MARKERS:
            continue
        if payload.get("event_type") in {EVENT_EPOCH_BEGIN, EVENT_DAY_STATE, EVENT_MEASUREMENT_TRANSITION}:
            continue
        if payload.get("status") == STATUS_TRAIN_EXPOSURE or payload.get("event_type") == STATUS_TRAIN_EXPOSURE:
            continue
        if payload.get("status") in REAL_OBSERVATION_STATUSES and payload.get("question_role") in {
            ROLE_PROBE,
            None,
            "",
        }:
            if payload.get("reason") in {
                "PROBE_BEFORE_TRAIN_BLOCK_COMPLETE",
                "WRONG_MEASUREMENT_DAY",
                "MEASUREMENT_MODE_NOT_ACTIVE",
                "UNSCHEDULED_PROBE",
            }:
                continue
            count += 1
    return count


def _read_ledger_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists() or path.stat().st_size == 0:
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Cand01R3AuthorityError("EMPIRICAL_LEDGER_CORRUPT") from exc
        if not isinstance(payload, dict):
            raise Cand01R3AuthorityError("EMPIRICAL_LEDGER_CORRUPT")
        events.append(payload)
    return events


def _authority_identity(authority: RuntimeAuthority, *, learner_id: str, protocol: Mapping[str, Any]) -> dict[str, str]:
    return {
        "measurement_epoch": MEASUREMENT_EPOCH,
        "protocol_version": str(protocol.get("protocol_version") or PROTOCOL_VERSION),
        "protocol_sha256": protocol_sha256(protocol),
        "partition_epoch": authority.partition_epoch or PARTITION_EPOCH,
        "manifest_sha256": authority.manifest_sha256,
        "store_sha256": authority.store_sha256,
        "semantic_audit_sha256": authority.semantic_audit_sha256,
        "compiled_sha256": authority.compiled_sha256,
        "candidate_bank_identity": authority.compiled_sha256,
        "learner_id": learner_id,
    }


def _session_identity_fields() -> dict[str, str]:
    authority = _SESSION.ledger.authority if _SESSION.ledger is not None else None
    context = get_context()
    return {
        "measurement_epoch": _SESSION.measurement_epoch,
        "protocol_version": _SESSION.protocol_version,
        "protocol_sha256": _SESSION.protocol_sha256,
        "partition_epoch": _SESSION.partition_epoch,
        "manifest_sha256": (authority.manifest_sha256 if authority else context.manifest_sha256),
        "store_sha256": (authority.store_sha256 if authority else context.store_sha256),
        "semantic_audit_sha256": (authority.semantic_audit_sha256 if authority else context.semantic_audit_sha256),
        "compiled_sha256": (authority.compiled_sha256 if authority else context.compiled_sha256),
        "candidate_bank_identity": _SESSION.candidate_bank_identity,
        "learner_id": _SESSION.learner_id,
    }


def _ledger_identity(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    preferred = [event for event in events if event.get("event_type") == EVENT_EPOCH_BEGIN]
    for event in preferred + list(events):
        for key in (
            "measurement_epoch",
            "protocol_version",
            "protocol_sha256",
            "partition_epoch",
            "manifest_sha256",
            "store_sha256",
            "semantic_audit_sha256",
            "compiled_sha256",
            "candidate_bank_identity",
            "learner_id",
        ):
            value = event.get(key)
            if value and key not in identity:
                identity[key] = value
        if len(identity) >= 10:
            break
    return identity


def _verify_resume_identity(
    events: Sequence[Mapping[str, Any]],
    *,
    learner_id: str,
    measurement_epoch: str,
    protocol: Mapping[str, Any],
    authority: RuntimeAuthority,
) -> None:
    identity = _ledger_identity(events)
    if not identity:
        raise Cand01R3AuthorityError("LEDGER_IDENTITY_MISSING")
    expected = _authority_identity(authority, learner_id=learner_id, protocol=protocol)
    if identity.get("measurement_epoch") and identity.get("measurement_epoch") != measurement_epoch:
        raise Cand01R3AuthorityError("WRONG_MEASUREMENT_EPOCH")
    if identity.get("measurement_epoch") and identity.get("measurement_epoch") != MEASUREMENT_EPOCH:
        raise Cand01R3AuthorityError("WRONG_MEASUREMENT_EPOCH")
    if identity.get("protocol_version") and identity.get("protocol_version") != PROTOCOL_VERSION:
        raise Cand01R3AuthorityError("PROTOCOL_VERSION_MISMATCH")
    if identity.get("protocol_sha256") and identity.get("protocol_sha256") != expected["protocol_sha256"]:
        raise Cand01R3AuthorityError("PROTOCOL_HASH_MISMATCH")
    if identity.get("learner_id") and identity.get("learner_id") != learner_id:
        raise Cand01R3AuthorityError("LEARNER_IDENTITY_MISMATCH")
    if identity.get("partition_epoch") and identity.get("partition_epoch") != expected["partition_epoch"]:
        raise Cand01R3AuthorityError("PARTITION_EPOCH_MISMATCH")
    for hash_name in (
        "manifest_sha256",
        "store_sha256",
        "semantic_audit_sha256",
        "compiled_sha256",
        "candidate_bank_identity",
    ):
        if identity.get(hash_name) and identity.get(hash_name) != expected[hash_name]:
            raise Cand01R3AuthorityError("AUTHORITY_HASH_MISMATCH")


def _policy_row(scheduled_day: int) -> dict[str, Any]:
    for row in POLICY_SEQUENCE:
        if int(row["scheduled_day"]) == int(scheduled_day):
            return row
    raise ValueError("UNKNOWN_SCHEDULED_DAY")


def current_train_block(scheduled_day: int) -> dict[str, Any]:
    row = _policy_row(scheduled_day)
    blocks = list(row.get("training_blocks") or [])
    if int(scheduled_day) < 7:
        return dict(blocks[0])
    for block in blocks:
        budget = int(block.get("train_item_budget") or 0)
        if _counted_train_exposures(scheduled_day, str(block["policy_id"])) < budget:
            return dict(block)
    return dict(blocks[-1])


def train_budget_for_day(scheduled_day: int, policy_id: str | None = None) -> int:
    if int(scheduled_day) < 7:
        return int(_policy_row(scheduled_day).get("train_item_budget") or PRIMARY_DAILY_TRAIN_BUDGET)
    block = current_train_block(scheduled_day)
    if policy_id and policy_id != block.get("policy_id"):
        for item in _policy_row(scheduled_day).get("training_blocks") or []:
            if item.get("policy_id") == policy_id:
                return int(item.get("train_item_budget") or 0)
    return int(block.get("train_item_budget") or 0)


def _counted_train_exposures(scheduled_day: int, policy_id: str | None = None) -> int:
    count = 0
    for row in _SESSION.train_log:
        if not row.get("counted"):
            continue
        if int(row.get("scheduled_day") or 0) != int(scheduled_day):
            continue
        if policy_id and str(row.get("policy_id") or "") != policy_id:
            continue
        count += 1
    return count


def measurement_train_session_limit() -> int | None:
    if not is_measurement_active() or _SESSION.current_scheduled_day is None:
        return None
    day = int(_SESSION.current_scheduled_day)
    block = current_train_block(day)
    budget = int(block.get("train_item_budget") or 0)
    completed = _counted_train_exposures(day, str(block.get("policy_id") or ""))
    return max(0, budget - completed)


def ordered_scheduled_probe_ids_for_day(scheduled_day: int) -> list[str]:
    protocol = _SESSION.protocol or build_protocol()
    return [
        str(row["question_id"])
        for row in protocol.get("schedule") or []
        if int(row.get("scheduled_day") or 0) == int(scheduled_day)
    ]


def scheduled_probe_ids_for_day(scheduled_day: int) -> set[str]:
    return set(ordered_scheduled_probe_ids_for_day(scheduled_day))


def todays_scheduled_probe_ids() -> set[str]:
    if _SESSION.current_scheduled_day is None:
        return set()
    return scheduled_probe_ids_for_day(int(_SESSION.current_scheduled_day))


def _training_complete_for_day(scheduled_day: int) -> bool:
    if int(scheduled_day) >= 7:
        return (
            _counted_train_exposures(7, "SMART_PRACTICE") >= DAY7_BLOCK_TRAIN_BUDGET
            and _counted_train_exposures(7, "RRC_1") >= DAY7_BLOCK_TRAIN_BUDGET
        )
    return _counted_train_exposures(int(scheduled_day)) >= train_budget_for_day(int(scheduled_day))


def _probe_terminal_ids(scheduled_day: int) -> set[str]:
    terminal: set[str] = set()
    for event in _SESSION.events:
        if int(event.get("scheduled_day") or 0) != int(scheduled_day):
            continue
        if event.get("status") not in TERMINAL_PROBE_STATUSES:
            continue
        question_id = str(event.get("question_id") or "")
        if question_id:
            terminal.add(question_id)
    if _SESSION.ledger is not None:
        for question_id in scheduled_probe_ids_for_day(scheduled_day):
            if _SESSION.ledger.is_contaminated(question_id):
                terminal.add(question_id)
            unobserved = getattr(_SESSION.ledger, "_unobserved", {})
            if question_id in unobserved:
                terminal.add(question_id)
            primary = _SESSION.ledger.primary_observation(question_id)
            if primary is not None:
                terminal.add(question_id)
    return terminal


def _day_is_complete(scheduled_day: int) -> bool:
    required = scheduled_probe_ids_for_day(scheduled_day)
    if not required:
        return False
    return required <= _probe_terminal_ids(scheduled_day)


def _day_has_progress(scheduled_day: int) -> bool:
    if _counted_train_exposures(int(scheduled_day)) > 0:
        return True
    if _probe_terminal_ids(int(scheduled_day)):
        return True
    for event in _SESSION.events:
        if int(event.get("scheduled_day") or 0) == int(scheduled_day):
            return True
    return False


def _derive_day_state(scheduled_day: int | None) -> str:
    if scheduled_day is None:
        return STATE_DAY_NOT_STARTED
    day = int(scheduled_day)
    if _day_is_complete(day):
        return STATE_DAY_COMPLETE
    measurement_begun = any(
        event.get("event_type") == EVENT_MEASUREMENT_TRANSITION and int(event.get("scheduled_day") or 0) == day
        for event in _SESSION.events
    ) or any(
        event.get("status") in TERMINAL_PROBE_STATUSES | {STATUS_DUPLICATE}
        and int(event.get("scheduled_day") or 0) == day
        for event in _SESSION.events
    )
    if measurement_begun:
        return STATE_MEASUREMENT
    if int(day) >= 7:
        sp_done = _counted_train_exposures(7, "SMART_PRACTICE")
        rrc_done = _counted_train_exposures(7, "RRC_1")
        if sp_done < DAY7_BLOCK_TRAIN_BUDGET:
            return STATE_SMART_PRACTICE_TRAINING
        if rrc_done < DAY7_BLOCK_TRAIN_BUDGET:
            return STATE_RRC1_TRAINING
        return STATE_RRC1_COMPLETE
    if _training_complete_for_day(day):
        return STATE_TRAINING_COMPLETE
    if _day_has_progress(day) or _SESSION.current_scheduled_day == day:
        return STATE_TRAINING
    return STATE_DAY_NOT_STARTED


def measurement_runtime_state() -> str:
    if not _SESSION.active:
        return STATE_DAY_NOT_STARTED
    derived = _derive_day_state(_SESSION.current_scheduled_day)
    _SESSION.day_state = derived
    return derived


def _runtime_policy_for_state(scheduled_day: int | None, day_state: str) -> tuple[str, str]:
    if scheduled_day is None:
        return POLICY_SMART_PRACTICE, INTENDED_USE_TRAINING
    if day_state in {STATE_MEASUREMENT, STATE_DAY_COMPLETE}:
        return POLICY_MEASUREMENT, INTENDED_USE_MEASUREMENT
    if int(scheduled_day) >= 7:
        if day_state in {STATE_RRC1_TRAINING, STATE_RRC1_COMPLETE}:
            return POLICY_RRC1, INTENDED_USE_TRAINING
        return POLICY_SMART_PRACTICE, INTENDED_USE_TRAINING
    allocated = allocated_policy_for_day(int(scheduled_day))
    return RUNTIME_POLICY_MAP.get(allocated, allocated), INTENDED_USE_TRAINING


def _apply_runtime_for_current_state() -> None:
    if not is_cand01r3_active() or not _SESSION.active:
        return
    day_state = measurement_runtime_state()
    policy_id, intended_use = _runtime_policy_for_state(_SESSION.current_scheduled_day, day_state)
    get_context().policy_id = policy_id
    get_context().intended_use = intended_use


def _apply_day7_handoff() -> None:
    if not _SESSION.active or _SESSION.current_scheduled_day != 7:
        return
    if measurement_runtime_state() in {STATE_MEASUREMENT, STATE_DAY_COMPLETE}:
        return
    sp_done = _counted_train_exposures(7, "SMART_PRACTICE")
    rrc_done = _counted_train_exposures(7, "RRC_1")
    if sp_done >= DAY7_BLOCK_TRAIN_BUDGET and rrc_done < DAY7_BLOCK_TRAIN_BUDGET:
        _SESSION.day_state = STATE_RRC1_TRAINING
        if is_cand01r3_active():
            get_context().policy_id = POLICY_RRC1
            get_context().intended_use = INTENDED_USE_TRAINING
    elif sp_done >= DAY7_BLOCK_TRAIN_BUDGET and rrc_done >= DAY7_BLOCK_TRAIN_BUDGET:
        _SESSION.day_state = STATE_RRC1_COMPLETE
        if is_cand01r3_active():
            get_context().policy_id = POLICY_RRC1
            get_context().intended_use = INTENDED_USE_TRAINING


def _restore_ledger_from_events(ledger: MeasurementLedger, events: Sequence[Mapping[str, Any]]) -> None:
    for event in events:
        question_id = canonical_question_id(str(event.get("question_id") or ""))
        if not question_id:
            continue
        status = str(event.get("status") or "")
        if status == STATUS_CONTAMINATED or event.get("contaminated"):
            ledger.record_contamination(
                question_id, str(event.get("contamination_reason") or event.get("reason") or "CONTAMINATED")
            )
            continue
        if status == STATUS_PRIMARY:
            if question_id in ledger._unobserved or ledger.is_contaminated(question_id):
                continue
            if question_id in ledger._observations:
                continue
            if type(event.get("correct")) is not bool:
                raise Cand01R3AuthorityError("INVALID_MEASUREMENT_SCORE")
            identity_raw = event.get("evaluation_id") or []
            identity = (
                tuple(str(part) for part in identity_raw)
                if isinstance(identity_raw, list) and len(identity_raw) == 4
                else ledger._identity(question_id)
            )
            ledger._observations[question_id] = {
                "status": STATUS_PRIMARY,
                "reason": event.get("reason") or "OK",
                "question_id": question_id,
                "correct": event.get("correct"),
                "selected_option_ids": list(event.get("selected_option_ids") or []),
                "evaluation_identity": identity,
            }
        elif status == STATUS_UNOBSERVED:
            if question_id in ledger._observations or ledger.is_contaminated(question_id) or question_id in ledger._unobserved:
                continue
            ledger._unobserved[question_id] = {
                "status": STATUS_UNOBSERVED,
                "reason": event.get("reason") or "UNOBSERVED",
                "question_id": question_id,
                "correct": None,
            }


def _restore_session_from_events(events: Sequence[Mapping[str, Any]]) -> None:
    train_log: list[dict[str, Any]] = []
    restored_events: list[dict[str, Any]] = []
    current_day: int | None = None
    day1_local_date = ""
    calendar_utc_offset_minutes: int | None = None
    last_local_date = ""
    for event in events:
        event_day1 = str(event.get("day1_local_date") or "")
        if event_day1 and not day1_local_date:
            day1_local_date = event_day1
        if event.get("calendar_utc_offset_minutes") is not None and calendar_utc_offset_minutes is None:
            calendar_utc_offset_minutes = int(event.get("calendar_utc_offset_minutes"))
        event_local_date = str(event.get("calendar_local_date") or "")
        if event_local_date and (not last_local_date or event_local_date > last_local_date):
            last_local_date = event_local_date
        restored_events.append(dict(event))
        scheduled_day = event.get("scheduled_day")
        event_type = str(event.get("event_type") or "")
        status = str(event.get("status") or "")
        if scheduled_day is not None and event_type in {EVENT_DAY_STATE, EVENT_MEASUREMENT_TRANSITION}:
            current_day = int(scheduled_day)
        if status == STATUS_TRAIN_EXPOSURE or event_type == STATUS_TRAIN_EXPOSURE:
            row = {
                "policy_id": event.get("policy_id") or event.get("policy_context") or "",
                "question_id": canonical_question_id(str(event.get("question_id") or "")),
                "semantic_family_id": event.get("semantic_family_id") or "",
                "domain": event.get("domain") or "",
                "objective": event.get("objective") or "",
                "service_class": event.get("service_class") or "",
                "scheduled_day": scheduled_day,
                "counted": bool(event.get("counted", True)),
                "status": "COUNTED" if event.get("counted", True) else "PROTOCOL_DEVIATION",
                "reason": event.get("reason") or "OK",
            }
            train_log.append(row)
            if scheduled_day is not None:
                current_day = int(scheduled_day)
        elif status == STATUS_DEVIATION and event.get("reason") in {
            "WRONG_POLICY_USED",
            "OVER_BUDGET_TRAIN_EXPOSURE",
            "TRAINING_AFTER_BLOCK_COMPLETE",
            "INSUFFICIENT_TRAIN_CAPACITY",
        }:
            train_log.append(
                {
                    "policy_id": event.get("policy_id") or event.get("policy_context") or "",
                    "question_id": canonical_question_id(str(event.get("question_id") or "")),
                    "semantic_family_id": event.get("semantic_family_id") or "",
                    "domain": event.get("domain") or "",
                    "objective": event.get("objective") or "",
                    "service_class": event.get("service_class") or "",
                    "scheduled_day": scheduled_day,
                    "counted": False,
                    "status": STATUS_DEVIATION,
                    "reason": event.get("reason"),
                }
            )
            if scheduled_day is not None:
                current_day = int(scheduled_day)
        elif status in REAL_OBSERVATION_STATUSES | TERMINAL_PROBE_STATUSES and scheduled_day is not None:
            current_day = int(scheduled_day)
    _SESSION.train_log = train_log
    _SESSION.events = restored_events
    if current_day is None:
        for event in reversed(events):
            if event.get("scheduled_day") is not None:
                current_day = int(event["scheduled_day"])
                break
    _SESSION.current_scheduled_day = current_day
    _SESSION.day1_local_date = day1_local_date
    _SESSION.calendar_utc_offset_minutes = calendar_utc_offset_minutes
    _SESSION.last_local_date = last_local_date
    if _SESSION.ledger is not None:
        _restore_ledger_from_events(_SESSION.ledger, events)
    _SESSION.protocol_locked = any(
        event.get("status") in REAL_OBSERVATION_STATUSES and not event.get("synthetic") for event in events
    )
    _SESSION.day_state = _derive_day_state(current_day)


def _persist_event(payload: Mapping[str, Any], ledger_path: Path | None = None) -> dict[str, Any]:
    event = dict(payload)
    _SESSION.events.append(event)
    path = ledger_path if ledger_path is not None else _SESSION.ledger_path
    if path is not None:
        _append_ledger(event, Path(path))
    return event


def load_committed_protocol() -> dict[str, Any]:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def allocated_policy_for_day(scheduled_day: int, historical_prior: Mapping[str, Any] | None = None) -> str:
    del historical_prior
    for row in POLICY_SEQUENCE:
        if int(row["scheduled_day"]) == int(scheduled_day):
            return str(row["policy_id"])
    raise ValueError("UNKNOWN_SCHEDULED_DAY")


def default_production_ledger_path(epoch: str = MEASUREMENT_EPOCH) -> Path:
    return Path.home() / USER_DATA_DIRNAME / "measurement" / f"{epoch}.jsonl"


def pre_run_disposition(protocol: Mapping[str, Any], *, real_observations: int) -> dict[str, Any]:
    return {
        "status": "CAND01R3_MEASUREMENT_PROTOCOL_FROZEN",
        "PROTOCOL_VERSION": protocol.get("protocol_version"),
        "MEASUREMENT_EPOCH": protocol.get("measurement_epoch"),
        "TRAIN_QUESTIONS": int(protocol.get("train_question_count") or 0),
        "PROBE_QUESTIONS": int(protocol.get("probe_question_count") or 0),
        "INDEPENDENT_PROBE_FAMILIES": int(protocol.get("probe_family_count") or 0),
        "POLICY_SEQUENCE": "FROZEN",
        "PROBE_SCHEDULE": "FROZEN",
        "PRIMARY_ENDPOINT": "FROZEN",
        "MISSINGNESS_RULE": "FROZEN",
        "CONTAMINATION_RULE": "FROZEN",
        "ANALYSIS_PLAN": "FROZEN",
        "REAL_OBSERVATIONS": int(real_observations),
        "EMPIRICAL_RESULT": "NOT_YET_AVAILABLE",
        "DEFAULT_BANK_UNCHANGED": "YES",
        "DEPLOYMENT_AUTHORIZED": "NO",
    }


def _require_frozen_authority(authority: RuntimeAuthority) -> None:
    if not authority.valid:
        raise Cand01R3AuthorityError(authority.reason)
    if authority.train_count != 171 or authority.probe_count != 29:
        raise Cand01R3AuthorityError("PARTITION_COUNT_MISMATCH")
    if tuple(authority.probe_family_ids) != EXPECTED_PROBE_FAMILIES:
        raise Cand01R3AuthorityError("PROBE_FAMILY_MISMATCH")
    expected = {
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "store_sha256": EXPECTED_STORE_SHA256,
        "semantic_audit_sha256": EXPECTED_SEMANTIC_AUDIT_SHA256,
        "compiled_sha256": EXPECTED_COMPILED_SHA256,
    }
    actual = {
        "manifest_sha256": authority.manifest_sha256,
        "store_sha256": authority.store_sha256,
        "semantic_audit_sha256": authority.semantic_audit_sha256,
        "compiled_sha256": authority.compiled_sha256,
    }
    if actual != expected:
        raise Cand01R3AuthorityError("FROZEN_HASH_MISMATCH")


def begin_cand01r3_measurement(
    *,
    learner_id: str,
    measurement_epoch: str,
    schedule_version: str,
    policy_sequence_version: str,
    manifest_sha256: str,
    store_sha256: str,
    semantic_audit_sha256: str,
    compiled_sha256: str,
    candidate_bank_identity: str,
    ledger_path: str | Path | None = None,
    authority: RuntimeAuthority | None = None,
    allow_synthetic: bool = False,
) -> MeasurementSession:
    loaded = authority if authority is not None else load_runtime_authority()
    _require_frozen_authority(loaded)
    protocol = build_protocol(loaded)
    if measurement_epoch != MEASUREMENT_EPOCH:
        raise Cand01R3AuthorityError("WRONG_MEASUREMENT_EPOCH")
    if schedule_version != SCHEDULE_VERSION:
        raise Cand01R3AuthorityError("WRONG_SCHEDULE_VERSION")
    if policy_sequence_version != POLICY_SEQUENCE_VERSION:
        raise Cand01R3AuthorityError("WRONG_POLICY_SEQUENCE_VERSION")
    if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        raise Cand01R3AuthorityError("MANIFEST_HASH_MISMATCH")
    if store_sha256 != EXPECTED_STORE_SHA256:
        raise Cand01R3AuthorityError("STORE_HASH_MISMATCH")
    if semantic_audit_sha256 != EXPECTED_SEMANTIC_AUDIT_SHA256:
        raise Cand01R3AuthorityError("SEMANTIC_AUDIT_HASH_MISMATCH")
    if compiled_sha256 != EXPECTED_COMPILED_SHA256 or candidate_bank_identity != EXPECTED_COMPILED_SHA256:
        raise Cand01R3AuthorityError("COMPILED_HASH_MISMATCH")
    path = Path(ledger_path) if ledger_path is not None else default_production_ledger_path(measurement_epoch)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_ledger_events(path)
    resume = bool(existing)
    if resume:
        _verify_resume_identity(
            existing,
            learner_id=learner_id,
            measurement_epoch=measurement_epoch,
            protocol=protocol,
            authority=loaded,
        )
    session = MeasurementSession(
        active=True,
        learner_id=learner_id,
        measurement_epoch=measurement_epoch,
        schedule_version=schedule_version,
        policy_sequence_version=policy_sequence_version,
        protocol_version=PROTOCOL_VERSION,
        protocol_sha256=protocol_sha256(protocol),
        candidate_bank_identity=candidate_bank_identity,
        partition_epoch=loaded.partition_epoch or PARTITION_EPOCH,
        ledger_path=path,
        allow_synthetic=allow_synthetic,
        protocol=protocol,
        schedule_index={row["question_id"]: row for row in protocol["schedule"]},
        train_ids={qid for qid, item in loaded.items.items() if item.get("role") == ROLE_TRAIN},
        probe_ids={qid for qid, item in loaded.items.items() if item.get("role") == ROLE_PROBE},
        ledger=MeasurementLedger(learner_id=learner_id, authority=loaded),
        day_state=STATE_DAY_NOT_STARTED,
    )
    global _SESSION
    _SESSION = session
    if resume:
        _restore_session_from_events(existing)
        day_state = measurement_runtime_state()
        policy_id, intended_use = _runtime_policy_for_state(_SESSION.current_scheduled_day, day_state)
        activate_cand01r3_experiment(
            policy_id=policy_id,
            experiment_id=MEASUREMENT_EPOCH,
            evaluation_epoch=MEASUREMENT_EPOCH,
            intended_use=intended_use,
            authority=loaded,
            learner_id=learner_id,
        )
        _apply_runtime_for_current_state()
        return _SESSION
    if not path.exists():
        path.write_text("", encoding="utf-8")
    activate_cand01r3_experiment(
        policy_id=POLICY_SMART_PRACTICE,
        experiment_id=MEASUREMENT_EPOCH,
        evaluation_epoch=MEASUREMENT_EPOCH,
        intended_use=INTENDED_USE_TRAINING,
        authority=loaded,
        learner_id=learner_id,
    )
    begin_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": EVENT_EPOCH_BEGIN,
        "status": EVENT_EPOCH_BEGIN,
        "reason": "BEGIN_NEW_FROZEN_EPOCH",
        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scheduled_day": None,
        "counted": False,
        **_authority_identity(loaded, learner_id=learner_id, protocol=protocol),
    }
    _persist_event(begin_payload, path)
    return _SESSION


def _lock_if_real(event: Mapping[str, Any]) -> None:
    if event.get("synthetic") or str(event.get("marker") or "") in SYNTHETIC_MARKERS:
        return
    if event.get("status") in {
        STATUS_PRIMARY,
        STATUS_UNOBSERVED,
        STATUS_CONTAMINATED,
        STATUS_DUPLICATE,
        STATUS_DEVIATION,
    }:
        _SESSION.protocol_locked = True


def _append_ledger(payload: Mapping[str, Any], ledger_path: Path | None) -> None:
    path = Path(ledger_path or _SESSION.ledger_path or default_production_ledger_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n")


def _exposure_snapshot() -> tuple[dict[str, Any], dict[str, Any]]:
    policies = {"SMART_PRACTICE": _empty_policy_exposure(), "RRC_1": _empty_policy_exposure()}
    seen: dict[str, set[str]] = {"SMART_PRACTICE": set(), "RRC_1": set()}
    families: dict[str, set[str]] = {"SMART_PRACTICE": set(), "RRC_1": set()}
    for row in _SESSION.train_log:
        if row.get("counted") is False:
            continue
        policy_id = str(row.get("policy_id") or "")
        if policy_id not in policies:
            policies[policy_id] = _empty_policy_exposure()
            seen[policy_id] = set()
            families[policy_id] = set()
        bucket = policies[policy_id]
        bucket["train_questions_seen"] += 1
        question_id = str(row.get("question_id") or "")
        if question_id:
            seen[policy_id].add(question_id)
        family_id = str(row.get("semantic_family_id") or "")
        if family_id:
            families[policy_id].add(family_id)
        domain = str(row.get("domain") or "")
        objective = str(row.get("objective") or "")
        if domain:
            bucket["domain_counts"][domain] = bucket["domain_counts"].get(domain, 0) + 1
        if objective:
            bucket["objective_counts"][objective] = bucket["objective_counts"].get(objective, 0) + 1
        service = str(row.get("service_class") or "")
        if service == "REPAIR":
            bucket["REPAIR_service_count"] += 1
        elif service == "REVIEW":
            bucket["REVIEW_service_count"] += 1
        elif service == "COVERAGE":
            bucket["COVERAGE_service_count"] += 1
    for policy_id, bucket in policies.items():
        bucket["unique_train_questions_seen"] = len(seen.get(policy_id) or [])
        bucket["semantic_families_seen"] = sorted(families.get(policy_id) or [])
    return policies, {key: dict(value) for key, value in policies.items()}


def record_train_exposure(
    *,
    policy_id: str,
    question_id: str,
    semantic_family_id: str = "",
    domain: str = "",
    objective: str = "",
    service_class: str = "",
    session_duration_seconds: float | None = None,
    rrc1_fairness: Mapping[str, Any] | None = None,
    scheduled_day: int | None = None,
) -> dict[str, Any]:
    qid = canonical_question_id(question_id)
    day = scheduled_day if scheduled_day is not None else _SESSION.current_scheduled_day
    row: dict[str, Any] = {
        "policy_id": policy_id,
        "question_id": qid,
        "semantic_family_id": semantic_family_id,
        "domain": domain,
        "objective": objective,
        "service_class": service_class,
        "session_duration_seconds": session_duration_seconds,
        "rrc1_fairness": dict(rrc1_fairness or {}),
        "scheduled_day": day,
        "counted": False,
        "status": "COUNTED",
        "reason": "OK",
    }
    if qid in _SESSION.probe_ids:
        row["status"] = "NOT_ELIGIBLE"
        row["reason"] = "PROBE_CANNOT_SATISFY_TRAIN_BUDGET"
        return row
    if _SESSION.active and _SESSION.train_ids and qid not in _SESSION.train_ids:
        row["status"] = "NOT_ELIGIBLE"
        row["reason"] = "QUESTION_NOT_IN_TRAIN"
        return row
    if day is not None:
        expected_policy = allocated_policy_for_day(int(day))
        if int(day) < 7 and policy_id != expected_policy:
            row["status"] = "PROTOCOL_DEVIATION"
            row["reason"] = "WRONG_POLICY_USED"
            if _SESSION.active:
                _SESSION.train_log.append(row)
                _persist_train_deviation(row, "WRONG_POLICY_USED")
            return row
        if int(day) >= 7:
            expected_block = current_train_block(int(day))
            expected_block_policy = str(expected_block.get("policy_id") or "")
            if policy_id != expected_block_policy and not (
                policy_id == "RRC_1" and _counted_train_exposures(int(day), "SMART_PRACTICE") >= DAY7_BLOCK_TRAIN_BUDGET
            ):
                if policy_id != expected_block_policy:
                    row["status"] = "PROTOCOL_DEVIATION"
                    row["reason"] = "WRONG_POLICY_USED"
                    if _SESSION.active:
                        _SESSION.train_log.append(row)
                        _persist_train_deviation(row, "WRONG_POLICY_USED")
                    return row
        budget = train_budget_for_day(int(day), policy_id if int(day) >= 7 else expected_policy)
        completed = _counted_train_exposures(int(day), policy_id if int(day) >= 7 else None)
        if completed >= budget:
            day_state = measurement_runtime_state()
            reason = (
                "TRAINING_AFTER_BLOCK_COMPLETE"
                if day_state in {STATE_TRAINING_COMPLETE, STATE_RRC1_COMPLETE, STATE_MEASUREMENT, STATE_DAY_COMPLETE}
                else "OVER_BUDGET_TRAIN_EXPOSURE"
            )
            if day_state in {STATE_TRAINING_COMPLETE, STATE_RRC1_COMPLETE} and completed >= budget:
                reason = "OVER_BUDGET_TRAIN_EXPOSURE"
            row["status"] = "PROTOCOL_DEVIATION"
            row["reason"] = reason
            if _SESSION.active:
                _SESSION.train_log.append(row)
                _persist_train_deviation(row, reason)
            return row
    row["counted"] = True
    if _SESSION.active:
        _SESSION.train_log.append(row)
        _persist_train_exposure(row)
        if day is not None and int(day) < 7 and _training_complete_for_day(int(day)):
            _SESSION.day_state = STATE_TRAINING_COMPLETE
        _apply_day7_handoff()
    return row


def _persist_train_exposure(row: Mapping[str, Any]) -> None:
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": STATUS_TRAIN_EXPOSURE,
        "status": STATUS_TRAIN_EXPOSURE,
        "reason": row.get("reason") or "OK",
        "question_id": row.get("question_id") or "",
        "policy_id": row.get("policy_id") or "",
        "policy_context": row.get("policy_id") or "",
        "semantic_family_id": row.get("semantic_family_id") or "",
        "domain": row.get("domain") or "",
        "objective": row.get("objective") or "",
        "service_class": row.get("service_class") or "",
        "scheduled_day": row.get("scheduled_day"),
        "counted": True,
        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intended_use": INTENDED_USE_TRAINING,
        "question_role": ROLE_TRAIN,
        **_session_identity_fields(),
    }
    _persist_event(payload)


def _persist_train_deviation(row: Mapping[str, Any], reason: str) -> None:
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": STATUS_DEVIATION,
        "status": STATUS_DEVIATION,
        "reason": reason,
        "question_id": row.get("question_id") or "",
        "policy_id": row.get("policy_id") or "",
        "policy_context": row.get("policy_id") or "",
        "semantic_family_id": row.get("semantic_family_id") or "",
        "domain": row.get("domain") or "",
        "objective": row.get("objective") or "",
        "service_class": row.get("service_class") or "",
        "scheduled_day": row.get("scheduled_day"),
        "counted": False,
        "observed": False,
        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intended_use": INTENDED_USE_TRAINING,
        "question_role": ROLE_TRAIN,
        **_session_identity_fields(),
    }
    _persist_event(payload)


def _reject_probe(
    question_id: str,
    scheduled: Mapping[str, Any] | None,
    reason: str,
    *,
    ledger_path: Path | None = None,
    synthetic: bool = False,
    marker: str = "",
    calendar_timestamp: str | None = None,
) -> MeasurementObservation:
    payload = _event_payload(
        question_id=question_id,
        status=STATUS_DEVIATION,
        reason=reason,
        selected=None,
        correct=None,
        kind="REJECTED",
        scheduled=scheduled,
        synthetic=synthetic,
        marker=marker,
        calendar_timestamp=calendar_timestamp,
        observed=False,
        first_attempt=False,
        clean=False,
        contaminated=False,
        contamination_reason=reason,
    )
    payload["intended_use"] = get_context().intended_use
    payload["counts_toward_primary"] = False
    if not synthetic:
        _append_ledger(payload, ledger_path or _SESSION.ledger_path)
        _SESSION.events.append(payload)
    return _observation_from_payload(payload, STATUS_DEVIATION, reason)


def _probe_gate_rejection(
    question_id: str,
    scheduled: Mapping[str, Any],
    *,
    ledger_path: Path | None = None,
    synthetic: bool = False,
    marker: str = "",
    calendar_timestamp: str | None = None,
) -> MeasurementObservation | None:
    day = _SESSION.current_scheduled_day
    state = measurement_runtime_state()
    scheduled_day = int(scheduled["scheduled_day"])
    if state not in {STATE_MEASUREMENT, STATE_DAY_COMPLETE}:
        reason = (
            "PROBE_BEFORE_TRAIN_BLOCK_COMPLETE"
            if day is None or not _training_complete_for_day(int(day))
            else "MEASUREMENT_MODE_NOT_ACTIVE"
        )
        return _reject_probe(
            question_id,
            scheduled,
            reason,
            ledger_path=ledger_path,
            synthetic=synthetic,
            marker=marker,
            calendar_timestamp=calendar_timestamp,
        )
    if day is None:
        return _reject_probe(
            question_id,
            scheduled,
            "MEASUREMENT_MODE_NOT_ACTIVE",
            ledger_path=ledger_path,
            synthetic=synthetic,
            marker=marker,
            calendar_timestamp=calendar_timestamp,
        )
    if scheduled_day != int(day):
        return _reject_probe(
            question_id,
            scheduled,
            "WRONG_MEASUREMENT_DAY",
            ledger_path=ledger_path,
            synthetic=synthetic,
            marker=marker,
            calendar_timestamp=calendar_timestamp,
        )
    if question_id not in todays_scheduled_probe_ids():
        return _reject_probe(
            question_id,
            scheduled,
            "UNSCHEDULED_PROBE",
            ledger_path=ledger_path,
            synthetic=synthetic,
            marker=marker,
            calendar_timestamp=calendar_timestamp,
        )
    return None


def _inactive_observation(reason: str, question_id: str = "") -> MeasurementObservation:
    return MeasurementObservation(status=STATUS_NOT_ELIGIBLE, reason=reason, question_id=question_id, payload={})


def _current_experiment_local_date() -> str:
    if _SESSION.calendar_utc_offset_minutes is not None:
        local_now = datetime.now(UTC) + timedelta(minutes=int(_SESSION.calendar_utc_offset_minutes))
        return local_now.date().isoformat()
    return datetime.now().astimezone().date().isoformat()


def _current_utc_offset_minutes() -> int:
    offset = datetime.now().astimezone().utcoffset()
    return int((offset.total_seconds() if offset is not None else 0) // 60)


def _calendar_fields() -> dict[str, Any]:
    return {
        "calendar_local_date": _current_experiment_local_date(),
        "day1_local_date": _SESSION.day1_local_date,
        "calendar_utc_offset_minutes": _SESSION.calendar_utc_offset_minutes,
    }


def _observation_from_payload(payload: Mapping[str, Any], status: str, reason: str) -> MeasurementObservation:
    identity_raw = payload.get("evaluation_id") or []
    identity: tuple[str, str, str, str] | None = None
    if isinstance(identity_raw, (list, tuple)) and len(identity_raw) == 4:
        identity = (str(identity_raw[0]), str(identity_raw[1]), str(identity_raw[2]), str(identity_raw[3]))
    correct = payload.get("correct")
    clean = bool(payload.get("clean"))
    counts = bool(payload.get("observed") and payload.get("first_attempt") and clean and status == STATUS_PRIMARY)
    return MeasurementObservation(
        status=status,
        reason=reason,
        question_id=str(payload.get("question_id") or ""),
        correct=correct if type(correct) is bool else None,
        evaluation_identity=identity,
        clean=clean,
        counts_toward_primary=counts,
        payload=dict(payload),
    )


def record_measurement_event(
    question: Mapping[str, Any] | str,
    *,
    selected: list[str] | None = None,
    correct: bool | None = None,
    kind: str = "SCORED",
    measurement_epoch: str | None = None,
    ledger_path: str | Path | None = None,
    synthetic: bool = False,
    marker: str = "",
    calendar_timestamp: str | None = None,
    contaminated: bool = False,
    contamination_reason: str = "",
) -> MeasurementObservation:
    question_id = canonical_question_id(question)
    marker_value = str(marker or ("SYNTHETIC" if synthetic else ""))
    synthetic_event = bool(synthetic or marker_value in SYNTHETIC_MARKERS)
    if not _SESSION.active:
        return _inactive_observation("MEASUREMENT_EPOCH_INACTIVE", question_id)
    if measurement_epoch and measurement_epoch != _SESSION.measurement_epoch:
        return _inactive_observation("WRONG_MEASUREMENT_EPOCH", question_id)
    target_path = Path(ledger_path or _SESSION.ledger_path or default_production_ledger_path())
    if synthetic_event and not _SESSION.allow_synthetic:
        return _inactive_observation("SYNTHETIC_FORBIDDEN_IN_PRODUCTION_LEDGER", question_id)
    authority = _SESSION.ledger.authority if _SESSION.ledger is not None else None
    item = (authority.items.get(question_id) if authority else None) or {}
    role = str(item.get("role") or "")
    if role == ROLE_TRAIN or question_id in _SESSION.train_ids:
        return _inactive_observation("TRAIN", question_id)
    scheduled = _SESSION.schedule_index.get(question_id)
    if scheduled is None:
        payload = _event_payload(
            question_id=question_id,
            status=STATUS_DEVIATION,
            reason="UNSCHEDULED_PROBE",
            selected=selected,
            correct=correct,
            kind=kind,
            scheduled=None,
            synthetic=synthetic_event,
            marker=marker_value,
            calendar_timestamp=calendar_timestamp,
            observed=True,
            first_attempt=False,
            clean=False,
            contaminated=True,
            contamination_reason="UNSCHEDULED_PROBE",
        )
        if not synthetic_event:
            _append_ledger(payload, target_path)
            _SESSION.events.append(payload)
            _lock_if_real(payload)
        return _observation_from_payload(payload, STATUS_DEVIATION, "UNSCHEDULED_PROBE")
    rejected = _probe_gate_rejection(
        question_id,
        scheduled,
        ledger_path=target_path,
        synthetic=synthetic_event,
        marker=marker_value,
        calendar_timestamp=calendar_timestamp,
    )
    if rejected is not None:
        return rejected
    if _SESSION.ledger is None:
        return _inactive_observation("MEASUREMENT_EPOCH_INACTIVE", question_id)
    if contaminated or _SESSION.ledger.is_contaminated(question_id):
        if contaminated:
            _SESSION.ledger.record_contamination(question_id, contamination_reason or "CONTAMINATED")
        payload = _event_payload(
            question_id=question_id,
            status=STATUS_CONTAMINATED,
            reason=contamination_reason or "CONTAMINATED",
            selected=selected,
            correct=correct,
            kind=kind,
            scheduled=scheduled,
            synthetic=synthetic_event,
            marker=marker_value,
            calendar_timestamp=calendar_timestamp,
            observed=True,
            first_attempt=False,
            clean=False,
            contaminated=True,
            contamination_reason=contamination_reason or "CONTAMINATED",
        )
        if not synthetic_event:
            _append_ledger(payload, target_path)
            _SESSION.events.append(payload)
            _lock_if_real(payload)
        return _observation_from_payload(payload, STATUS_CONTAMINATED, payload["contamination_reason"])
    question_payload = question if isinstance(question, Mapping) else {"id": question_id, "question_id": question_id}
    observation = _SESSION.ledger.record_scored_attempt(
        question_payload,
        selected=selected,
        correct=correct,
        kind=kind,
        persist=True,
    )
    status = observation.status
    first_attempt = status == STATUS_PRIMARY
    clean = first_attempt and not _SESSION.ledger.is_contaminated(question_id)
    payload = _event_payload(
        question_id=question_id,
        status=status,
        reason=observation.reason,
        selected=selected,
        correct=correct if status == STATUS_PRIMARY else (bool(correct) if correct is not None else None),
        kind=kind,
        scheduled=scheduled,
        synthetic=synthetic_event,
        marker=marker_value,
        calendar_timestamp=calendar_timestamp,
        observed=True,
        first_attempt=first_attempt,
        clean=clean,
        contaminated=False,
        contamination_reason="",
        evaluation_identity=observation.evaluation_identity,
    )
    if not synthetic_event:
        _append_ledger(payload, target_path)
        _SESSION.events.append(payload)
        _lock_if_real(payload)
    result = _observation_from_payload(payload, status, observation.reason)
    result.evaluation_identity = observation.evaluation_identity
    measurement_runtime_state()
    return result


def _event_payload(
    *,
    question_id: str,
    status: str,
    reason: str,
    selected: list[str] | None,
    correct: bool | None,
    kind: str,
    scheduled: Mapping[str, Any] | None,
    synthetic: bool,
    marker: str,
    calendar_timestamp: str | None,
    observed: bool,
    first_attempt: bool,
    clean: bool,
    contaminated: bool,
    contamination_reason: str,
    evaluation_identity: tuple[str, str, str, str] | None = None,
) -> dict[str, Any]:
    train_snapshot, policy_snapshot = _exposure_snapshot()
    scheduled_day = int(scheduled["scheduled_day"]) if scheduled else None
    family_id = str(scheduled.get("semantic_family_id") if scheduled else "")
    identity_fields = _session_identity_fields()
    identity = evaluation_identity or (
        _SESSION.learner_id,
        EXAM_ID,
        _SESSION.partition_epoch,
        question_id,
    )
    return {
        "event_id": str(uuid.uuid4()),
        "evaluation_id": list(identity),
        "learner_id": _SESSION.learner_id,
        "exam": EXAM_ID,
        "measurement_epoch": _SESSION.measurement_epoch,
        "calendar_timestamp": calendar_timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **_calendar_fields(),
        "scheduled_day": scheduled_day,
        "sequence_position": scheduled.get("sequence_position") if scheduled else None,
        "question_id": question_id,
        "semantic_family_id": family_id,
        "domain": scheduled.get("domain") if scheduled else "",
        "objective": scheduled.get("objective") if scheduled else "",
        "policy_context": scheduled.get("policy_id") if scheduled else get_context().policy_id,
        "intended_use": INTENDED_USE_MEASUREMENT,
        "question_role": ROLE_PROBE,
        "first_attempt": first_attempt,
        "clean": clean,
        "contaminated": contaminated,
        "contamination_reason": contamination_reason,
        "observed": observed,
        "correct": correct,
        "kind": kind,
        "status": status,
        "reason": reason,
        "selected_option_ids": list(selected or []),
        "train_exposure_snapshot": train_snapshot,
        "policy_exposure_snapshot": policy_snapshot,
        "synthetic": synthetic,
        "marker": marker,
        "protocol_version": _SESSION.protocol_version,
        "protocol_sha256": _SESSION.protocol_sha256,
        "duplicate_kind": kind if kind in DUPLICATE_KINDS else "",
        "partition_epoch": identity_fields["partition_epoch"],
        "manifest_sha256": identity_fields["manifest_sha256"],
        "store_sha256": identity_fields["store_sha256"],
        "semantic_audit_sha256": identity_fields["semantic_audit_sha256"],
        "compiled_sha256": identity_fields["compiled_sha256"],
        "candidate_bank_identity": identity_fields["candidate_bank_identity"],
    }


def record_unobserved(
    question_id: str,
    *,
    reason: str,
    ledger_path: str | Path | None = None,
) -> MeasurementObservation:
    if not _SESSION.active or _SESSION.ledger is None:
        return _inactive_observation("MEASUREMENT_EPOCH_INACTIVE", question_id)
    qid = canonical_question_id(question_id)
    scheduled = _SESSION.schedule_index.get(qid)
    if scheduled is None:
        return _inactive_observation("UNSCHEDULED_PROBE", qid)
    rejected = _probe_gate_rejection(
        qid, scheduled, ledger_path=Path(ledger_path) if ledger_path else _SESSION.ledger_path
    )
    if rejected is not None:
        return rejected
    observation = _SESSION.ledger.record_unobserved(qid, reason=reason)
    payload = _event_payload(
        question_id=qid,
        status=observation.status,
        reason=observation.reason,
        selected=None,
        correct=None,
        kind="UNOBSERVED",
        scheduled=scheduled,
        synthetic=False,
        marker="",
        calendar_timestamp=None,
        observed=False,
        first_attempt=False,
        clean=False,
        contaminated=False,
        contamination_reason="",
        evaluation_identity=observation.evaluation_identity,
    )
    _append_ledger(payload, Path(ledger_path) if ledger_path else _SESSION.ledger_path)
    _SESSION.events.append(payload)
    _lock_if_real(payload)
    result = _observation_from_payload(payload, observation.status, observation.reason)
    result.correct = None
    result.counts_toward_primary = False
    measurement_runtime_state()
    return result


def record_contamination(question_id: str, reason: str, *, ledger_path: str | Path | None = None) -> None:
    if not _SESSION.active or _SESSION.ledger is None:
        raise Cand01R3AuthorityError("MEASUREMENT_EPOCH_INACTIVE")
    qid = canonical_question_id(question_id)
    _SESSION.ledger.record_contamination(qid, reason)
    for event in _SESSION.events:
        if str(event.get("question_id") or "") == qid:
            event["contaminated"] = True
            event["clean"] = False
            event["first_attempt"] = False
            if event.get("status") == STATUS_PRIMARY:
                event["status"] = STATUS_CONTAMINATED
                event["contamination_reason"] = reason
    scheduled = _SESSION.schedule_index.get(qid)
    payload = _event_payload(
        question_id=qid,
        status=STATUS_CONTAMINATED,
        reason=reason,
        selected=None,
        correct=None,
        kind="CONTAMINATION",
        scheduled=scheduled,
        synthetic=False,
        marker="",
        calendar_timestamp=None,
        observed=False,
        first_attempt=False,
        clean=False,
        contaminated=True,
        contamination_reason=reason,
    )
    _append_ledger(payload, Path(ledger_path) if ledger_path else _SESSION.ledger_path)
    _SESSION.events.append(payload)
    _lock_if_real(payload)
    measurement_runtime_state()


def clear_contamination(question_id: str) -> None:
    if _SESSION.ledger is None:
        raise ValueError("contamination is monotonic")
    _SESSION.ledger.clear_contamination(question_id)


def clean_primary_events(*, ledger_path: str | Path | None = None) -> list[dict[str, Any]]:
    del ledger_path
    contaminated_ids = {
        str(event.get("question_id") or "")
        for event in _SESSION.events
        if event.get("contaminated") or event.get("status") == STATUS_CONTAMINATED
    }
    if _SESSION.ledger is not None:
        contaminated_ids.update(
            canonical_question_id(row["question_id"]) for row in _SESSION.ledger.contaminated_observations()
        )
    return [
        dict(event)
        for event in _SESSION.events
        if event.get("status") == STATUS_PRIMARY
        and event.get("clean")
        and not event.get("contaminated")
        and str(event.get("question_id") or "") not in contaminated_ids
    ]


def record_outside_study(
    code: str,
    *,
    note: str = "",
    scheduled_day: int | None = None,
    ledger_path: str | Path | None = None,
) -> MeasurementObservation:
    if not _SESSION.active:
        return _inactive_observation("MEASUREMENT_EPOCH_INACTIVE")
    if code not in OUTSIDE_STUDY_CODES:
        return _inactive_observation("UNKNOWN_OUTSIDE_STUDY")
    payload: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "evaluation_id": [],
        "learner_id": _SESSION.learner_id,
        "exam": EXAM_ID,
        "measurement_epoch": _SESSION.measurement_epoch,
        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scheduled_day": scheduled_day,
        "question_id": "",
        "semantic_family_id": "",
        "policy_context": allocated_policy_for_day(scheduled_day) if scheduled_day else "",
        "intended_use": "OBSERVATIONAL_METADATA",
        "first_attempt": False,
        "clean": False,
        "contaminated": False,
        "contamination_reason": "",
        "observed": False,
        "correct": None,
        "status": STATUS_OUTSIDE_STUDY,
        "outside_study": code,
        "note": note,
        "synthetic": False,
        "marker": "",
        "protocol_version": _SESSION.protocol_version,
        "protocol_sha256": _SESSION.protocol_sha256,
    }
    _append_ledger(payload, Path(ledger_path) if ledger_path else _SESSION.ledger_path)
    _SESSION.events.append(payload)
    return MeasurementObservation(
        status=STATUS_OUTSIDE_STUDY,
        reason="OK",
        payload=payload,
        counts_toward_primary=False,
        clean=False,
    )


def mutate_policy_sequence(new_sequence: list[Mapping[str, Any]]) -> None:
    del new_sequence
    if _SESSION.protocol_locked:
        raise ValueError("PROTOCOL_FROZEN_AFTER_FIRST_OBSERVATION")
    raise ValueError("POLICY_SEQUENCE_IS_FROZEN")


def replace_active_protocol(new_protocol: Mapping[str, Any]) -> None:
    del new_protocol
    if _SESSION.protocol_locked:
        raise ValueError("PROTOCOL_FROZEN_AFTER_FIRST_OBSERVATION")
    raise ValueError("PROTOCOL_IS_FROZEN")


def set_measurement_day(scheduled_day: int) -> str:
    new_day = int(scheduled_day)
    _policy_row(new_day)
    current = _SESSION.current_scheduled_day
    local_date = _current_experiment_local_date()
    if _SESSION.active:
        if current is not None and int(current) != new_day and not _day_is_complete(int(current)):
            raise Cand01R3AuthorityError("PREVIOUS_DAY_INCOMPLETE")
        for prior in range(1, new_day):
            if not _day_is_complete(prior):
                raise Cand01R3AuthorityError("PREVIOUS_DAY_INCOMPLETE")
        if _SESSION.last_local_date and local_date < _SESSION.last_local_date:
            raise Cand01R3AuthorityError("MEASUREMENT_CLOCK_REGRESSION")
        if not _SESSION.day1_local_date:
            if new_day != 1:
                raise Cand01R3AuthorityError("DAY1_CALENDAR_ANCHOR_MISSING")
            _SESSION.day1_local_date = local_date
            _SESSION.calendar_utc_offset_minutes = _current_utc_offset_minutes()
        anchor = date.fromisoformat(_SESSION.day1_local_date)
        earliest = anchor + timedelta(days=new_day - 1)
        if date.fromisoformat(local_date) < earliest:
            raise Cand01R3AuthorityError("MEASUREMENT_DAY_TOO_EARLY")
        _SESSION.last_local_date = local_date
    policy_id = allocated_policy_for_day(new_day)
    _SESSION.current_scheduled_day = new_day
    if new_day >= 7:
        _SESSION.day_state = _derive_day_state(new_day) if _day_has_progress(new_day) else STATE_SMART_PRACTICE_TRAINING
    else:
        _SESSION.day_state = _derive_day_state(new_day) if _day_has_progress(new_day) else STATE_TRAINING
    if _SESSION.active:
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": EVENT_DAY_STATE,
            "status": EVENT_DAY_STATE,
            "reason": "SET_MEASUREMENT_DAY",
            "scheduled_day": new_day,
            "day_state": _SESSION.day_state,
            "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **_calendar_fields(),
            "counted": False,
            **_session_identity_fields(),
        }
        _persist_event(payload)
        if is_cand01r3_active():
            _apply_runtime_for_current_state()
    return policy_id


def begin_todays_probe_measurement() -> dict[str, Any]:
    if not _SESSION.active:
        raise Cand01R3AuthorityError("MEASUREMENT_EPOCH_INACTIVE")
    day = _SESSION.current_scheduled_day
    if day is None:
        raise Cand01R3AuthorityError("MEASUREMENT_DAY_NOT_SET")
    if not _training_complete_for_day(int(day)):
        raise Cand01R3AuthorityError("PROBE_BEFORE_TRAIN_BLOCK_COMPLETE")
    state = measurement_runtime_state()
    if state in {STATE_MEASUREMENT, STATE_DAY_COMPLETE}:
        _apply_runtime_for_current_state()
        return {
            "day_state": state,
            "intended_use": INTENDED_USE_MEASUREMENT,
            "scheduled_day": int(day),
            "probe_ids": ordered_scheduled_probe_ids_for_day(int(day)),
        }
    _SESSION.day_state = STATE_MEASUREMENT
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": EVENT_MEASUREMENT_TRANSITION,
        "status": EVENT_MEASUREMENT_TRANSITION,
        "reason": "BEGIN_TODAYS_PROBE_MEASUREMENT",
        "scheduled_day": int(day),
        "day_state": STATE_MEASUREMENT,
        "calendar_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **_calendar_fields(),
        "counted": False,
        **_session_identity_fields(),
    }
    _persist_event(payload)
    if is_cand01r3_active():
        get_context().policy_id = POLICY_MEASUREMENT
        get_context().intended_use = INTENDED_USE_MEASUREMENT
    return {
        "day_state": STATE_MEASUREMENT,
        "intended_use": INTENDED_USE_MEASUREMENT,
        "scheduled_day": int(day),
        "probe_ids": sorted(todays_scheduled_probe_ids()),
    }


def _frozen_compiled_answer_key(question_id: str) -> tuple[str, ...]:
    actual_sha256 = hashlib.sha256(
        COMPILED_PATH.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    ).hexdigest()
    if actual_sha256 != EXPECTED_COMPILED_SHA256:
        raise Cand01R3AuthorityError("COMPILED_BANK_HASH_MISMATCH")
    raw = json.loads(COMPILED_PATH.read_text(encoding="utf-8"))
    questions = raw.get("questions") if isinstance(raw, Mapping) else raw
    if isinstance(raw, Mapping) and questions is None:
        questions = raw.get("items") or []
    for row in questions or []:
        if not isinstance(row, Mapping) or canonical_question_id(row) != question_id:
            continue
        correct = row.get("correct")
        if not isinstance(correct, (list, tuple, set)) or not correct:
            raise Cand01R3AuthorityError("INVALID_MEASUREMENT_ANSWER_KEY")
        return tuple(str(value) for value in correct)
    raise Cand01R3AuthorityError("MEASUREMENT_ANSWER_KEY_NOT_FOUND")


def score_measurement_probe_answer(question: Mapping[str, Any], selected: Sequence[str] | None = None) -> bool:
    question_id = canonical_question_id(question)
    if not question_id:
        raise Cand01R3AuthorityError("MEASUREMENT_QUESTION_ID_MISSING")
    correct = _frozen_compiled_answer_key(question_id)
    selected_ids = {str(value) for value in (selected or [])}
    return selected_ids == set(correct)


def record_measurement_probe_answer(
    question: Mapping[str, Any],
    *,
    selected: Sequence[str] | None = None,
    kind: str = "SCORED",
) -> MeasurementObservation:
    correct = score_measurement_probe_answer(question, selected)
    return record_measurement_event(question, selected=list(selected or []), correct=correct, kind=kind)


def notify_scored_attempt(
    question: Mapping[str, Any],
    *,
    selected: list[str] | None = None,
    correct: bool | None = None,
    kind: str = "SCORED",
    service_class: str = "",
) -> MeasurementObservation | None:
    if not is_measurement_active():
        return None
    question_id = canonical_question_id(question)
    if question_id in _SESSION.train_ids:
        policy_id = "SMART_PRACTICE"
        runtime_policy = get_context().policy_id
        if runtime_policy == POLICY_RRC1:
            policy_id = "RRC_1"
        record_train_exposure(
            policy_id=policy_id,
            question_id=question_id,
            semantic_family_id=str(question.get("semantic_family_id") or ""),
            domain=str(question.get("domain") or ""),
            objective=str(question.get("objective") or question.get("objective_code") or ""),
            service_class=service_class,
            scheduled_day=_SESSION.current_scheduled_day,
        )
        return None
    return record_measurement_probe_answer(question, selected=selected, kind=kind)


def today_measurement_card(scheduled_day: int) -> dict[str, Any]:
    protocol = _SESSION.protocol or build_protocol()
    rows = [row for row in protocol["schedule"] if int(row["scheduled_day"]) == int(scheduled_day)]
    policy_id = allocated_policy_for_day(scheduled_day)
    if int(scheduled_day) >= 7:
        block = current_train_block(int(scheduled_day))
        budget = int(block.get("train_item_budget") or 0)
        completed = _counted_train_exposures(int(scheduled_day), str(block.get("policy_id") or ""))
        remaining = max(0, budget - completed)
        day7_blocks = []
        for item in _policy_row(int(scheduled_day)).get("training_blocks") or []:
            item_budget = int(item.get("train_item_budget") or 0)
            item_done = _counted_train_exposures(int(scheduled_day), str(item.get("policy_id") or ""))
            day7_blocks.append(
                {
                    "policy_id": item.get("policy_id"),
                    "train_budget": item_budget,
                    "train_exposures_completed": item_done,
                    "train_exposures_remaining": max(0, item_budget - item_done),
                }
            )
    else:
        budget = train_budget_for_day(int(scheduled_day))
        completed = _counted_train_exposures(int(scheduled_day))
        remaining = max(0, budget - completed)
        day7_blocks = []
    complete = remaining == 0 and budget > 0
    return {
        "scheduled_day": scheduled_day,
        "policy_id": policy_id,
        "questions": rows,
        "measurement_active": is_measurement_active(),
        "real_observations": len([event for event in _SESSION.events if not event.get("synthetic")]),
        "train_budget": budget,
        "train_exposures_completed": completed,
        "train_exposures_remaining": remaining,
        "training_block_status": "TRAINING_BLOCK_COMPLETE" if complete else "IN_PROGRESS",
        "next_action": (
            "BEGIN TODAY'S PROBE MEASUREMENT"
            if complete and measurement_runtime_state() not in {STATE_MEASUREMENT, STATE_DAY_COMPLETE}
            else ("PROCEED TO TODAY'S SCHEDULED PROBE" if complete else "CONTINUE TRAIN BLOCK")
        ),
        "day7_blocks": day7_blocks,
        "day_state": measurement_runtime_state() if is_measurement_active() else STATE_DAY_NOT_STARTED,
        "intended_use": get_context().intended_use if is_cand01r3_active() else "",
    }


def write_committed_protocol(path: Path | None = None) -> dict[str, Any]:
    protocol = build_protocol()
    target = Path(path or PROTOCOL_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return protocol


def deactivate_measurement() -> None:
    reset_measurement_session()
    reset_cand01r3_runtime()


def measurement_context_metadata() -> dict[str, str]:
    context: Cand01R3RuntimeContext = get_context()
    return {
        "measurement_epoch": _SESSION.measurement_epoch,
        "protocol_version": _SESSION.protocol_version,
        "protocol_sha256": _SESSION.protocol_sha256,
        "policy_id": context.policy_id,
        "learner_id": _SESSION.learner_id,
    }
