from __future__ import annotations

import copy
import unittest

from content_revision_authority import AdmittedRevision, RevisionEdge
from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    derive_migration_id,
    history_event_matches_approved_revision,
    history_events_for_question_revision_aware,
    migrate_progress_payload,
)
from question_identity import (
    bank_content_fingerprint,
    canonical_question_history_map,
    history_event_matches_question,
    question_content_fingerprint,
)


def _question(qid: str, *, choice_b: str = "beta") -> dict:
    return {
        "id": qid,
        "question_id": qid,
        "question_number": 1,
        "prompt": f"Prompt {qid}",
        "choices": {"A": "alpha", "B": choice_b, "C": "gamma", "D": "delta"},
        "correct": ["A"],
        "general_explanation": "because",
        "choice_explanations": {"A": "A", "B": "B", "C": "C", "D": "D"},
        "domain": "Identity",
        "topics": ["Entra"],
        "objective_code": "1.1",
        "question_type": "single",
        "study_focus": "Core",
        "exam_calibration_tier": "FUNDAMENTALS_CORE",
        "exam_simulation_eligible": True,
        "reasoning_steps": 1,
        "calibration_version": "v1",
    }


def _record() -> dict:
    return {
        "attempts": 4,
        "correct_count": 3,
        "wrong_count": 1,
        "correct_streak": 2,
        "last_seen": "2026-09-01",
        "next_review": "2026-09-10",
        "last_selected": ["A"],
        "last_correct": True,
        "last_confidence": "Sure",
        "flagged": True,
        "learner_memory": {"retrievability": 0.8, "stability": 12.0},
    }


def _revision(source_questions, target_questions, edges) -> AdmittedRevision:
    return AdmittedRevision(
        manifest_sha256="a" * 64,
        source_bank_filename="source_bank.json",
        source_bank_file_sha256="b" * 64,
        source_bank_content_fingerprint=bank_content_fingerprint(source_questions),
        target_bank_filename="target_bank.json",
        target_bank_file_sha256="c" * 64,
        target_bank_content_fingerprint=bank_content_fingerprint(target_questions),
        edges=edges,
    )


class ContentRevisionProgressMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.unchanged_source = _question("keep")
        self.unchanged_target = copy.deepcopy(self.unchanged_source)
        self.changed_source = _question("change", choice_b="beta")
        self.changed_target = _question("change", choice_b="beta rebalanced")
        self.source_questions = [self.unchanged_source, self.changed_source]
        self.target_questions = [self.unchanged_target, self.changed_target]
        self.edge = RevisionEdge(
            "change",
            question_content_fingerprint(self.changed_source),
            question_content_fingerprint(self.changed_target),
            "review.json",
            "d" * 64,
        )
        self.revision = _revision(self.source_questions, self.target_questions, (self.edge,))
        self.migrated_at = "2026-09-17T00:00:00"
        self.source_payload = {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": self.revision.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                "keep": question_content_fingerprint(self.unchanged_source),
                "change": question_content_fingerprint(self.changed_source),
            },
            "questions": {"keep": _record(), "change": _record()},
            "history": [
                {
                    "question_id": "change",
                    "question_content_fingerprint": question_content_fingerprint(self.changed_source),
                    "selected_texts": ["old wording"],
                    "correct_texts": ["alpha"],
                    "correct": True,
                }
            ],
            "quarantined_questions": {
                "gone": {"reason": "CHANGED_CONTENT", "record": {"attempts": 9}, "fingerprint": "x"}
            },
        }

    def test_full_metric_preservation_history_and_quarantine(self) -> None:
        result = migrate_progress_payload(self.source_payload, self.target_questions, self.revision, self.migrated_at)
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        self.assertTrue(result.changed)
        self.assertEqual(_record(), result.payload["questions"]["change"])
        self.assertEqual(_record(), result.payload["questions"]["keep"])
        self.assertEqual(self.source_payload["history"], result.payload["history"])
        self.assertEqual(self.source_payload["quarantined_questions"], result.payload["quarantined_questions"])
        self.assertNotIn("gone", result.payload["questions"])
        self.assertEqual(self.revision.target_bank_content_fingerprint, result.payload["bank_fingerprint"])
        self.assertEqual(question_content_fingerprint(self.changed_target), result.payload["question_content_fingerprints"]["change"])
        self.assertEqual(1, len(result.payload["content_revision_lineage"]))
        self.assertEqual("change", result.payload["content_revision_lineage"][0]["question_id"])
        self.assertEqual(derive_migration_id(self.revision), result.migration_id)

    def test_source_bank_mismatch(self) -> None:
        self.source_payload["bank_fingerprint"] = "f" * 64
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(self.source_payload, self.target_questions, self.revision, self.migrated_at)
        self.assertEqual(MigrationFailureReason.SOURCE_BANK_MISMATCH, ctx.exception.reason)

    def test_source_active_fingerprint_mismatch(self) -> None:
        self.source_payload["question_content_fingerprints"]["keep"] = "1" * 64
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(self.source_payload, self.target_questions, self.revision, self.migrated_at)
        self.assertEqual(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, ctx.exception.reason)

    def test_source_payload_with_edge_to_partial_state_fails(self) -> None:
        self.source_payload["question_content_fingerprints"]["change"] = self.edge.to_content_fingerprint
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(self.source_payload, self.target_questions, self.revision, self.migrated_at)
        self.assertEqual(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, ctx.exception.reason)

    def test_missing_target_question(self) -> None:
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(self.source_payload, [self.changed_target], self.revision, self.migrated_at)
        self.assertEqual(MigrationFailureReason.TARGET_QUESTION_MISSING, ctx.exception.reason)

    def test_unauthorized_transition(self) -> None:
        bad_edge = RevisionEdge("change", self.edge.from_content_fingerprint, "e" * 64, "review.json", "d" * 64)
        unauthorized = _revision(self.source_questions, self.target_questions, (bad_edge,))
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(self.source_payload, self.target_questions, unauthorized, self.migrated_at)
        self.assertEqual(MigrationFailureReason.UNAUTHORIZED_TRANSITION, ctx.exception.reason)

    def test_idempotent_target_no_op(self) -> None:
        first = migrate_progress_payload(self.source_payload, self.target_questions, self.revision, self.migrated_at)
        second = migrate_progress_payload(first.payload, self.target_questions, self.revision, "2026-09-18T00:00:00")
        self.assertEqual(MigrationStatus.MIGRATION_ALREADY_APPLIED, second.status)
        self.assertFalse(second.changed)
        self.assertEqual(first.payload["content_revision_lineage"], second.payload["content_revision_lineage"])
        self.assertEqual(first.payload["history"], second.payload["history"])

    def test_incomplete_target_lineage_fails(self) -> None:
        first = migrate_progress_payload(self.source_payload, self.target_questions, self.revision, self.migrated_at)
        first.payload["content_revision_lineage"] = []
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(first.payload, self.target_questions, self.revision, self.migrated_at)
        self.assertEqual(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, ctx.exception.reason)

    def test_strict_same_fp_history_and_approved_old_to_new(self) -> None:
        event = self.source_payload["history"][0]
        self.assertTrue(history_event_matches_question(event, self.changed_source))
        self.assertFalse(history_event_matches_question(event, self.changed_target))
        self.assertTrue(history_event_matches_approved_revision(event, self.changed_target, self.revision))
        self.assertFalse(history_event_matches_approved_revision(event, self.changed_target, None))
        mapped = canonical_question_history_map(self.source_payload["history"])
        attached = history_events_for_question_revision_aware(mapped, self.changed_target, self.revision)
        self.assertEqual(1, len(attached))
        self.assertEqual(["old wording"], attached[0]["selected_texts"])
        self.assertEqual(question_content_fingerprint(self.changed_source), attached[0]["question_content_fingerprint"])

    def test_different_id_and_reverse_only_do_not_attach(self) -> None:
        event = self.source_payload["history"][0]
        other = _question("other", choice_b="beta rebalanced")
        self.assertFalse(history_event_matches_approved_revision(event, other, self.revision))
        reverse = _revision(
            self.target_questions,
            self.source_questions,
            (
                RevisionEdge(
                    "change",
                    question_content_fingerprint(self.changed_target),
                    question_content_fingerprint(self.changed_source),
                    "review.json",
                    "d" * 64,
                ),
            ),
        )
        self.assertFalse(history_event_matches_approved_revision(event, self.changed_target, reverse))

    def test_complete_chain_and_missing_middle(self) -> None:
        v1 = _question("change", choice_b="beta")
        v2 = _question("change", choice_b="beta two")
        v3 = _question("change", choice_b="beta three")
        e12 = RevisionEdge("change", question_content_fingerprint(v1), question_content_fingerprint(v2), "r1.json", "1" * 64)
        e23 = RevisionEdge("change", question_content_fingerprint(v2), question_content_fingerprint(v3), "r2.json", "2" * 64)
        rev12 = _revision([v1], [v2], (e12,))
        rev23 = _revision([v2], [v3], (e23,))
        event = {
            "question_id": "change",
            "question_content_fingerprint": question_content_fingerprint(v1),
            "selected_texts": ["v1 text"],
        }
        self.assertTrue(history_event_matches_approved_revision(event, v3, [rev12, rev23]))
        self.assertFalse(history_event_matches_approved_revision(event, v3, [rev23]))
        attached = history_events_for_question_revision_aware(
            canonical_question_history_map([event]),
            v3,
            [rev12, rev23],
        )
        self.assertEqual(["v1 text"], attached[0]["selected_texts"])


if __name__ == "__main__":
    unittest.main()
