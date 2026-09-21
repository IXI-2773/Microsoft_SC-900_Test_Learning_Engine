from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from app_constants import MODE_PRACTICE
from content_revision_authority import AdmissionStatus
from content_revision_explanation_authority import admit_explanation_revision
from content_revision_explanation_migration import (
    MigrationStatus,
    history_event_matches_explanation_revision,
    migrate_explanation_progress_payload,
    migrate_explanation_session_payload,
)
from question_identity import canonical_question_history_map, question_content_fingerprint
from session_store import build_session_snapshot

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "sc900_bank_v8_content_correction_001.json"
TARGET_PATH = ROOT / "sc900_bank_v8_explanation_tranche_1.json"
SPEC_PATH = ROOT / "content_revision_evidence/specs/sc900_explanation_tranche_1.json"
LEDGER_PATH = ROOT / "content_revision_evidence/reviews/SC900-EXPLANATION-TRANCHE-1/semantic_review_ledger.json"
MANIFEST_PATH = ROOT / "content_revision_evidence/manifests/sc900_explanation_tranche_1.json"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _answer(*, selected=None, pending=None, answered=False, flagged=False):
    return {
        "selected": list(selected or []),
        "pending": list(pending if pending is not None else selected or []),
        "answered": answered,
        "flagged": flagged,
        "suspended": False,
        "last_confidence": "Sure" if answered else "Unsure",
        "last_miss_reason": "Narrowed to two" if answered else "",
        "last_recall_failure": "",
        "answer_event_id": "event-1" if answered else "",
        "recall_ready": False,
        "session_tag": "weak_repair",
        "smart_primary_role": "weak_repair",
        "smart_selection_reasons": ["weakness"],
        "smart_utility": 7.5,
        "smart_utility_breakdown": {"weakness": 7.5},
        "smart_policy_version": "v1",
        "smart_policy_id": "smart",
        "smart_concept_key": "concept",
        "smart_root_cause": "misconception",
        "smart_root_cause_confidence": 0.8,
        "smart_supporting_concepts": ["support"],
        "smart_graph_version": "g1",
        "smart_information_value": 2.5,
        "smart_information_breakdown": {"x": 2.5},
        "smart_question_quality_status": "PASS",
        "smart_question_quality_confidence": 0.9,
        "smart_graph_bottleneck": 0.2,
        "repair_stage": "repair",
        "repair_concept_key": "concept",
        "legacy_repair_concept_key": "",
        "prediction_id": "pred",
        "prediction_snapshot": {"score": 1},
    }


class ExplanationMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = _load(SOURCE_PATH)
        cls.target = _load(TARGET_PATH)
        cls.source_questions = cls.source["questions"]
        cls.target_questions = cls.target["questions"]
        cls.source_by_id = {q["id"]: q for q in cls.source_questions}
        cls.target_by_id = {q["id"]: q for q in cls.target_questions}
        manifest = _load(MANIFEST_PATH)
        result = admit_explanation_revision(
            manifest,
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            ledger_path=LEDGER_PATH,
        )
        if result.status != AdmissionStatus.PASS or result.admitted is None:
            raise AssertionError(result.reasons)
        cls.revision = result.admitted
        cls.qids = ["sc900_p3_q025", "sc900_p3_q030"]

    def _progress_payload(self):
        records = {
            self.qids[0]: {
                "attempts": 9,
                "correct_count": 6,
                "wrong_count": 3,
                "correct_streak": 2,
                "last_seen": "2026-09-21T01:00:00",
                "next_review": "2026-09-25",
                "last_selected": ["B"],
                "last_correct": False,
                "last_confidence": "Sure",
                "last_miss_reason": "Narrowed to two",
                "flagged": True,
                "suspended": False,
                "learner_memory": {"retrievability": 0.7, "stability": 12.0},
                "smart_primary_role": "weak_repair",
                "smart_utility": 7.5,
                "smart_selection_reasons": ["weakness"],
            },
            self.qids[1]: {
                "attempts": 4,
                "correct_count": 3,
                "wrong_count": 1,
                "correct_streak": 1,
                "last_seen": "2026-09-20T01:00:00",
                "next_review": "2026-09-26",
                "last_selected": ["A"],
                "last_correct": True,
                "last_confidence": "Unsure",
                "last_miss_reason": "",
                "flagged": False,
                "suspended": True,
                "learner_memory": {"retrievability": 0.6, "stability": 8.0},
                "smart_primary_role": "due_retention",
                "smart_utility": 4.0,
                "smart_selection_reasons": ["retention"],
            },
        }
        history = [
            {
                "question_id": self.qids[0],
                "question_content_fingerprint": question_content_fingerprint(self.source_by_id[self.qids[0]]),
                "selected_texts": [self.source_by_id[self.qids[0]]["choices"]["B"]],
                "correct_texts": [
                    self.source_by_id[self.qids[0]]["choices"][self.source_by_id[self.qids[0]]["correct"][0]]
                ],
                "correct": False,
            }
        ]
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": self.revision.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                qid: question_content_fingerprint(self.source_by_id[qid]) for qid in self.qids
            },
            "questions": copy.deepcopy(records),
            "history": copy.deepcopy(history),
            "meta": {"session_history": [{"id": "session-1"}]},
        }

    def _session_snapshot(self):
        first = self.source_by_id[self.qids[0]]
        second = self.source_by_id[self.qids[1]]
        history_event = {
            "question_id": self.qids[0],
            "question_number": first["question_number"],
            "question_content_fingerprint": question_content_fingerprint(first),
            "selected_texts": [first["choices"]["B"]],
            "correct_texts": [first["choices"][first["correct"][0]]],
            "correct": False,
        }
        return build_session_snapshot(
            app_version="test",
            bank_file=SOURCE_PATH.name,
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
            question_numbers=[first["question_number"], second["question_number"]],
            restore_question_numbers=[first["question_number"], second["question_number"]],
            bank_fingerprint=self.revision.source_bank_content_fingerprint,
            question_ids=list(self.qids),
            restore_question_ids=list(self.qids),
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
            session_boss_markers=[2],
            session_stealth_markers=[1],
            session_xp_gained=7,
            answers=[
                _answer(selected=["B"], pending=["B"], answered=True, flagged=True),
                _answer(selected=["C"], pending=["C"], answered=False),
            ],
        )

    def test_expl_020_progress_continuity_preserved(self):
        payload = self._progress_payload()
        original_records = copy.deepcopy(payload["questions"])
        result = migrate_explanation_progress_payload(
            payload, self.target_questions, self.revision, "2026-09-21T10:00:00"
        )
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        self.assertEqual(original_records, result.payload["questions"])
        self.assertEqual(self.revision.target_bank_content_fingerprint, result.payload["bank_fingerprint"])

    def test_expl_021_session_continuity_preserved(self):
        saved = self._session_snapshot()
        result = migrate_explanation_session_payload(
            saved,
            self.target_questions,
            self.revision,
            TARGET_PATH.name,
            source_questions=self.source_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        for field in (
            "current_index",
            "elapsed_seconds",
            "exam_reveal",
            "checkpoints_saved",
            "session_rewards",
            "unlocked_rewards",
            "session_answer_history",
            "quest_completion_keys",
            "session_boss_markers",
            "session_stealth_markers",
            "session_xp_gained",
        ):
            self.assertEqual(saved[field], result.payload[field], field)

    def test_expl_022_selected_and_pending_state_preserved(self):
        saved = self._session_snapshot()
        result = migrate_explanation_session_payload(
            saved, self.target_questions, self.revision, TARGET_PATH.name, source_questions=self.source_questions
        )
        self.assertEqual(saved["answers"], result.payload["answers"])

    def test_expl_023_historical_attempts_and_fingerprints_preserved(self):
        payload = self._progress_payload()
        original_history = copy.deepcopy(payload["history"])
        old_fp = original_history[0]["question_content_fingerprint"]
        result = migrate_explanation_progress_payload(
            payload, self.target_questions, self.revision, "2026-09-21T10:00:00"
        )
        self.assertEqual(original_history, result.payload["history"])
        self.assertEqual(old_fp, result.payload["history"][0]["question_content_fingerprint"])
        self.assertTrue(
            history_event_matches_explanation_revision(
                result.payload["history"][0],
                self.target_by_id[self.qids[0]],
                self.revision,
            )
        )
        mapped = canonical_question_history_map(result.payload["history"])
        self.assertEqual(1, len(mapped[self.qids[0]]))

    def test_expl_024_smart_practice_and_learner_state_preserved(self):
        payload = self._progress_payload()
        result = migrate_explanation_progress_payload(
            payload, self.target_questions, self.revision, "2026-09-21T10:00:00"
        )
        for qid in self.qids:
            for field in (
                "attempts",
                "correct_count",
                "wrong_count",
                "correct_streak",
                "next_review",
                "last_confidence",
                "last_miss_reason",
                "flagged",
                "suspended",
                "learner_memory",
                "smart_primary_role",
                "smart_utility",
                "smart_selection_reasons",
            ):
                self.assertEqual(payload["questions"][qid][field], result.payload["questions"][qid][field])

    def test_expl_043_explanation_migration_preserves_pending_state(self):
        saved = self._session_snapshot()
        before = copy.deepcopy(saved["answers"][1])
        self.assertFalse(before["answered"])
        self.assertEqual(["C"], before["selected"])
        self.assertEqual(["C"], before["pending"])
        result = migrate_explanation_session_payload(
            saved, self.target_questions, self.revision, TARGET_PATH.name, source_questions=self.source_questions
        )
        self.assertEqual(before, result.payload["answers"][1])


if __name__ == "__main__":
    unittest.main()
