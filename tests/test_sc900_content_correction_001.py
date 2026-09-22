from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import patch

from answer_length_audit import audit_questions
from app_constants import MODE_PRACTICE
from content_revision_authority import AdmissionStatus, admit_content_revision, sha256_file
from content_revision_correction_authority import (
    CURRENTNESS_REQUIREMENTS,
    EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256,
    EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256,
    EXPECTED_SOURCE_BANK_SHA256,
    EXPECTED_SOURCE_CONTENT_FINGERPRINT,
    EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256,
    PERMITTED_CHANGE_CLASS,
    PROMPT_CHANGED_IDS,
    Q219_REPLACEMENT_WORK_ID,
    Q219_TESTED_DECISION,
    REQUIRED_QUESTION_COUNT,
    SOURCE_BANK_FILENAME,
    SOURCE_VALIDATION_WORK_ID,
    TARGET_BANK_FILENAME,
    TARGET_IDS,
    CorrectionFailureReason,
    admit_content_correction,
)
from content_revision_correction_migration import (
    ContentCorrectionMigrationError,
    migrate_correction_progress_payload,
    migrate_correction_session_payload,
)
from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    migrate_progress_payload,
)
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS
from progress_store import default_progress_record
from question_identity import question_content_fingerprint
from session_store import build_session_snapshot
from tools.build_sc900_content_correction_001 import (
    CORRECTION_SPEC_RELATIVE_PATH,
    CURRENTNESS_RECORD_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATH,
    REVIEW_DIRECTORY,
    SEMANTIC_TARGETS,
    T5_MANIFEST_RELATIVE_PATH,
    ContentCorrectionBuildError,
    build_sc900_content_correction_001,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
HISTORICAL_PATHS = (
    "sc900_bank_v8_length_rebalanced_t1.json",
    "sc900_bank_v8_length_rebalanced_t2.json",
    "sc900_bank_v8_length_rebalanced_t3.json",
    "sc900_bank_v8_length_rebalanced_t4.json",
    "sc900_bank_v8_length_rebalanced_t5.json",
    "content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json",
    "content_revision_evidence/manifests/sc900_answer_length_rebalance_t2.json",
    "content_revision_evidence/manifests/sc900_answer_length_rebalance_t3.json",
    "content_revision_evidence/manifests/sc900_answer_length_rebalance_t4.json",
    "content_revision_evidence/manifests/sc900_answer_length_rebalance_t5.json",
)
MIGRATED_AT = "2026-09-20T18:00:00Z"
CHOICE_LABELS = ("A", "B", "C", "D")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _progress_record(**overrides: Any) -> dict[str, Any]:
    record = default_progress_record()
    record.update(overrides)
    return record


def _session_answer(*, selected=None, pending=None, answered=False, flagged=False, suspended=False) -> dict[str, Any]:
    return {
        "selected": list(selected or []),
        "pending": list(pending if pending is not None else selected or []),
        "answered": answered,
        "flagged": flagged,
        "suspended": suspended,
        "last_confidence": "Sure" if answered else "",
        "last_miss_reason": "forgot" if answered else "",
        "last_recall_failure": "",
        "answer_event_id": "evt-1" if answered else "",
        "recall_ready": True if answered else False,
        "session_tag": "smart",
        "smart_primary_role": "repair",
        "smart_selection_reasons": ["weak"],
        "smart_utility": 1.0,
        "smart_utility_breakdown": {"x": 1.0},
        "smart_policy_version": "1",
        "smart_policy_id": "p1",
        "smart_concept_key": "concept",
        "smart_root_cause": "gap",
        "smart_root_cause_confidence": 0.4,
        "smart_supporting_concepts": ["c2"],
        "smart_graph_version": "g1",
        "smart_information_value": 0.2,
        "smart_information_breakdown": {},
        "smart_question_quality_status": "ok",
        "smart_question_quality_confidence": 0.1,
        "smart_graph_bottleneck": 0.0,
        "repair_stage": "contrast",
        "repair_concept_key": "concept",
        "legacy_repair_concept_key": "",
        "prediction_id": "pred-1",
        "prediction_snapshot": {"prediction_id": "pred-1"},
    }


class ContentCorrectionIsolatedBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        root = Path(cls.temp_dir.name)
        cls.source_path = root / SOURCE_BANK_FILENAME
        shutil.copy2(REPOSITORY_ROOT / SOURCE_BANK_FILENAME, cls.source_path)
        t5_manifest_src = REPOSITORY_ROOT / T5_MANIFEST_RELATIVE_PATH
        t5_manifest_dst = root / T5_MANIFEST_RELATIVE_PATH
        t5_manifest_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(t5_manifest_src, t5_manifest_dst)
        cls.candidate_path = root / TARGET_BANK_FILENAME
        cls.spec_path = root / "sc900_content_correction_001.json"
        cls.currentness_path = root / "sc900_content_correction_001_currentness.json"
        cls.review_root = root / "reviews"
        cls.manifest_path = root / "sc900_content_correction_001_manifest.json"
        cls.build = build_sc900_content_correction_001(
            cls.source_path,
            cls.candidate_path,
            cls.spec_path,
            cls.currentness_path,
            cls.review_root,
            cls.manifest_path,
        )
        cls.source = _read_json(cls.source_path)
        cls.candidate = _read_json(cls.candidate_path)
        cls.spec = _read_json(cls.spec_path)
        cls.currentness = _read_json(cls.currentness_path)
        cls.manifest = _read_json(cls.manifest_path)
        cls.source_questions = cls.source["questions"]
        cls.candidate_questions = cls.candidate["questions"]
        cls.source_by_id = {question["id"]: question for question in cls.source_questions}
        cls.candidate_by_id = {question["id"]: question for question in cls.candidate_questions}
        cls.admission = admit_content_correction(
            cls.manifest,
            spec=cls.spec,
            currentness_record=cls.currentness,
            source_bank_path=cls.source_path,
            target_bank_path=cls.candidate_path,
            spec_path=cls.spec_path,
            currentness_path=cls.currentness_path,
            review_root=cls.review_root,
        )
        assert cls.admission.admitted is not None
        cls.revision = cls.admission.admitted
        cls.unchanged_id = next(qid for qid in cls.source_by_id if qid not in TARGET_IDS)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def _progress_payload(
        self, records: dict[str, dict[str, Any]], history: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        fingerprints = {
            question_id: question_content_fingerprint(self.source_by_id[question_id]) for question_id in records
        }
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": self.revision.source_bank_content_fingerprint,
            "question_content_fingerprints": fingerprints,
            "questions": records,
            "history": list(history or []),
        }

    def _session_snapshot(self, rows: list[tuple[str, dict[str, Any]]], history: list[dict[str, Any]] | None = None):
        question_ids = [question_id for question_id, _answer in rows]
        numbers = [int(self.source_by_id[question_id]["question_number"]) for question_id in question_ids]
        return build_session_snapshot(
            app_version="test",
            bank_file=SOURCE_BANK_FILENAME,
            mode=MODE_PRACTICE,
            builder_context={
                "mode": MODE_PRACTICE,
                "count": str(len(question_ids)),
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
            question_ids=question_ids,
            restore_question_ids=question_ids,
            session_base_question_count=len(question_ids),
            session_question_limit=len(question_ids),
            current_index=0,
            elapsed_seconds=42,
            exam_reveal=True,
            checkpoints_saved=["cp1"],
            session_rewards=["r1"],
            unlocked_rewards=["u1"],
            session_answer_history=list(history or []),
            current_quests=[],
            quest_completion_keys=["q1"],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=7,
            answers=[{"question_id": question_id, **answer} for question_id, answer in rows],
        )

    def test_cc_a01_wrong_source_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            tampered = Path(temp) / SOURCE_BANK_FILENAME
            tampered.write_bytes(self.source_path.read_bytes() + b"\n")
            with self.assertRaises(ContentCorrectionBuildError) as caught:
                build_sc900_content_correction_001(
                    tampered,
                    Path(temp) / TARGET_BANK_FILENAME,
                    Path(temp) / "spec.json",
                    Path(temp) / "currentness.json",
                    Path(temp) / "reviews",
                    Path(temp) / "manifest.json",
                )
            self.assertIn("SOURCE_FILE_HASH_MISMATCH", str(caught.exception))

    def test_cc_a02_wrong_source_fingerprint(self) -> None:
        with patch(
            "tools.build_sc900_content_correction_001.bank_content_fingerprint",
            return_value="0" * 64,
        ):
            with tempfile.TemporaryDirectory() as temp:
                source = Path(temp) / SOURCE_BANK_FILENAME
                shutil.copy2(self.source_path, source)
                with self.assertRaises(ContentCorrectionBuildError) as caught:
                    build_sc900_content_correction_001(
                        source,
                        Path(temp) / TARGET_BANK_FILENAME,
                        Path(temp) / "spec.json",
                        Path(temp) / "currentness.json",
                        Path(temp) / "reviews",
                        Path(temp) / "manifest.json",
                    )
                self.assertIn("SOURCE_CONTENT_FINGERPRINT_MISMATCH", str(caught.exception))

    def test_cc_a06_spec_hash(self) -> None:
        self.assertEqual(EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256, self.spec["payload_sha256"])
        self.assertNotIn("correction_class", json.dumps(self.spec))

    def test_cc_a07_currentness_enforced(self) -> None:
        self.assertEqual(CURRENTNESS_REQUIREMENTS, self.spec["currentness_requirements"])
        self.assertEqual(EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256, self.currentness["payload_sha256"])
        self.assertEqual("PASS", self.currentness["overall_status"])
        mutated = copy.deepcopy(self.currentness)
        mutated["overall_status"] = "FAIL"
        result = admit_content_correction(
            self.manifest,
            spec=self.spec,
            currentness_record=mutated,
            source_bank_path=self.source_path,
            target_bank_path=self.candidate_path,
            spec_path=self.spec_path,
            currentness_path=self.currentness_path,
            review_root=self.review_root,
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)
        self.assertIn(CorrectionFailureReason.CURRENTNESS_GATE_FAILED, result.reasons)

    def test_cc_a08_v1_rejects_semantic_correction(self) -> None:
        result = admit_content_revision(
            self.manifest,
            source_questions=self.source_questions,
            target_questions=self.candidate_questions,
            source_bank_path=self.source_path,
            target_bank_path=self.candidate_path,
            review_root=self.review_root,
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_cc_a09_v1_revision_rejected_by_v2_migration(self) -> None:
        t5_manifest = _read_json(REPOSITORY_ROOT / T5_MANIFEST_RELATIVE_PATH)
        t5_bank = REPOSITORY_ROOT / SOURCE_BANK_FILENAME
        t4_bank = REPOSITORY_ROOT / "sc900_bank_v8_length_rebalanced_t4.json"
        v1 = admit_content_revision(
            t5_manifest,
            source_questions=_read_json(t4_bank)["questions"],
            target_questions=self.source_questions,
            source_bank_path=t4_bank,
            target_bank_path=t5_bank,
            review_root=REPOSITORY_ROOT / "content_revision_evidence" / "reviews",
        )
        self.assertEqual(AdmissionStatus.PASS, v1.status)
        assert v1.admitted is not None
        payload = self._progress_payload({self.unchanged_id: _progress_record()})
        with self.assertRaises(ContentCorrectionMigrationError) as caught:
            migrate_correction_progress_payload(payload, self.candidate_questions, v1.admitted, MIGRATED_AT)
        self.assertEqual(CorrectionFailureReason.AUTHORITY_KIND_MISMATCH, caught.exception.reason)

    def test_cc_a10_v2_revision_rejected_by_v1_migration(self) -> None:
        payload = self._progress_payload({TARGET_IDS[0]: _progress_record()})
        with self.assertRaises(ContentRevisionMigrationError) as caught:
            migrate_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        self.assertEqual(MigrationFailureReason.AUTHORITY_KIND_MISMATCH, caught.exception.reason)

    def test_cc_b01_exact_nine_changed_ids(self) -> None:
        changed = [qid for qid, source in self.source_by_id.items() if source != self.candidate_by_id[qid]]
        self.assertEqual(set(TARGET_IDS), set(changed))
        self.assertEqual(9, len(changed))

    def test_cc_b02_field_matrix(self) -> None:
        prompt_changed = [
            qid for qid in TARGET_IDS if self.source_by_id[qid]["prompt"] != self.candidate_by_id[qid]["prompt"]
        ]
        self.assertEqual(list(PROMPT_CHANGED_IDS), prompt_changed)
        self.assertEqual(6, len(prompt_changed))
        self.assertEqual(
            9, sum(self.source_by_id[qid]["choices"] != self.candidate_by_id[qid]["choices"] for qid in TARGET_IDS)
        )
        self.assertEqual(
            9,
            sum(
                self.source_by_id[qid]["general_explanation"] != self.candidate_by_id[qid]["general_explanation"]
                for qid in TARGET_IDS
            ),
        )
        self.assertEqual(
            9,
            sum(
                self.source_by_id[qid]["choice_explanations"] != self.candidate_by_id[qid]["choice_explanations"]
                for qid in TARGET_IDS
            ),
        )

    def test_cc_b03_protected_semantics(self) -> None:
        for question_id in TARGET_IDS:
            source = self.source_by_id[question_id]
            target = self.candidate_by_id[question_id]
            self.assertEqual(source["correct"], target["correct"])
            self.assertEqual(source["objective_code"], target["objective_code"])
            self.assertEqual(source["subobjective"], target["subobjective"])
            self.assertEqual(source["tested_decision"], target["tested_decision"])
        self.assertEqual(Q219_TESTED_DECISION, self.candidate_by_id["sc900_mlc_q219"]["tested_decision"])

    def test_cc_b04_explicit_explanations(self) -> None:
        for question_id in TARGET_IDS:
            explanation = SEMANTIC_TARGETS[question_id]["explanation"]
            target = self.candidate_by_id[question_id]
            self.assertEqual(explanation, target["general_explanation"])
            for letter in CHOICE_LABELS:
                self.assertEqual(explanation, target["choice_explanations"][letter])

    def test_cc_b08_provenance(self) -> None:
        self.assertEqual(9, len(self.manifest["edges"]))
        self.assertEqual(9, self.build["receipt_count"])
        for edge in self.manifest["edges"]:
            self.assertNotIn("correction_class", edge)
            self.assertNotIn("choice_semantics", edge)
            self.assertTrue(edge["authority_refs"])
            receipt = _read_json(self.review_root / edge["review_artifact"])
            self.assertNotIn("correction_class", receipt)
            self.assertEqual(edge["review_artifact_sha256"], sha256_file(self.review_root / edge["review_artifact"]))
        q219 = next(entry for entry in self.spec["corrections"] if entry["question_id"] == "sc900_mlc_q219")
        self.assertEqual(Q219_REPLACEMENT_WORK_ID, q219["semantic_validation_work_id"])
        self.assertIn("earlier on-premises synchronization", self.candidate_by_id["sc900_mlc_q219"]["prompt"])
        self.assertNotIn("computer objects", self.candidate_by_id["sc900_mlc_q219"]["prompt"].casefold())
        for entry in self.spec["corrections"]:
            if entry["question_id"] != "sc900_mlc_q219":
                self.assertEqual(SOURCE_VALIDATION_WORK_ID, entry["semantic_validation_work_id"])

    def test_cc_p01_missing_target_progress_not_created(self) -> None:
        payload = self._progress_payload({self.unchanged_id: _progress_record(attempts=3)})
        result = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        self.assertNotIn(TARGET_IDS[0], result.payload["questions"])
        self.assertEqual(3, result.payload["questions"][self.unchanged_id]["attempts"])

    def test_cc_p02_existing_target_progress_reset(self) -> None:
        payload = self._progress_payload({TARGET_IDS[0]: _progress_record(attempts=4, flagged=True, suspended=True)})
        result = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        record = result.payload["questions"][TARGET_IDS[0]]
        self.assertEqual(0, record["attempts"])
        self.assertTrue(record["flagged"])
        self.assertTrue(record["suspended"])

    def test_cc_p04_history_quarantined(self) -> None:
        event = {
            "question_id": TARGET_IDS[0],
            "question_number": self.source_by_id[TARGET_IDS[0]]["question_number"],
            "question_content_fingerprint": question_content_fingerprint(self.source_by_id[TARGET_IDS[0]]),
            "correct": True,
        }
        unrelated = {
            "question_id": self.unchanged_id,
            "question_number": self.source_by_id[self.unchanged_id]["question_number"],
            "question_content_fingerprint": question_content_fingerprint(self.source_by_id[self.unchanged_id]),
            "correct": False,
        }
        payload = self._progress_payload(
            {TARGET_IDS[0]: _progress_record(), self.unchanged_id: _progress_record()},
            [event, unrelated],
        )
        result = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        self.assertEqual([unrelated], result.payload["history"])
        self.assertEqual([event], result.payload["quarantined_history"])

    def test_cc_p06_legacy_no_fingerprint_history_quarantined(self) -> None:
        event = {
            "question_id": TARGET_IDS[1],
            "question_number": self.source_by_id[TARGET_IDS[1]]["question_number"],
            "correct": True,
        }
        payload = self._progress_payload({TARGET_IDS[1]: _progress_record()}, [event])
        result = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        self.assertEqual([], result.payload["history"])
        self.assertEqual([event], result.payload["quarantined_history"])

    def test_cc_p07_adaptive_reconciliation(self) -> None:
        target_id = TARGET_IDS[0]
        target_number = int(self.source_by_id[target_id]["question_number"])
        payload = self._progress_payload({target_id: _progress_record()})
        payload["meta"] = {
            "xp": 40,
            "repair_state": {
                "keep": {"last_question_id": self.unchanged_id, "status": "open"},
                "drop": {"last_question_id": target_id, "last_question_number": target_number, "status": "open"},
            },
            "smart_practice_policy_governance": {"active": True},
            "smart_practice_measurement": {
                "predictions": {
                    "drop": {"prediction_id": "drop", "question_number": target_number, "question_id": target_id},
                    "keep": {
                        "prediction_id": "keep",
                        "question_number": int(self.source_by_id[self.unchanged_id]["question_number"]),
                    },
                },
                "outcome_links": {"drop": {}, "keep": {}},
                "measurement_reports": [{"stale": True}],
                "calibration_recommendations": ["stale"],
                "active_policy": {"policy_version": "keep-me"},
            },
            "smart_practice_question_calibration": {
                "question_quality": {str(target_number): {"question_id": target_id, "question_number": target_number}},
                "information_value_history": {target_id: {"value": 1}},
                "edge_calibration": {"old": True},
                "graph_audits": {"old": True},
            },
            "smart_practice_concept_graph": {
                "concepts": {"c1": {"label": "static"}},
                "edges": {},
                "diagnoses": {
                    "d1": {"question_id": target_id, "evidence": target_id},
                    "d2": {"question_id": self.unchanged_id},
                },
            },
        }
        result = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        meta = result.payload["meta"]
        self.assertEqual(40, meta["xp"])
        self.assertIn("keep", meta["repair_state"])
        self.assertNotIn("drop", meta["repair_state"])
        self.assertEqual({"active": True}, meta["smart_practice_policy_governance"])
        self.assertEqual({"policy_version": "keep-me"}, meta["smart_practice_measurement"]["active_policy"])
        self.assertNotIn("drop", meta["smart_practice_measurement"]["predictions"])
        self.assertIn("keep", meta["smart_practice_measurement"]["predictions"])
        self.assertEqual({"c1": {"label": "static"}}, meta["smart_practice_concept_graph"]["concepts"])
        self.assertNotIn("d1", meta["smart_practice_concept_graph"]["diagnoses"])
        self.assertIn("d2", meta["smart_practice_concept_graph"]["diagnoses"])

    def test_cc_s01_answered_target_reset(self) -> None:
        snapshot = self._session_snapshot(
            [
                (TARGET_IDS[0], _session_answer(selected=["A"], answered=True, flagged=True)),
                (self.unchanged_id, _session_answer(selected=["B"], answered=True)),
            ],
            history=[
                {
                    "question_id": TARGET_IDS[0],
                    "question_number": self.source_by_id[TARGET_IDS[0]]["question_number"],
                    "correct": True,
                }
            ],
        )
        result = migrate_correction_session_payload(
            snapshot,
            self.candidate_questions,
            self.revision,
            TARGET_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        self.assertEqual([], answers[TARGET_IDS[0]]["selected"])
        self.assertFalse(answers[TARGET_IDS[0]]["answered"])
        self.assertTrue(answers[TARGET_IDS[0]]["flagged"])
        self.assertEqual("", answers[TARGET_IDS[0]]["prediction_id"])
        self.assertEqual(["B"], answers[self.unchanged_id]["selected"])
        self.assertEqual([], result.payload["session_answer_history"])

    def test_cc_m01_older_lineage_rejected(self) -> None:
        payload = self._progress_payload({TARGET_IDS[0]: _progress_record()})
        payload["bank_fingerprint"] = "t3-not-t5" + "0" * 53
        with self.assertRaises(ContentCorrectionMigrationError) as caught:
            migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        self.assertEqual(MigrationFailureReason.SOURCE_BANK_MISMATCH, caught.exception.reason)

    def test_cc_m02_idempotent_retry(self) -> None:
        payload = self._progress_payload({TARGET_IDS[0]: _progress_record(attempts=5, flagged=True)})
        first = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        first.payload["questions"][TARGET_IDS[0]]["attempts"] = 2
        second = migrate_correction_progress_payload(
            first.payload, self.candidate_questions, self.revision, MIGRATED_AT
        )
        self.assertEqual(MigrationStatus.MIGRATION_ALREADY_APPLIED, second.status)
        self.assertEqual(2, second.payload["questions"][TARGET_IDS[0]]["attempts"])

    def test_cc_m03_tamper_rejected(self) -> None:
        payload = self._progress_payload({TARGET_IDS[0]: _progress_record()})
        first = migrate_correction_progress_payload(payload, self.candidate_questions, self.revision, MIGRATED_AT)
        first.payload["question_content_fingerprints"][TARGET_IDS[0]] = "e" * 64
        with self.assertRaises(ContentCorrectionMigrationError):
            migrate_correction_progress_payload(first.payload, self.candidate_questions, self.revision, MIGRATED_AT)

    def test_cc_b07_two_isolated_builds(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            outputs = []
            for directory in (first_dir, second_dir):
                root = Path(directory)
                source = root / SOURCE_BANK_FILENAME
                shutil.copy2(self.source_path, source)
                t5 = root / T5_MANIFEST_RELATIVE_PATH
                t5.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPOSITORY_ROOT / T5_MANIFEST_RELATIVE_PATH, t5)
                result = build_sc900_content_correction_001(
                    source,
                    root / TARGET_BANK_FILENAME,
                    root / "spec.json",
                    root / "currentness.json",
                    root / "reviews",
                    root / "manifest.json",
                )
                outputs.append(
                    (
                        sha256_file(root / "spec.json"),
                        sha256_file(root / "currentness.json"),
                        sha256_file(root / TARGET_BANK_FILENAME),
                        sha256_file(root / "manifest.json"),
                        result["spec_payload_sha256"],
                        result["manifest_sha256"],
                    )
                )
            self.assertEqual(outputs[0], outputs[1])

    def test_cc_l01_leakage_thresholds(self) -> None:
        audit = audit_questions(self.candidate_questions)
        analyzable = audit["analyzable_single_answer"]
        domain_rows: dict[str, list[bool]] = {}
        for question in self.candidate_questions:
            choices = question.get("choices")
            if not isinstance(choices, Mapping):
                continue
            lengths = {letter: len(str(choices.get(letter, "")).strip()) for letter in CHOICE_LABELS}
            correct = question.get("correct")
            if not isinstance(correct, list) or len(correct) != 1:
                continue
            letter = correct[0]
            if letter not in lengths:
                continue
            strict = lengths[letter] > max(lengths[item] for item in CHOICE_LABELS if item != letter)
            domain_rows.setdefault(str(question.get("domain") or ""), []).append(strict)
        max_domain = max((sum(rows) / len(rows) for rows in domain_rows.values() if rows), default=0.0)
        self.assertLess(audit["strict_longest_correct"]["rate"], 0.40)
        self.assertLess(audit["unique_longest_heuristic"]["rate"], 0.40)
        self.assertLess(max_domain, 0.45)
        self.assertGreater(analyzable, 0)

    def test_cc_r01_production_inactivity(self) -> None:
        self.assertEqual(8, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        profile = _read_json(REPOSITORY_ROOT / "cert_profile_sc900.json")
        self.assertEqual("sc900_bank_v8_explanation_q118_repair.json", profile["runtime_bank"])


class ContentCorrectionRepositoryGateTests(unittest.TestCase):
    def test_cc_a03_source_identity(self) -> None:
        self.assertEqual(EXPECTED_SOURCE_BANK_SHA256, sha256_file(REPOSITORY_ROOT / SOURCE_BANK_FILENAME))
        self.assertEqual(
            EXPECTED_SOURCE_MANIFEST_PAYLOAD_SHA256,
            _read_json(REPOSITORY_ROOT / T5_MANIFEST_RELATIVE_PATH)["payload_sha256"],
        )
        source = _read_json(REPOSITORY_ROOT / SOURCE_BANK_FILENAME)
        self.assertEqual(REQUIRED_QUESTION_COUNT, len(source["questions"]))
        self.assertEqual(EXPECTED_SOURCE_CONTENT_FINGERPRINT, self._fingerprint(source["questions"]))

    def _fingerprint(self, questions: list[Mapping[str, Any]]) -> str:
        from question_identity import bank_content_fingerprint

        return bank_content_fingerprint(questions)

    def test_cc_b05_historical_t1_t5_byte_identity(self) -> None:
        for relative in HISTORICAL_PATHS:
            head = (
                subprocess.check_output(["git", "rev-parse", f"HEAD:{relative}"], cwd=REPOSITORY_ROOT).decode().strip()
            )
            worktree = subprocess.check_output(["git", "hash-object", relative], cwd=REPOSITORY_ROOT).decode().strip()
            self.assertEqual(head, worktree, relative)

    def test_cc_b06_partial_source_rejected(self) -> None:
        artifacts = [
            REPOSITORY_ROOT / TARGET_BANK_FILENAME,
            REPOSITORY_ROOT / CORRECTION_SPEC_RELATIVE_PATH,
            REPOSITORY_ROOT / CURRENTNESS_RECORD_RELATIVE_PATH,
            REPOSITORY_ROOT / MANIFEST_RELATIVE_PATH,
        ]
        if not all(path.is_file() for path in artifacts):
            self.skipTest("repository artifacts not materialized yet")
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / SOURCE_BANK_FILENAME
            shutil.copy2(REPOSITORY_ROOT / TARGET_BANK_FILENAME, source)
            with self.assertRaises(ContentCorrectionBuildError):
                build_sc900_content_correction_001(
                    source,
                    Path(temp) / TARGET_BANK_FILENAME,
                    Path(temp) / "spec.json",
                    Path(temp) / "currentness.json",
                    Path(temp) / "reviews",
                    Path(temp) / "manifest.json",
                )


class ContentCorrectionCommittedArtifactTests(unittest.TestCase):
    def test_committed_artifacts_match_frozen_hashes(self) -> None:
        spec_path = REPOSITORY_ROOT / CORRECTION_SPEC_RELATIVE_PATH
        currentness_path = REPOSITORY_ROOT / CURRENTNESS_RECORD_RELATIVE_PATH
        bank_path = REPOSITORY_ROOT / TARGET_BANK_FILENAME
        manifest_path = REPOSITORY_ROOT / MANIFEST_RELATIVE_PATH
        review_root = REPOSITORY_ROOT / "content_revision_evidence" / "reviews"
        if not all(path.is_file() for path in (spec_path, currentness_path, bank_path, manifest_path)):
            self.skipTest("repository artifacts not materialized yet")
        spec = _read_json(spec_path)
        currentness = _read_json(currentness_path)
        manifest = _read_json(manifest_path)
        result = admit_content_correction(
            manifest,
            spec=spec,
            currentness_record=currentness,
            source_bank_path=REPOSITORY_ROOT / SOURCE_BANK_FILENAME,
            target_bank_path=bank_path,
            spec_path=spec_path,
            currentness_path=currentness_path,
            review_root=review_root,
        )
        self.assertEqual(AdmissionStatus.PASS, result.status)
        self.assertEqual(EXPECTED_CORRECTION_SPEC_PAYLOAD_SHA256, spec["payload_sha256"])
        self.assertEqual(EXPECTED_CURRENTNESS_RECORD_PAYLOAD_SHA256, currentness["payload_sha256"])
        self.assertEqual(PERMITTED_CHANGE_CLASS, manifest["permitted_change_class"])
        self.assertEqual(9, len(list((review_root / REVIEW_DIRECTORY).glob("*.json"))))
        self.assertEqual(8, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))


if __name__ == "__main__":
    unittest.main()
