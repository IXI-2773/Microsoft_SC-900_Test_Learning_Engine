from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASE3_ROOT = ROOT / "content" / "sc900" / "phase3"
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"

EXPECTED_AUDIT_SHA256 = "e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701"
EXPECTED_STORE_SHA256 = "2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c"
EXPECTED_COMPILED_SHA256 = "72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b"
EXPECTED_MANIFEST_SHA256 = "67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90"
EXPECTED_DEFAULT_BANK_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"
PARTITION_EPOCH = "phase3-task6-train-probe-partition"
LEARNER_ID = "local-single-user"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def question(
    question_id: str,
    *,
    role_hint: str = "TRAIN",
    family: str = "family_train",
    status: str = "approved",
    suitability: str = "eligible",
    domain: str = "microsoft_entra",
    objective: str = "entra_authentication",
    question_number: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": question_id,
        "question_id": question_id,
        "question_number": question_number if question_number is not None else abs(hash(question_id)) % 10_000,
        "domain": domain,
        "objective": objective,
        "objective_code": objective,
        "promotion_status": status,
        "topics": [family],
        "prompt": f"stem for {question_id}",
        "choices": {"A": "alpha", "B": "beta"},
        "correct": ["A"],
        "general_explanation": f"explanation for {question_id}",
        "metadata": {
            "semantic_family_id": family,
            "future_probe_suitability": suitability,
            "role_hint": role_hint,
        },
    }
    payload.update(extra)
    return payload


def item_record(
    question_id: str,
    role: str,
    family: str,
    *,
    family_state: str = "resolved",
    status: str = "approved",
    suitability: str = "eligible",
) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "role": role,
        "semantic_family_id": family,
        "family_state": family_state,
        "promotion_status": status,
        "future_probe_suitability": suitability,
    }


def family_record(family: str, role: str, members: list[str], *, family_state: str = "resolved") -> dict[str, Any]:
    return {
        "semantic_family_id": family,
        "role": role,
        "member_ids": list(members),
        "family_state": family_state,
    }


def synthetic_authority(
    *,
    train_ids: list[str] | None = None,
    probe_ids: list[str] | None = None,
    unassigned_ids: list[str] | None = None,
    roles: dict[str, str] | None = None,
    family_map: dict[str, str] | None = None,
    family_roles: dict[str, str] | None = None,
    family_states: dict[str, str] | None = None,
    statuses: dict[str, str] | None = None,
    suitability: dict[str, str] | None = None,
    transfer_edges: list[dict[str, str]] | None = None,
    valid: bool = True,
    reason: str = "OK",
    partition_epoch: str = PARTITION_EPOCH,
    manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    store_sha256: str = EXPECTED_STORE_SHA256,
    semantic_audit_sha256: str = EXPECTED_AUDIT_SHA256,
    compiled_sha256: str = EXPECTED_COMPILED_SHA256,
):
    from cand01r3_partition import RuntimeAuthority

    train_ids = list(train_ids or ["train_a", "train_b", "train_c"])
    probe_ids = list(probe_ids or ["probe_a"])
    unassigned_ids = list(unassigned_ids or [])
    family_map = dict(family_map or {})
    family_roles = dict(family_roles or {})
    family_states = dict(family_states or {})
    statuses = dict(statuses or {})
    suitability = dict(suitability or {})
    roles = dict(roles or {})
    items: dict[str, dict[str, Any]] = {}
    families: dict[str, dict[str, Any]] = {}
    all_ids = train_ids + probe_ids + unassigned_ids
    for question_id in all_ids:
        if question_id in train_ids:
            default_role = "TRAIN"
            default_family = "family_train"
        elif question_id in probe_ids:
            default_role = "PROBE"
            default_family = "family_probe"
        else:
            default_role = "UNASSIGNED"
            default_family = f"family_{question_id}"
        role = roles.get(question_id, default_role)
        family = family_map.get(question_id, default_family)
        items[question_id] = item_record(
            question_id,
            role,
            family,
            family_state=family_states.get(family, "resolved"),
            status=statuses.get(question_id, "approved"),
            suitability=suitability.get(question_id, "eligible"),
        )
        families.setdefault(
            family,
            family_record(family, family_roles.get(family, role), [], family_state=family_states.get(family, "resolved")),
        )
        families[family]["member_ids"].append(question_id)
        if family not in family_roles:
            families[family]["role"] = role
    return RuntimeAuthority(
        valid=valid,
        reason=reason,
        partition_epoch=partition_epoch,
        manifest_sha256=manifest_sha256,
        store_sha256=store_sha256,
        semantic_audit_sha256=semantic_audit_sha256,
        compiled_sha256=compiled_sha256,
        items=items,
        families=families,
        transfer_edges=list(transfer_edges or []),
        probe_family_ids=tuple(sorted({family_map.get(qid, "family_probe") for qid in probe_ids})),
        train_family_ids=tuple(sorted({family_map.get(qid, "family_train") for qid in train_ids})),
    )


def activate_synthetic(authority=None, **kwargs):
    from cand01r3_runtime import activate_cand01r3_experiment, reset_cand01r3_runtime

    reset_cand01r3_runtime()
    authority = authority or synthetic_authority()
    return activate_cand01r3_experiment(
        policy_id=kwargs.get("policy_id", "RRC_1_CHALLENGER"),
        experiment_id=kwargs.get("experiment_id", "cand01r3-test"),
        evaluation_epoch=kwargs.get("evaluation_epoch", "eval-1"),
        intended_use=kwargs.get("intended_use", "TRAINING"),
        authority=authority,
        learner_id=kwargs.get("learner_id", LEARNER_ID),
    )


def progress_record(**overrides: Any) -> dict[str, Any]:
    record = {
        "attempts": 0,
        "correct_count": 0,
        "wrong_count": 0,
        "correct_streak": 0,
        "last_correct": None,
        "last_seen": "",
        "next_review": "",
        "suspended": False,
        "flagged": False,
        "last_confidence": "Sure",
        "learner_memory": {"next_review_at": "", "retrievability": 1.0},
        "historical_prior": {"sy0701_mastery": 0.91, "security_plus_profile": "strong"},
        "cross_exam_readiness": 0.8,
        "slow_success": False,
        "response_seconds": 12.0,
        "smart_utility": 99.0,
        "concept_graph_score": 88.0,
        "brier": 0.11,
        "ece": 0.04,
        "session_endurance_recommendation": 40,
    }
    record.update(overrides)
    return record


class _Var:
    def __init__(self, value: Any = ""):
        self.value = value

    def get(self) -> Any:
        return self.value

    def set(self, value: Any) -> None:
        self.value = value


class SessionBuilderHarness:
    def __init__(self, questions: list[dict[str, Any]], records: dict[str, dict[str, Any]] | None = None):
        from app_session_builder_mixin import SessionBuilderMixin

        self.master_questions = copy.deepcopy(questions)
        self.questions = []
        self.progress_data = {"questions": records or {}, "meta": {}, "history": []}
        self.session_answer_history = []
        self.active_session_mode = "Practice"
        self.domain_filter_var = _Var("All domains")
        self.topic_filter_var = _Var("All topics")
        self.session_source_var = _Var("All")
        self.session_mode_var = _Var("Practice")
        self.session_count_var = _Var("All visible")
        self.session_random_var = _Var(False)
        self.smart_practice_signal_cache_key = None
        self.smart_practice_signal_cache_payload = None
        self.smart_practice_pool_cache = {}
        self.smart_practice_prewarm = None
        self._builder = SessionBuilderMixin

    def _question_key(self, q):
        from progress_store import question_key

        return question_key(q)

    def _progress_questions(self):
        return self.progress_data.setdefault("questions", {})

    def _normalized_study_label(self, value: str) -> str:
        return str(value or "").strip().casefold()

    def get_filtered_master_pool(self):
        return self._builder.get_filtered_master_pool(self)

    def get_session_builder_pool(self):
        return self._builder.get_session_builder_pool(self)

    def filter_pool_by_session_source(self, pool):
        return list(pool)

    def build_due_review_pool(self):
        return self._builder.build_due_review_pool(self)

    def build_weak_retest_pool(self):
        return self._builder.build_weak_retest_pool(self)

    def _smart_practice_worker_snapshot(self, *, base_pool=None):
        return self._builder._smart_practice_worker_snapshot(self, base_pool=base_pool)

    def _smart_practice_signal_key(self):
        from cand01r3_runtime import partition_cache_identity

        return ("test-key", partition_cache_identity())


class QuestionFlowHarness:
    def __init__(self, questions: list[dict[str, Any]], records: dict[str, dict[str, Any]] | None = None):
        from app_question_flow_mixin import QuestionFlowMixin

        self.master_questions = copy.deepcopy(questions)
        self.questions = copy.deepcopy(questions[:1])
        self.index = 0
        self.progress_data = {"questions": records or {}, "meta": {}, "history": []}
        self.session_answer_history = []
        self.active_session_mode = "Practice"
        self.followup_candidate_index = None
        self.followup_candidate_index_signature = None
        self.last_question_list_signature = None
        self.session_question_limit = None
        self._flow = QuestionFlowMixin

    def _question_key(self, q):
        from progress_store import question_key

        return question_key(q)

    def _progress_questions(self):
        return self.progress_data.setdefault("questions", {})

    def _progress_record(self, q, create=False):
        key = self._question_key(q)
        records = self._progress_questions()
        if key not in records and create:
            records[key] = progress_record()
        return records.get(key, {})

    def _clone_questions(self, questions):
        return copy.deepcopy(list(questions))

    def _reset_runtime_question_state(self, questions) -> None:
        for question in questions:
            question["answered"] = False

    def refresh_session_runtime_identity(self) -> None:
        return None

    def _coverage_unit_for_question(self, q):
        return "objective", str(q.get("objective") or "obj")

    def _stem_style_for_question(self, q):
        return str(q.get("stem_style") or "single_answer")

    def find_question_twins(self, q, limit: int = 2):
        return self._flow.find_question_twins(self, q, limit=limit)

    def maybe_queue_question_twins(self, q):
        return self._flow.maybe_queue_question_twins(self, q)

    def _rebuild_followup_candidate_index(self):
        return self._flow._rebuild_followup_candidate_index(self)

    def _followup_index_signature(self):
        return self._flow._followup_index_signature(self)

    def _insert_followup_questions(self, current_q, candidates, tag):
        return self._flow._insert_followup_questions(self, current_q, candidates, tag)

    def find_memory_ramp_candidates(self, q, limit: int = 2):
        return self._flow.find_memory_ramp_candidates(self, q, limit=limit)

    def find_wrong_answer_memory_candidates(self, q, limit: int = 2):
        return self._flow.find_wrong_answer_memory_candidates(self, q, limit=limit)

    def find_confusion_pair_candidates(self, q, limit: int = 1):
        return self._flow.find_confusion_pair_candidates(self, q, limit=limit)

    def plan_misconception_repair(self, q, is_correct: bool):
        return self._flow.plan_misconception_repair(self, q, is_correct)


def ids_of(questions: list[dict[str, Any]]) -> set[str]:
    from cand01r3_partition import canonical_question_id

    return {canonical_question_id(question) for question in questions}


def ns(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)
