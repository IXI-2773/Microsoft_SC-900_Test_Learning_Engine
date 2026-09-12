from __future__ import annotations

import copy
import unittest

from cand01r3_fixtures import (
    EXPECTED_MANIFEST_SHA256,
    PARTITION_EPOCH,
    activate_synthetic,
    progress_record,
    question,
    synthetic_authority,
)


class Cand01R3Rrc1Tests(unittest.TestCase):
    def setUp(self):
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()
        self.authority = synthetic_authority(train_ids=["repair_q", "review_q", "cover_q", "cover_q2"], probe_ids=["probe_a"])
        activate_synthetic(self.authority, policy_id="RRC_1_CHALLENGER")
        self.questions = [
            question("repair_q", question_number=1, domain="d1", objective="o1"),
            question("review_q", question_number=2, domain="d1", objective="o2"),
            question("cover_q", question_number=3, domain="d2", objective="o3"),
            question("cover_q2", question_number=4, domain="d2", objective="o3"),
            question("probe_a", question_number=9, domain="d9", objective="o9", family="family_probe"),
        ]

    def tearDown(self):
        from cand01r3_runtime import reset_cand01r3_runtime

        reset_cand01r3_runtime()

    def records(self, **overrides):
        base = {
            "repair_q": progress_record(attempts=3, wrong_count=3, correct_count=0, last_correct=False, last_seen="2026-09-01"),
            "review_q": progress_record(
                attempts=2,
                wrong_count=0,
                correct_count=2,
                last_correct=True,
                last_seen="2026-09-02",
                next_review="2026-09-01",
                learner_memory={"next_review_at": "2026-09-01", "retrievability": 0.2},
            ),
            "cover_q": progress_record(attempts=0, last_seen=""),
            "cover_q2": progress_record(attempts=1, correct_count=1, last_correct=True, last_seen="2026-09-10"),
            "probe_a": progress_record(attempts=5, wrong_count=5, last_correct=False),
        }
        for key, value in overrides.items():
            base[key] = value
        return base

    def test_g3_008_probe_rejected_from_rrc1(self):
        from cand01r3_rrc1 import classify_question, select_rrc1_session

        records = self.records()
        self.assertIsNone(classify_question(self.questions[-1], records["probe_a"], self.authority))
        result = select_rrc1_session(self.questions, records, self.authority, session_size=10)
        selected_ids = [row["id"] for row in result.questions]
        self.assertNotIn("probe_a", selected_ids)
        self.assertTrue(all(qid != "probe_a" for qid in selected_ids))

    def test_repair_owns_weak_and_due_item(self):
        from cand01r3_rrc1 import CLASS_REPAIR, classify_question

        record = progress_record(
            attempts=4,
            wrong_count=3,
            correct_count=1,
            last_correct=False,
            next_review="2026-09-01",
            learner_memory={"next_review_at": "2026-09-01", "retrievability": 0.1},
        )
        self.assertEqual(CLASS_REPAIR, classify_question(self.questions[0], record, self.authority))

    def test_review_contains_due_nonweak_item(self):
        from cand01r3_rrc1 import CLASS_REVIEW, classify_question

        self.assertEqual(CLASS_REVIEW, classify_question(self.questions[1], self.records()["review_q"], self.authority))

    def test_coverage_contains_neither_weak_nor_due(self):
        from cand01r3_rrc1 import CLASS_COVERAGE, classify_question

        self.assertEqual(CLASS_COVERAGE, classify_question(self.questions[2], self.records()["cover_q"], self.authority))

    def test_classes_are_mutually_exclusive(self):
        from cand01r3_rrc1 import classify_classes

        classes = classify_classes(self.questions, self.records(), self.authority)
        seen = []
        for _class_name, members in classes.items():
            for question_id in members:
                self.assertNotIn(question_id, seen)
                seen.append(question_id)
        self.assertEqual({"repair_q"}, set(classes["REPAIR"]))
        self.assertEqual({"review_q"}, set(classes["REVIEW"]))
        self.assertEqual({"cover_q", "cover_q2"}, set(classes["COVERAGE"]))

    def test_round_robin_repair_review_coverage(self):
        from cand01r3_rrc1 import select_rrc1_session

        result = select_rrc1_session(self.questions, self.records(), self.authority, session_size=3)
        self.assertEqual(["repair_q", "review_q", "cover_q"], [row["id"] for row in result.questions])
        self.assertEqual(["REPAIR", "REVIEW", "COVERAGE"], result.service_classes)

    def test_empty_class_is_skipped_without_fake_credit(self):
        from cand01r3_rrc1 import select_rrc1_session

        records = self.records()
        records["repair_q"] = progress_record(attempts=0)
        result = select_rrc1_session(self.questions[1:], records, self.authority, session_size=3)
        self.assertIn("EMPTY_CLASS_SKIP", result.events)
        self.assertEqual("REPAIR", result.events["EMPTY_CLASS_SKIP"][0]["class_name"])
        self.assertEqual(["review_q", "cover_q", "cover_q2"], [row["id"] for row in result.questions])
        self.assertNotIn("REPAIR", result.service_classes)

    def test_session_size_limit_and_deterministic_ordering(self):
        from cand01r3_rrc1 import select_rrc1_session

        first = select_rrc1_session(self.questions, self.records(), self.authority, session_size=2)
        second = select_rrc1_session(self.questions, self.records(), self.authority, session_size=2)
        self.assertEqual(["repair_q", "review_q"], [row["id"] for row in first.questions])
        self.assertEqual([row["id"] for row in first.questions], [row["id"] for row in second.questions])
        self.assertEqual(2, len(first.questions))

    def test_stable_id_breaks_coverage_ties(self):
        from cand01r3_rrc1 import CLASS_COVERAGE, in_class_order

        q_b = question("cover_b", question_number=20, domain="d2", objective="o3")
        q_a = question("cover_a", question_number=21, domain="d2", objective="o3")
        records = {
            "cover_b": progress_record(attempts=0, last_seen=""),
            "cover_a": progress_record(attempts=0, last_seen=""),
        }
        ordered = in_class_order(CLASS_COVERAGE, [q_b, q_a], records, self.authority)
        self.assertEqual(["cover_a", "cover_b"], [row["id"] for row in ordered])

    def test_no_weighted_utility_field_used(self):
        from cand01r3_rrc1 import select_rrc1_session

        result = select_rrc1_session(self.questions, self.records(), self.authority, session_size=4)
        self.assertFalse(hasattr(result, "utility_scores"))
        self.assertNotIn("weighted_utility", result.metrics)

    def test_g3_038_historical_prior_mutation_cannot_change_rrc1_selection(self):
        from cand01r3_rrc1 import select_rrc1_session

        baseline = select_rrc1_session(self.questions, self.records(), self.authority, session_size=4)
        mutated_questions = copy.deepcopy(self.questions)
        for row in mutated_questions:
            row["historical_prior"] = {"sy0701_mastery": 0.01, "security_plus_profile": "weak"}
            row["cross_exam_readiness"] = 0.0
        mutated_records = self.records()
        for record in mutated_records.values():
            record["historical_prior"] = {"sy0701_mastery": 0.01}
            record["cross_exam_readiness"] = 0.0
            record["session_endurance_recommendation"] = 3
            record["brier"] = 0.9
            record["ece"] = 0.9
            record["concept_graph_score"] = 0.0
            record["smart_utility"] = 0.0
        mutated = select_rrc1_session(mutated_questions, mutated_records, self.authority, session_size=4)
        self.assertEqual([row["id"] for row in baseline.questions], [row["id"] for row in mutated.questions])
        self.assertEqual(baseline.service_classes, mutated.service_classes)

    def test_g3_039_confidence_mutation_cannot_change_rrc1_class(self):
        from cand01r3_rrc1 import classify_question

        record = self.records()["cover_q"]
        baseline = classify_question(self.questions[2], record, self.authority)
        mutated = copy.deepcopy(record)
        mutated["last_confidence"] = "Guessed"
        mutated["confidence"] = "Guessed"
        self.assertEqual(baseline, classify_question(self.questions[2], mutated, self.authority))

    def test_g3_040_response_time_mutation_cannot_change_rrc1_class(self):
        from cand01r3_rrc1 import classify_question

        record = self.records()["cover_q"]
        baseline = classify_question(self.questions[2], record, self.authority)
        mutated = copy.deepcopy(record)
        mutated["response_seconds"] = 180.0
        mutated["slow_success"] = True
        mutated["effective_response_seconds"] = 240.0
        self.assertEqual(baseline, classify_question(self.questions[2], mutated, self.authority))

    def test_fairness_metrics_exist_without_pass_fail_thresholds(self):
        from cand01r3_rrc1 import select_rrc1_session

        result = select_rrc1_session(self.questions, self.records(), self.authority, session_size=4)
        for key in (
            "MAX_SERVICE_DELAY",
            "OVERDUE_RATE",
            "STARVATION_RATE",
            "QUEUE_AGE",
            "COVERAGE_DEBT",
            "DOMAIN_SERVICE_BALANCE",
            "OBJECTIVE_SERVICE_BALANCE",
            "CLASS_SERVICE_SHARE",
            "BACKLOG_SIZE",
            "SESSION_CLASS_DOMINANCE",
        ):
            self.assertIn(key, result.metrics)
        self.assertNotIn("acceptable_starvation_percentage", result.metrics)
        self.assertNotIn("coverage_minimum", result.metrics)
        self.assertNotIn("maximum_overdue_days", result.metrics)
        self.assertNotIn("dominance_cutoff", result.metrics)

    def test_service_events_include_policy_and_class_fields(self):
        from cand01r3_rrc1 import select_rrc1_session

        result = select_rrc1_session(self.questions, self.records(), self.authority, session_size=3)
        event = result.service_log[0]
        self.assertEqual("RRC_1_CHALLENGER", event["policy_id"])
        self.assertEqual("REPAIR", event["service_class"])
        self.assertEqual("repair_q", event["question_id"])
        self.assertEqual(PARTITION_EPOCH, event["partition_epoch"])
        self.assertEqual(EXPECTED_MANIFEST_SHA256, event["manifest_sha256"])
        self.assertIn("weak_state", event)
        self.assertIn("due_state", event)


if __name__ == "__main__":
    unittest.main()
