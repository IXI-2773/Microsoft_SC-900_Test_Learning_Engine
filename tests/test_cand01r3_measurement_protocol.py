from __future__ import annotations

import copy
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
    PARTITION_EPOCH,
    activate_synthetic,
    question,
    sha256_file,
    synthetic_authority,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"
FROZEN_PROBE_FAMILIES = {
    "azure_key_vault",
    "entra_roles_rbac",
    "multifactor_authentication",
    "privileged_identity_management",
    "purview_portal",
    "shared_responsibility_model",
    "zero_trust_and_identity_perimeter",
}
OUTSIDE_STUDY_VALUES = {
    "NONE",
    "MICROSOFT_LEARN",
    "BOOK",
    "VIDEO_COURSE",
    "PRACTICE_TEST",
    "OTHER",
}


class Cand01R3MeasurementProtocolTests(unittest.TestCase):
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

    def test_m001_protocol_hash_deterministic(self):
        from cand01r3_protocol import build_protocol, protocol_sha256

        first = protocol_sha256(build_protocol())
        second = protocol_sha256(build_protocol())
        self.assertEqual(first, second)
        self.assertEqual(64, len(first))

    def test_m002_schedule_covers_exactly_29_probe_ids(self):
        from cand01r3_protocol import build_protocol

        schedule = build_protocol()["schedule"]
        ids = [row["question_id"] for row in schedule]
        self.assertEqual(29, len(ids))

    def test_m003_schedule_contains_no_train_ids(self):
        from cand01r3_partition import ROLE_TRAIN, load_runtime_authority
        from cand01r3_protocol import build_protocol

        authority = load_runtime_authority()
        train_ids = {qid for qid, item in authority.items.items() if item.get("role") == ROLE_TRAIN}
        schedule_ids = {row["question_id"] for row in build_protocol()["schedule"]}
        self.assertTrue(schedule_ids.isdisjoint(train_ids))

    def test_m004_all_seven_probe_families_represented(self):
        from cand01r3_protocol import build_protocol

        families = {row["semantic_family_id"] for row in build_protocol()["schedule"]}
        self.assertEqual(FROZEN_PROBE_FAMILIES, families)
        self.assertEqual(7, len(families))

    def test_m005_question_appears_once_in_schedule(self):
        from cand01r3_protocol import build_protocol

        ids = [row["question_id"] for row in build_protocol()["schedule"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_m006_policy_sequence_frozen(self):
        from cand01r3_protocol import POLICY_SEQUENCE, build_protocol

        protocol = build_protocol()
        self.assertEqual(POLICY_SEQUENCE, protocol["policy_sequence"])
        days = {int(row["scheduled_day"]): row["policy_id"] for row in protocol["policy_sequence"]}
        self.assertEqual("SMART_PRACTICE", days[1])
        self.assertEqual("RRC_1", days[2])
        self.assertEqual("SMART_PRACTICE", days[3])
        self.assertEqual("RRC_1", days[4])
        self.assertEqual("SMART_PRACTICE", days[5])
        self.assertEqual("RRC_1", days[6])
        self.assertEqual("DAY7_BALANCED_MEASUREMENT", days[7])

    def test_m007_protocol_mutation_changes_authority_hash(self):
        from cand01r3_protocol import build_protocol, protocol_sha256

        protocol = build_protocol()
        mutated = copy.deepcopy(protocol)
        mutated["policy_sequence"][0]["policy_id"] = "RRC_1"
        self.assertNotEqual(protocol_sha256(protocol), protocol_sha256(mutated))

    def test_m008_first_real_event_requires_active_measurement_epoch(self):
        from cand01r3_protocol import record_measurement_event

        result = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("NOT_ELIGIBLE", result.status)
        self.assertEqual("MEASUREMENT_EPOCH_INACTIVE", result.reason)

    def test_m009_wrong_epoch_rejected(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        result = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            measurement_epoch="other-epoch",
            ledger_path=self.ledger_path,
        )
        self.assertEqual("NOT_ELIGIBLE", result.status)
        self.assertEqual("WRONG_MEASUREMENT_EPOCH", result.reason)

    def test_m010_train_question_rejected_from_measurement(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        result = record_measurement_event(
            question("sc900_p1_q022", role_hint="TRAIN", family="authentication_methods"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("NOT_ELIGIBLE", result.status)
        self.assertIn(result.reason, {"TRAIN", "TRAIN_QUESTION_NOT_MEASUREMENT"})

    def test_m011_unscheduled_probe_marked_protocol_deviation(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        result = record_measurement_event(
            question("unscheduled_probe", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("PROTOCOL_DEVIATION", result.status)
        self.assertFalse(result.clean)

    def test_m012_duplicate_first_attempt_excluded(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        first = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=False,
            ledger_path=self.ledger_path,
        )
        duplicate = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertEqual("PRIMARY", first.status)
        self.assertEqual("DUPLICATE_NOT_PRIMARY", duplicate.status)
        self.assertFalse(duplicate.clean)

    def test_m013_retry_excluded(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["B"],
            correct=False,
            ledger_path=self.ledger_path,
        )
        retry = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            kind="RETRY",
            ledger_path=self.ledger_path,
        )
        self.assertEqual("DUPLICATE_NOT_PRIMARY", retry.status)

    def test_m014_redo_excluded(self):
        from cand01r3_protocol import record_measurement_event

        self._begin()
        record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["B"],
            correct=False,
            ledger_path=self.ledger_path,
        )
        redo = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            kind="REDO",
            ledger_path=self.ledger_path,
        )
        self.assertEqual("DUPLICATE_NOT_PRIMARY", redo.status)

    def test_m015_unobserved_valid(self):
        from cand01r3_protocol import record_unobserved

        self._begin()
        observation = record_unobserved("sc900_p1_q001", reason="MISSED_SCHEDULED_PROBE", ledger_path=self.ledger_path)
        self.assertEqual("UNOBSERVED", observation.status)
        self.assertIsNone(observation.correct)
        self.assertFalse(observation.counts_toward_primary)

    def test_m016_contaminated_event_excluded_from_clean_endpoint(self):
        from cand01r3_protocol import clean_primary_events, record_contamination, record_measurement_event

        self._begin()
        record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        record_contamination("sc900_p1_q001", "EXPLANATION_EXPOSURE", ledger_path=self.ledger_path)
        self.assertEqual([], clean_primary_events(ledger_path=self.ledger_path))

    def test_m017_contamination_monotonic(self):
        from cand01r3_protocol import clear_contamination, record_contamination

        self._begin()
        record_contamination("sc900_p1_q001", "STEM_EXPOSURE", ledger_path=self.ledger_path)
        with self.assertRaises(ValueError):
            clear_contamination("sc900_p1_q001")

    def test_m018_train_exposure_snapshot_recorded(self):
        from cand01r3_protocol import record_measurement_event, record_train_exposure

        self._begin()
        record_train_exposure(
            policy_id="SMART_PRACTICE",
            question_id="sc900_p1_q022",
            semantic_family_id="authentication_methods",
            domain="microsoft_entra",
            objective="entra_authentication",
            service_class="COVERAGE",
        )
        event = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        snapshot = event.payload["train_exposure_snapshot"]
        self.assertGreaterEqual(snapshot["SMART_PRACTICE"]["train_questions_seen"], 1)
        self.assertGreaterEqual(snapshot["SMART_PRACTICE"]["unique_train_questions_seen"], 1)

    def test_m019_policy_exposure_recorded(self):
        from cand01r3_protocol import record_measurement_event, record_train_exposure

        self._begin()
        record_train_exposure(policy_id="RRC_1", question_id="sc900_p1_q022", service_class="REPAIR")
        event = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        self.assertIn("RRC_1", event.payload["policy_exposure_snapshot"])
        self.assertGreaterEqual(event.payload["policy_exposure_snapshot"]["RRC_1"]["train_questions_seen"], 1)

    def test_m020_synthetic_test_event_cannot_enter_production_ledger(self):
        from cand01r3_protocol import record_measurement_event

        production = Path(self.tmpdir.name) / "production.jsonl"
        production.write_text("", encoding="utf-8")
        self._begin(ledger_path=production)
        result = record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            synthetic=True,
            marker="TEST_ONLY",
            ledger_path=production,
        )
        self.assertEqual("NOT_ELIGIBLE", result.status)
        self.assertEqual("SYNTHETIC_FORBIDDEN_IN_PRODUCTION_LEDGER", result.reason)
        self.assertEqual("", production.read_text(encoding="utf-8"))

    def test_m021_default_engine_remains_unchanged_outside_experiment(self):
        from cand01r3_protocol import is_measurement_active
        from cand01r3_runtime import filter_training_questions, is_cand01r3_active

        pool = [question("train_a"), question("probe_a", role_hint="PROBE", family="family_probe")]
        self.assertFalse(is_cand01r3_active())
        self.assertFalse(is_measurement_active())
        self.assertEqual(["train_a", "probe_a"], [item["id"] for item in filter_training_questions(pool)])

    def test_m022_launch_bank_unchanged(self):
        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, sha256_file(DEFAULT_BANK))

    def test_m023_historical_prior_does_not_affect_policy_allocation(self):
        from cand01r3_protocol import allocated_policy_for_day, build_protocol

        protocol = build_protocol()
        with_prior = allocated_policy_for_day(1, historical_prior={"sy0701_mastery": 0.99})
        without_prior = allocated_policy_for_day(1, historical_prior=None)
        self.assertEqual(protocol["policy_sequence"][0]["policy_id"], with_prior)
        self.assertEqual(with_prior, without_prior)
        self.assertEqual("SMART_PRACTICE", with_prior)

    def test_m024_policy_order_cannot_change_after_first_real_observation(self):
        from cand01r3_protocol import mutate_policy_sequence, record_measurement_event

        self._begin()
        record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        with self.assertRaises(ValueError):
            mutate_policy_sequence([{"scheduled_day": 1, "policy_id": "RRC_1"}])

    def test_m025_protocol_cannot_be_silently_edited_after_first_real_observation(self):
        from cand01r3_protocol import record_measurement_event, replace_active_protocol

        self._begin()
        record_measurement_event(
            question("sc900_p1_q001", role_hint="PROBE", family="shared_responsibility_model"),
            selected=["A"],
            correct=True,
            ledger_path=self.ledger_path,
        )
        with self.assertRaises(ValueError):
            replace_active_protocol({"protocol_version": "mutated"})

    def test_committed_protocol_matches_builder(self):
        from cand01r3_protocol import build_protocol, load_committed_protocol, protocol_sha256

        committed = load_committed_protocol()
        built = build_protocol()
        self.assertEqual(protocol_sha256(built), protocol_sha256(committed))
        self.assertEqual(built["protocol_version"], committed["protocol_version"])
        self.assertEqual(0, committed["real_observations"])
        self.assertEqual("NOT_YET_AVAILABLE", committed["empirical_result"])

    def test_family_members_are_spread_across_days(self):
        from collections import defaultdict

        from cand01r3_protocol import build_protocol

        by_day = defaultdict(list)
        for row in build_protocol()["schedule"]:
            by_day[int(row["scheduled_day"])].append(row["semantic_family_id"])
        for day, families in by_day.items():
            self.assertEqual(len(families), len(set(families)), f"day {day} clustered a family")

    def test_begin_does_not_replace_default_bank_identity(self):
        from cand01r3_protocol import DEFAULT_LAUNCH_BANK_SHA256

        session = self._begin()
        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, DEFAULT_LAUNCH_BANK_SHA256)
        self.assertNotEqual(session.candidate_bank_identity, DEFAULT_LAUNCH_BANK_SHA256)
        self.assertEqual(EXPECTED_COMPILED_SHA256, session.candidate_bank_identity)

    def test_outside_study_values_are_observational(self):
        from cand01r3_protocol import OUTSIDE_STUDY_CODES, record_outside_study

        self._begin()
        self.assertEqual(OUTSIDE_STUDY_VALUES, set(OUTSIDE_STUDY_CODES))
        event = record_outside_study("MICROSOFT_LEARN", note="optional", scheduled_day=1, ledger_path=self.ledger_path)
        self.assertEqual("OUTSIDE_STUDY", event.status)
        self.assertEqual("MICROSOFT_LEARN", event.payload["outside_study"])
        self.assertFalse(event.counts_toward_primary)

    def test_synthetic_authority_cannot_satisfy_begin(self):
        from cand01r3_protocol import begin_cand01r3_measurement
        from cand01r3_runtime import Cand01R3AuthorityError

        activate_synthetic(synthetic_authority(), intended_use="MEASUREMENT")
        with self.assertRaises(Cand01R3AuthorityError):
            begin_cand01r3_measurement(
                learner_id=LEARNER_ID,
                measurement_epoch="cand01r3-measurement-001",
                schedule_version="cand01r3-probe-schedule-v1",
                policy_sequence_version="cand01r3-alt-crossover-v1",
                manifest_sha256=EXPECTED_MANIFEST_SHA256,
                store_sha256=EXPECTED_STORE_SHA256,
                semantic_audit_sha256=EXPECTED_AUDIT_SHA256,
                compiled_sha256=EXPECTED_COMPILED_SHA256,
                candidate_bank_identity=EXPECTED_COMPILED_SHA256,
                ledger_path=self.ledger_path,
                authority=synthetic_authority(),
            )


class Cand01R3ProtocolArtifactTests(unittest.TestCase):
    def test_protocol_json_has_no_variable_timestamp(self):
        from cand01r3_protocol import PROTOCOL_PATH, build_protocol

        raw = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        for key in ("generated_at", "created_at", "timestamp", "frozen_at"):
            self.assertNotIn(key, raw)
            self.assertNotIn(key, build_protocol())

    def test_pre_run_disposition_fields(self):
        from cand01r3_protocol import build_protocol, pre_run_disposition

        disposition = pre_run_disposition(build_protocol(), real_observations=0)
        self.assertEqual("CAND01R3_MEASUREMENT_PROTOCOL_FROZEN", disposition["status"])
        self.assertEqual(171, disposition["TRAIN_QUESTIONS"])
        self.assertEqual(29, disposition["PROBE_QUESTIONS"])
        self.assertEqual(7, disposition["INDEPENDENT_PROBE_FAMILIES"])
        self.assertEqual(0, disposition["REAL_OBSERVATIONS"])
        self.assertEqual("NOT_YET_AVAILABLE", disposition["EMPIRICAL_RESULT"])
        self.assertEqual("YES", disposition["DEFAULT_BANK_UNCHANGED"])
        self.assertEqual("NO", disposition["DEPLOYMENT_AUTHORIZED"])


if __name__ == "__main__":
    unittest.main()
