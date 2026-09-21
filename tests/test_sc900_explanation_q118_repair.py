from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from app_constants import MODE_PRACTICE
from content_revision_authority import (
    AdmissionStatus,
    admit_content_revision,
    canonical_manifest_sha256,
    sha256_file,
)
from content_revision_correction_authority import admit_content_correction
from content_revision_explanation_authority import (
    WORK_ID,
    ExplanationFailureReason,
    admit_explanation_revision,
)
from content_revision_explanation_migration import (
    MigrationStatus,
    migrate_explanation_progress_payload,
    migrate_explanation_session_payload,
)
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS
from question_identity import question_content_fingerprint
from session_store import build_session_snapshot
from tests.test_explanation_rendering import RenderingHarness
from tools.build_sc900_explanation_q118_repair import (
    EXPECTED_CHOICES,
    EXPECTED_CORRECT,
    EXPECTED_OBJECTIVE_CODE,
    EXPECTED_PROMPT,
    EXPECTED_SOURCE_BANK_SHA256,
    EXPECTED_SOURCE_CONTENT_FINGERPRINT,
    EXPECTED_SOURCE_Q118_FINGERPRINT,
    EXPECTED_TARGET_BANK_SHA256,
    EXPECTED_TARGET_CONTENT_FINGERPRINT,
    EXPECTED_TARGET_Q118_FINGERPRINT,
    EXPECTED_TESTED_DECISION,
    QUESTION_ID,
    TARGET_CHOICE_EXPLANATIONS,
    TARGET_GENERAL_EXPLANATION,
    build_sc900_explanation_q118_repair,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "sc900_bank_v8_explanation_tranche_1.json"
TARGET_PATH = ROOT / "sc900_bank_v8_explanation_q118_repair.json"
SPEC_PATH = ROOT / "content_revision_evidence/specs/sc900_explanation_q118_repair_001.json"
LEDGER_PATH = ROOT / "content_revision_evidence/reviews/SC900-EXPLANATION-Q118-REPAIR-001/semantic_review_ledger.json"
MANIFEST_PATH = ROOT / "content_revision_evidence/manifests/sc900_explanation_q118_repair_001.json"
RECEIPT_PATH = ROOT / "content_revision_evidence/receipts/sc900_explanation_q118_repair_001.json"
TRANCHE_SOURCE_PATH = ROOT / "sc900_bank_v8_content_correction_001.json"
TRANCHE_TARGET_PATH = ROOT / "sc900_bank_v8_explanation_tranche_1.json"
TRANCHE_SPEC_PATH = ROOT / "content_revision_evidence/specs/sc900_explanation_tranche_1.json"
TRANCHE_LEDGER_PATH = ROOT / "content_revision_evidence/reviews/SC900-EXPLANATION-TRANCHE-1/semantic_review_ledger.json"
TRANCHE_MANIFEST_PATH = ROOT / "content_revision_evidence/manifests/sc900_explanation_tranche_1.json"
PR37_PRESERVED_IDS = (
    "sc900_mlc_q064",
    "sc900_mlc_q150",
    "sc900_mlc_q198",
    "sc900_mlc_q219",
    "sc900_mlc_q226",
    "sc900_mlc_q242",
    "sc900_mlc_q249",
    "sc900_mlc_q269",
)
ALLOWED_FIELDS = {"general_explanation", "choice_explanations"}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(payload):
    payload = copy.deepcopy(payload)
    payload["payload_sha256"] = ""
    payload["payload_sha256"] = canonical_manifest_sha256(payload)
    return payload


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
        "answer_event_id": "event-q118" if answered else "",
        "recall_ready": False,
        "session_tag": "weak_repair",
        "smart_primary_role": "weak_repair",
        "smart_selection_reasons": ["weakness"],
        "smart_utility": 7.5,
        "smart_utility_breakdown": {"weakness": 7.5},
        "smart_policy_version": "v1",
        "smart_policy_id": "smart",
        "smart_concept_key": "mdvm",
        "smart_root_cause": "misconception",
        "smart_root_cause_confidence": 0.8,
        "smart_supporting_concepts": ["endpoint-vulnerabilities"],
        "smart_graph_version": "g1",
        "smart_information_value": 2.5,
        "smart_information_breakdown": {"x": 2.5},
        "smart_question_quality_status": "PASS",
        "smart_question_quality_confidence": 0.9,
        "smart_graph_bottleneck": 0.2,
        "repair_stage": "repair",
        "repair_concept_key": "mdvm",
        "legacy_repair_concept_key": "",
        "prediction_id": "pred-q118",
        "prediction_snapshot": {"score": 1},
    }


class Q118ExplanationRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = _load(SOURCE_PATH)
        cls.target = _load(TARGET_PATH)
        cls.source_by_id = {question["id"]: question for question in cls.source["questions"]}
        cls.target_by_id = {question["id"]: question for question in cls.target["questions"]}
        cls.spec = _load(SPEC_PATH)
        cls.ledger = _load(LEDGER_PATH)
        cls.manifest = _load(MANIFEST_PATH)
        result = admit_explanation_revision(
            cls.manifest,
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            ledger_path=LEDGER_PATH,
        )
        if result.status != AdmissionStatus.PASS or result.admitted is None:
            raise AssertionError(result.reasons)
        cls.revision = result.admitted
        cls.tranche_ids = tuple(_load(TRANCHE_SPEC_PATH)["target_ids"])

    def test_q118_001_exact_source_fingerprint_gate(self):
        self.assertEqual(EXPECTED_SOURCE_BANK_SHA256, sha256_file(SOURCE_PATH))
        self.assertEqual(EXPECTED_SOURCE_CONTENT_FINGERPRINT, self.manifest["source_bank"]["content_fingerprint"])
        self.assertEqual(
            EXPECTED_SOURCE_Q118_FINGERPRINT,
            question_content_fingerprint(self.source_by_id[QUESTION_ID]),
        )
        self.assertEqual(EXPECTED_SOURCE_Q118_FINGERPRINT, self.spec["revisions"][0]["source_content_fingerprint"])

    def test_q118_002_exact_target_fingerprint(self):
        self.assertEqual(
            EXPECTED_TARGET_Q118_FINGERPRINT,
            question_content_fingerprint(self.target_by_id[QUESTION_ID]),
        )
        self.assertEqual(EXPECTED_TARGET_Q118_FINGERPRINT, self.spec["revisions"][0]["target_content_fingerprint"])

    def test_q118_003_only_q118_changes(self):
        changed = [qid for qid in self.source_by_id if self.source_by_id[qid] != self.target_by_id[qid]]
        self.assertEqual([QUESTION_ID], changed)
        self.assertEqual(
            [question["id"] for question in self.source["questions"]],
            [question["id"] for question in self.target["questions"]],
        )
        for qid in self.tranche_ids:
            self.assertEqual(self.source_by_id[qid], self.target_by_id[qid], qid)
        for qid in PR37_PRESERVED_IDS:
            self.assertEqual(self.source_by_id[qid], self.target_by_id[qid], qid)

    def test_q118_004_only_explanation_fields_change(self):
        before = self.source_by_id[QUESTION_ID]
        after = self.target_by_id[QUESTION_ID]
        changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
        self.assertEqual(["choice_explanations", "general_explanation"], changed)
        for field in set(before) | set(after):
            if field not in ALLOWED_FIELDS:
                self.assertEqual(before.get(field), after.get(field), field)

    def test_q118_005_prompt_unchanged(self):
        self.assertEqual(EXPECTED_PROMPT, self.target_by_id[QUESTION_ID]["prompt"])
        self.assertEqual(self.source_by_id[QUESTION_ID]["prompt"], self.target_by_id[QUESTION_ID]["prompt"])

    def test_q118_006_choices_unchanged(self):
        self.assertEqual(EXPECTED_CHOICES, self.target_by_id[QUESTION_ID]["choices"])
        self.assertEqual(self.source_by_id[QUESTION_ID]["choices"], self.target_by_id[QUESTION_ID]["choices"])

    def test_q118_007_key_unchanged(self):
        self.assertEqual(EXPECTED_CORRECT, self.target_by_id[QUESTION_ID]["correct"])
        self.assertEqual(self.source_by_id[QUESTION_ID]["correct"], self.target_by_id[QUESTION_ID]["correct"])

    def test_q118_008_objective_and_tested_decision_unchanged(self):
        target = self.target_by_id[QUESTION_ID]
        source = self.source_by_id[QUESTION_ID]
        self.assertEqual(EXPECTED_OBJECTIVE_CODE, target["objective_code"])
        self.assertEqual(EXPECTED_TESTED_DECISION, target["tested_decision"])
        self.assertEqual(source["objective_code"], target["objective_code"])
        self.assertEqual(source["tested_decision"], target["tested_decision"])

    def test_q118_009_sparse_map_exactly_abc(self):
        self.assertEqual(TARGET_CHOICE_EXPLANATIONS, self.target_by_id[QUESTION_ID]["choice_explanations"])
        self.assertEqual(["A", "B", "C"], list(self.target_by_id[QUESTION_ID]["choice_explanations"]))

    def test_q118_010_d_feedback_absent(self):
        self.assertNotIn("D", self.target_by_id[QUESTION_ID]["choice_explanations"])

    def test_q118_011_target_bank_exact_identity(self):
        self.assertEqual(EXPECTED_TARGET_BANK_SHA256, sha256_file(TARGET_PATH))
        self.assertEqual(EXPECTED_TARGET_CONTENT_FINGERPRINT, self.manifest["target_bank"]["content_fingerprint"])
        self.assertEqual(454, len(self.target["questions"]))

    def test_q118_012_q118_authority_package_admits(self):
        self.assertEqual(QUESTION_ID, self.revision.edges[0].question_id)
        self.assertEqual(EXPECTED_SOURCE_Q118_FINGERPRINT, self.revision.edges[0].from_content_fingerprint)
        self.assertEqual(EXPECTED_TARGET_Q118_FINGERPRINT, self.revision.edges[0].to_content_fingerprint)
        self.assertEqual(1, len(self.revision.edges))
        self.assertEqual({}, AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        self.assertFalse(self.ledger["independent_pre_implementation_semantic_review"])
        self.assertEqual("EXPLICIT_IMPLEMENTATION_DIRECTIVE", self.ledger["wording_authority"])

    def test_q118_013_unknown_explanation_package_profile_rejects(self):
        bad = _rehash({**self.manifest, "work_id": "SC900-EXPLANATION-UNKNOWN-PACKAGE"})
        result = admit_explanation_revision(
            bad,
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            ledger_path=LEDGER_PATH,
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)
        self.assertIn(ExplanationFailureReason.AUTHORITY_KIND_MISMATCH, result.reasons)

    def test_q118_014_tranche_1_package_still_admits(self):
        result = admit_explanation_revision(
            _load(TRANCHE_MANIFEST_PATH),
            source_bank_path=TRANCHE_SOURCE_PATH,
            target_bank_path=TRANCHE_TARGET_PATH,
            spec_path=TRANCHE_SPEC_PATH,
            ledger_path=TRANCHE_LEDGER_PATH,
        )
        self.assertEqual(AdmissionStatus.PASS, result.status)
        self.assertIsNotNone(result.admitted)
        self.assertEqual(48, len(result.admitted.edges))
        self.assertEqual(WORK_ID, _load(TRANCHE_MANIFEST_PATH)["work_id"])

    def test_q118_015_package_b_v1_rejects_explanation_package(self):
        result = admit_content_revision(
            self.manifest,
            source_questions=self.source["questions"],
            target_questions=self.target["questions"],
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            review_root=ROOT / "content_revision_evidence/reviews",
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def test_q118_016_semantic_correction_v2_rejects_explanation_package(self):
        result = admit_content_correction(
            self.manifest,
            spec=self.spec,
            currentness_record={"schema_version": 2},
            source_bank_path=SOURCE_PATH,
            target_bank_path=TARGET_PATH,
            spec_path=SPEC_PATH,
            currentness_path=SPEC_PATH,
            review_root=ROOT / "content_revision_evidence/reviews",
        )
        self.assertEqual(AdmissionStatus.FAIL, result.status)

    def _progress_payload(self):
        preserved_id = PR37_PRESERVED_IDS[0]
        source_q118 = self.source_by_id[QUESTION_ID]
        records = {
            QUESTION_ID: {
                "attempts": 9,
                "correct_count": 6,
                "wrong_count": 3,
                "correct_streak": 2,
                "last_seen": "2026-09-21T01:00:00",
                "next_review": "2026-09-25",
                "last_selected": ["A"],
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
            preserved_id: {
                "attempts": 4,
                "correct_count": 3,
                "wrong_count": 1,
                "correct_streak": 1,
                "last_seen": "2026-09-20T01:00:00",
                "next_review": "2026-09-26",
                "last_selected": ["D"],
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
                "question_id": QUESTION_ID,
                "question_content_fingerprint": question_content_fingerprint(source_q118),
                "selected_texts": [source_q118["choices"]["A"]],
                "correct_texts": [source_q118["choices"]["D"]],
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
                QUESTION_ID: question_content_fingerprint(source_q118),
                preserved_id: question_content_fingerprint(self.source_by_id[preserved_id]),
            },
            "questions": copy.deepcopy(records),
            "history": copy.deepcopy(history),
            "meta": {"session_history": [{"id": "session-q118"}]},
        }

    def _session_snapshot(self):
        first = self.source_by_id[QUESTION_ID]
        second = self.source_by_id[PR37_PRESERVED_IDS[0]]
        history_event = {
            "question_id": QUESTION_ID,
            "question_number": first["question_number"],
            "question_content_fingerprint": question_content_fingerprint(first),
            "selected_texts": [first["choices"]["B"]],
            "correct_texts": [first["choices"]["D"]],
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
            question_ids=[QUESTION_ID, PR37_PRESERVED_IDS[0]],
            restore_question_ids=[QUESTION_ID, PR37_PRESERVED_IDS[0]],
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

    def test_q118_017_full_progress_continuity(self):
        payload = self._progress_payload()
        original_records = copy.deepcopy(payload["questions"])
        result = migrate_explanation_progress_payload(
            payload, self.target["questions"], self.revision, "2026-09-21T10:00:00"
        )
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        self.assertEqual(original_records, result.payload["questions"])
        self.assertEqual(self.revision.target_bank_content_fingerprint, result.payload["bank_fingerprint"])
        self.assertEqual(payload["meta"], result.payload["meta"])

    def test_q118_018_selected_pending_session_state_preserved(self):
        saved = self._session_snapshot()
        result = migrate_explanation_session_payload(
            saved,
            self.target["questions"],
            self.revision,
            TARGET_PATH.name,
            source_questions=self.source["questions"],
        )
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        self.assertEqual(saved["answers"], result.payload["answers"])
        self.assertEqual(saved["current_index"], result.payload["current_index"])
        self.assertEqual(["B"], result.payload["answers"][0]["selected"])
        self.assertEqual(["B"], result.payload["answers"][0]["pending"])
        self.assertEqual(["C"], result.payload["answers"][1]["selected"])
        self.assertEqual(["C"], result.payload["answers"][1]["pending"])

    def test_q118_019_historical_evidence_preserved(self):
        payload = self._progress_payload()
        original_history = copy.deepcopy(payload["history"])
        result = migrate_explanation_progress_payload(
            payload, self.target["questions"], self.revision, "2026-09-21T10:00:00"
        )
        self.assertEqual(original_history, result.payload["history"])
        self.assertEqual(
            EXPECTED_SOURCE_Q118_FINGERPRINT,
            result.payload["history"][0]["question_content_fingerprint"],
        )
        saved = self._session_snapshot()
        session = migrate_explanation_session_payload(
            saved,
            self.target["questions"],
            self.revision,
            TARGET_PATH.name,
            source_questions=self.source["questions"],
        )
        self.assertEqual(saved["session_answer_history"], session.payload["session_answer_history"])

    def test_q118_020_smart_practice_state_preserved(self):
        payload = self._progress_payload()
        result = migrate_explanation_progress_payload(
            payload, self.target["questions"], self.revision, "2026-09-21T10:00:00"
        )
        for qid in (QUESTION_ID, PR37_PRESERVED_IDS[0]):
            for field in (
                "attempts",
                "correct_count",
                "wrong_count",
                "correct_streak",
                "next_review",
                "last_seen",
                "last_confidence",
                "last_miss_reason",
                "flagged",
                "suspended",
                "learner_memory",
                "smart_primary_role",
                "smart_utility",
                "smart_selection_reasons",
            ):
                self.assertEqual(payload["questions"][qid][field], result.payload["questions"][qid][field], field)
        saved = self._session_snapshot()
        session = migrate_explanation_session_payload(
            saved,
            self.target["questions"],
            self.revision,
            TARGET_PATH.name,
            source_questions=self.source["questions"],
        )
        self.assertEqual("weak_repair", session.payload["answers"][0]["smart_primary_role"])
        self.assertEqual(["weakness"], session.payload["answers"][0]["smart_selection_reasons"])
        self.assertEqual(7.5, session.payload["answers"][0]["smart_utility"])

    def test_q118_021_selected_wrong_rendering_for_abc(self):
        engine = RenderingHarness()
        for letter in ("A", "B", "C"):
            question = copy.deepcopy(self.target_by_id[QUESTION_ID])
            question["selected"] = [letter]
            question["pending"] = [letter]
            question["answered"] = True
            engine._render_choice_rows(question, True)
            engine._render_general_explanation_block(question, True)
            self.assertEqual(TARGET_GENERAL_EXPLANATION, engine.general_card.config["text"])
            self.assertEqual(TARGET_CHOICE_EXPLANATIONS[letter], engine.choice_rows[letter].detail)
            for other in "ABCD":
                if other != letter:
                    self.assertEqual("", engine.choice_rows[other].detail, other)

    def test_q118_022_correct_d_receives_no_selected_wrong_feedback(self):
        engine = RenderingHarness()
        question = copy.deepcopy(self.target_by_id[QUESTION_ID])
        question["selected"] = ["D"]
        question["pending"] = ["D"]
        question["answered"] = True
        engine._render_choice_rows(question, True)
        engine._render_general_explanation_block(question, True)
        self.assertEqual("", engine.choice_rows["D"].detail)
        self.assertEqual(TARGET_GENERAL_EXPLANATION, engine.general_card.config["text"])
        self.assertNotIn("D", question["choice_explanations"])

    def test_q118_023_deterministic_two_build_equality(self):
        build_sc900_explanation_q118_repair(ROOT)
        first = {path: path.read_bytes() for path in (TARGET_PATH, MANIFEST_PATH, RECEIPT_PATH)}
        build_sc900_explanation_q118_repair(ROOT)
        second = {path: path.read_bytes() for path in first}
        self.assertEqual(first, second)
        self.assertEqual(EXPECTED_TARGET_BANK_SHA256, sha256_file(TARGET_PATH))


if __name__ == "__main__":
    unittest.main()
