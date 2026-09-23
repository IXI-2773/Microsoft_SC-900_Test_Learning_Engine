from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from answer_length_audit import LETTERS, audit_questions
from app_constants import MODE_PRACTICE
from content_revision_authority import (
    AdmissionStatus,
    RevisionFailureReason,
    admit_content_revision,
    canonical_manifest_sha256,
    sha256_file,
)
from content_revision_migration import (
    MigrationStatus,
    migrate_progress_payload,
    migrate_session_payload,
)
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS
from question_identity import bank_content_fingerprint, question_content_fingerprint
from session_identity import canonical_session_signature
from session_store import build_session_snapshot
from tools.build_package_b_tranche3 import (
    EXPECTED_T2_SOURCE_SHA256,
    T1_SKIP_QUESTION_IDS,
    T1_SOURCE_BANK_FILENAME,
    T2_SKIP_QUESTION_IDS,
    T2_SOURCE_BANK_FILENAME,
    T3_CANDIDATE_BANK_FILENAME,
    T3_DESIGN_QUEUE,
    build_package_b_tranche3,
)
from tools.run_quality_checks import QUALITY_TARGETS

QUESTION_COUNT = 454
CHOICE_LABELS = ("A", "B", "C", "D")
MS_LEARN_REF = "https://learn.microsoft.com/en-us/security/zero-trust/"
WORK_ID = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / PACKAGE-B / TRANCHE-3"
TASK5_WORK_ID = "SC900-PACKAGE-B-TRANCHE3-TASK5-REAL-CANDIDATE-CONTINUITY-LEAKAGE-001"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
SOURCE_BANK_FILENAME = T2_SOURCE_BANK_FILENAME
CANDIDATE_BANK_FILENAME = T3_CANDIDATE_BANK_FILENAME
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t3.json"
REVIEW_ROOT_RELATIVE_PATH = "content_revision_evidence/reviews"
T2_METRICS_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/15-PACKAGE-B-TRANCHE2-CANDIDATE-METRICS.json"
)
CANDIDATE_METRICS_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/21-PACKAGE-B-TRANCHE3-CANDIDATE-METRICS.json"
)
SEMANTIC_REVIEW_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/20-PACKAGE-B-TRANCHE3-SEMANTIC-REVIEW.json"
)
LEAKAGE_METRIC_KEYS = (
    "strict_longest_correct",
    "strict_shortest_correct",
    "unique_longest_heuristic",
    "unique_shortest_heuristic",
)
EXPECTED_T2_SOURCE_FINGERPRINT = "34b5278570d89ab17ce09dfda891be0ab31a2b4e134b4727a10ed9b65a2b1f8b"
EXPECTED_SOURCE_STRICT_LONGEST_COUNT = 270
EXPECTED_STRICT_LONGEST_DENOMINATOR = 449
EXPECTED_SOURCE_UNIQUE_LONGEST_SUCCESSES = 270
EXPECTED_SOURCE_UNIQUE_LONGEST_DENOMINATOR = 428
EXPECTED_SOURCE_STRICT_SHORTEST_COUNT = 47
EXPECTED_SOURCE_UNIQUE_SHORTEST_SUCCESSES = 47
PRIOR_SKIP_QUESTION_IDS = T1_SKIP_QUESTION_IDS | T2_SKIP_QUESTION_IDS
SECOND_PASS_QUESTION_IDS = (
    "sc900_mlc_q288",
    "sc900_mlc_q126",
    "sc900_mlc_q138",
    "sc900_mlc_q109",
    "sc900_mlc_q177",
    "sc900_mlc_q216",
    "sc900_p3_q054",
    "sc900_mlc_q295",
    "sc900_mlc_q217",
    "sc900_mlc_q134",
)
FRESH_QUESTION_IDS = tuple(
    question_id for question_id in T3_DESIGN_QUEUE if question_id not in SECOND_PASS_QUESTION_IDS
)
MIGRATED_AT = "2026-09-18T00:00:00"
RECEIPT_FIELDS = {
    "question_id",
    "from_content_fingerprint",
    "to_content_fingerprint",
    "before",
    "after",
    "semantic_review",
    "correct_key_before",
    "correct_key_after",
    "authority_refs",
    "disposition",
}
MANIFEST_FIELDS = {
    "schema_version",
    "manifest_kind",
    "work_id",
    "continuity_policy",
    "source_bank",
    "target_bank",
    "permitted_change_class",
    "edges",
    "payload_sha256",
}
EDGE_FIELDS = {
    "question_id",
    "from_content_fingerprint",
    "to_content_fingerprint",
    "correct_key_unchanged",
    "choice_letter_mapping_unchanged",
    "prompt_unchanged",
    "objective_unchanged",
    "tier_unchanged",
    "exam_eligibility_unchanged",
    "choice_semantics",
    "review_status",
    "review_artifact",
    "review_artifact_sha256",
    "authority_refs",
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _question(index: int, question_id: str | None = None) -> dict[str, Any]:
    resolved_id = question_id or f"sc900_syn_{index:03d}"
    correct = CHOICE_LABELS[(index - 1) % len(CHOICE_LABELS)]
    return {
        "id": resolved_id,
        "question_number": index,
        "prompt": f"Which synthetic statement is correct for {resolved_id}?",
        "choices": {
            "A": f"{resolved_id} alpha statement",
            "B": f"{resolved_id} beta statement",
            "C": f"{resolved_id} gamma statement",
            "D": f"{resolved_id} delta statement",
        },
        "correct": [correct],
        "general_explanation": f"Synthetic explanation for {resolved_id}.",
        "choice_explanations": {
            "A": f"Explanation A for {resolved_id}.",
            "B": f"Explanation B for {resolved_id}.",
            "C": f"Explanation C for {resolved_id}.",
            "D": f"Explanation D for {resolved_id}.",
        },
        "domain": "microsoft_entra",
        "chapter": "Synthetic chapter",
        "subtitle": "Synthetic subtitle",
        "question_type": "single_choice",
        "topics": ["synthetic", "identity"],
        "objective_code": "1.1",
        "study_focus": "Synthetic focus",
        "exam_calibration_tier": "FUNDAMENTALS_CORE",
        "exam_simulation_eligible": True,
    }


def _bank(question_count: int = QUESTION_COUNT) -> dict[str, Any]:
    return {
        "title": "SC-900 Synthetic Package-B T3 Bank",
        "version": 1,
        "questions": [_question(index) for index in range(1, question_count + 1)],
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_subset(audit: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(audit[key]) for key in LEAKAGE_METRIC_KEYS}


def _metric_delta(baseline: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, int | float]:
    delta: dict[str, int | float] = {}
    for key in LEAKAGE_METRIC_KEYS:
        before = baseline[key]
        after = candidate[key]
        if "count" in before:
            delta[f"{key}_count"] = after["count"] - before["count"]
        if "successes" in before:
            delta[f"{key}_successes"] = after["successes"] - before["successes"]
        delta[f"{key}_rate"] = after["rate"] - before["rate"]
    return delta


def _max_domain_strict_longest(audit: Mapping[str, Any]) -> dict[str, Any]:
    maximum: dict[str, Any] | None = None
    for domain, payload in audit["domains"].items():
        metric = payload["strict_longest_correct"]
        row = {
            "domain": domain,
            "count": metric["count"],
            "denominator": metric["denominator"],
            "rate": metric["rate"],
        }
        if maximum is None:
            maximum = row
            continue
        if (row["rate"], row["count"], row["domain"]) > (
            maximum["rate"],
            maximum["count"],
            maximum["domain"],
        ):
            maximum = row
    assert maximum is not None
    return maximum


def _choice_mechanism(source_choices: Mapping[str, str], target_choices: Mapping[str, str], correct: str) -> str:
    correct_changed = source_choices[correct] != target_choices[correct]
    distractor_changed = any(
        source_choices[letter] != target_choices[letter] for letter in CHOICE_LABELS if letter != correct
    )
    if correct_changed and distractor_changed:
        return "BOTH"
    if correct_changed:
        return "CORRECT_ONLY"
    if distractor_changed:
        return "DISTRACTOR_ONLY"
    return "UNCHANGED"


def build_package_b_tranche3_candidate_metrics(
    source_questions: list[dict[str, Any]],
    candidate_questions: list[dict[str, Any]],
    *,
    edited_ids: list[str],
    skipped_ids: list[str],
    source_by_id: Mapping[str, Mapping[str, Any]],
    candidate_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    baseline_audit = audit_questions(source_questions)
    candidate_audit = audit_questions(candidate_questions)
    baseline_metrics = _metric_subset(baseline_audit)
    candidate_metrics = _metric_subset(candidate_audit)
    delta = _metric_delta(baseline_metrics, candidate_metrics)

    def _strict_longest_ids(questions: list[dict[str, Any]]) -> set[str]:
        ids: set[str] = set()
        for question in questions:
            choices = question.get("choices")
            correct_values = question.get("correct")
            if not isinstance(choices, Mapping) or not isinstance(correct_values, list) or not correct_values:
                continue
            correct = correct_values[0]
            if correct not in CHOICE_LABELS:
                continue
            lengths = {letter: len(choices[letter]) for letter in CHOICE_LABELS}
            if lengths[correct] > max(lengths[letter] for letter in CHOICE_LABELS if letter != correct):
                ids.add(question["id"])
        return ids

    baseline_strict = _strict_longest_ids(source_questions)
    candidate_strict = _strict_longest_ids(candidate_questions)
    crossed_ids = sorted(baseline_strict - candidate_strict)
    yield_rows = []
    distractor_growths: list[int] = []
    mechanism_counts = {"CORRECT_ONLY": 0, "DISTRACTOR_ONLY": 0, "BOTH": 0}
    crossing_by_mechanism = {"CORRECT_ONLY": 0, "DISTRACTOR_ONLY": 0, "BOTH": 0}
    for question_id in edited_ids:
        source_question = source_by_id[question_id]
        target_question = candidate_by_id[question_id]
        correct = source_question["correct"][0]
        mechanism = _choice_mechanism(source_question["choices"], target_question["choices"], correct)
        mechanism_counts[mechanism] += 1
        crossed = question_id in crossed_ids
        if crossed:
            crossing_by_mechanism[mechanism] += 1
        source_distractors = [len(source_question["choices"][letter]) for letter in CHOICE_LABELS if letter != correct]
        target_distractors = [len(target_question["choices"][letter]) for letter in CHOICE_LABELS if letter != correct]
        growth = max(target_distractors) - max(source_distractors)
        distractor_growths.append(growth)
        source_correct_len = len(source_question["choices"][correct])
        target_correct_len = len(target_question["choices"][correct])
        source_max_d = max(source_distractors)
        target_max_d = max(target_distractors)
        if source_correct_len > source_max_d and target_correct_len == target_max_d:
            crossing_kind = "TIE"
        elif source_correct_len > source_max_d and target_correct_len < target_max_d:
            crossing_kind = "SHORTER"
        else:
            crossing_kind = "NONE"
        option_lengths = {
            letter: {
                "after": len(target_question["choices"][letter]),
                "before": len(source_question["choices"][letter]),
                "delta": len(target_question["choices"][letter]) - len(source_question["choices"][letter]),
            }
            for letter in CHOICE_LABELS
        }
        bucket = "SECOND_PASS" if question_id in SECOND_PASS_QUESTION_IDS else "FRESH_YIELD_BAND"
        yield_rows.append(
            {
                "question_id": question_id,
                "mechanism": mechanism,
                "selection_bucket": bucket,
                "crossed_strict_longest": crossed,
                "crossing_kind": crossing_kind,
                "source_correct_chars": source_correct_len,
                "target_correct_chars": target_correct_len,
                "source_max_distractor_chars": source_max_d,
                "target_max_distractor_chars": target_max_d,
                "distractor_growth": growth,
                "option_lengths": option_lengths,
            }
        )
    second_pass_edits = [question_id for question_id in edited_ids if question_id in SECOND_PASS_QUESTION_IDS]
    fresh_edits = [question_id for question_id in edited_ids if question_id not in SECOND_PASS_QUESTION_IDS]
    second_pass_skips = [question_id for question_id in skipped_ids if question_id in SECOND_PASS_QUESTION_IDS]
    fresh_skips = [question_id for question_id in skipped_ids if question_id not in SECOND_PASS_QUESTION_IDS]
    second_pass_crossings = [
        row["question_id"]
        for row in yield_rows
        if row["selection_bucket"] == "SECOND_PASS" and row["crossed_strict_longest"]
    ]
    fresh_crossings = [
        row["question_id"]
        for row in yield_rows
        if row["selection_bucket"] == "FRESH_YIELD_BAND" and row["crossed_strict_longest"]
    ]
    crossing_to_tie = [row["question_id"] for row in yield_rows if row["crossing_kind"] == "TIE"]
    crossing_to_shorter = [row["question_id"] for row in yield_rows if row["crossing_kind"] == "SHORTER"]
    closure_result = (
        "PASS"
        if delta["strict_longest_correct_count"] <= 0 and delta["unique_longest_heuristic_successes"] <= 0
        else "FAIL"
    )
    return {
        "analyzable_single_answer": candidate_audit["analyzable_single_answer"],
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "candidate_bank": CANDIDATE_BANK_FILENAME,
        "closure_result": closure_result,
        "correct_letter_counts": candidate_audit["correct_letter_counts"],
        "delta": delta,
        "distractor_growth": {
            "count": len(distractor_growths),
            "max": max(distractor_growths) if distractor_growths else 0,
            "mean": (sum(distractor_growths) / len(distractor_growths)) if distractor_growths else 0.0,
            "values": distractor_growths,
        },
        "domain_strict_longest": {
            domain: copy.deepcopy(payload["strict_longest_correct"])
            for domain, payload in candidate_audit["domains"].items()
        },
        "edit_count": len(edited_ids),
        "edit_yield": yield_rows,
        "max_domain_strict_longest": {
            "after": _max_domain_strict_longest(candidate_audit),
            "before": _max_domain_strict_longest(baseline_audit),
        },
        "mechanism_counts": mechanism_counts,
        "crossing_by_mechanism": crossing_by_mechanism,
        "question_count": candidate_audit["question_count"],
        "skip_count": len(skipped_ids),
        "skipped_audit_question_ids": list(candidate_audit["skipped_question_ids"]),
        "skipped_review_question_ids": list(skipped_ids),
        "source_bank": SOURCE_BANK_FILENAME,
        "strict_longest_crossed_question_ids": crossed_ids,
        "crossing_to_tie_count": len(crossing_to_tie),
        "crossing_to_tie_question_ids": crossing_to_tie,
        "crossing_to_shorter_count": len(crossing_to_shorter),
        "crossing_to_shorter_question_ids": crossing_to_shorter,
        "second_pass_edit_count": len(second_pass_edits),
        "second_pass_skip_count": len(second_pass_skips),
        "second_pass_crossing_count": len(second_pass_crossings),
        "fresh_edit_count": len(fresh_edits),
        "fresh_skip_count": len(fresh_skips),
        "fresh_crossing_count": len(fresh_crossings),
        "work_id": TASK5_WORK_ID,
    }


def serialize_candidate_metrics(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _progress_record() -> dict[str, Any]:
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


def _session_answer(*, selected=None, pending=None, answered=False, flagged=False) -> dict[str, Any]:
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


def _after(question: dict[str, Any]) -> dict[str, str]:
    return {letter: f"{question['choices'][letter]} with reviewed wording" for letter in CHOICE_LABELS}


def _edit_row(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": question["id"],
        "disposition": "EDIT",
        "after": _after(question),
        "semantic_review": {letter: "EQUIVALENT" for letter in CHOICE_LABELS},
        "authority_refs": [MS_LEARN_REF],
        "review_note": "All four choices preserve their original roles and meaning.",
    }


class PackageBTranche3BuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_path = self.root / "source_bank.json"
        self.semantic_path = self.root / "semantic_review.json"
        self.candidate_path = self.root / "candidate_bank.json"
        self.review_root = self.root / "reviews"
        self.manifest_path = self.root / "manifest.json"
        self.source_payload = _bank()
        _write_json(self.source_path, self.source_payload)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _semantic_review(self) -> dict[str, Any]:
        questions = self.source_payload["questions"]
        return {
            "work_id": WORK_ID,
            "source_bank": self.source_path.name,
            "candidate_bank": self.candidate_path.name,
            "review_queue": [
                _edit_row(questions[1]),
                {
                    "question_id": questions[2]["id"],
                    "disposition": "SKIP",
                    "review_note": "No wording change is needed.",
                },
                _edit_row(questions[0]),
            ],
        }

    def _write_semantic_review(self, payload: dict[str, Any]) -> None:
        _write_json(self.semantic_path, payload)

    def _build(self) -> dict[str, Any]:
        return build_package_b_tranche3(
            self.source_path,
            self.semantic_path,
            self.candidate_path,
            self.review_root,
            self.manifest_path,
        )

    def _assert_build_fails(self, payload: dict[str, Any]) -> None:
        self._write_semantic_review(payload)
        with self.assertRaises(ValueError):
            self._build()
        self.assertFalse(self.candidate_path.exists())
        self.assertFalse(self.manifest_path.exists())

    def test_valid_two_edit_package_is_exact_deterministic_and_admitted(self) -> None:
        semantic_review = self._semantic_review()
        self._write_semantic_review(semantic_review)
        source_before = self.source_path.read_bytes()
        registry_before = copy.deepcopy(AUTHORIZED_CONTENT_REVISION_MANIFESTS)

        summary = self._build()

        self.assertTrue(
            {
                "edited_question_ids",
                "skipped_question_ids",
                "source_file_sha256",
                "target_file_sha256",
                "source_bank_content_fingerprint",
                "target_bank_content_fingerprint",
                "manifest_sha256",
                "review_count",
                "admission_status",
            }.issubset(summary)
        )
        self.assertEqual(["sc900_syn_001", "sc900_syn_002"], summary["edited_question_ids"])
        self.assertEqual(["sc900_syn_003"], summary["skipped_question_ids"])
        self.assertEqual(2, summary["review_count"])
        self.assertEqual(AdmissionStatus.PASS.value, summary["admission_status"])
        self.assertNotEqual(source_before, self.candidate_path.read_bytes())
        self.assertEqual(source_before, self.source_path.read_bytes())
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)

        source = _read_json(self.source_path)
        candidate = _read_json(self.candidate_path)
        self.assertEqual(
            json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            self.candidate_path.read_text(encoding="utf-8"),
        )
        source_by_id = {question["id"]: question for question in source["questions"]}
        target_by_id = {question["id"]: question for question in candidate["questions"]}
        edited_ids = set(summary["edited_question_ids"])
        for question_id, source_question in source_by_id.items():
            target_question = target_by_id[question_id]
            if question_id not in edited_ids:
                self.assertEqual(source_question, target_question)
                continue
            source_without_choices = {key: value for key, value in source_question.items() if key != "choices"}
            target_without_choices = {key: value for key, value in target_question.items() if key != "choices"}
            self.assertEqual(source_without_choices, target_without_choices)
            self.assertEqual(set(CHOICE_LABELS), set(target_question["choices"]))
            self.assertNotEqual(source_question["choices"], target_question["choices"])
            self.assertEqual(source_question["correct"], target_question["correct"])

        manifest = _read_json(self.manifest_path)
        self.assertEqual(MANIFEST_FIELDS, set(manifest))
        self.assertEqual(manifest["payload_sha256"], canonical_manifest_sha256(manifest))
        self.assertEqual(self.source_path.name, manifest["source_bank"]["filename"])
        self.assertEqual(self.candidate_path.name, manifest["target_bank"]["filename"])
        self.assertEqual(
            ["sc900_syn_001", "sc900_syn_002"],
            [edge["question_id"] for edge in manifest["edges"]],
        )
        for edge in manifest["edges"]:
            self.assertEqual(EDGE_FIELDS, set(edge))
            self.assertEqual(
                f"SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T3/{edge['question_id']}.json",
                edge["review_artifact"],
            )
            receipt_path = self.review_root / edge["review_artifact"]
            receipt = _read_json(receipt_path)
            self.assertEqual(RECEIPT_FIELDS, set(receipt))
            self.assertNotIn("review_note", receipt)
            self.assertEqual(sha256_file(receipt_path), edge["review_artifact_sha256"])
        self.assertEqual(summary, self._build())

    def test_source_and_candidate_filename_must_differ(self) -> None:
        review = self._semantic_review()
        same_name_candidate = self.root / "nested" / self.source_path.name
        review["candidate_bank"] = same_name_candidate.name
        self._write_semantic_review(review)
        with self.assertRaises(ValueError):
            build_package_b_tranche3(
                self.source_path,
                self.semantic_path,
                same_name_candidate,
                self.review_root,
                self.manifest_path,
            )

    def test_candidate_cannot_use_frozen_bank_filename(self) -> None:
        review = self._semantic_review()
        frozen_candidate = self.root / T1_SOURCE_BANK_FILENAME
        review["candidate_bank"] = frozen_candidate.name
        self._write_semantic_review(review)
        with self.assertRaises(ValueError):
            build_package_b_tranche3(
                self.source_path,
                self.semantic_path,
                frozen_candidate,
                self.review_root,
                self.manifest_path,
            )

    def test_output_path_cannot_overwrite_source(self) -> None:
        review = self._semantic_review()
        self._write_semantic_review(review)
        with self.assertRaises(ValueError):
            build_package_b_tranche3(
                self.source_path,
                self.semantic_path,
                self.candidate_path,
                self.review_root,
                self.source_path,
            )

    def test_t1_skip_id_cannot_be_edited(self) -> None:
        skip_id = next(iter(T1_SKIP_QUESTION_IDS))
        self.source_payload["questions"][0]["id"] = skip_id
        _write_json(self.source_path, self.source_payload)
        review = self._semantic_review()
        review["review_queue"][2]["question_id"] = skip_id
        self._assert_build_fails(review)

    def test_wrong_t2_source_hash_fails(self) -> None:
        t2_named = self.root / T2_SOURCE_BANK_FILENAME
        _write_json(t2_named, self.source_payload)
        review = self._semantic_review()
        review["source_bank"] = t2_named.name
        self._write_semantic_review(review)
        with self.assertRaises(ValueError):
            build_package_b_tranche3(
                t2_named,
                self.semantic_path,
                self.candidate_path,
                self.review_root,
                self.manifest_path,
            )
        self.assertFalse(self.candidate_path.exists())

    def test_t2_skip_id_cannot_be_edited(self) -> None:
        skip_id = next(iter(T2_SKIP_QUESTION_IDS))
        self.source_payload["questions"][0]["id"] = skip_id
        _write_json(self.source_path, self.source_payload)
        review = self._semantic_review()
        review["review_queue"][2]["question_id"] = skip_id
        self._assert_build_fails(review)

    def test_duplicate_review_queue_id_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"].append(copy.deepcopy(review["review_queue"][0]))
        self._assert_build_fails(review)

    def test_unknown_question_id_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["question_id"] = "sc900_missing_q001"
        self._assert_build_fails(review)

    def test_edit_requires_microsoft_learn_authority(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["authority_refs"] = ["https://example.invalid/not-learn"]
        self._assert_build_fails(review)

    def test_non_equivalent_semantic_review_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["semantic_review"]["A"] = "CHANGED"
        self._assert_build_fails(review)

    def test_unchanged_edit_fails(self) -> None:
        review = self._semantic_review()
        question = self.source_payload["questions"][1]
        review["review_queue"][0]["after"] = copy.deepcopy(question["choices"])
        self._assert_build_fails(review)

    def test_edit_after_must_be_exact_ad_string_mapping(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["after"] = {"A": "only A"}
        self._assert_build_fails(review)

    def test_edit_review_note_must_be_nonblank(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["review_note"] = "   "
        self._assert_build_fails(review)

    def test_skip_review_note_must_be_nonblank(self) -> None:
        review = self._semantic_review()
        review["review_queue"][1]["review_note"] = ""
        self._assert_build_fails(review)

    def test_invalid_disposition_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"][1]["disposition"] = "DEFER"
        self._assert_build_fails(review)

    def test_source_question_count_must_be_454(self) -> None:
        self.source_payload["questions"] = self.source_payload["questions"][:10]
        _write_json(self.source_path, self.source_payload)
        self._assert_build_fails(self._semantic_review())

    def test_semantic_review_source_filename_binding_must_match(self) -> None:
        review = self._semantic_review()
        review["source_bank"] = "other.json"
        self._assert_build_fails(review)

    def test_semantic_review_candidate_filename_binding_must_match(self) -> None:
        review = self._semantic_review()
        review["candidate_bank"] = "other.json"
        self._assert_build_fails(review)

    def test_builder_is_in_repository_quality_targets(self) -> None:
        self.assertIn("tools/build_package_b_tranche3.py", QUALITY_TARGETS)
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))


class PackageBTranche3CliTests(unittest.TestCase):
    def _materialize_package(self, root: Path) -> tuple[Path, Path, Path, Path, Path]:
        source_path = root / "source_bank.json"
        semantic_path = root / "semantic_review.json"
        candidate_path = root / "candidate_bank.json"
        review_root = root / "reviews"
        manifest_path = root / "manifest.json"
        source_payload = _bank()
        _write_json(source_path, source_payload)
        questions = source_payload["questions"]
        _write_json(
            semantic_path,
            {
                "work_id": WORK_ID,
                "source_bank": source_path.name,
                "candidate_bank": candidate_path.name,
                "review_queue": [
                    _edit_row(questions[1]),
                    {
                        "question_id": questions[2]["id"],
                        "disposition": "SKIP",
                        "review_note": "No wording change is needed.",
                    },
                    _edit_row(questions[0]),
                ],
            },
        )
        return source_path, semantic_path, candidate_path, review_root, manifest_path

    def _run_cli(
        self,
        source_path: Path,
        semantic_path: Path,
        candidate_path: Path,
        review_root: Path,
        manifest_path: Path,
        *,
        include_manifest: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-m",
            "tools.build_package_b_tranche3",
            "--source-bank",
            str(source_path),
            "--semantic-review",
            str(semantic_path),
            "--candidate-bank",
            str(candidate_path),
            "--review-root",
            str(review_root),
        ]
        if include_manifest:
            command.extend(["--manifest", str(manifest_path)])
        return subprocess.run(command, cwd=REPOSITORY_ROOT, check=False, capture_output=True, text=True)

    def test_cli_builds_an_admissible_synthetic_package_and_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self._materialize_package(Path(temporary_directory))
            source_path, _, candidate_path, review_root, manifest_path = paths

            completed = self._run_cli(*paths)

            self.assertEqual(0, completed.returncode, completed.stderr)
            summary = json.loads(completed.stdout)
            self.assertEqual("PASS", summary["admission_status"])
            self.assertEqual(["sc900_syn_001", "sc900_syn_002"], summary["edited_question_ids"])
            self.assertTrue(candidate_path.exists())
            self.assertTrue(manifest_path.exists())
            for question_id in summary["edited_question_ids"]:
                self.assertTrue(
                    (review_root / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T3" / f"{question_id}.json").exists()
                )
            self.assertEqual(source_path.read_bytes(), Path(source_path).read_bytes())

    def test_cli_returns_nonzero_and_no_manifest_for_invalid_semantic_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self._materialize_package(Path(temporary_directory))
            source_path, semantic_path, candidate_path, review_root, manifest_path = paths
            review = _read_json(semantic_path)
            review["review_queue"][0]["authority_refs"] = ["https://example.invalid/x"]
            _write_json(semantic_path, review)

            completed = self._run_cli(*paths)

            self.assertEqual(2, completed.returncode)
            self.assertFalse(candidate_path.exists())
            self.assertFalse(manifest_path.exists())

    def test_cli_requires_all_arguments(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "tools.build_package_b_tranche3"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(0, completed.returncode)


class PackageBTranche3RealCandidateClosureTests(unittest.TestCase):
    SOURCE_BANK_PATH = REPOSITORY_ROOT / SOURCE_BANK_FILENAME
    CANDIDATE_BANK_PATH = REPOSITORY_ROOT / CANDIDATE_BANK_FILENAME
    PRODUCTION_BANK_PATH = REPOSITORY_ROOT / PRODUCTION_BANK_FILENAME
    MANIFEST_PATH = REPOSITORY_ROOT / MANIFEST_RELATIVE_PATH
    REVIEW_ROOT = REPOSITORY_ROOT / REVIEW_ROOT_RELATIVE_PATH
    T2_METRICS_PATH = REPOSITORY_ROOT / T2_METRICS_RELATIVE_PATH
    CANDIDATE_METRICS_PATH = REPOSITORY_ROOT / CANDIDATE_METRICS_RELATIVE_PATH
    SEMANTIC_REVIEW_PATH = REPOSITORY_ROOT / SEMANTIC_REVIEW_RELATIVE_PATH
    T3_RECEIPT_DIR = REVIEW_ROOT / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T3"

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry_before = copy.deepcopy(AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        cls.source_bytes = cls.SOURCE_BANK_PATH.read_bytes()
        cls.candidate_bytes = cls.CANDIDATE_BANK_PATH.read_bytes()
        cls.production_bytes = cls.PRODUCTION_BANK_PATH.read_bytes()
        cls.manifest_bytes = cls.MANIFEST_PATH.read_bytes()
        cls.receipt_bytes = {
            path.relative_to(cls.T3_RECEIPT_DIR).as_posix(): path.read_bytes()
            for path in sorted(cls.T3_RECEIPT_DIR.glob("*.json"))
        }
        cls.source_payload = json.loads(cls.source_bytes.decode("utf-8"))
        cls.candidate_payload = json.loads(cls.candidate_bytes.decode("utf-8"))
        cls.manifest = json.loads(cls.manifest_bytes.decode("utf-8"))
        cls.semantic_review = _read_json(cls.SEMANTIC_REVIEW_PATH)
        cls.source_questions = cls.source_payload["questions"]
        cls.candidate_questions = cls.candidate_payload["questions"]
        cls.source_by_id = {question["id"]: question for question in cls.source_questions}
        cls.candidate_by_id = {question["id"]: question for question in cls.candidate_questions}
        cls.changed_ids = [edge["question_id"] for edge in cls.manifest["edges"]]
        changed = set(cls.changed_ids)
        cls.skipped_ids = [
            row["question_id"] for row in cls.semantic_review["review_queue"] if row["disposition"] == "SKIP"
        ]
        cls.changed_id = cls.changed_ids[0]
        cls.unchanged_id = next(question_id for question_id in cls.source_by_id if question_id not in changed)
        cls.changed_source = cls.source_by_id[cls.changed_id]
        cls.changed_target = cls.candidate_by_id[cls.changed_id]
        cls.unchanged_source = cls.source_by_id[cls.unchanged_id]
        cls.unchanged_target = cls.candidate_by_id[cls.unchanged_id]

    def tearDown(self) -> None:
        self.assertEqual(self.registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        self.assertEqual(self.source_bytes, self.SOURCE_BANK_PATH.read_bytes())
        self.assertEqual(self.candidate_bytes, self.CANDIDATE_BANK_PATH.read_bytes())
        self.assertEqual(self.production_bytes, self.PRODUCTION_BANK_PATH.read_bytes())
        self.assertEqual(self.manifest_bytes, self.MANIFEST_PATH.read_bytes())
        self.assertEqual(
            self.receipt_bytes,
            {
                path.relative_to(self.T3_RECEIPT_DIR).as_posix(): path.read_bytes()
                for path in sorted(self.T3_RECEIPT_DIR.glob("*.json"))
            },
        )

    def _admit(
        self,
        *,
        source_path: Path | None = None,
        target_path: Path | None = None,
        manifest: Mapping[str, Any] | None = None,
        review_root: Path | None = None,
    ):
        source_path = self.SOURCE_BANK_PATH if source_path is None else source_path
        target_path = self.CANDIDATE_BANK_PATH if target_path is None else target_path
        source_questions = _read_json(source_path)["questions"]
        target_questions = _read_json(target_path)["questions"]
        return admit_content_revision(
            self.manifest if manifest is None else manifest,
            source_questions=source_questions,
            target_questions=target_questions,
            source_bank_path=source_path,
            target_bank_path=target_path,
            review_root=self.REVIEW_ROOT if review_root is None else review_root,
        )

    def _materialize_real_package(self, root: Path) -> tuple[Path, Path, Path, Path]:
        source_path = root / SOURCE_BANK_FILENAME
        candidate_path = root / CANDIDATE_BANK_FILENAME
        manifest_path = root / Path(MANIFEST_RELATIVE_PATH).name
        review_root = root / "reviews"
        shutil.copy2(self.SOURCE_BANK_PATH, source_path)
        shutil.copy2(self.CANDIDATE_BANK_PATH, candidate_path)
        shutil.copy2(self.MANIFEST_PATH, manifest_path)
        shutil.copytree(self.REVIEW_ROOT, review_root)
        return source_path, candidate_path, manifest_path, review_root

    def _source_progress_payload(self, revision) -> dict[str, Any]:
        changed_fp = question_content_fingerprint(self.changed_source)
        unchanged_fp = question_content_fingerprint(self.unchanged_source)
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": revision.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                self.unchanged_id: unchanged_fp,
                self.changed_id: changed_fp,
            },
            "questions": {
                self.unchanged_id: _progress_record(),
                self.changed_id: _progress_record(),
            },
            "history": [
                {
                    "question_id": self.changed_id,
                    "question_content_fingerprint": changed_fp,
                    "selected_texts": [self.changed_source["choices"]["A"]],
                    "correct_texts": [self.changed_source["choices"][self.changed_source["correct"][0]]],
                    "correct": True,
                }
            ],
        }

    def test_real_t2_source_identity_is_pinned(self) -> None:
        self.assertEqual(EXPECTED_T2_SOURCE_SHA256, sha256_file(self.SOURCE_BANK_PATH))
        self.assertEqual(EXPECTED_T2_SOURCE_FINGERPRINT, bank_content_fingerprint(self.source_questions))
        self.assertEqual(SOURCE_BANK_FILENAME, self.manifest["source_bank"]["filename"])
        self.assertEqual(EXPECTED_T2_SOURCE_SHA256, self.manifest["source_bank"]["file_sha256"])
        self.assertEqual(EXPECTED_T2_SOURCE_FINGERPRINT, self.manifest["source_bank"]["content_fingerprint"])
        self.assertEqual(CANDIDATE_BANK_FILENAME, self.manifest["target_bank"]["filename"])
        self.assertNotEqual(PRODUCTION_BANK_FILENAME, self.manifest["source_bank"]["filename"])
        self.assertNotEqual(PRODUCTION_BANK_FILENAME, self.manifest["target_bank"]["filename"])

    def test_real_package_admission_passes_without_activating_registry(self) -> None:
        admission = self._admit()

        self.assertEqual(AdmissionStatus.PASS, admission.status)
        self.assertEqual((), admission.reasons)
        self.assertIsNotNone(admission.admitted)
        assert admission.admitted is not None
        self.assertEqual(SOURCE_BANK_FILENAME, admission.admitted.source_bank_filename)
        self.assertEqual(CANDIDATE_BANK_FILENAME, admission.admitted.target_bank_filename)
        self.assertEqual(self.changed_ids, [edge.question_id for edge in admission.admitted.edges])
        actual_changed = [
            question_id
            for question_id, source_question in self.source_by_id.items()
            if source_question != self.candidate_by_id[question_id]
        ]
        self.assertEqual(set(self.changed_ids), set(actual_changed))
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(self.registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)

    def test_semantic_invariants_and_skip_invariants(self) -> None:
        reviewed_ids = [row["question_id"] for row in self.semantic_review["review_queue"]]
        self.assertEqual(set(T3_DESIGN_QUEUE), set(reviewed_ids))
        self.assertEqual(36, len(reviewed_ids))
        self.assertEqual(10, len(SECOND_PASS_QUESTION_IDS))
        self.assertEqual(26, len(FRESH_QUESTION_IDS))
        self.assertEqual(set(SECOND_PASS_QUESTION_IDS) | set(FRESH_QUESTION_IDS), set(T3_DESIGN_QUEUE))
        self.assertTrue(set(PRIOR_SKIP_QUESTION_IDS).isdisjoint(self.changed_ids))
        self.assertTrue(set(PRIOR_SKIP_QUESTION_IDS).isdisjoint(set(reviewed_ids)))
        for question_id in PRIOR_SKIP_QUESTION_IDS:
            self.assertEqual(self.source_by_id[question_id], self.candidate_by_id[question_id])
        for question_id in self.changed_ids:
            source_question = self.source_by_id[question_id]
            target_question = self.candidate_by_id[question_id]
            source_nonchoices = {key: value for key, value in source_question.items() if key != "choices"}
            target_nonchoices = {key: value for key, value in target_question.items() if key != "choices"}
            self.assertEqual(source_nonchoices, target_nonchoices)
            self.assertEqual(source_question["id"], target_question["id"])
            self.assertEqual(source_question["prompt"], target_question["prompt"])
            self.assertEqual(source_question["correct"], target_question["correct"])
            self.assertEqual(source_question["objective_code"], target_question["objective_code"])
            self.assertEqual(source_question["domain"], target_question["domain"])
            self.assertEqual(source_question["topics"], target_question["topics"])
            self.assertEqual(source_question["exam_calibration_tier"], target_question["exam_calibration_tier"])
            self.assertEqual(
                source_question["exam_simulation_eligible"],
                target_question["exam_simulation_eligible"],
            )
            self.assertEqual(source_question["question_type"], target_question["question_type"])
        for question_id in self.skipped_ids:
            self.assertEqual(self.source_by_id[question_id], self.candidate_by_id[question_id])
        for question_id, source_question in self.source_by_id.items():
            if question_id not in set(self.changed_ids):
                self.assertEqual(source_question, self.candidate_by_id[question_id])

    def test_receipts_bind_to_source_candidate_and_manifest(self) -> None:
        for edge in self.manifest["edges"]:
            receipt_path = self.REVIEW_ROOT / edge["review_artifact"]
            receipt = _read_json(receipt_path)
            self.assertEqual(edge["question_id"], receipt["question_id"])
            self.assertEqual(edge["from_content_fingerprint"], receipt["from_content_fingerprint"])
            self.assertEqual(edge["to_content_fingerprint"], receipt["to_content_fingerprint"])
            self.assertEqual(sha256_file(receipt_path), edge["review_artifact_sha256"])
            self.assertEqual(
                question_content_fingerprint(self.source_by_id[edge["question_id"]]),
                receipt["from_content_fingerprint"],
            )
            self.assertEqual(
                question_content_fingerprint(self.candidate_by_id[edge["question_id"]]),
                receipt["to_content_fingerprint"],
            )
            self.assertEqual(self.source_by_id[edge["question_id"]]["choices"], receipt["before"])
            self.assertEqual(self.candidate_by_id[edge["question_id"]]["choices"], receipt["after"])

    def test_real_progress_continuity_and_idempotence(self) -> None:
        admission = self._admit()
        self.assertEqual(AdmissionStatus.PASS, admission.status)
        assert admission.admitted is not None
        revision = admission.admitted
        source_payload = self._source_progress_payload(revision)
        unchanged_fp = source_payload["question_content_fingerprints"][self.unchanged_id]
        changed_from_fp = source_payload["question_content_fingerprints"][self.changed_id]

        first = migrate_progress_payload(source_payload, self.candidate_questions, revision, MIGRATED_AT)

        self.assertEqual(MigrationStatus.APPLIED, first.status)
        self.assertTrue(first.changed)
        self.assertEqual({self.unchanged_id, self.changed_id}, set(first.payload["questions"]))
        self.assertEqual(_progress_record(), first.payload["questions"][self.changed_id])
        self.assertEqual(_progress_record(), first.payload["questions"][self.unchanged_id])
        self.assertEqual(source_payload["history"], first.payload["history"])
        self.assertEqual(revision.target_bank_content_fingerprint, first.payload["bank_fingerprint"])
        self.assertEqual(unchanged_fp, first.payload["question_content_fingerprints"][self.unchanged_id])
        self.assertEqual(
            question_content_fingerprint(self.changed_target),
            first.payload["question_content_fingerprints"][self.changed_id],
        )
        self.assertEqual(unchanged_fp, question_content_fingerprint(self.unchanged_target))
        self.assertNotEqual(changed_from_fp, first.payload["question_content_fingerprints"][self.changed_id])
        self.assertEqual(1, len(first.payload["content_revision_lineage"]))
        lineage = first.payload["content_revision_lineage"][0]
        self.assertEqual(self.changed_id, lineage["question_id"])
        self.assertEqual(revision.manifest_sha256, lineage["manifest_sha256"])

        second = migrate_progress_payload(first.payload, self.candidate_questions, revision, "2026-09-19T00:00:00")
        self.assertEqual(MigrationStatus.MIGRATION_ALREADY_APPLIED, second.status)
        self.assertFalse(second.changed)
        self.assertEqual(first.payload, second.payload)
        self.assertEqual(first.payload["history"], second.payload["history"])
        self.assertEqual(first.payload["content_revision_lineage"], second.payload["content_revision_lineage"])
        self.assertEqual(
            first.payload["questions"][self.changed_id]["attempts"],
            second.payload["questions"][self.changed_id]["attempts"],
        )
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))

    def test_real_session_continuity_and_idempotence(self) -> None:
        admission = self._admit()
        self.assertEqual(AdmissionStatus.PASS, admission.status)
        assert admission.admitted is not None
        revision = admission.admitted
        unchanged_number = int(self.unchanged_source["question_number"])
        changed_number = int(self.changed_source["question_number"])
        question_ids = [self.unchanged_id, self.changed_id]
        history_event = {
            "question_id": self.changed_id,
            "question_number": changed_number,
            "question_content_fingerprint": question_content_fingerprint(self.changed_source),
            "selected_texts": [self.changed_source["choices"]["A"]],
            "correct_texts": [self.changed_source["choices"][self.changed_source["correct"][0]]],
            "correct": True,
        }
        snapshot = build_session_snapshot(
            app_version="test",
            bank_file=SOURCE_BANK_FILENAME,
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
            question_numbers=[unchanged_number, changed_number],
            restore_question_numbers=[unchanged_number, changed_number],
            bank_fingerprint=revision.source_bank_content_fingerprint,
            question_ids=question_ids,
            restore_question_ids=question_ids,
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
                _session_answer(selected=["A"], answered=True, flagged=True),
                _session_answer(selected=["B"], pending=["B"], answered=False),
            ],
        )

        result = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            revision,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )

        self.assertEqual(MigrationStatus.APPLIED, result.status)
        self.assertEqual(question_ids, result.payload["question_ids"])
        self.assertEqual([unchanged_number, changed_number], result.payload["question_numbers"])
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        self.assertEqual(["A"], answers[self.unchanged_id]["selected"])
        self.assertTrue(answers[self.unchanged_id]["answered"])
        self.assertFalse(answers[self.changed_id]["answered"])
        self.assertEqual([], answers[self.changed_id]["selected"])
        self.assertEqual(snapshot["session_answer_history"], result.payload["session_answer_history"])
        self.assertEqual(CANDIDATE_BANK_FILENAME, result.payload["bank_file"])
        self.assertEqual(revision.target_bank_content_fingerprint, result.payload["bank_fingerprint"])
        self.assertEqual(
            canonical_session_signature(MODE_PRACTICE, revision.target_bank_content_fingerprint, question_ids),
            result.payload["session_signature"],
        )

        second = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            revision,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, second.status)
        self.assertEqual(result.payload, second.payload)
        self.assertEqual(result.payload["session_answer_history"], second.payload["session_answer_history"])
        self.assertEqual(result.payload["elapsed_seconds"], second.payload["elapsed_seconds"])
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))

    def test_tampered_review_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, _, review_root = self._materialize_real_package(Path(temporary_directory))
            receipt_path = review_root / self.manifest["edges"][0]["review_artifact"]
            receipt = _read_json(receipt_path)
            receipt["after"]["A"] = f"{receipt['after']['A']} tampered"
            _write_json(receipt_path, receipt)

            admission = self._admit(source_path=source_path, target_path=candidate_path, review_root=review_root)

            self.assertEqual(AdmissionStatus.FAIL, admission.status)
            self.assertEqual((RevisionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH,), admission.reasons)
            self.assertIsNone(admission.admitted)

    def test_missing_review_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, _, review_root = self._materialize_real_package(Path(temporary_directory))
            receipt_path = review_root / self.manifest["edges"][0]["review_artifact"]
            receipt_path.unlink()

            admission = self._admit(source_path=source_path, target_path=candidate_path, review_root=review_root)

            self.assertEqual(AdmissionStatus.FAIL, admission.status)
            self.assertEqual((RevisionFailureReason.SEMANTIC_REVIEW_MISSING,), admission.reasons)
            self.assertIsNone(admission.admitted)

    def test_missing_learn_authority_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, manifest_path, review_root = self._materialize_real_package(
                Path(temporary_directory)
            )
            manifest = _read_json(manifest_path)
            edge = manifest["edges"][0]
            receipt_path = review_root / edge["review_artifact"]
            receipt = _read_json(receipt_path)
            receipt["authority_refs"] = ["https://example.invalid/not-learn"]
            edge["authority_refs"] = ["https://example.invalid/not-learn"]
            _write_json(receipt_path, receipt)
            edge["review_artifact_sha256"] = sha256_file(receipt_path)
            manifest["payload_sha256"] = ""
            manifest["payload_sha256"] = canonical_manifest_sha256(manifest)

            admission = self._admit(
                source_path=source_path,
                target_path=candidate_path,
                manifest=manifest,
                review_root=review_root,
            )

            self.assertEqual(AdmissionStatus.FAIL, admission.status)
            self.assertEqual((RevisionFailureReason.AUTHORITY_EVIDENCE_MISSING,), admission.reasons)
            self.assertIsNone(admission.admitted)

    def test_wrong_t3_candidate_hash_fails_closed_before_migration(self) -> None:
        admission = self._admit()
        self.assertEqual(AdmissionStatus.PASS, admission.status)
        assert admission.admitted is not None
        source_payload = self._source_progress_payload(admission.admitted)
        original_payload = copy.deepcopy(source_payload)

        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, _, review_root = self._materialize_real_package(Path(temporary_directory))
            candidate_path.write_bytes(candidate_path.read_bytes() + b"\n")

            failed = self._admit(source_path=source_path, target_path=candidate_path, review_root=review_root)

            self.assertEqual(AdmissionStatus.FAIL, failed.status)
            self.assertEqual((RevisionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH,), failed.reasons)
            self.assertIsNone(failed.admitted)
            self.assertEqual(original_payload, source_payload)

    def test_wrong_t2_source_hash_fails_closed_before_migration(self) -> None:
        admission = self._admit()
        assert admission.admitted is not None
        source_payload = self._source_progress_payload(admission.admitted)
        original_payload = copy.deepcopy(source_payload)
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, _, review_root = self._materialize_real_package(Path(temporary_directory))
            source_path.write_bytes(source_path.read_bytes() + b"\n")

            failed = self._admit(source_path=source_path, target_path=candidate_path, review_root=review_root)

            self.assertEqual(AdmissionStatus.FAIL, failed.status)
            self.assertEqual((RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH,), failed.reasons)
            self.assertIsNone(failed.admitted)
            self.assertEqual(original_payload, source_payload)

    def test_non_choice_drift_fails_closed_with_prompt_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, manifest_path, review_root = self._materialize_real_package(
                Path(temporary_directory)
            )
            candidate = _read_json(candidate_path)
            candidate["questions"][0]["prompt"] = f"{candidate['questions'][0]['prompt']} drifted"
            _write_json(candidate_path, candidate)
            manifest = _read_json(manifest_path)
            manifest["target_bank"]["file_sha256"] = sha256_file(candidate_path)
            manifest["payload_sha256"] = ""
            manifest["payload_sha256"] = canonical_manifest_sha256(manifest)

            failed = self._admit(
                source_path=source_path,
                target_path=candidate_path,
                manifest=manifest,
                review_root=review_root,
            )

            self.assertEqual(AdmissionStatus.FAIL, failed.status)
            self.assertEqual((RevisionFailureReason.PROMPT_CHANGED,), failed.reasons)
            self.assertIsNone(failed.admitted)

    def test_unresolved_real_t3_queue_fails_before_candidate_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / SOURCE_BANK_FILENAME
            shutil.copy2(self.SOURCE_BANK_PATH, source_path)
            review = copy.deepcopy(self.semantic_review)
            review["review_queue"] = review["review_queue"][:-1]
            review_path = root / "semantic_review.json"
            candidate_path = root / CANDIDATE_BANK_FILENAME
            manifest_path = root / "manifest.json"
            _write_json(review_path, review)
            with self.assertRaises(ValueError):
                build_package_b_tranche3(
                    source_path,
                    review_path,
                    candidate_path,
                    root / "reviews",
                    manifest_path,
                )
            self.assertFalse(candidate_path.exists())
            self.assertFalse(manifest_path.exists())
            self.assertEqual(EXPECTED_T2_SOURCE_SHA256, sha256_file(source_path))

    def test_candidate_leakage_metrics_do_not_worsen_strict_longest_and_match_artifact(self) -> None:
        computed = build_package_b_tranche3_candidate_metrics(
            self.source_questions,
            self.candidate_questions,
            edited_ids=self.changed_ids,
            skipped_ids=self.skipped_ids,
            source_by_id=self.source_by_id,
            candidate_by_id=self.candidate_by_id,
        )
        t2_metrics = _read_json(self.T2_METRICS_PATH)
        serialized = serialize_candidate_metrics(computed)

        self.assertEqual(
            EXPECTED_SOURCE_STRICT_LONGEST_COUNT,
            computed["baseline"]["strict_longest_correct"]["count"],
        )
        self.assertEqual(
            EXPECTED_STRICT_LONGEST_DENOMINATOR,
            computed["baseline"]["strict_longest_correct"]["denominator"],
        )
        self.assertEqual(
            t2_metrics["candidate"]["strict_longest_correct"],
            computed["baseline"]["strict_longest_correct"],
        )
        self.assertEqual(
            t2_metrics["candidate"]["unique_longest_heuristic"],
            computed["baseline"]["unique_longest_heuristic"],
        )
        self.assertEqual(
            EXPECTED_SOURCE_UNIQUE_LONGEST_SUCCESSES,
            computed["baseline"]["unique_longest_heuristic"]["successes"],
        )
        self.assertEqual(
            EXPECTED_SOURCE_UNIQUE_LONGEST_DENOMINATOR,
            computed["baseline"]["unique_longest_heuristic"]["denominator"],
        )
        self.assertEqual(
            EXPECTED_SOURCE_STRICT_SHORTEST_COUNT,
            computed["baseline"]["strict_shortest_correct"]["count"],
        )
        self.assertEqual(
            EXPECTED_SOURCE_UNIQUE_SHORTEST_SUCCESSES,
            computed["baseline"]["unique_shortest_heuristic"]["successes"],
        )
        self.assertLessEqual(
            computed["candidate"]["strict_longest_correct"]["count"],
            EXPECTED_SOURCE_STRICT_LONGEST_COUNT,
        )
        self.assertLessEqual(
            computed["candidate"]["unique_longest_heuristic"]["successes"],
            EXPECTED_SOURCE_UNIQUE_LONGEST_SUCCESSES,
        )
        self.assertLessEqual(
            computed["candidate"]["strict_shortest_correct"]["count"],
            computed["baseline"]["strict_shortest_correct"]["count"] + 1,
        )
        self.assertEqual(set(LETTERS), set(computed["correct_letter_counts"]))
        self.assertEqual("PASS", computed["closure_result"])
        self.assertEqual(serialized, self.CANDIDATE_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(computed, _read_json(self.CANDIDATE_METRICS_PATH))
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(
            "sc900_bank_v8_final_content_correction_002.json",
            _read_json(REPOSITORY_ROOT / "cert_profile_sc900.json")["runtime_bank"],
        )


if __name__ == "__main__":
    unittest.main()
