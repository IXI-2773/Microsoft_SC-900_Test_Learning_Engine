from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cand01r3_fixtures import (
    DEFAULT_BANK,
    EXPECTED_AUDIT_SHA256,
    EXPECTED_COMPILED_SHA256,
    EXPECTED_DEFAULT_BANK_SHA256,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_STORE_SHA256,
    PARTITION_EPOCH,
    PHASE3_ROOT,
    question,
    sha256_file,
    synthetic_authority,
)


class Cand01R3PartitionTests(unittest.TestCase):
    def test_frozen_hash_bindings_match_committed_artifacts(self):
        from cand01r3_partition import (
            EXPECTED_COMPILED_SHA256 as compiled,
        )
        from cand01r3_partition import (
            EXPECTED_MANIFEST_SHA256 as manifest,
        )
        from cand01r3_partition import (
            EXPECTED_SEMANTIC_AUDIT_SHA256 as audit,
        )
        from cand01r3_partition import (
            EXPECTED_STORE_SHA256 as store,
        )
        from cand01r3_partition import (
            load_runtime_authority,
        )

        authority = load_runtime_authority()
        self.assertTrue(authority.valid)
        self.assertEqual(EXPECTED_AUDIT_SHA256, audit)
        self.assertEqual(EXPECTED_STORE_SHA256, store)
        self.assertEqual(EXPECTED_COMPILED_SHA256, compiled)
        self.assertEqual(EXPECTED_MANIFEST_SHA256, manifest)
        self.assertEqual(EXPECTED_AUDIT_SHA256, sha256_file(PHASE3_ROOT / "semantic_family_audit.json"))
        self.assertEqual(EXPECTED_STORE_SHA256, sha256_file(PHASE3_ROOT / "store" / "questions.json"))
        self.assertEqual(
            EXPECTED_COMPILED_SHA256,
            sha256_file(PHASE3_ROOT / "compiled" / "sc900_phase3_reviewed_bank.json"),
        )
        self.assertEqual(EXPECTED_MANIFEST_SHA256, sha256_file(PHASE3_ROOT / "train_probe_manifest.json"))
        self.assertEqual(PARTITION_EPOCH, authority.partition_epoch)
        self.assertEqual(171, authority.train_count)
        self.assertEqual(29, authority.probe_count)
        self.assertEqual(20, len(authority.train_family_ids))
        self.assertEqual(7, len(authority.probe_family_ids))

    def test_g3_019_missing_manifest_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, load_runtime_authority, partition_eligibility

        authority = load_runtime_authority(manifest_path=Path("missing-manifest.json"))
        self.assertFalse(authority.valid)
        self.assertEqual("MISSING_MANIFEST", authority.reason)
        decision = partition_eligibility(question("train_a"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("MISSING_MANIFEST", decision.reason)

    def test_g3_020_manifest_sha_mismatch_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, load_runtime_authority, partition_eligibility

        authority = load_runtime_authority(expected_manifest_sha256="0" * 64)
        self.assertFalse(authority.valid)
        self.assertEqual("MANIFEST_HASH_MISMATCH", authority.reason)
        decision = partition_eligibility(question("sc900_p1_q002"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("MANIFEST_HASH_MISMATCH", decision.reason)

    def test_g3_021_store_sha_mismatch_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, load_runtime_authority, partition_eligibility

        authority = load_runtime_authority(expected_store_sha256="1" * 64)
        self.assertFalse(authority.valid)
        self.assertEqual("STORE_HASH_MISMATCH", authority.reason)
        decision = partition_eligibility(question("sc900_p1_q002"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("STORE_HASH_MISMATCH", decision.reason)

    def test_g3_022_semantic_audit_sha_mismatch_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, load_runtime_authority, partition_eligibility

        authority = load_runtime_authority(expected_semantic_audit_sha256="2" * 64)
        self.assertFalse(authority.valid)
        self.assertEqual("SEMANTIC_AUDIT_HASH_MISMATCH", authority.reason)
        decision = partition_eligibility(question("sc900_p1_q002"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("SEMANTIC_AUDIT_HASH_MISMATCH", decision.reason)

    def test_g3_023_unknown_question_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, partition_eligibility

        decision = partition_eligibility(question("not_in_manifest"), INTENDED_USE_TRAINING, synthetic_authority())
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("QUESTION_NOT_IN_MANIFEST", decision.reason)

    def test_g3_024_unknown_and_malformed_role_fail_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, partition_eligibility

        unknown = synthetic_authority(train_ids=["q1"], roles={"q1": "SOMETIMES"})
        malformed = synthetic_authority(train_ids=["q1"], roles={"q1": ""})
        missing = synthetic_authority(train_ids=["q1"], roles={"q1": "MISSING_ROLE"})
        unknown.items["q1"]["role"] = "WEIRD"
        malformed.items["q1"]["role"] = None
        missing.items["q1"]["role"] = "MISSING_ROLE"
        self.assertEqual(
            "UNKNOWN_ROLE",
            partition_eligibility(question("q1"), INTENDED_USE_TRAINING, unknown).reason,
        )
        self.assertEqual(
            "MALFORMED_ROLE",
            partition_eligibility(question("q1"), INTENDED_USE_TRAINING, malformed).reason,
        )
        self.assertEqual(
            "UNKNOWN_ROLE",
            partition_eligibility(question("q1"), INTENDED_USE_TRAINING, missing).reason,
        )

    def test_g3_025_nonapproved_item_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, partition_eligibility

        authority = synthetic_authority(train_ids=["q1"], statuses={"q1": "pending"})
        decision = partition_eligibility(question("q1"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("UNAPPROVED_ITEM", decision.reason)

    def test_g3_026_unknown_and_unresolved_family_fail_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, partition_eligibility

        unknown = synthetic_authority(train_ids=["q1"])
        unknown.items["q1"]["semantic_family_id"] = "missing_family"
        unresolved = synthetic_authority(train_ids=["q1"], family_states={"family_train": "unresolved"})
        self.assertEqual(
            "UNKNOWN_FAMILY",
            partition_eligibility(question("q1"), INTENDED_USE_TRAINING, unknown).reason,
        )
        self.assertEqual(
            "UNRESOLVED_FAMILY",
            partition_eligibility(question("q1"), INTENDED_USE_TRAINING, unresolved).reason,
        )

    def test_g3_027_unassigned_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_MEASUREMENT, INTENDED_USE_TRAINING, partition_eligibility

        authority = synthetic_authority(train_ids=[], probe_ids=[], unassigned_ids=["q_u"], roles={"q_u": "UNASSIGNED"})
        for intended_use in (INTENDED_USE_TRAINING, INTENDED_USE_MEASUREMENT):
            decision = partition_eligibility(question("q_u"), intended_use, authority)
            self.assertEqual("NOT_ELIGIBLE", decision.role)
            self.assertEqual("UNASSIGNED", decision.reason)

    def test_g3_028_train_rejected_from_probe_measurement(self):
        from cand01r3_partition import INTENDED_USE_MEASUREMENT, partition_eligibility

        decision = partition_eligibility(question("train_a"), INTENDED_USE_MEASUREMENT, synthetic_authority())
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("TRAIN", decision.reason)

    def test_g3_029_probe_ineligible_item_rejected_from_measurement(self):
        from cand01r3_partition import INTENDED_USE_MEASUREMENT, partition_eligibility

        authority = synthetic_authority(probe_ids=["probe_a"], suitability={"probe_a": "train_only"})
        decision = partition_eligibility(question("probe_a"), INTENDED_USE_MEASUREMENT, authority)
        self.assertEqual("NOT_ELIGIBLE", decision.role)
        self.assertEqual("PROBE_INELIGIBLE", decision.reason)

    def test_training_accepts_train_and_rejects_probe(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, filter_questions, partition_eligibility

        authority = synthetic_authority()
        train = partition_eligibility(question("train_a"), INTENDED_USE_TRAINING, authority)
        probe = partition_eligibility(question("probe_a"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("TRAIN", train.role)
        self.assertEqual("NOT_ELIGIBLE", probe.role)
        self.assertEqual("PROBE", probe.reason)
        filtered = filter_questions(
            [question("train_a"), question("probe_a"), question("train_b")],
            INTENDED_USE_TRAINING,
            authority,
        )
        self.assertEqual(["train_a", "train_b"], [row["id"] for row in filtered])

    def test_empty_train_pool_does_not_fall_back_to_probe_or_full_bank(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, filter_questions

        authority = synthetic_authority(train_ids=[], probe_ids=["probe_a"])
        filtered = filter_questions([question("probe_a")], INTENDED_USE_TRAINING, authority)
        self.assertEqual([], filtered)

    def test_family_role_inconsistency_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_TRAINING, partition_eligibility

        authority = synthetic_authority(train_ids=["q1"], family_roles={"family_train": "PROBE"})
        decision = partition_eligibility(question("q1"), INTENDED_USE_TRAINING, authority)
        self.assertEqual("FAMILY_ROLE_INCONSISTENCY", decision.reason)

    def test_transfer_edge_conflict_fails_closed(self):
        from cand01r3_partition import INTENDED_USE_MEASUREMENT, INTENDED_USE_TRAINING, partition_eligibility

        authority = synthetic_authority(
            train_ids=["train_a"],
            probe_ids=["probe_a"],
            transfer_edges=[{"left": "train_a", "right": "probe_a", "semantic_family_id": "mixed"}],
        )
        self.assertEqual(
            "TRANSFER_EDGE_CONFLICT",
            partition_eligibility(question("train_a"), INTENDED_USE_TRAINING, authority).reason,
        )
        self.assertEqual(
            "TRANSFER_EDGE_CONFLICT",
            partition_eligibility(question("probe_a"), INTENDED_USE_MEASUREMENT, authority).reason,
        )

    def test_measurement_rejects_probe_family_with_train_member(self):
        from cand01r3_partition import INTENDED_USE_MEASUREMENT, partition_eligibility

        authority = synthetic_authority(
            train_ids=["train_mix"],
            probe_ids=["probe_mix"],
            family_map={"train_mix": "shared", "probe_mix": "shared"},
            family_roles={"shared": "PROBE"},
            roles={"train_mix": "TRAIN", "probe_mix": "PROBE"},
        )
        decision = partition_eligibility(question("probe_mix"), INTENDED_USE_MEASUREMENT, authority)
        self.assertEqual("FAMILY_ROLE_INCONSISTENCY", decision.reason)

    def test_g3_037_default_launch_bank_selection_unchanged(self):
        import app as app_module
        from cert_config import QUESTION_BANK_FILENAME

        self.assertEqual(EXPECTED_DEFAULT_BANK_SHA256, sha256_file(DEFAULT_BANK))
        self.assertTrue(str(app_module.DEFAULT_BANK).endswith(QUESTION_BANK_FILENAME) or app_module.DEFAULT_BANK.exists())
        self.assertNotEqual(
            EXPECTED_COMPILED_SHA256,
            sha256_file(DEFAULT_BANK),
        )

    def test_mutated_temp_manifest_does_not_rewrite_frozen_files(self):
        original = sha256_file(PHASE3_ROOT / "train_probe_manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "train_probe_manifest.json"
            fake.write_text("{}", encoding="utf-8")
            from cand01r3_partition import load_runtime_authority

            authority = load_runtime_authority(manifest_path=fake)
            self.assertFalse(authority.valid)
        self.assertEqual(original, sha256_file(PHASE3_ROOT / "train_probe_manifest.json"))


if __name__ == "__main__":
    unittest.main()
