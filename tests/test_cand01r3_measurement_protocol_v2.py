from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cand01r3_fixtures import (
    EXPECTED_AUDIT_SHA256,
    EXPECTED_COMPILED_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_STORE_SHA256,
    LEARNER_ID,
    question,
)

V1_PROTOCOL_VERSION = "cand01r3-measurement-001-v1"
V1_PROTOCOL_SHA256 = "493b371d6200c88fe51428953947fac864fae8535667374e38050198b018e081"
V1_PRIMARY_ENDPOINT = "7-day first-attempt correctness on CLEAN HELD-OUT SC-900 PROBE items"
V1_MISSINGNESS = (
    "A missed scheduled PROBE is UNOBSERVED. It is not coerced to incorrect, correct, or zero, and it is not dropped."
)
V1_CONTAMINATION = (
    "Improper PROBE exposure is recorded as contaminated, excluded from the clean primary endpoint, "
    "and not silently replaced. Contamination is monotonic. No post-hoc replacement rule exists."
)
V1_POLICY_ORDER = [
    "SMART_PRACTICE",
    "RRC_1",
    "SMART_PRACTICE",
    "RRC_1",
    "SMART_PRACTICE",
    "RRC_1",
    "DAY7_BALANCED_MEASUREMENT",
]
V1_SCHEDULE = [
    (1, "sc900_p1_q023", "entra_roles_rbac"),
    (1, "sc900_p1_q004", "multifactor_authentication"),
    (1, "sc900_p1_q024", "privileged_identity_management"),
    (1, "sc900_p1_q001", "shared_responsibility_model"),
    (2, "sc900_p1_q006", "azure_key_vault"),
    (2, "sc900_p1_q042", "multifactor_authentication"),
    (2, "sc900_p2_q042", "purview_portal"),
    (2, "sc900_p1_q011", "zero_trust_and_identity_perimeter"),
    (3, "sc900_p2_q015", "entra_roles_rbac"),
    (3, "sc900_p2_q018", "privileged_identity_management"),
    (3, "sc900_p2_q003", "shared_responsibility_model"),
    (3, "sc900_p2_q004", "zero_trust_and_identity_perimeter"),
    (4, "sc900_p2_q026", "azure_key_vault"),
    (4, "sc900_p3_q062", "entra_roles_rbac"),
    (4, "sc900_p2_q011", "multifactor_authentication"),
    (4, "sc900_p3_q029", "purview_portal"),
    (5, "sc900_p3_q034", "multifactor_authentication"),
    (5, "sc900_p3_q053", "privileged_identity_management"),
    (5, "sc900_p3_q002", "shared_responsibility_model"),
    (5, "sc900_p3_q001", "zero_trust_and_identity_perimeter"),
    (6, "sc900_p3_q097", "azure_key_vault"),
    (6, "sc900_p3_q073", "entra_roles_rbac"),
    (6, "sc900_p3_q052", "multifactor_authentication"),
    (6, "sc900_p3_q040", "purview_portal"),
    (7, "sc900_p3_q084", "entra_roles_rbac"),
    (7, "sc900_p3_q063", "multifactor_authentication"),
    (7, "sc900_p3_q064", "privileged_identity_management"),
    (7, "sc900_p3_q012", "shared_responsibility_model"),
    (7, "sc900_p3_q051", "zero_trust_and_identity_perimeter"),
]


class Cand01R3MeasurementProtocolV2Tests(unittest.TestCase):
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

    def _train_ids(self, count: int) -> list[str]:
        from cand01r3_partition import ROLE_TRAIN, load_runtime_authority

        ids = sorted(qid for qid, item in load_runtime_authority().items.items() if item.get("role") == ROLE_TRAIN)
        return ids[:count]

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

    def _ready_day1_measurement(self) -> None:
        from cand01r3_protocol import begin_todays_probe_measurement, record_train_exposure, set_measurement_day

        set_measurement_day(1)
        for question_id in self._train_ids(20):
            record_train_exposure(policy_id="SMART_PRACTICE", question_id=question_id, scheduled_day=1)
        begin_todays_probe_measurement()

    def test_m2_001_protocol_version_is_v2(self):
        from cand01r3_protocol import PROTOCOL_VERSION, build_protocol, load_committed_protocol

        self.assertEqual("cand01r3-measurement-001-v2", PROTOCOL_VERSION)
        self.assertEqual("cand01r3-measurement-001-v2", build_protocol()["protocol_version"])
        self.assertEqual("cand01r3-measurement-001-v2", load_committed_protocol()["protocol_version"])

    def test_m2_002_days_1_to_6_have_train_item_budget_20(self):
        from cand01r3_protocol import build_protocol

        for row in build_protocol()["policy_sequence"]:
            if int(row["scheduled_day"]) > 6:
                continue
            self.assertEqual(20, row["train_item_budget"])
            self.assertEqual(20, row["training_blocks"][0]["train_item_budget"])

    def test_m2_003_smart_practice_primary_exposure_budget_totals_60(self):
        from cand01r3_protocol import primary_train_exposure_totals

        totals = primary_train_exposure_totals()
        self.assertEqual(60, totals["SMART_PRACTICE"])

    def test_m2_004_rrc1_primary_exposure_budget_totals_60(self):
        from cand01r3_protocol import primary_train_exposure_totals

        totals = primary_train_exposure_totals()
        self.assertEqual(60, totals["RRC_1"])

    def test_m2_005_primary_exposure_difference_equals_0(self):
        from cand01r3_protocol import primary_train_exposure_totals

        totals = primary_train_exposure_totals()
        self.assertEqual(0, totals["PRIMARY_TRAIN_EXPOSURE_DIFFERENCE"])

    def test_m2_006_day_7_remains_10_plus_10(self):
        from cand01r3_protocol import build_protocol

        day7 = [row for row in build_protocol()["policy_sequence"] if int(row["scheduled_day"]) == 7][0]
        self.assertEqual("DAY7_BALANCED_MEASUREMENT", day7["policy_id"])
        self.assertFalse(day7["primary_policy_contrast"])
        blocks = {(block["policy_id"], int(block["train_item_budget"])) for block in day7["training_blocks"]}
        self.assertEqual({("SMART_PRACTICE", 10), ("RRC_1", 10)}, blocks)

    def test_m2_007_probe_schedule_unchanged_from_v1(self):
        from cand01r3_protocol import build_protocol

        actual = [
            (int(row["scheduled_day"]), row["question_id"], row["semantic_family_id"])
            for row in build_protocol()["schedule"]
        ]
        self.assertEqual(V1_SCHEDULE, actual)

    def test_m2_008_train_probe_manifest_hash_unchanged(self):
        from cand01r3_partition import EXPECTED_MANIFEST_SHA256 as PARTITION_MANIFEST
        from cand01r3_protocol import build_protocol

        self.assertEqual(EXPECTED_MANIFEST_SHA256, PARTITION_MANIFEST)
        self.assertEqual(
            EXPECTED_MANIFEST_SHA256,
            build_protocol()["frozen_artifact_hashes"]["train_probe_manifest_sha256"],
        )

    def test_m2_009_primary_endpoint_unchanged(self):
        from cand01r3_protocol import PRIMARY_ENDPOINT, build_protocol

        self.assertEqual(V1_PRIMARY_ENDPOINT, PRIMARY_ENDPOINT)
        self.assertEqual(V1_PRIMARY_ENDPOINT, build_protocol()["primary_endpoint"])

    def test_m2_010_missingness_rule_unchanged(self):
        from cand01r3_protocol import MISSINGNESS_RULE, build_protocol

        self.assertEqual(V1_MISSINGNESS, MISSINGNESS_RULE)
        self.assertEqual(V1_MISSINGNESS, build_protocol()["missingness_rule"])

    def test_m2_011_contamination_rule_unchanged(self):
        from cand01r3_protocol import CONTAMINATION_RULE, build_protocol

        self.assertEqual(V1_CONTAMINATION, CONTAMINATION_RULE)
        self.assertEqual(V1_CONTAMINATION, build_protocol()["contamination_rule"])

    def test_m2_012_policy_order_unchanged(self):
        from cand01r3_protocol import build_protocol

        order = [row["policy_id"] for row in build_protocol()["policy_sequence"]]
        self.assertEqual(V1_POLICY_ORDER, order)

    def test_m2_013_training_block_rejects_exposure_21(self):
        from cand01r3_protocol import record_train_exposure, set_measurement_day

        self._begin()
        set_measurement_day(1)
        train_ids = self._train_ids(21)
        for question_id in train_ids[:20]:
            result = record_train_exposure(
                policy_id="SMART_PRACTICE",
                question_id=question_id,
                scheduled_day=1,
            )
            self.assertEqual("COUNTED", result["status"])
        over = record_train_exposure(
            policy_id="SMART_PRACTICE",
            question_id=train_ids[20],
            scheduled_day=1,
        )
        self.assertEqual("PROTOCOL_DEVIATION", over["status"])
        self.assertEqual("OVER_BUDGET_TRAIN_EXPOSURE", over["reason"])
        self.assertFalse(over["counted"])

    def test_m2_014_probe_cannot_satisfy_train_budget_deficit(self):
        from cand01r3_protocol import record_train_exposure, set_measurement_day

        self._begin()
        set_measurement_day(1)
        result = record_train_exposure(
            policy_id="SMART_PRACTICE",
            question_id="sc900_p1_q001",
            scheduled_day=1,
        )
        self.assertEqual("NOT_ELIGIBLE", result["status"])
        self.assertIn(result["reason"], {"PROBE", "PROBE_CANNOT_SATISFY_TRAIN_BUDGET"})
        self.assertFalse(result["counted"])

    def test_m2_015_insufficient_train_capacity_fails_closed(self):
        from cand01r3_protocol import require_train_capacity

        result = require_train_capacity(expected_budget=20, actual_eligible=4, policy_id="RRC_1")
        self.assertEqual("INSUFFICIENT_TRAIN_CAPACITY", result["status"])
        self.assertEqual(20, result["expected_budget"])
        self.assertEqual(4, result["actual_exposures"])
        self.assertFalse(result.get("filled_with_probe"))

    def test_m2_016_normal_default_engine_remains_unaffected(self):
        from cand01r3_protocol import is_measurement_active
        from cand01r3_runtime import filter_training_questions, is_cand01r3_active

        pool = [question("train_a"), question("probe_a", role_hint="PROBE", family="family_probe")]
        self.assertFalse(is_cand01r3_active())
        self.assertFalse(is_measurement_active())
        self.assertEqual(["train_a", "probe_a"], [item["id"] for item in filter_training_questions(pool)])

    def test_m2_017_v1_supersession_allowed_only_when_real_observations_are_zero(self):
        from cand01r3_protocol import allow_v2_supersession

        allowed = allow_v2_supersession(real_observations=0)
        self.assertTrue(allowed["allowed"])
        self.assertEqual(0, allowed["REAL_OBSERVATIONS_AT_SUPERSESSION"])
        blocked = allow_v2_supersession(real_observations=1)
        self.assertFalse(blocked["allowed"])
        self.assertEqual("NEW_MEASUREMENT_EPOCH_REQUIRED", blocked["reason"])

    def test_m2_018_protocol_cannot_change_from_v2_after_first_real_event(self):
        from cand01r3_protocol import record_measurement_event, replace_active_protocol

        self._begin()
        self._ready_day1_measurement()
        record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        with self.assertRaises(ValueError):
            replace_active_protocol({"protocol_version": "cand01r3-measurement-001-v3"})

    def test_m2_019_new_protocol_sha_deterministic(self):
        from cand01r3_protocol import build_protocol, load_committed_protocol, protocol_sha256

        first = protocol_sha256(build_protocol())
        second = protocol_sha256(build_protocol())
        self.assertEqual(first, second)
        self.assertEqual(64, len(first))
        self.assertNotEqual(V1_PROTOCOL_SHA256, first)
        self.assertEqual(first, load_committed_protocol()["protocol_sha256"])
        self.assertEqual(V1_PROTOCOL_VERSION, V1_PROTOCOL_VERSION)

    def test_m2_020_measurement_card_reports_remaining_train_exposure_count(self):
        from cand01r3_protocol import record_train_exposure, set_measurement_day, today_measurement_card

        self._begin()
        set_measurement_day(1)
        train_ids = self._train_ids(20)
        card = today_measurement_card(1)
        self.assertEqual("SMART_PRACTICE", card["policy_id"])
        self.assertEqual(20, card["train_budget"])
        self.assertEqual(0, card["train_exposures_completed"])
        self.assertEqual(20, card["train_exposures_remaining"])
        self.assertEqual("IN_PROGRESS", card["training_block_status"])
        record_train_exposure(policy_id="SMART_PRACTICE", question_id=train_ids[0], scheduled_day=1)
        card = today_measurement_card(1)
        self.assertEqual(1, card["train_exposures_completed"])
        self.assertEqual(19, card["train_exposures_remaining"])
        for question_id in train_ids[1:]:
            record_train_exposure(policy_id="SMART_PRACTICE", question_id=question_id, scheduled_day=1)
        card = today_measurement_card(1)
        self.assertEqual(0, card["train_exposures_remaining"])
        self.assertEqual("TRAINING_BLOCK_COMPLETE", card["training_block_status"])
        self.assertEqual("BEGIN TODAY'S PROBE MEASUREMENT", card["next_action"])


if __name__ == "__main__":
    unittest.main()
