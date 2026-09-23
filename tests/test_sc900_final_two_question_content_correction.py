from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app_constants import MODE_PRACTICE
from content_revision_authority import AdmissionStatus, sha256_file
from content_revision_correction_migration import (
    migrate_correction_progress_payload,
    migrate_correction_session_payload,
)
from content_revision_final_correction_authority import (
    EXPECTED_SOURCE_BANK_SHA256,
    EXPECTED_SOURCE_CONTENT_FINGERPRINT,
    SOURCE_BANK_FILENAME,
    TARGET_BANK_FILENAME,
    TARGET_IDS,
    admit_final_content_correction,
)
from progress_store import default_progress_record
from question_identity import bank_content_fingerprint, question_content_fingerprint
from session_store import build_session_snapshot
from tools.build_sc900_final_two_question_content_correction import (
    CURRENTNESS_FILENAME,
    MANIFEST_FILENAME,
    SPEC_FILENAME,
    build_final_two_question_content_correction,
)

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TARGET_SHA256 = "f97f76591ebb41dd1b92ca5623c6f040b2d9a75ca6f7f1d5b0ebd9adf371581f"
EXPECTED_TARGET_FINGERPRINT = "76a2ca2d8779e6e0b422f9192868e19ac1f7e0e0543e555a80a8dde9be14f407"
EXPECTED_MANIFEST_SHA256 = "3e62c4a195d2fe8961b29d98694a184a6f4c2a2265da20602f4cd09819f51345"
MIGRATED_AT = "2026-09-23T01:00:00Z"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _progress_record(**overrides):
    record = default_progress_record()
    record.update(overrides)
    return record


def _answer(question_id: str, selected: list[str], answered: bool, flagged: bool = False):
    return {
        "question_id": question_id,
        "selected": list(selected),
        "pending": list(selected),
        "answered": answered,
        "flagged": flagged,
        "suspended": False,
        "last_confidence": "Sure" if answered else "",
        "last_miss_reason": "forgot" if answered else "",
        "last_recall_failure": "",
        "answer_event_id": "evt" if answered else "",
        "recall_ready": answered,
        "session_tag": "smart",
        "smart_primary_role": "repair",
        "smart_selection_reasons": ["weak"],
        "smart_utility": 1.0,
        "smart_utility_breakdown": {},
        "smart_policy_version": "1",
        "smart_policy_id": "p1",
        "smart_concept_key": "concept",
        "smart_root_cause": "gap",
        "smart_root_cause_confidence": 0.4,
        "smart_supporting_concepts": [],
        "smart_graph_version": "g1",
        "smart_information_value": 0.2,
        "smart_information_breakdown": {},
        "smart_question_quality_status": "ok",
        "smart_question_quality_confidence": 0.1,
        "smart_graph_bottleneck": 0.0,
        "repair_stage": "contrast",
        "repair_concept_key": "concept",
        "legacy_repair_concept_key": "",
        "prediction_id": "pred" if answered else "",
        "prediction_snapshot": {"prediction_id": "pred"} if answered else {},
    }


class FinalTwoQuestionContentCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_path = ROOT / SOURCE_BANK_FILENAME
        cls.target_path = ROOT / TARGET_BANK_FILENAME
        cls.spec_path = ROOT / "content_revision_evidence" / "specs" / SPEC_FILENAME
        cls.currentness_path = ROOT / "content_revision_evidence" / "currentness" / CURRENTNESS_FILENAME
        cls.manifest_path = ROOT / "content_revision_evidence" / "manifests" / MANIFEST_FILENAME
        cls.review_root = ROOT / "content_revision_evidence" / "reviews"
        cls.source = _read(cls.source_path)
        cls.target = _read(cls.target_path)
        cls.spec = _read(cls.spec_path)
        cls.currentness = _read(cls.currentness_path)
        cls.manifest = _read(cls.manifest_path)
        cls.source_by_id = {q["id"]: q for q in cls.source["questions"]}
        cls.target_by_id = {q["id"]: q for q in cls.target["questions"]}
        cls.unchanged_id = next(qid for qid in cls.source_by_id if qid not in TARGET_IDS)
        cls.admission = admit_final_content_correction(
            cls.manifest,
            spec=cls.spec,
            currentness_record=cls.currentness,
            source_bank_path=cls.source_path,
            target_bank_path=cls.target_path,
            spec_path=cls.spec_path,
            currentness_path=cls.currentness_path,
            review_root=cls.review_root,
        )
        assert cls.admission.admitted is not None
        cls.revision = cls.admission.admitted

    def _progress_payload(self):
        ids = [*TARGET_IDS, self.unchanged_id]
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": self.revision.source_bank_content_fingerprint,
            "question_content_fingerprints": {qid: question_content_fingerprint(self.source_by_id[qid]) for qid in ids},
            "questions": {
                TARGET_IDS[0]: _progress_record(attempts=4, flagged=True),
                TARGET_IDS[1]: _progress_record(attempts=3, suspended=True),
                self.unchanged_id: _progress_record(attempts=7),
            },
            "history": [
                {"question_id": TARGET_IDS[0], "question_number": self.source_by_id[TARGET_IDS[0]]["question_number"]},
                {"question_id": TARGET_IDS[1], "question_number": self.source_by_id[TARGET_IDS[1]]["question_number"]},
                {
                    "question_id": self.unchanged_id,
                    "question_number": self.source_by_id[self.unchanged_id]["question_number"],
                },
            ],
        }

    def _session_snapshot(self):
        ids = [*TARGET_IDS, self.unchanged_id]
        numbers = [self.source_by_id[qid]["question_number"] for qid in ids]
        return build_session_snapshot(
            app_version="test",
            bank_file=SOURCE_BANK_FILENAME,
            mode=MODE_PRACTICE,
            builder_context={
                "mode": MODE_PRACTICE,
                "count": str(len(ids)),
                "source_label": "Full bank",
                "session_source": "",
                "randomize": False,
                "domain_filter": "All domains",
                "topic_filter": "All topics",
                "status_filter": "All questions",
            },
            source_label="Full bank",
            question_numbers=numbers,
            restore_question_numbers=numbers,
            bank_fingerprint=self.revision.source_bank_content_fingerprint,
            question_ids=ids,
            restore_question_ids=ids,
            session_base_question_count=len(ids),
            session_question_limit=len(ids),
            current_index=0,
            elapsed_seconds=42,
            exam_reveal=True,
            checkpoints_saved=[],
            session_rewards=[],
            unlocked_rewards=[],
            session_answer_history=[
                {"question_id": TARGET_IDS[0], "question_number": numbers[0], "correct": True},
                {"question_id": self.unchanged_id, "question_number": numbers[2], "correct": False},
            ],
            current_quests=[],
            quest_completion_keys=[],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=0,
            answers=[
                _answer(TARGET_IDS[0], ["D"], True, flagged=True),
                _answer(TARGET_IDS[1], ["A"], True),
                _answer(self.unchanged_id, ["B"], True),
            ],
        )

    def test_authority_and_frozen_identity(self):
        self.assertEqual(AdmissionStatus.PASS, self.admission.status)
        self.assertEqual(EXPECTED_SOURCE_BANK_SHA256, sha256_file(self.source_path))
        self.assertEqual(EXPECTED_SOURCE_CONTENT_FINGERPRINT, bank_content_fingerprint(self.source["questions"]))
        self.assertEqual(EXPECTED_TARGET_SHA256, sha256_file(self.target_path))
        self.assertEqual(EXPECTED_TARGET_FINGERPRINT, bank_content_fingerprint(self.target["questions"]))
        self.assertEqual(EXPECTED_MANIFEST_SHA256, self.manifest["payload_sha256"])

    def test_deterministic_rebuild(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copy2(self.source_path, root / SOURCE_BANK_FILENAME)
            result = build_final_two_question_content_correction(root)
            self.assertEqual(EXPECTED_TARGET_SHA256, result["target_sha256"])
            self.assertEqual(EXPECTED_TARGET_FINGERPRINT, result["target_content_fingerprint"])
            self.assertEqual(EXPECTED_MANIFEST_SHA256, result["manifest_sha256"])

    def test_exact_two_changed_questions_and_protected_fields(self):
        changed = [qid for qid in self.source_by_id if self.source_by_id[qid] != self.target_by_id[qid]]
        self.assertEqual(list(TARGET_IDS), changed)
        self.assertEqual(454, len(self.target["questions"]))
        for qid in TARGET_IDS:
            before = self.source_by_id[qid]
            after = self.target_by_id[qid]
            self.assertEqual(before["prompt"], after["prompt"])
            self.assertEqual(before["correct"], after["correct"])
            self.assertEqual(before["objective_code"], after["objective_code"])
            self.assertEqual(before["tested_decision"], after["tested_decision"])

    def test_p2_q001_duplicate_correct_answer_removed(self):
        q = self.target_by_id["sc900_p2_q001"]
        self.assertEqual(["B"], q["correct"])
        self.assertEqual("Encryption", q["choices"]["B"])
        self.assertEqual("Encoding", q["choices"]["D"])
        self.assertEqual(4, len({value.casefold() for value in q["choices"].values()}))
        self.assertIn("does not provide confidentiality", q["choice_explanations"]["D"])

    def test_p3_q071_duplicate_correct_answer_removed(self):
        q = self.target_by_id["sc900_p3_q071"]
        self.assertEqual(["C"], q["correct"])
        self.assertEqual("Hashing", q["choices"]["C"])
        self.assertEqual("Encoding", q["choices"]["A"])
        self.assertEqual(4, len({value.casefold() for value in q["choices"].values()}))
        self.assertIn("not designed to produce an integrity check value", q["choice_explanations"]["A"])

    def test_progress_resets_exactly_affected_ids_and_quarantines_history(self):
        result = migrate_correction_progress_payload(
            self._progress_payload(), self.target["questions"], self.revision, MIGRATED_AT
        )
        self.assertEqual(0, result.payload["questions"][TARGET_IDS[0]]["attempts"])
        self.assertTrue(result.payload["questions"][TARGET_IDS[0]]["flagged"])
        self.assertEqual(0, result.payload["questions"][TARGET_IDS[1]]["attempts"])
        self.assertTrue(result.payload["questions"][TARGET_IDS[1]]["suspended"])
        self.assertEqual(7, result.payload["questions"][self.unchanged_id]["attempts"])
        self.assertEqual([self.unchanged_id], [row["question_id"] for row in result.payload["history"]])
        self.assertEqual(set(TARGET_IDS), {row["question_id"] for row in result.payload["quarantined_history"]})

    def test_session_answers_reset_exactly_affected_ids(self):
        result = migrate_correction_session_payload(
            self._session_snapshot(),
            self.target["questions"],
            self.revision,
            TARGET_BANK_FILENAME,
            source_questions=self.source["questions"],
        )
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        for qid in TARGET_IDS:
            self.assertEqual([], answers[qid]["selected"])
            self.assertEqual([], answers[qid]["pending"])
            self.assertFalse(answers[qid]["answered"])
        self.assertTrue(answers[TARGET_IDS[0]]["flagged"])
        self.assertEqual(["B"], answers[self.unchanged_id]["selected"])
        self.assertTrue(answers[self.unchanged_id]["answered"])
        self.assertEqual([self.unchanged_id], [row["question_id"] for row in result.payload["session_answer_history"]])

    def test_cand_protocol_frozen(self):
        from cand01r3_protocol import build_protocol, protocol_sha256

        self.assertEqual(
            "51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72",
            protocol_sha256(build_protocol()),
        )

    def test_currentness_and_review_evidence(self):
        self.assertEqual("PASS", self.currentness["overall_status"])
        self.assertEqual(list(TARGET_IDS), [row["question_id"] for row in self.currentness["targets"]])
        for edge in self.manifest["edges"]:
            review = self.review_root / edge["review_artifact"]
            self.assertTrue(review.exists())
            self.assertEqual(edge["review_artifact_sha256"], sha256_file(review))


if __name__ == "__main__":
    unittest.main()
