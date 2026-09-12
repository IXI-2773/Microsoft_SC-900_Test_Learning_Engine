from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from cand01r3_partition import (
    EXAM_ID,
    INTENDED_USE_MEASUREMENT,
    PARTITION_EPOCH,
    ROLE_PROBE,
    RuntimeAuthority,
    canonical_question_id,
    partition_eligibility,
)
from cand01r3_runtime import DEFAULT_LEARNER_ID, current_authority, get_context

STATUS_PRIMARY = "PRIMARY"
STATUS_DUPLICATE = "DUPLICATE_NOT_PRIMARY"
STATUS_UNOBSERVED = "UNOBSERVED"
STATUS_CONTAMINATED = "CONTAMINATED"
STATUS_NOT_ELIGIBLE = "NOT_ELIGIBLE"
DUPLICATE_KINDS = {"REDO", "RETRY", "RESTORE_DUPLICATE", "IMPORTED_DUPLICATE"}


def evaluation_id(
    learner_id: str,
    exam: str,
    partition_epoch: str,
    canonical_id: str,
) -> tuple[str, str, str, str]:
    return (str(learner_id), str(exam), str(partition_epoch), str(canonical_id))


@dataclass
class MeasurementObservation:
    status: str
    reason: str = "OK"
    question_id: str = ""
    correct: bool | None = None
    evaluation_identity: tuple[str, str, str, str] | None = None
    clean: bool = False
    counts_toward_primary: bool = False
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class MeasurementLedger:
    learner_id: str = DEFAULT_LEARNER_ID
    authority: RuntimeAuthority | None = None
    exam: str = EXAM_ID
    _observations: dict[str, dict[str, Any]] = field(default_factory=dict)
    _contaminated: dict[str, list[str]] = field(default_factory=dict)
    _persisted: list[dict[str, Any]] = field(default_factory=list)
    _unobserved: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _authority(self) -> RuntimeAuthority | None:
        return self.authority if self.authority is not None else current_authority()

    def _identity(self, question_id: str) -> tuple[str, str, str, str]:
        authority = self._authority()
        epoch = (authority.partition_epoch if authority else None) or get_context().partition_epoch or PARTITION_EPOCH
        return evaluation_id(self.learner_id, self.exam, epoch, question_id)

    def is_contaminated(self, question_id: str) -> bool:
        return bool(self._contaminated.get(canonical_question_id(question_id)))

    def record_contamination(self, question_id: str, reason: str) -> None:
        qid = canonical_question_id(question_id)
        bucket = self._contaminated.setdefault(qid, [])
        if reason not in bucket:
            bucket.append(reason)
        existing = self._observations.get(qid)
        if existing and existing.get("status") == STATUS_PRIMARY:
            existing["status"] = STATUS_CONTAMINATED
            existing["reason"] = reason

    def clear_contamination(self, question_id: str) -> None:
        raise ValueError("contamination is monotonic")

    def record_scored_attempt(
        self,
        question: Mapping[str, Any],
        *,
        selected: list[str] | None = None,
        correct: bool | None = None,
        kind: str = "SCORED",
        persist: bool = False,
    ) -> MeasurementObservation:
        question_id = canonical_question_id(question)
        identity = self._identity(question_id)
        decision = partition_eligibility(question, INTENDED_USE_MEASUREMENT, self._authority())
        if decision.role != ROLE_PROBE:
            return MeasurementObservation(
                status=STATUS_NOT_ELIGIBLE,
                reason=decision.reason,
                question_id=question_id,
                correct=None,
                evaluation_identity=identity,
            )
        if self.is_contaminated(question_id):
            return MeasurementObservation(
                status=STATUS_CONTAMINATED,
                reason=self._contaminated[question_id][0],
                question_id=question_id,
                correct=None,
                evaluation_identity=identity,
            )
        if question_id in self._unobserved:
            return MeasurementObservation(
                status=STATUS_DUPLICATE,
                reason="LATE_NOT_PRIMARY",
                question_id=question_id,
                correct=None,
                evaluation_identity=identity,
            )
        existing = self._observations.get(question_id)
        if existing is not None or kind in DUPLICATE_KINDS:
            observation = MeasurementObservation(
                status=STATUS_DUPLICATE,
                reason=kind if kind in DUPLICATE_KINDS else "DUPLICATE",
                question_id=question_id,
                correct=bool(correct),
                evaluation_identity=identity,
            )
            return observation
        if type(correct) is not bool:
            return MeasurementObservation(
                status=STATUS_NOT_ELIGIBLE,
                reason="INVALID_MEASUREMENT_SCORE",
                question_id=question_id,
                correct=None,
                evaluation_identity=identity,
            )
        payload = {
            "status": STATUS_PRIMARY,
            "reason": "OK",
            "question_id": question_id,
            "correct": correct,
            "selected_option_ids": list(selected or []),
            "evaluation_identity": identity,
        }
        self._observations[question_id] = payload
        if persist:
            self._persisted.append(
                {
                    "question_id": question_id,
                    "selected_option_ids": list(selected or []),
                    "correct": correct,
                    "evaluation_identity": list(identity),
                    "status": STATUS_PRIMARY,
                }
            )
        return MeasurementObservation(
            status=STATUS_PRIMARY,
            reason="OK",
            question_id=question_id,
            correct=correct,
            evaluation_identity=identity,
        )

    def record_unobserved(self, question_id: str, *, reason: str) -> MeasurementObservation:
        qid = canonical_question_id(question_id)
        identity = self._identity(qid)
        if self.is_contaminated(qid):
            return MeasurementObservation(
                status=STATUS_CONTAMINATED,
                reason=self._contaminated[qid][0],
                question_id=qid,
                correct=None,
                evaluation_identity=identity,
            )
        if qid in self._observations:
            return MeasurementObservation(
                status=STATUS_DUPLICATE,
                reason="PRIMARY_ALREADY_TERMINAL",
                question_id=qid,
                correct=None,
                evaluation_identity=identity,
            )
        if qid in self._unobserved:
            return MeasurementObservation(
                status=STATUS_DUPLICATE,
                reason="UNOBSERVED_ALREADY_TERMINAL",
                question_id=qid,
                correct=None,
                evaluation_identity=identity,
            )
        payload = {
            "status": STATUS_UNOBSERVED,
            "reason": reason,
            "question_id": qid,
            "correct": None,
            "evaluation_identity": identity,
        }
        self._unobserved[qid] = payload
        return MeasurementObservation(
            status=STATUS_UNOBSERVED,
            reason=reason,
            question_id=qid,
            correct=None,
            evaluation_identity=identity,
        )

    def primary_observation(self, question_id: str) -> dict[str, Any] | None:
        payload = self._observations.get(canonical_question_id(question_id))
        if not payload or payload.get("status") != STATUS_PRIMARY:
            return None
        return dict(payload)

    def contaminated_observations(self) -> list[dict[str, Any]]:
        rows = []
        for question_id, reasons in self._contaminated.items():
            rows.append({"question_id": question_id, "reason": reasons[0], "reasons": list(reasons)})
        return rows

    def clean_primary_ids(self) -> list[str]:
        return [
            question_id
            for question_id, payload in self._observations.items()
            if payload.get("status") == STATUS_PRIMARY and not self.is_contaminated(question_id)
        ]

    def clean_primary_numerator(self) -> int:
        return sum(
            1 for question_id in self.clean_primary_ids() if self._observations[question_id].get("correct") is True
        )

    def clean_primary_denominator(self) -> int:
        return len(self.clean_primary_ids())

    def persisted_records(self) -> list[dict[str, Any]]:
        return list(self._persisted)

    def reporting_identity(self) -> dict[str, int]:
        authority = self._authority()
        return {
            "PROBE_QUESTIONS": 29,
            "INDEPENDENT_PROBE_FAMILIES": 7,
            "authority_probe_questions": int(authority.probe_count) if authority else 0,
            "authority_probe_families": len(authority.probe_family_ids) if authority else 0,
        }
