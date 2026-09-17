from __future__ import annotations

import copy
import unittest

from app_constants import MODE_PRACTICE
from content_revision_authority import AdmittedRevision, RevisionEdge
from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    derive_migration_id,
    history_event_matches_approved_revision,
    history_events_for_question_revision_aware,
    migrate_progress_payload,
    migrate_session_payload,
)
from question_identity import (
    bank_content_fingerprint,
    canonical_question_history_map,
    history_event_matches_question,
    question_content_fingerprint,
)
from session_identity import canonical_session_signature
from session_store import build_session_snapshot


def _question(qid: str, *, choice_b: str = "beta", number: int = 1) -> dict:
    return {
        "id": qid,
        "question_id": qid,
        "question_number": number,
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
        self.assertEqual(
            question_content_fingerprint(self.changed_target), result.payload["question_content_fingerprints"]["change"]
        )
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
        e12 = RevisionEdge(
            "change", question_content_fingerprint(v1), question_content_fingerprint(v2), "r1.json", "1" * 64
        )
        e23 = RevisionEdge(
            "change", question_content_fingerprint(v2), question_content_fingerprint(v3), "r2.json", "2" * 64
        )
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


def _answer(*, selected=None, pending=None, answered=False, flagged=False):
    return {
        "selected": list(selected or []),
        "pending": list(pending if pending is not None else selected or []),
        "answered": answered,
        "flagged": flagged,
        "suspended": False,
        "last_confidence": "Sure" if answered else "",
        "last_miss_reason": "",
        "recall_ready": False,
        "session_tag": "",
        "smart_primary_role": "",
        "smart_selection_reasons": [],
        "smart_utility": 0.0,
        "smart_utility_breakdown": {},
        "smart_policy_version": "",
        "smart_policy_id": "",
        "smart_concept_key": "",
        "smart_root_cause": "",
        "smart_root_cause_confidence": 0.0,
        "smart_supporting_concepts": [],
        "smart_graph_version": "",
        "smart_information_value": 0.0,
        "smart_information_breakdown": {},
        "smart_question_quality_status": "",
        "smart_question_quality_confidence": 0.0,
        "smart_graph_bottleneck": 0.0,
        "repair_stage": "",
        "repair_concept_key": "",
        "legacy_repair_concept_key": "",
        "prediction_id": "",
        "prediction_snapshot": {},
    }


class ContentRevisionSessionMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keep_source = _question("keep", number=1)
        self.keep_target = copy.deepcopy(self.keep_source)
        self.change_source = _question("change", choice_b="beta", number=2)
        self.change_target = _question("change", choice_b="beta rebalanced", number=2)
        self.source_questions = [self.keep_source, self.change_source]
        self.target_questions = [self.keep_target, self.change_target]
        self.edge = RevisionEdge(
            "change",
            question_content_fingerprint(self.change_source),
            question_content_fingerprint(self.change_target),
            "review.json",
            "d" * 64,
        )
        self.revision = _revision(self.source_questions, self.target_questions, (self.edge,))
        history_event = {
            "question_id": "change",
            "question_number": 2,
            "question_content_fingerprint": question_content_fingerprint(self.change_source),
            "selected_texts": ["beta"],
            "correct_texts": ["alpha"],
            "correct": False,
        }
        self.snapshot = build_session_snapshot(
            app_version="test",
            bank_file="source_bank.json",
            mode=MODE_PRACTICE,
            builder_context={
                "mode": MODE_PRACTICE,
                "count": "2",
                "source_label": "Full bank",
                "session_source": "",
                "randomize": False,
                "domain_filter": "All domains",
                "topic_filter": "All topics",
                "status_filter": "All questions",
            },
            source_label="Full bank",
            question_numbers=[1, 2],
            restore_question_numbers=[1, 2],
            bank_fingerprint=self.revision.source_bank_content_fingerprint,
            question_ids=["keep", "change"],
            restore_question_ids=["keep", "change"],
            session_base_question_count=2,
            session_question_limit=2,
            current_index=1,
            elapsed_seconds=42,
            exam_reveal=True,
            checkpoints_saved=["cp1"],
            session_rewards=["r1"],
            unlocked_rewards=["u1"],
            session_answer_history=[history_event],
            current_quests=[],
            quest_completion_keys=["q1"],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=7,
            answers=[
                _answer(selected=["A"], answered=True, flagged=True),
                _answer(selected=["B"], pending=["B"], answered=False),
            ],
        )

    def _migrate(self, snapshot=None, revision=None, target_questions=None):
        return migrate_session_payload(
            snapshot if snapshot is not None else self.snapshot,
            target_questions if target_questions is not None else self.target_questions,
            revision if revision is not None else self.revision,
            "target_bank.json",
            source_questions=self.source_questions,
        )

    def test_completed_changed_and_unanswered_pending_reset(self) -> None:
        result = self._migrate()
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        self.assertEqual(["A"], answers["keep"]["selected"])
        self.assertTrue(answers["keep"]["answered"])
        self.assertTrue(answers["keep"]["flagged"])
        self.assertEqual([], answers["change"]["selected"])
        self.assertEqual([], answers["change"]["pending"])
        self.assertFalse(answers["change"]["answered"])
        self.assertEqual(self.snapshot["session_answer_history"], result.payload["session_answer_history"])
        self.assertEqual(1, result.payload["current_index"])
        self.assertEqual(42, result.payload["elapsed_seconds"])
        self.assertEqual(["cp1"], result.payload["checkpoints_saved"])
        self.assertEqual("target_bank.json", result.payload["bank_file"])
        self.assertEqual(self.revision.target_bank_content_fingerprint, result.payload["bank_fingerprint"])
        self.assertEqual(
            canonical_session_signature(
                MODE_PRACTICE, self.revision.target_bank_content_fingerprint, ["keep", "change"]
            ),
            result.payload["session_signature"],
        )
        self.assertNotEqual(self.snapshot["session_signature"], result.payload["session_signature"])

    def test_source_bank_fingerprint_mismatch(self) -> None:
        self.snapshot["bank_fingerprint"] = "f" * 64
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            self._migrate()
        self.assertEqual(MigrationFailureReason.SOURCE_BANK_MISMATCH, ctx.exception.reason)

    def test_invalid_source_signatures(self) -> None:
        self.snapshot["session_signature"] = "deadbeef"
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            self._migrate()
        self.assertEqual(MigrationFailureReason.INVALID_SOURCE_SESSION, ctx.exception.reason)

    def test_unknown_target_question(self) -> None:
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            self._migrate(target_questions=[self.change_target])
        self.assertEqual(MigrationFailureReason.TARGET_QUESTION_MISSING, ctx.exception.reason)

    def test_changed_target_fingerprint_mismatch(self) -> None:
        wrong_target = _question("change", choice_b="other wording", number=2)
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            self._migrate(target_questions=[self.keep_target, wrong_target])
        self.assertEqual(MigrationFailureReason.UNAUTHORIZED_TRANSITION, ctx.exception.reason)

    def test_changed_question_missing_edge(self) -> None:
        empty = _revision(self.source_questions, self.target_questions, ())
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            self._migrate(revision=empty)
        self.assertEqual(MigrationFailureReason.CHANGED_QUESTION_MISSING_EDGE, ctx.exception.reason)


if __name__ == "__main__":
    unittest.main()
