from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cand01r3_fixtures import (
    EXPECTED_AUDIT_SHA256,
    EXPECTED_COMPILED_SHA256,
    EXPECTED_DEFAULT_BANK_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_STORE_SHA256,
    LEARNER_ID,
    question,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"
EXPECTED_PROTOCOL_SHA256 = "51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72"
DAY1_PROBES = (
    "sc900_p1_q023",
    "sc900_p1_q004",
    "sc900_p1_q024",
    "sc900_p1_q001",
)
DAY2_PROBES = (
    "sc900_p1_q006",
    "sc900_p1_q042",
    "sc900_p2_q042",
    "sc900_p1_q011",
)
DAY7_PROBES = (
    "sc900_p3_q084",
    "sc900_p3_q063",
    "sc900_p3_q064",
    "sc900_p3_q012",
    "sc900_p3_q051",
)
PROBES_BY_DAY = {
    1: DAY1_PROBES,
    2: DAY2_PROBES,
    3: (
        "sc900_p2_q015",
        "sc900_p2_q018",
        "sc900_p2_q003",
        "sc900_p2_q004",
    ),
    4: (
        "sc900_p2_q026",
        "sc900_p3_q062",
        "sc900_p2_q011",
        "sc900_p3_q029",
    ),
    5: (
        "sc900_p3_q034",
        "sc900_p3_q053",
        "sc900_p3_q002",
        "sc900_p3_q001",
    ),
    6: (
        "sc900_p3_q097",
        "sc900_p3_q073",
        "sc900_p3_q052",
        "sc900_p3_q040",
    ),
    7: DAY7_PROBES,
}


class Cand01R3MeasurementRuntimeResumeTests(unittest.TestCase):
    def setUp(self):
        from cand01r3_protocol import reset_measurement_session
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()
        reset_measurement_session()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.tmpdir.name) / "epoch.jsonl"

    def tearDown(self):
        from cand01r3_protocol import reset_measurement_session
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_measurement_session()
        reset_cand01r3_runtime()
        self.tmpdir.cleanup()

    def _begin(self, **overrides):
        from cand01r3_protocol import begin_cand01r3_measurement

        payload = {
            "learner_id": LEARNER_ID,
            "measurement_epoch": "cand01r3-measurement-001",
            "schedule_version": "cand01r3-probe-schedule-v1",
            "policy_sequence_version": "cand01r3-alt-crossover-v1",
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "store_sha256": EXPECTED_STORE_SHA256,
            "semantic_audit_sha256": EXPECTED_AUDIT_SHA256,
            "compiled_sha256": EXPECTED_COMPILED_SHA256,
            "candidate_bank_identity": EXPECTED_COMPILED_SHA256,
            "ledger_path": self.ledger_path,
        }
        payload.update(overrides)
        return begin_cand01r3_measurement(**payload)

    def _restart(self):
        from cand01r3_protocol import reset_measurement_session
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_measurement_session()
        reset_cand01r3_runtime()
        return self._begin()

    def _train_ids(self, count: int, *, offset: int = 0) -> list[str]:
        from cand01r3_partition import ROLE_TRAIN, load_runtime_authority

        ids = sorted(qid for qid, item in load_runtime_authority().items.items() if item.get("role") == ROLE_TRAIN)
        return ids[offset : offset + count]

    def _complete_train(self, scheduled_day: int, count: int | None = None, policy_id: str | None = None) -> None:
        from cand01r3_protocol import allocated_policy_for_day, record_train_exposure, train_budget_for_day

        policy_id = policy_id or allocated_policy_for_day(scheduled_day)
        count = count if count is not None else train_budget_for_day(scheduled_day, policy_id)
        offset = _counted_session_trains()
        for question_id in self._train_ids(count, offset=offset):
            result = record_train_exposure(
                policy_id=policy_id,
                question_id=question_id,
                semantic_family_id="family_train",
                domain="microsoft_entra",
                objective="entra_authentication",
                service_class="COVERAGE",
                scheduled_day=scheduled_day,
            )
            self.assertTrue(result["counted"], result)

    def _enter_measurement(self, scheduled_day: int = 1) -> None:
        from cand01r3_protocol import (
            begin_todays_probe_measurement,
            current_measurement_session,
            set_measurement_day,
            train_budget_for_day,
        )

        set_measurement_day(scheduled_day)
        session = current_measurement_session()
        if scheduled_day < 7:
            already = len(
                [
                    row
                    for row in session.train_log
                    if row.get("counted") and int(row.get("scheduled_day") or 0) == scheduled_day
                ]
            )
            remaining = train_budget_for_day(scheduled_day) - already
            if remaining > 0:
                self._complete_train(scheduled_day, count=remaining)
        else:
            already_sp = len(
                [
                    row
                    for row in session.train_log
                    if row.get("counted")
                    and int(row.get("scheduled_day") or 0) == 7
                    and row.get("policy_id") == "SMART_PRACTICE"
                ]
            )
            already_rrc = len(
                [
                    row
                    for row in session.train_log
                    if row.get("counted")
                    and int(row.get("scheduled_day") or 0) == 7
                    and row.get("policy_id") == "RRC_1"
                ]
            )
            if already_sp < 10:
                self._complete_train(7, count=10 - already_sp, policy_id="SMART_PRACTICE")
            if already_rrc < 10:
                self._complete_train(7, count=10 - already_rrc, policy_id="RRC_1")
        begin_todays_probe_measurement()

    def _finish_day(self, scheduled_day: int) -> None:
        from cand01r3_protocol import record_measurement_event

        self._enter_measurement(scheduled_day)
        for question_id in PROBES_BY_DAY[scheduled_day]:
            result = record_measurement_event(
                question(question_id, role_hint="PROBE"),
                selected=["A"],
                correct=True,
                ledger_path=self.ledger_path,
            )
            self.assertIn(result.status, {"PRIMARY", "CONTAMINATED", "UNOBSERVED"})

    def _finish_days(self, last_day: int) -> None:
        for day in range(1, last_day + 1):
            self._finish_day(day)

    def _ledger_rows(self) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        rows = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _rewrite_ledger_field(self, field: str, value: str) -> None:
        rows = self._ledger_rows()
        self.assertTrue(rows)
        rewritten = []
        for row in rows:
            payload = dict(row)
            if field in payload:
                payload[field] = value
            rewritten.append(json.dumps(payload, sort_keys=True, ensure_ascii=True))
        self.ledger_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")

    def _resume_snapshot(self) -> dict:
        from cand01r3_protocol import current_measurement_session, measurement_runtime_state, today_measurement_card
        from cand01r3_runtime import get_context

        session = current_measurement_session()
        day = session.current_scheduled_day
        card = today_measurement_card(day) if day is not None else {}
        return {
            "measurement_epoch": session.measurement_epoch,
            "protocol_version": session.protocol_version,
            "protocol_sha256": session.protocol_sha256,
            "learner_id": session.learner_id,
            "current_scheduled_day": session.current_scheduled_day,
            "day_state": measurement_runtime_state(),
            "intended_use": get_context().intended_use,
            "policy_id": get_context().policy_id,
            "train_exposures_completed": card.get("train_exposures_completed"),
            "train_exposures_remaining": card.get("train_exposures_remaining"),
            "probe_event_ids": [
                (event.get("question_id"), event.get("status"), event.get("first_attempt"))
                for event in session.events
                if event.get("question_role") == "PROBE"
            ],
            "contaminated": sorted(
                str(event.get("question_id") or "")
                for event in session.events
                if event.get("contaminated") or event.get("status") == "CONTAMINATED"
            ),
            "train_log_counted": [
                (row.get("question_id"), row.get("policy_id"), row.get("scheduled_day"))
                for row in session.train_log
                if row.get("counted")
            ],
        }

    def test_r1_001_same_frozen_v2_epoch_can_resume_after_one_real_observation(self):
        from cand01r3_protocol import current_measurement_session, record_measurement_event
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        self._enter_measurement(1)
        first = record_measurement_event(
            question(DAY1_PROBES[0], role_hint="PROBE", family="entra_roles_rbac"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("PRIMARY", first.status)
        try:
            session = self._restart()
        except Cand01R3AuthorityError as exc:
            self.fail(f"same-epoch resume was rejected: {exc}")
        self.assertEqual("cand01r3-measurement-001", session.measurement_epoch)
        self.assertEqual("cand01r3-measurement-001-v2", session.protocol_version)
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, session.protocol_sha256)
        self.assertEqual(1, current_measurement_session().current_scheduled_day)

    def test_r1_002_resume_rejects_wrong_protocol_hash(self):
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        self._enter_measurement(1)
        self._rewrite_ledger_field("protocol_sha256", "0" * 64)
        with self.assertRaises(Cand01R3AuthorityError) as raised:
            self._restart()
        self.assertIn("PROTOCOL", str(raised.exception))

    def test_r1_003_resume_rejects_wrong_epoch(self):
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        self._enter_measurement(1)
        self._rewrite_ledger_field("measurement_epoch", "other-epoch")
        with self.assertRaises(Cand01R3AuthorityError) as raised:
            self._restart()
        self.assertIn("EPOCH", str(raised.exception))

    def test_r1_004_resume_rejects_incompatible_authority_hashes(self):
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        self._enter_measurement(1)
        self._rewrite_ledger_field("manifest_sha256", "f" * 64)
        with self.assertRaises(Cand01R3AuthorityError) as raised:
            self._restart()
        self.assertIn("HASH", str(raised.exception))

    def test_r1_005_ten_train_exposures_survive_restart_as_10_of_20(self):
        from cand01r3_protocol import measurement_runtime_state, set_measurement_day, today_measurement_card
        from cand01r3_runtime import get_context

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=10)
        self._restart()
        card = today_measurement_card(1)
        self.assertEqual(1, card["scheduled_day"])
        self.assertEqual("SMART_PRACTICE", card["policy_id"])
        self.assertEqual(10, card["train_exposures_completed"])
        self.assertEqual(10, card["train_exposures_remaining"])
        self.assertEqual("TRAINING", measurement_runtime_state())
        self.assertEqual("TRAINING", get_context().intended_use)

    def test_r1_006_twenty_train_exposures_survive_restart_as_complete(self):
        from cand01r3_protocol import measurement_runtime_state, set_measurement_day, today_measurement_card

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=20)
        self._restart()
        card = today_measurement_card(1)
        self.assertEqual(20, card["train_exposures_completed"])
        self.assertEqual(0, card["train_exposures_remaining"])
        self.assertEqual("TRAINING_BLOCK_COMPLETE", card["training_block_status"])
        self.assertEqual("TRAINING_COMPLETE", measurement_runtime_state())

    def test_r1_007_train_exposure_events_are_append_only_persisted(self):
        from cand01r3_protocol import set_measurement_day

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=3)
        rows = [
            row
            for row in self._ledger_rows()
            if row.get("status") == "TRAIN_EXPOSURE" or row.get("event_type") == "TRAIN_EXPOSURE"
        ]
        self.assertEqual(3, len(rows))
        first_count = len(self._ledger_rows())
        self._complete_train(1, count=1)
        self.assertEqual(first_count + 1, len(self._ledger_rows()))
        for row in rows:
            self.assertTrue(row.get("counted"))
            self.assertEqual("cand01r3-measurement-001", row.get("measurement_epoch"))
            self.assertEqual("cand01r3-measurement-001-v2", row.get("protocol_version"))
            self.assertIn("event_id", row)
            self.assertNotIn("selected_option_ids", row)
            self.assertNotIn("correct", row)

    def test_r1_008_wrong_policy_used_is_persisted(self):
        from cand01r3_protocol import record_train_exposure, set_measurement_day

        self._begin()
        set_measurement_day(1)
        result = record_train_exposure(
            policy_id="RRC_1",
            question_id=self._train_ids(1)[0],
            scheduled_day=1,
        )
        self.assertEqual("PROTOCOL_DEVIATION", result["status"])
        self.assertEqual("WRONG_POLICY_USED", result["reason"])
        reasons = [row.get("reason") for row in self._ledger_rows()]
        self.assertIn("WRONG_POLICY_USED", reasons)

    def test_r1_009_over_budget_deviation_remains_persisted(self):
        from cand01r3_protocol import record_train_exposure, set_measurement_day

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=20)
        over = record_train_exposure(
            policy_id="SMART_PRACTICE",
            question_id=self._train_ids(1, offset=20)[0],
            scheduled_day=1,
        )
        self.assertEqual("OVER_BUDGET_TRAIN_EXPOSURE", over["reason"])
        self._restart()
        reasons = [row.get("reason") for row in self._ledger_rows()]
        self.assertIn("OVER_BUDGET_TRAIN_EXPOSURE", reasons)

    def test_r1_010_probe_before_20_train_is_rejected(self):
        from cand01r3_protocol import record_measurement_event, set_measurement_day

        self._begin()
        set_measurement_day(1)
        result = record_measurement_event(
            question(DAY1_PROBES[3], role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertNotEqual("PRIMARY", result.status)
        self.assertEqual("PROBE_BEFORE_TRAIN_BLOCK_COMPLETE", result.reason)

    def test_r1_011_probe_before_measurement_transition_is_rejected(self):
        from cand01r3_protocol import record_measurement_event, set_measurement_day

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=20)
        result = record_measurement_event(
            question(DAY1_PROBES[3], role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertNotEqual("PRIMARY", result.status)
        self.assertEqual("MEASUREMENT_MODE_NOT_ACTIVE", result.reason)

    def test_r1_012_probe_from_another_scheduled_day_is_rejected(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        self._enter_measurement(1)
        result = record_measurement_event(
            question(DAY2_PROBES[0], role_hint="PROBE", family="azure_key_vault"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertNotEqual("PRIMARY", result.status)
        self.assertEqual("WRONG_MEASUREMENT_DAY", result.reason)

    def test_r1_013_only_todays_scheduled_probes_are_eligible_in_measurement(self):
        from cand01r3_runtime import filter_training_questions, revalidate_training_question

        self._begin()
        self._enter_measurement(1)
        pool = [
            question(DAY1_PROBES[0], role_hint="PROBE", family="entra_roles_rbac"),
            question(DAY2_PROBES[0], role_hint="PROBE", family="azure_key_vault"),
            question(self._train_ids(1)[0]),
        ]
        eligible_ids = [item["id"] for item in filter_training_questions(pool)]
        self.assertEqual([DAY1_PROBES[0]], eligible_ids)
        today = revalidate_training_question(pool[0], action="RENDER")
        other = revalidate_training_question(pool[1], action="RENDER")
        self.assertEqual("PROBE", today.role)
        self.assertNotEqual("PROBE", other.role)

    def test_r1_014_after_20_train_explicit_measurement_transition_succeeds(self):
        from cand01r3_protocol import begin_todays_probe_measurement, measurement_runtime_state, set_measurement_day

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=20)
        result = begin_todays_probe_measurement()
        self.assertEqual("MEASUREMENT", result["day_state"])
        self.assertEqual("MEASUREMENT", measurement_runtime_state())

    def test_r1_015_runtime_intended_use_switches_training_to_measurement(self):
        from cand01r3_protocol import begin_todays_probe_measurement, set_measurement_day
        from cand01r3_runtime import get_context

        self._begin()
        set_measurement_day(1)
        self.assertEqual("TRAINING", get_context().intended_use)
        self._complete_train(1, count=20)
        self.assertEqual("TRAINING", get_context().intended_use)
        begin_todays_probe_measurement()
        self.assertEqual("MEASUREMENT", get_context().intended_use)

    def test_r1_016_renderer_accepts_todays_probe_in_measurement_state(self):
        from cand01r3_runtime import revalidate_training_question

        self._begin()
        self._enter_measurement(1)
        decision = revalidate_training_question(
            question(DAY1_PROBES[3], role_hint="PROBE", family="shared_responsibility_model"),
            action="RENDER",
        )
        self.assertEqual("PROBE", decision.role)
        self.assertEqual("OK", decision.reason)

    def test_r1_017_renderer_still_rejects_probe_during_training_state(self):
        from cand01r3_protocol import set_measurement_day
        from cand01r3_runtime import revalidate_training_question

        self._begin()
        set_measurement_day(1)
        decision = revalidate_training_question(
            question(DAY1_PROBES[3], role_hint="PROBE", family="shared_responsibility_model"),
            action="RENDER",
        )
        self.assertNotEqual("PROBE", decision.role)

    def test_r1_018_two_completed_probes_survive_restart_without_new_first_attempts(self):
        from cand01r3_protocol import measurement_runtime_state, record_measurement_event

        self._begin()
        self._enter_measurement(1)
        for question_id, family in (
            (DAY1_PROBES[0], "entra_roles_rbac"),
            (DAY1_PROBES[1], "multifactor_authentication"),
        ):
            result = record_measurement_event(
                question(question_id, role_hint="PROBE", family=family),
                selected=["A"],
                correct=True,
                ledger_path=self.ledger_path,
            )
            self.assertEqual("PRIMARY", result.status)
        self._restart()
        self.assertEqual("MEASUREMENT", measurement_runtime_state())
        for question_id, family in (
            (DAY1_PROBES[0], "entra_roles_rbac"),
            (DAY1_PROBES[1], "multifactor_authentication"),
        ):
            duplicate = record_measurement_event(
                question(question_id, role_hint="PROBE", family=family),
                selected=["B"],
                correct=False,
                ledger_path=self.ledger_path,
            )
            self.assertEqual("DUPLICATE_NOT_PRIMARY", duplicate.status)
            self.assertFalse(duplicate.counts_toward_primary)

    def test_r1_019_unobserved_survives_restart(self):
        from cand01r3_protocol import record_unobserved

        self._begin()
        self._enter_measurement(1)
        observation = record_unobserved(DAY1_PROBES[2], reason="MISSED_SCHEDULED_PROBE", ledger_path=self.ledger_path)
        self.assertEqual("UNOBSERVED", observation.status)
        self._restart()
        statuses = {
            row.get("question_id"): row.get("status")
            for row in self._ledger_rows()
            if row.get("question_id") == DAY1_PROBES[2]
        }
        self.assertEqual("UNOBSERVED", statuses[DAY1_PROBES[2]])
        from cand01r3_protocol import current_measurement_session

        session = current_measurement_session()
        self.assertTrue(any(event.get("status") == "UNOBSERVED" for event in session.events))

    def test_r1_020_contamination_survives_restart_and_stays_monotonic(self):
        from cand01r3_protocol import clear_contamination, current_measurement_session, record_contamination

        self._begin()
        self._enter_measurement(1)
        record_contamination(DAY1_PROBES[3], "STEM_EXPOSURE", ledger_path=self.ledger_path)
        self._restart()
        session = current_measurement_session()
        self.assertTrue(session.ledger is not None and session.ledger.is_contaminated(DAY1_PROBES[3]))
        with self.assertRaises(ValueError):
            clear_contamination(DAY1_PROBES[3])

    def test_r1_021_day_7_starts_on_smart_practice(self):
        from cand01r3_protocol import measurement_runtime_state, set_measurement_day
        from cand01r3_runtime import get_context

        self._begin()
        self._finish_days(6)
        policy_id = set_measurement_day(7)
        self.assertEqual("DAY7_BALANCED_MEASUREMENT", policy_id)
        self.assertEqual("SMART_PRACTICE_CHAMPION", get_context().policy_id)
        self.assertEqual("SMART_PRACTICE_TRAINING", measurement_runtime_state())

    def test_r1_022_day_7_automatically_switches_to_rrc1_after_10_smart_practice(self):
        from cand01r3_protocol import measurement_runtime_state, set_measurement_day
        from cand01r3_runtime import get_context

        self._begin()
        self._finish_days(6)
        set_measurement_day(7)
        self._complete_train(7, count=10, policy_id="SMART_PRACTICE")
        self.assertEqual("RRC_1_CHALLENGER", get_context().policy_id)
        self.assertEqual("RRC1_TRAINING", measurement_runtime_state())

    def test_r1_023_day_7_blocks_measurement_before_both_blocks_complete(self):
        from cand01r3_protocol import begin_todays_probe_measurement, set_measurement_day
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        self._finish_days(6)
        set_measurement_day(7)
        self._complete_train(7, count=10, policy_id="SMART_PRACTICE")
        with self.assertRaises(Cand01R3AuthorityError) as raised:
            begin_todays_probe_measurement()
        self.assertIn("TRAIN", str(raised.exception))

    def test_r1_024_day_7_permits_measurement_after_10_plus_10(self):
        from cand01r3_protocol import begin_todays_probe_measurement, measurement_runtime_state, set_measurement_day
        from cand01r3_runtime import get_context

        self._begin()
        self._finish_days(6)
        set_measurement_day(7)
        self._complete_train(7, count=10, policy_id="SMART_PRACTICE")
        self._complete_train(7, count=10, policy_id="RRC_1")
        result = begin_todays_probe_measurement()
        self.assertEqual("MEASUREMENT", result["day_state"])
        self.assertEqual("MEASUREMENT", measurement_runtime_state())
        self.assertEqual("MEASUREMENT", get_context().intended_use)

    def test_r1_025_day_completion_requires_all_scheduled_probes_terminal(self):
        from cand01r3_protocol import measurement_runtime_state, record_measurement_event, record_unobserved

        self._begin()
        self._enter_measurement(1)
        record_measurement_event(
            question(DAY1_PROBES[0], role_hint="PROBE", family="entra_roles_rbac"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("MEASUREMENT", measurement_runtime_state())
        record_measurement_event(
            question(DAY1_PROBES[1], role_hint="PROBE", family="multifactor_authentication"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        record_unobserved(DAY1_PROBES[2], reason="MISSED_SCHEDULED_PROBE", ledger_path=self.ledger_path)
        self.assertNotEqual("DAY_COMPLETE", measurement_runtime_state())
        record_measurement_event(
            question(DAY1_PROBES[3], role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("DAY_COMPLETE", measurement_runtime_state())

    def test_r1_026_next_day_cannot_silently_begin_while_previous_day_incomplete(self):
        from cand01r3_protocol import set_measurement_day
        from cand01r3_runtime import Cand01R3AuthorityError

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=10)
        with self.assertRaises(Cand01R3AuthorityError) as raised:
            set_measurement_day(2)
        self.assertIn("INCOMPLETE", str(raised.exception))

    def test_r1_027_normal_default_engine_remains_unchanged(self):
        from cand01r3_protocol import is_measurement_active
        from cand01r3_runtime import filter_training_questions, is_cand01r3_active

        pool = [question("train_a"), question("probe_a", role_hint="PROBE", family="family_probe")]
        self.assertFalse(is_cand01r3_active())
        self.assertFalse(is_measurement_active())
        self.assertEqual(["train_a", "probe_a"], [item["id"] for item in filter_training_questions(pool)])

    def test_r1_028_protocol_sha_remains_unchanged_by_this_implementation_repair(self):
        from cand01r3_protocol import PROTOCOL_VERSION, build_protocol, load_committed_protocol, protocol_sha256

        self.assertEqual("cand01r3-measurement-001-v2", PROTOCOL_VERSION)
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, protocol_sha256(build_protocol()))
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, load_committed_protocol()["protocol_sha256"])

    def test_r1_029_real_observations_remain_zero_in_repository_pre_run_artifact(self):
        from cand01r3_protocol import (
            _ledger_real_observation_count,
            build_protocol,
            load_committed_protocol,
            measurement_runtime_state,
            protocol_sha256,
            set_measurement_day,
        )

        committed = load_committed_protocol()
        self.assertEqual(0, committed["real_observations"])
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, protocol_sha256(build_protocol()))
        self.assertEqual(EXPECTED_PROTOCOL_SHA256, committed["protocol_sha256"])
        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, sha256_file(DEFAULT_BANK))
        self._begin()
        set_measurement_day(1)
        self.assertEqual("TRAINING", measurement_runtime_state())
        self.assertGreater(self.ledger_path.stat().st_size, 0)
        rows = self._ledger_rows()
        self.assertIn("EPOCH_BEGIN", {row.get("event_type") for row in rows})
        day_state = next(row for row in rows if row.get("event_type") == "DAY_STATE")
        self.assertEqual("TRAINING", day_state.get("day_state"))
        self.assertEqual(1, day_state.get("scheduled_day"))
        self.assertEqual(0, _ledger_real_observation_count(self.ledger_path))

    def test_r1_031_one_valid_primary_probe_counts_as_one_real_observation(self):
        from cand01r3_protocol import _ledger_real_observation_count, record_measurement_event

        self._begin()
        self._enter_measurement(1)
        self.assertEqual(0, _ledger_real_observation_count(self.ledger_path))
        result = record_measurement_event(
            question(DAY1_PROBES[0], role_hint="PROBE", family="entra_roles_rbac"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("PRIMARY", result.status)
        self.assertEqual(1, _ledger_real_observation_count(self.ledger_path))

    def test_r1_030_resume_reconstruction_is_deterministic_from_the_same_ledger(self):
        from cand01r3_protocol import record_measurement_event, set_measurement_day

        self._begin()
        set_measurement_day(1)
        self._complete_train(1, count=10)
        first = self._resume_snapshot()
        self._restart()
        second = self._resume_snapshot()
        self.assertEqual(first, second)
        self._enter_measurement(1)
        record_measurement_event(
            question(DAY1_PROBES[0], role_hint="PROBE", family="entra_roles_rbac"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        after_probe = self._resume_snapshot()
        self._restart()
        self.assertEqual(after_probe, self._resume_snapshot())


def _counted_session_trains() -> int:
    from cand01r3_protocol import current_measurement_session

    return len([row for row in current_measurement_session().train_log if row.get("counted")])


if __name__ == "__main__":
    unittest.main()
