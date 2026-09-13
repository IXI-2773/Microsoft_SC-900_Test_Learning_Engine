from __future__ import annotations

import unittest

from cand01r3_fixtures import LEARNER_ID, PARTITION_EPOCH, activate_synthetic, question, synthetic_authority


class Cand01R3MeasurementTests(unittest.TestCase):
    def setUp(self):
        from cand01r3_measurement import MeasurementLedger
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()
        self.authority = synthetic_authority()
        activate_synthetic(self.authority, intended_use="MEASUREMENT", policy_id="PROBE_MEASUREMENT")
        self.ledger = MeasurementLedger(learner_id=LEARNER_ID, authority=self.authority)

    def tearDown(self):
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()

    def test_evaluation_identity_is_stable(self):
        from cand01r3_measurement import evaluation_id

        first = evaluation_id(LEARNER_ID, "SC-900", PARTITION_EPOCH, "probe_a")
        second = evaluation_id(LEARNER_ID, "SC-900", PARTITION_EPOCH, "probe_a")
        self.assertEqual(first, second)
        self.assertEqual((LEARNER_ID, "SC-900", PARTITION_EPOCH, "probe_a"), first)

    def test_g3_030_contaminated_probe_excluded(self):
        observation = self.ledger.record_scored_attempt(question("probe_a"), selected=["A"], correct=True)
        self.assertEqual("PRIMARY", observation.status)
        self.ledger.record_contamination("probe_a", "EXPLANATION_EXPOSURE")
        self.assertTrue(self.ledger.is_contaminated("probe_a"))
        self.assertIsNone(self.ledger.primary_observation("probe_a"))
        self.assertEqual(0, self.ledger.clean_primary_denominator())
        contaminated = self.ledger.contaminated_observations()
        self.assertEqual(1, len(contaminated))
        self.assertEqual("EXPLANATION_EXPOSURE", contaminated[0]["reason"])

    def test_contamination_is_monotonic(self):
        self.ledger.record_contamination("probe_a", "STEM_EXPOSURE")
        self.ledger.record_contamination("probe_a", "ANSWER_EXPOSURE")
        self.assertTrue(self.ledger.is_contaminated("probe_a"))
        with self.assertRaises(ValueError):
            self.ledger.clear_contamination("probe_a")
        self.assertTrue(self.ledger.is_contaminated("probe_a"))

    def test_g3_031_redo_is_not_a_new_first_attempt(self):
        first = self.ledger.record_scored_attempt(question("probe_a"), selected=["B"], correct=False)
        redo = self.ledger.record_scored_attempt(question("probe_a"), selected=["A"], correct=True, kind="REDO")
        self.assertEqual("PRIMARY", first.status)
        self.assertEqual("DUPLICATE_NOT_PRIMARY", redo.status)
        self.assertFalse(self.ledger.primary_observation("probe_a")["correct"])

    def test_g3_032_retry_is_not_a_new_first_attempt(self):
        self.ledger.record_scored_attempt(question("probe_a"), selected=["B"], correct=False)
        retry = self.ledger.record_scored_attempt(question("probe_a"), selected=["A"], correct=True, kind="RETRY")
        self.assertEqual("DUPLICATE_NOT_PRIMARY", retry.status)

    def test_g3_033_restore_duplicate_is_not_a_new_first_attempt(self):
        self.ledger.record_scored_attempt(question("probe_a"), selected=["A"], correct=True)
        restored = self.ledger.record_scored_attempt(
            question("probe_a"), selected=["A"], correct=True, kind="RESTORE_DUPLICATE"
        )
        self.assertEqual("DUPLICATE_NOT_PRIMARY", restored.status)
        self.assertEqual(1, self.ledger.clean_primary_denominator())

    def test_g3_034_unobserved_is_neither_correct_nor_wrong(self):
        observation = self.ledger.record_unobserved("probe_a", reason="MISSED_DELAYED_MEASUREMENT")
        self.assertEqual("UNOBSERVED", observation.status)
        self.assertIsNone(observation.correct)
        self.assertEqual(0, self.ledger.clean_primary_numerator())
        self.assertEqual(0, self.ledger.clean_primary_denominator())
        self.assertNotIn("probe_a", self.ledger.clean_primary_ids())

    def test_train_item_cannot_enter_measurement_ledger(self):
        observation = self.ledger.record_scored_attempt(question("train_a"), selected=["A"], correct=True)
        self.assertEqual("NOT_ELIGIBLE", observation.status)
        self.assertEqual("TRAIN", observation.reason)

    def test_effective_n_preserves_family_independence(self):
        summary = self.ledger.reporting_identity()
        self.assertEqual(29, summary["PROBE_QUESTIONS"])
        self.assertEqual(7, summary["INDEPENDENT_PROBE_FAMILIES"])
        self.assertNotEqual(summary["PROBE_QUESTIONS"], summary["INDEPENDENT_PROBE_FAMILIES"])

    def test_probe_answer_custody_avoids_stem_and_explanation_text(self):
        observation = self.ledger.record_scored_attempt(
            question("probe_a"), selected=["A"], correct=True, persist=True
        )
        stored = self.ledger.persisted_records()[0]
        self.assertEqual("probe_a", stored["question_id"])
        self.assertEqual(["A"], stored["selected_option_ids"])
        self.assertNotIn("stem", stored)
        self.assertNotIn("prompt", stored)
        self.assertNotIn("explanation", stored)
        self.assertNotIn("correct_texts", stored)
        self.assertNotIn("general_explanation", stored)
        self.assertTrue(observation.correct)

    def test_imported_duplicate_history_is_not_primary(self):
        self.ledger.record_scored_attempt(question("probe_a"), selected=["A"], correct=True)
        imported = self.ledger.record_scored_attempt(
            question("probe_a"), selected=["A"], correct=True, kind="IMPORTED_DUPLICATE"
        )
        self.assertEqual("DUPLICATE_NOT_PRIMARY", imported.status)


if __name__ == "__main__":
    unittest.main()
