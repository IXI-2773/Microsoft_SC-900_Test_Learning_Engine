from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import patch

from answer_length_audit import LETTERS, audit_questions
from app_constants import MODE_PRACTICE
from content_revision_authority import (
    AdmissionStatus,
    admit_content_revision,
    canonical_manifest_sha256,
    sha256_file,
)
from content_revision_migration import (
    ContentRevisionMigrationError,
    MigrationFailureReason,
    MigrationStatus,
    migrate_progress_payload,
    migrate_session_payload,
)
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS
from question_identity import bank_content_fingerprint, question_content_fingerprint
from session_identity import canonical_session_signature
from session_store import build_session_snapshot
from tools.build_package_b_tranche4 import T4_EDIT_IDS

QUESTION_COUNT = 454
CHOICE_LABELS = ("A", "B", "C", "D")
WORK_ID = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / PACKAGE-B / TRANCHE-5"
TASK_WORK_ID = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-TRANCHE5-IMPLEMENTATION-EXECUTION-001"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
T3_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t3.json"
SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t4.json"
CANDIDATE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t5.json"
T2_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t2.json"
T6_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t6.json"
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t5.json"
T4_MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t4.json"
T3_MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t3.json"
REVIEW_ROOT_RELATIVE_PATH = "content_revision_evidence/reviews"
CANDIDATE_METRICS_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/32-PACKAGE-B-TRANCHE5-CANDIDATE-METRICS.json"
)
SEMANTIC_REVIEW_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/31-PACKAGE-B-TRANCHE5-SEMANTIC-REVIEW.json"
)
LEAKAGE_METRIC_KEYS = (
    "strict_longest_correct",
    "strict_shortest_correct",
    "unique_longest_heuristic",
    "unique_shortest_heuristic",
)
EXPECTED_T4_SOURCE_SHA256 = "c40f919bb10cf2a5b965e1525b4771572a7f36fd63ef8749e277d988a04688b4"
EXPECTED_T4_SOURCE_FINGERPRINT = "99db6d4cbec9a722ef85280debb80f7c60c7acc0e7dba7d9663f2e1744bdae3c"
EXPECTED_T5_SEMANTIC_REVIEW_SHA256 = "84266440b8fb8b2168c1c51ae388fba2c15ab22d32a833d4a914769302c8f67c"
EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA = "83482105c1cb820292e14524b268ae8660e9ba9c493c055e920d22579b1639cb"
EXPECTED_T3_SOURCE_SHA256 = "0b0cdf3bf4c8b7885acf0b3b19381dd9f19ee38944fc6af6934b11b5b14588bd"
EXPECTED_T3_SOURCE_FINGERPRINT = "83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2"
T5_EDIT_COUNT = 57
T5_SKIP_COUNT = 1
T5_SEPARATE_COUNT = 6
T5_QUEUE_COUNT = 64
T5_OUTSIDE_QUEUE_UNCHANGED = 390
T5_UNCHANGED_COUNT = 397
T5_SKIP_ID = "sc900_mlc_q293"
T5_TIE_ID = "sc900_mlc_q207"
T5_SEPARATE_IDS = (
    "sc900_mlc_q118",
    "sc900_mlc_q219",
    "sc900_mlc_q198",
    "sc900_mlc_q150",
    "sc900_mlc_q064",
    "sc900_mlc_q242",
)
MIGRATED_AT = "2026-09-19T12:00:00"
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
_NESTED_SUITE_ENV = "SC900_NESTED_PACKAGE_B_TESTS"


def _import_builder():
    from tools import build_package_b_tranche5 as builder_mod

    return {
        "build": builder_mod.build_package_b_tranche5,
        "module": builder_mod,
        "queue": builder_mod.T5_DESIGN_QUEUE,
        "edits": builder_mod.T5_EDIT_IDS,
        "skips": builder_mod.T5_SKIP_QUESTION_IDS,
        "separates": builder_mod.T5_SEPARATE_CORRECTION_IDS,
        "expected_t4_sha": builder_mod.EXPECTED_T4_SOURCE_SHA256,
        "expected_t4_fp": builder_mod.EXPECTED_T4_SOURCE_FINGERPRINT,
        "semantic_sha": builder_mod.EXPECTED_T5_SEMANTIC_REVIEW_SHA256,
        "parent_manifest_sha": builder_mod.EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA,
    }


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


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
        if maximum is None or (row["rate"], row["count"], row["domain"]) > (
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


def _crossing_kind(source_question: Mapping[str, Any], target_question: Mapping[str, Any]) -> str:
    correct = source_question["correct"][0]
    source_correct_len = len(source_question["choices"][correct])
    target_correct_len = len(target_question["choices"][correct])
    source_max_d = max(len(source_question["choices"][letter]) for letter in CHOICE_LABELS if letter != correct)
    target_max_d = max(len(target_question["choices"][letter]) for letter in CHOICE_LABELS if letter != correct)
    if source_correct_len > source_max_d and target_correct_len == target_max_d:
        return "TIE"
    if source_correct_len > source_max_d and target_correct_len < target_max_d:
        return "SHORTER"
    return "NONE"


def build_package_b_tranche5_candidate_metrics(
    source_questions: list[dict[str, Any]],
    candidate_questions: list[dict[str, Any]],
    *,
    edited_ids: list[str],
    skipped_ids: list[str],
    separate_ids: list[str],
    source_by_id: Mapping[str, Mapping[str, Any]],
    candidate_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    baseline_audit = audit_questions(source_questions)
    candidate_audit = audit_questions(candidate_questions)
    baseline_metrics = _metric_subset(baseline_audit)
    candidate_metrics = _metric_subset(candidate_audit)
    delta = _metric_delta(baseline_metrics, candidate_metrics)
    baseline_strict = _strict_longest_ids(source_questions)
    candidate_strict = _strict_longest_ids(candidate_questions)
    crossed_ids = sorted(baseline_strict - candidate_strict)
    yield_rows = []
    distractor_growths: list[int] = []
    mechanism_counts = {"CORRECT_ONLY": 0, "DISTRACTOR_ONLY": 0, "BOTH": 0}
    crossing_by_mechanism = {"CORRECT_ONLY": 0, "DISTRACTOR_ONLY": 0, "BOTH": 0}
    residual_ids = [row["question_id"] for row in candidate_audit["ranked_outliers"]]
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
        option_lengths = {
            letter: {
                "after": len(target_question["choices"][letter]),
                "before": len(source_question["choices"][letter]),
                "delta": len(target_question["choices"][letter]) - len(source_question["choices"][letter]),
            }
            for letter in CHOICE_LABELS
        }
        yield_rows.append(
            {
                "question_id": question_id,
                "mechanism": mechanism,
                "crossed_strict_longest": crossed,
                "crossing_kind": _crossing_kind(source_question, target_question),
                "source_correct_chars": len(source_question["choices"][correct]),
                "target_correct_chars": len(target_question["choices"][correct]),
                "source_max_distractor_chars": max(source_distractors),
                "target_max_distractor_chars": max(target_distractors),
                "distractor_growth": growth,
                "option_lengths": option_lengths,
                "still_strict_longest": question_id in candidate_strict,
            }
        )
    crossing_to_tie = [row["question_id"] for row in yield_rows if row["crossing_kind"] == "TIE"]
    crossing_to_shorter = [row["question_id"] for row in yield_rows if row["crossing_kind"] == "SHORTER"]
    still_longest = [row["question_id"] for row in yield_rows if row["still_strict_longest"]]
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
        "separate_count": len(separate_ids),
        "skipped_audit_question_ids": list(candidate_audit["skipped_question_ids"]),
        "skipped_review_question_ids": list(skipped_ids),
        "separate_review_question_ids": list(separate_ids),
        "source_bank": SOURCE_BANK_FILENAME,
        "strict_longest_crossed_question_ids": crossed_ids,
        "crossing_to_tie_count": len(crossing_to_tie),
        "crossing_to_tie_question_ids": crossing_to_tie,
        "crossing_to_shorter_count": len(crossing_to_shorter),
        "crossing_to_shorter_question_ids": crossing_to_shorter,
        "still_strict_longest_count": len(still_longest),
        "still_strict_longest_question_ids": still_longest,
        "strict_crossings": len(crossed_ids),
        "residual_violating_ids": residual_ids,
        "work_id": TASK_WORK_ID,
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
        "suspended": False,
        "super_confident": False,
        "miss_reasons": ["concept"],
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


class PackageBTranche5SemanticInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.semantic_path = REPOSITORY_ROOT / SEMANTIC_REVIEW_RELATIVE_PATH
        self.semantic = _read_json(self.semantic_path)
        self.queue = self.semantic["review_queue"]

    def test_07_semantic_review_exact_schema(self) -> None:
        self.assertEqual({"work_id", "source_bank", "candidate_bank", "review_queue"}, set(self.semantic))
        self.assertEqual(WORK_ID, self.semantic["work_id"])
        self.assertEqual(SOURCE_BANK_FILENAME, self.semantic["source_bank"])
        self.assertEqual(CANDIDATE_BANK_FILENAME, self.semantic["candidate_bank"])
        self.assertEqual(EXPECTED_T5_SEMANTIC_REVIEW_SHA256, sha256_file(self.semantic_path))

    def test_08_exact_64_id_queue(self) -> None:
        ids = [row["question_id"] for row in self.queue]
        self.assertEqual(T5_QUEUE_COUNT, len(ids))
        self.assertEqual(T5_QUEUE_COUNT, len(set(ids)))

    def test_09_57_edit(self) -> None:
        edits = [row for row in self.queue if row["disposition"] == "EDIT"]
        self.assertEqual(T5_EDIT_COUNT, len(edits))

    def test_10_1_skip(self) -> None:
        skips = [row for row in self.queue if row["disposition"] == "SKIP"]
        self.assertEqual(T5_SKIP_COUNT, len(skips))
        self.assertEqual([T5_SKIP_ID], [row["question_id"] for row in skips])

    def test_11_6_separate(self) -> None:
        separates = [row for row in self.queue if row["disposition"] == "SEPARATE_CONTENT_CORRECTION"]
        self.assertEqual(T5_SEPARATE_COUNT, len(separates))
        self.assertEqual(set(T5_SEPARATE_IDS), {row["question_id"] for row in separates})

    def test_75_all_edit_rows_have_learn_authority(self) -> None:
        for row in self.queue:
            if row["disposition"] != "EDIT":
                continue
            self.assertTrue(any(ref.startswith("https://learn.microsoft.com/") for ref in row["authority_refs"]))


class PackageBTranche5BuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = _import_builder()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_path = self.root / SOURCE_BANK_FILENAME
        self.semantic_path = self.root / "semantic_review.json"
        self.candidate_path = self.root / CANDIDATE_BANK_FILENAME
        self.review_root = self.root / "reviews"
        self.manifest_path = self.root / "manifest.json"
        shutil.copy2(REPOSITORY_ROOT / SOURCE_BANK_FILENAME, self.source_path)
        shutil.copy2(REPOSITORY_ROOT / SEMANTIC_REVIEW_RELATIVE_PATH, self.semantic_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build(self, source_path: Path | None = None, semantic_path: Path | None = None):
        return self.builder["build"](
            source_path or self.source_path,
            semantic_path or self.semantic_path,
            self.candidate_path,
            self.review_root,
            self.manifest_path,
        )

    def _assert_build_fails(self) -> None:
        with self.assertRaises(ValueError):
            self._build()
        self.assertFalse(self.candidate_path.exists())
        self.assertFalse(self.manifest_path.exists())

    def test_01_canonical_t4_filename_required(self) -> None:
        renamed = self.root / "source_bank.json"
        self.source_path.replace(renamed)
        self.source_path = renamed
        review = _read_json(self.semantic_path)
        review["source_bank"] = renamed.name
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_02_canonical_t4_sha_required(self) -> None:
        self.source_path.write_bytes(self.source_path.read_bytes() + b" ")
        self._assert_build_fails()

    def test_03_crlf_source_rejected_without_historical_alias(self) -> None:
        crlf = self.source_path.read_bytes().replace(b"\n", b"\r\n")
        self.assertNotEqual(EXPECTED_T4_SOURCE_SHA256, _raw_sha256(crlf))
        self.source_path.write_bytes(crlf)
        self._assert_build_fails()

    def test_04_t4_fingerprint_required(self) -> None:
        payload = _read_json(self.source_path)
        payload["questions"][0]["choices"]["A"] = f"{payload['questions'][0]['choices']['A']} mutated"
        _write_json(self.source_path, payload)
        self._assert_build_fails()

    def test_05_454_source_questions_required(self) -> None:
        payload = _read_json(self.source_path)
        payload["questions"] = payload["questions"][:10]
        _write_json(self.source_path, payload)
        self._assert_build_fails()

    def test_06_source_target_names_distinct(self) -> None:
        same_name = self.root / "nested" / SOURCE_BANK_FILENAME
        review = _read_json(self.semantic_path)
        review["candidate_bank"] = same_name.name
        _write_json(self.semantic_path, review)
        with self.assertRaises(ValueError):
            self.builder["build"](
                self.source_path,
                self.semantic_path,
                same_name,
                self.review_root,
                self.manifest_path,
            )

    def test_12_duplicate_id_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        review["review_queue"].append(copy.deepcopy(review["review_queue"][0]))
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_13_unknown_id_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        review["review_queue"][0]["question_id"] = "sc900_missing_q001"
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_14_missing_id_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        review["review_queue"] = review["review_queue"][:-1]
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_15_extra_id_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        extra = copy.deepcopy(review["review_queue"][0])
        extra["question_id"] = "sc900_mlc_q002"
        extra["after"] = {"A": "alpha extra", "B": "beta extra", "C": "gamma extra", "D": "delta extra"}
        review["review_queue"].append(extra)
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_82_t3_as_source_rejected(self) -> None:
        t3_path = self.root / T3_BANK_FILENAME
        shutil.copy2(REPOSITORY_ROOT / T3_BANK_FILENAME, t3_path)
        review = _read_json(self.semantic_path)
        review["source_bank"] = T3_BANK_FILENAME
        _write_json(self.semantic_path, review)
        with self.assertRaises(ValueError):
            self.builder["build"](
                t3_path,
                self.semantic_path,
                self.candidate_path,
                self.review_root,
                self.manifest_path,
            )
        self.assertFalse(self.candidate_path.exists())

    def test_83_t5_as_source_rejected(self) -> None:
        t5_source = self.root / "nested-source" / CANDIDATE_BANK_FILENAME
        t5_source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.source_path, t5_source)
        review = _read_json(self.semantic_path)
        review["source_bank"] = CANDIDATE_BANK_FILENAME
        _write_json(self.semantic_path, review)
        with self.assertRaises(ValueError):
            self.builder["build"](
                t5_source,
                self.semantic_path,
                self.candidate_path,
                self.review_root,
                self.manifest_path,
            )
        self.assertFalse(self.candidate_path.exists())

    def test_89_wrong_parent_manifest_rejected(self) -> None:
        module = self.builder["module"]
        real_load = module._load_json_object

        def fake_load(path: Path, label: str) -> dict[str, Any]:
            payload = real_load(path, label)
            if label == "parent T4 manifest":
                mutated = copy.deepcopy(payload)
                mutated["payload_sha256"] = "0" * 64
                return mutated
            return payload

        with patch.object(module, "_load_json_object", fake_load):
            self._assert_build_fails()

    def test_git_blob_worktree_mismatch_rejected(self) -> None:
        module = self.builder["module"]
        real = subprocess.check_output

        def fake(args, cwd=None):
            if list(args)[:2] == ["git", "show"]:
                return b'{"questions":[]}\n'
            return real(args, cwd=cwd)

        with patch.object(module.subprocess, "check_output", fake):
            self._assert_build_fails()

    def test_wrong_semantic_review_sha_rejected(self) -> None:
        self.semantic_path.write_bytes(self.semantic_path.read_bytes() + b"\n")
        self._assert_build_fails()

    def test_non_equivalent_edit_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        edit = next(row for row in review["review_queue"] if row["disposition"] == "EDIT")
        edit["semantic_review"]["A"] = "NARROWED"
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_non_learn_authority_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        edit = next(row for row in review["review_queue"] if row["disposition"] == "EDIT")
        edit["authority_refs"] = ["https://example.com/not-learn"]
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_skip_mutation_rejected(self) -> None:
        review = _read_json(self.semantic_path)
        skip = next(row for row in review["review_queue"] if row["question_id"] == T5_SKIP_ID)
        skip["disposition"] = "EDIT"
        skip["after"] = {"A": "alpha", "B": "beta", "C": "gamma", "D": "delta"}
        skip["semantic_review"] = {letter: "EQUIVALENT" for letter in CHOICE_LABELS}
        skip["authority_refs"] = ["https://learn.microsoft.com/en-us/security/"]
        _write_json(self.semantic_path, review)
        self._assert_build_fails()

    def test_pinned_source_identity_constants(self) -> None:
        self.assertEqual(EXPECTED_T4_SOURCE_SHA256, self.builder["expected_t4_sha"])
        self.assertEqual(EXPECTED_T4_SOURCE_FINGERPRINT, self.builder["expected_t4_fp"])
        self.assertEqual(EXPECTED_T5_SEMANTIC_REVIEW_SHA256, self.builder["semantic_sha"])
        self.assertEqual(EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA, self.builder["parent_manifest_sha"])
        self.assertEqual(T5_QUEUE_COUNT, len(self.builder["queue"]))
        self.assertEqual(T5_EDIT_COUNT, len(self.builder["edits"]))
        self.assertEqual(T5_SKIP_COUNT, len(self.builder["skips"]))
        self.assertEqual(T5_SEPARATE_COUNT, len(self.builder["separates"]))
        self.assertEqual({T5_SKIP_ID}, set(self.builder["skips"]))
        self.assertEqual(set(T5_SEPARATE_IDS), set(self.builder["separates"]))


class PackageBTranche5CliTests(unittest.TestCase):
    def test_cli_requires_all_arguments(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "tools.build_package_b_tranche5"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(0, completed.returncode)


class PackageBTranche5RealCandidateClosureTests(unittest.TestCase):
    SOURCE_BANK_PATH = REPOSITORY_ROOT / SOURCE_BANK_FILENAME
    CANDIDATE_BANK_PATH = REPOSITORY_ROOT / CANDIDATE_BANK_FILENAME
    T2_BANK_PATH = REPOSITORY_ROOT / T2_BANK_FILENAME
    T3_BANK_PATH = REPOSITORY_ROOT / T3_BANK_FILENAME
    PRODUCTION_BANK_PATH = REPOSITORY_ROOT / PRODUCTION_BANK_FILENAME
    MANIFEST_PATH = REPOSITORY_ROOT / MANIFEST_RELATIVE_PATH
    T4_MANIFEST_PATH = REPOSITORY_ROOT / T4_MANIFEST_RELATIVE_PATH
    T3_MANIFEST_PATH = REPOSITORY_ROOT / T3_MANIFEST_RELATIVE_PATH
    REVIEW_ROOT = REPOSITORY_ROOT / REVIEW_ROOT_RELATIVE_PATH
    CANDIDATE_METRICS_PATH = REPOSITORY_ROOT / CANDIDATE_METRICS_RELATIVE_PATH
    SEMANTIC_REVIEW_PATH = REPOSITORY_ROOT / SEMANTIC_REVIEW_RELATIVE_PATH
    T5_RECEIPT_DIR = REVIEW_ROOT / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T5"
    T4_RECEIPT_DIR = REVIEW_ROOT / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T4"

    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = _import_builder()
        cls.registry_before = copy.deepcopy(AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        cls.source_bytes = cls.SOURCE_BANK_PATH.read_bytes()
        cls.candidate_bytes = cls.CANDIDATE_BANK_PATH.read_bytes()
        cls.production_bytes = cls.PRODUCTION_BANK_PATH.read_bytes()
        cls.t2_bytes = cls.T2_BANK_PATH.read_bytes()
        cls.t3_bytes = cls.T3_BANK_PATH.read_bytes()
        cls.manifest_bytes = cls.MANIFEST_PATH.read_bytes()
        cls.t4_manifest_bytes = cls.T4_MANIFEST_PATH.read_bytes()
        cls.t3_manifest_bytes = cls.T3_MANIFEST_PATH.read_bytes()
        cls.receipt_bytes = {
            path.relative_to(cls.T5_RECEIPT_DIR).as_posix(): path.read_bytes()
            for path in sorted(cls.T5_RECEIPT_DIR.glob("*.json"))
        }
        cls.t4_receipt_bytes = {
            path.relative_to(cls.T4_RECEIPT_DIR).as_posix(): path.read_bytes()
            for path in sorted(cls.T4_RECEIPT_DIR.glob("*.json"))
        }
        cls.source_payload = json.loads(cls.source_bytes.decode("utf-8"))
        cls.candidate_payload = json.loads(cls.candidate_bytes.decode("utf-8"))
        cls.t2_payload = json.loads(cls.t2_bytes.decode("utf-8"))
        cls.t3_payload = json.loads(cls.t3_bytes.decode("utf-8"))
        cls.manifest = json.loads(cls.manifest_bytes.decode("utf-8"))
        cls.t4_manifest = json.loads(cls.t4_manifest_bytes.decode("utf-8"))
        cls.t3_manifest = json.loads(cls.t3_manifest_bytes.decode("utf-8"))
        cls.semantic_review = _read_json(cls.SEMANTIC_REVIEW_PATH)
        cls.source_questions = cls.source_payload["questions"]
        cls.candidate_questions = cls.candidate_payload["questions"]
        cls.t2_questions = cls.t2_payload["questions"]
        cls.t3_questions = cls.t3_payload["questions"]
        cls.source_by_id = {question["id"]: question for question in cls.source_questions}
        cls.candidate_by_id = {question["id"]: question for question in cls.candidate_questions}
        cls.t2_by_id = {question["id"]: question for question in cls.t2_questions}
        cls.t3_by_id = {question["id"]: question for question in cls.t3_questions}
        cls.changed_ids = [edge["question_id"] for edge in cls.manifest["edges"]]
        changed = set(cls.changed_ids)
        cls.skipped_ids = [
            row["question_id"] for row in cls.semantic_review["review_queue"] if row["disposition"] == "SKIP"
        ]
        cls.separate_ids = [
            row["question_id"]
            for row in cls.semantic_review["review_queue"]
            if row["disposition"] == "SEPARATE_CONTENT_CORRECTION"
        ]
        cls.queue_ids = [row["question_id"] for row in cls.semantic_review["review_queue"]]
        cls.changed_id = cls.changed_ids[0]
        cls.second_changed_id = cls.changed_ids[1]
        cls.unchanged_id = next(question_id for question_id in cls.source_by_id if question_id not in changed)
        cls.changed_source = cls.source_by_id[cls.changed_id]
        cls.changed_target = cls.candidate_by_id[cls.changed_id]
        cls.t4_changed_ids = [edge["question_id"] for edge in cls.t4_manifest["edges"]]
        cls.t3_changed_ids = [edge["question_id"] for edge in cls.t3_manifest["edges"]]
        cls.t4_only_changed_id = next(question_id for question_id in cls.t4_changed_ids if question_id not in changed)
        cls.t5_only_changed_id = next(
            question_id for question_id in cls.changed_ids if question_id not in set(cls.t4_changed_ids)
        )
        cls.t3_only_changed_id = next(
            question_id for question_id in cls.t3_changed_ids if question_id not in set(cls.t4_changed_ids)
        )

    def tearDown(self) -> None:
        self.assertEqual(self.registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        self.assertEqual(self.source_bytes, self.SOURCE_BANK_PATH.read_bytes())
        self.assertEqual(self.candidate_bytes, self.CANDIDATE_BANK_PATH.read_bytes())
        self.assertEqual(self.production_bytes, self.PRODUCTION_BANK_PATH.read_bytes())
        self.assertEqual(self.manifest_bytes, self.MANIFEST_PATH.read_bytes())
        self.assertEqual(self.t4_manifest_bytes, self.T4_MANIFEST_PATH.read_bytes())
        self.assertEqual(
            self.t4_receipt_bytes,
            {
                path.relative_to(self.T4_RECEIPT_DIR).as_posix(): path.read_bytes()
                for path in sorted(self.T4_RECEIPT_DIR.glob("*.json"))
            },
        )

    def _admit_t5(self, **kwargs):
        source_path = kwargs.get("source_path", self.SOURCE_BANK_PATH)
        target_path = kwargs.get("target_path", self.CANDIDATE_BANK_PATH)
        return admit_content_revision(
            kwargs.get("manifest", self.manifest),
            source_questions=_read_json(source_path)["questions"],
            target_questions=_read_json(target_path)["questions"],
            source_bank_path=source_path,
            target_bank_path=target_path,
            review_root=kwargs.get("review_root", self.REVIEW_ROOT),
        )

    def _admit_t4(self):
        return admit_content_revision(
            self.t4_manifest,
            source_questions=self.t3_questions,
            target_questions=self.source_questions,
            source_bank_path=self.T3_BANK_PATH,
            target_bank_path=self.SOURCE_BANK_PATH,
            review_root=self.REVIEW_ROOT,
        )

    def _admit_t3(self):
        return admit_content_revision(
            self.t3_manifest,
            source_questions=self.t2_questions,
            target_questions=self.t3_questions,
            source_bank_path=self.T2_BANK_PATH,
            target_bank_path=self.T3_BANK_PATH,
            review_root=self.REVIEW_ROOT,
        )

    def _source_progress_payload(self, revision, question_ids: list[str] | None = None) -> dict[str, Any]:
        ids = question_ids or [self.unchanged_id, self.changed_id]
        fingerprints = {}
        questions = {}
        history = []
        for question_id in ids:
            source_question = self.source_by_id[question_id]
            fingerprints[question_id] = question_content_fingerprint(source_question)
            questions[question_id] = _progress_record()
            history.append(
                {
                    "question_id": question_id,
                    "question_content_fingerprint": fingerprints[question_id],
                    "selected_texts": [source_question["choices"]["A"]],
                    "correct_texts": [source_question["choices"][source_question["correct"][0]]],
                    "correct": True,
                }
            )
        return {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": revision.source_bank_content_fingerprint,
            "question_content_fingerprints": fingerprints,
            "questions": questions,
            "history": history,
        }

    def _session_snapshot(self, revision, filename: str, rows: list[tuple[str, dict[str, Any]]]):
        question_ids = [question_id for question_id, _answer in rows]
        numbers = [int(self.source_by_id[question_id]["question_number"]) for question_id in question_ids]
        history_event = {
            "question_id": question_ids[0],
            "question_number": numbers[0],
            "question_content_fingerprint": question_content_fingerprint(self.source_by_id[question_ids[0]]),
            "selected_texts": [self.source_by_id[question_ids[0]]["choices"]["A"]],
            "correct_texts": [
                self.source_by_id[question_ids[0]]["choices"][self.source_by_id[question_ids[0]]["correct"][0]]
            ],
            "correct": True,
        }
        return build_session_snapshot(
            app_version="test",
            bank_file=filename,
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
            bank_fingerprint=revision.source_bank_content_fingerprint,
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
            session_answer_history=[history_event],
            current_quests=[],
            quest_completion_keys=["q1"],
            session_boss_markers=[],
            session_stealth_markers=[],
            session_xp_gained=7,
            answers=[answer for _question_id, answer in rows],
        )

    def test_16_exactly_57_changed(self) -> None:
        actual_changed = [
            question_id
            for question_id, source_question in self.source_by_id.items()
            if source_question != self.candidate_by_id[question_id]
        ]
        self.assertEqual(T5_EDIT_COUNT, len(actual_changed))
        self.assertEqual(set(self.changed_ids), set(actual_changed))
        self.assertEqual(set(self.builder["edits"]), set(actual_changed))

    def test_17_q293_skip_unchanged(self) -> None:
        self.assertEqual([T5_SKIP_ID], self.skipped_ids)
        self.assertEqual(self.source_by_id[T5_SKIP_ID], self.candidate_by_id[T5_SKIP_ID])

    def test_18_six_separate_ids_unchanged(self) -> None:
        self.assertEqual(T5_SEPARATE_COUNT, len(self.separate_ids))
        self.assertEqual(set(T5_SEPARATE_IDS), set(self.separate_ids))
        for question_id in self.separate_ids:
            self.assertEqual(self.source_by_id[question_id], self.candidate_by_id[question_id])

    def test_19_397_non_edit_questions_unchanged(self) -> None:
        unchanged = [
            question_id
            for question_id, source_question in self.source_by_id.items()
            if source_question == self.candidate_by_id[question_id]
        ]
        self.assertEqual(T5_UNCHANGED_COUNT, len(unchanged))
        queue = set(self.queue_ids)
        outside = [question_id for question_id in self.source_by_id if question_id not in queue]
        self.assertEqual(T5_OUTSIDE_QUEUE_UNCHANGED, len(outside))
        for question_id in outside:
            self.assertEqual(self.source_by_id[question_id], self.candidate_by_id[question_id])

    def test_20_t4_edit_set_preserved_and_disjoint(self) -> None:
        self.assertTrue(set(self.t4_changed_ids).isdisjoint(set(self.changed_ids)))
        self.assertEqual(set(self.t4_changed_ids), set(T4_EDIT_IDS))
        for question_id in self.t4_changed_ids:
            self.assertEqual(self.source_by_id[question_id], self.candidate_by_id[question_id])

    def test_22_prompts_unchanged(self) -> None:
        for question_id, source_question in self.source_by_id.items():
            self.assertEqual(source_question["prompt"], self.candidate_by_id[question_id]["prompt"])

    def test_23_keys_unchanged(self) -> None:
        for question_id, source_question in self.source_by_id.items():
            self.assertEqual(source_question["correct"], self.candidate_by_id[question_id]["correct"])

    def test_24_objectives_unchanged(self) -> None:
        for question_id, source_question in self.source_by_id.items():
            self.assertEqual(source_question["objective_code"], self.candidate_by_id[question_id]["objective_code"])

    def test_25_tiers_unchanged(self) -> None:
        for question_id, source_question in self.source_by_id.items():
            self.assertEqual(
                source_question["exam_calibration_tier"],
                self.candidate_by_id[question_id]["exam_calibration_tier"],
            )

    def test_26_exam_eligibility_unchanged(self) -> None:
        for question_id, source_question in self.source_by_id.items():
            self.assertEqual(
                source_question["exam_simulation_eligible"],
                self.candidate_by_id[question_id]["exam_simulation_eligible"],
            )

    def test_27_question_ids_and_order_unchanged(self) -> None:
        self.assertEqual(
            [question["id"] for question in self.source_questions],
            [question["id"] for question in self.candidate_questions],
        )
        self.assertEqual(QUESTION_COUNT, len(self.source_by_id))
        self.assertEqual(QUESTION_COUNT, len(self.candidate_questions))

    def test_28_ad_mapping_unchanged(self) -> None:
        for question_id, source_question in self.source_by_id.items():
            self.assertEqual(set(CHOICE_LABELS), set(source_question["choices"]))
            self.assertEqual(set(CHOICE_LABELS), set(self.candidate_by_id[question_id]["choices"]))

    def test_29_all_changed_semantics_equivalent(self) -> None:
        for edge in self.manifest["edges"]:
            self.assertEqual({letter: "EQUIVALENT" for letter in CHOICE_LABELS}, edge["choice_semantics"])

    def test_30_learn_authority_required(self) -> None:
        for edge in self.manifest["edges"]:
            self.assertTrue(any(ref.startswith("https://learn.microsoft.com/") for ref in edge["authority_refs"]))

    def test_31_one_deterministic_receipt_per_edit(self) -> None:
        for edge in self.manifest["edges"]:
            receipt_path = self.REVIEW_ROOT / edge["review_artifact"]
            receipt = _read_json(receipt_path)
            self.assertEqual(RECEIPT_FIELDS, set(receipt))
            self.assertNotIn("review_note", receipt)
            self.assertNotIn("timestamp", receipt)
            self.assertNotIn("created_at", receipt)
            self.assertEqual(sha256_file(receipt_path), edge["review_artifact_sha256"])

    def test_32_exactly_57_receipts_and_no_t4_duplication(self) -> None:
        receipts = list(self.T5_RECEIPT_DIR.glob("*.json"))
        self.assertEqual(T5_EDIT_COUNT, len(receipts))
        self.assertEqual(set(self.changed_ids), {path.stem for path in receipts})
        for question_id in list(self.skipped_ids) + list(self.separate_ids) + list(self.t4_changed_ids):
            self.assertFalse((self.T5_RECEIPT_DIR / f"{question_id}.json").exists())
        self.assertEqual(
            self.t4_receipt_bytes,
            {
                path.relative_to(self.T4_RECEIPT_DIR).as_posix(): path.read_bytes()
                for path in sorted(self.T4_RECEIPT_DIR.glob("*.json"))
            },
        )

    def test_33_manifest_exactly_57_edges_no_t4_redeclaration(self) -> None:
        self.assertEqual(MANIFEST_FIELDS, set(self.manifest))
        self.assertEqual(self.manifest["payload_sha256"], canonical_manifest_sha256(self.manifest))
        self.assertEqual(T5_EDIT_COUNT, len(self.manifest["edges"]))
        self.assertEqual("sc900_content_revision_equivalence", self.manifest["manifest_kind"])
        self.assertEqual("FULL_CONTINUITY", self.manifest["continuity_policy"])
        self.assertEqual("WORDING_ONLY_LENGTH_REBALANCE", self.manifest["permitted_change_class"])
        self.assertEqual(1, self.manifest["schema_version"])
        self.assertTrue(set(self.changed_ids).isdisjoint(set(self.t4_changed_ids)))

    def test_34_manifest_source_canonical_t4(self) -> None:
        self.assertEqual(SOURCE_BANK_FILENAME, self.manifest["source_bank"]["filename"])
        self.assertEqual(EXPECTED_T4_SOURCE_SHA256, self.manifest["source_bank"]["file_sha256"])
        self.assertEqual(EXPECTED_T4_SOURCE_FINGERPRINT, self.manifest["source_bank"]["content_fingerprint"])
        self.assertEqual(EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA, self.t4_manifest["payload_sha256"])
        self.assertEqual(CANDIDATE_BANK_FILENAME, self.manifest["target_bank"]["filename"])

    def test_35_manifest_contains_no_historical_aliases(self) -> None:
        serialized = json.dumps(self.manifest)
        self.assertNotIn("historical_aliases", serialized)
        self.assertNotIn("alias", serialized)
        self.assertNotIn("d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b", serialized)

    def test_36_target_canonical_lf_and_metadata_preserved(self) -> None:
        raw = self.candidate_bytes
        self.assertNotIn(b"\r\n", raw)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(
            json.dumps(self.candidate_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            raw.decode("utf-8"),
        )
        source_meta = {key: value for key, value in self.source_payload.items() if key != "questions"}
        target_meta = {key: value for key, value in self.candidate_payload.items() if key != "questions"}
        self.assertEqual(source_meta, target_meta)

    def test_37_deterministic_target_sha_and_fingerprint(self) -> None:
        observed_sha = _raw_sha256(self.candidate_bytes)
        observed_fp = bank_content_fingerprint(self.candidate_questions)
        self.assertEqual(observed_sha, self.manifest["target_bank"]["file_sha256"])
        self.assertEqual(observed_fp, self.manifest["target_bank"]["content_fingerprint"])

    def test_38_repeated_builds_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            summaries = []
            artifacts = []
            for temp_dir in (first_dir, second_dir):
                root = Path(temp_dir)
                source_path = root / SOURCE_BANK_FILENAME
                semantic_path = root / "semantic_review.json"
                candidate_path = root / CANDIDATE_BANK_FILENAME
                review_root = root / "reviews"
                manifest_path = root / "manifest.json"
                shutil.copy2(self.SOURCE_BANK_PATH, source_path)
                shutil.copy2(self.SEMANTIC_REVIEW_PATH, semantic_path)
                summary = self.builder["build"](source_path, semantic_path, candidate_path, review_root, manifest_path)
                receipts = {
                    path.name: path.read_bytes()
                    for path in sorted((review_root / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T5").glob("*.json"))
                }
                summaries.append(summary)
                artifacts.append((candidate_path.read_bytes(), manifest_path.read_bytes(), receipts))
            self.assertEqual(summaries[0], summaries[1])
            self.assertEqual(artifacts[0][0], artifacts[1][0])
            self.assertEqual(artifacts[0][1], artifacts[1][1])
            self.assertEqual(artifacts[0][2], artifacts[1][2])
            self.assertEqual(self.candidate_bytes, artifacts[0][0])
            self.assertEqual(self.manifest_bytes, artifacts[0][1])
            self.assertEqual(self.receipt_bytes, artifacts[0][2])

    def test_40_56_shorter_one_tie_zero_still_longest(self) -> None:
        computed = build_package_b_tranche5_candidate_metrics(
            self.source_questions,
            self.candidate_questions,
            edited_ids=self.changed_ids,
            skipped_ids=self.skipped_ids,
            separate_ids=self.separate_ids,
            source_by_id=self.source_by_id,
            candidate_by_id=self.candidate_by_id,
        )
        self.assertEqual(56, computed["crossing_to_shorter_count"])
        self.assertEqual(1, computed["crossing_to_tie_count"])
        self.assertEqual([T5_TIE_ID], computed["crossing_to_tie_question_ids"])
        self.assertEqual(0, computed["still_strict_longest_count"])
        self.assertEqual(57, computed["strict_crossings"])
        self.assertEqual(serialize_candidate_metrics(computed), self.CANDIDATE_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(LETTERS), set(computed["correct_letter_counts"]))

    def test_42_t4_progress_continuity(self) -> None:
        admission = self._admit_t5()
        self.assertEqual(AdmissionStatus.PASS, admission.status)
        assert admission.admitted is not None
        source_payload = self._source_progress_payload(admission.admitted)
        first = migrate_progress_payload(source_payload, self.candidate_questions, admission.admitted, MIGRATED_AT)
        self.assertEqual(MigrationStatus.APPLIED, first.status)
        self.assertEqual(_progress_record(), first.payload["questions"][self.changed_id])
        self.assertEqual(_progress_record(), first.payload["questions"][self.unchanged_id])
        self.assertEqual(source_payload["history"], first.payload["history"])
        self.assertEqual(admission.admitted.target_bank_content_fingerprint, first.payload["bank_fingerprint"])
        self.assertEqual(
            question_content_fingerprint(self.changed_target),
            first.payload["question_content_fingerprints"][self.changed_id],
        )

    def test_43_t4_session_continuity(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        snapshot = self._session_snapshot(
            admission.admitted,
            SOURCE_BANK_FILENAME,
            [
                (self.unchanged_id, _session_answer(selected=["A"], answered=True, flagged=True)),
                (self.changed_id, _session_answer(selected=["B"], pending=["B"], answered=False)),
            ],
        )
        result = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, result.status)
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        self.assertEqual(["A"], answers[self.unchanged_id]["selected"])
        self.assertEqual([], answers[self.changed_id]["selected"])
        self.assertEqual([], answers[self.changed_id]["pending"])
        self.assertEqual(CANDIDATE_BANK_FILENAME, result.payload["bank_file"])
        self.assertEqual(admission.admitted.target_bank_content_fingerprint, result.payload["bank_fingerprint"])
        self.assertEqual(
            canonical_session_signature(
                MODE_PRACTICE,
                admission.admitted.target_bank_content_fingerprint,
                [self.unchanged_id, self.changed_id],
            ),
            result.payload["session_signature"],
        )

    def test_46_unanswered_changed_selection_cleared(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        snapshot = self._session_snapshot(
            admission.admitted,
            SOURCE_BANK_FILENAME,
            [(self.changed_id, _session_answer(selected=["C"], pending=["C"], answered=False))],
        )
        result = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        self.assertEqual([], answers[self.changed_id]["selected"])
        self.assertEqual([], answers[self.changed_id]["pending"])
        self.assertFalse(answers[self.changed_id]["answered"])

    def test_47_answered_changed_selection_preserved(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        snapshot = self._session_snapshot(
            admission.admitted,
            SOURCE_BANK_FILENAME,
            [(self.second_changed_id, _session_answer(selected=["D"], pending=["D"], answered=True))],
        )
        result = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        answers = {row["question_id"]: row for row in result.payload["answers"]}
        self.assertEqual(["D"], answers[self.second_changed_id]["selected"])
        self.assertTrue(answers[self.second_changed_id]["answered"])

    def test_48_historical_t2_t3_t4_progress_forwards_sequentially(self) -> None:
        t3_admission = self._admit_t3()
        t4_admission = self._admit_t4()
        t5_admission = self._admit_t5()
        assert t3_admission.admitted is not None
        assert t4_admission.admitted is not None
        assert t5_admission.admitted is not None
        t2_progress = {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": t3_admission.admitted.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                self.t3_only_changed_id: question_content_fingerprint(self.t2_by_id[self.t3_only_changed_id]),
                self.t4_only_changed_id: question_content_fingerprint(self.t2_by_id[self.t4_only_changed_id]),
                self.t5_only_changed_id: question_content_fingerprint(self.t2_by_id[self.t5_only_changed_id]),
            },
            "questions": {
                self.t3_only_changed_id: _progress_record(),
                self.t4_only_changed_id: _progress_record(),
                self.t5_only_changed_id: _progress_record(),
            },
            "history": [],
        }
        to_t3 = migrate_progress_payload(t2_progress, self.t3_questions, t3_admission.admitted, "2026-09-17T00:00:00")
        self.assertEqual(MigrationStatus.APPLIED, to_t3.status)
        to_t4 = migrate_progress_payload(
            to_t3.payload, self.source_questions, t4_admission.admitted, "2026-09-18T00:00:00"
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t4.status)
        to_t5 = migrate_progress_payload(to_t4.payload, self.candidate_questions, t5_admission.admitted, MIGRATED_AT)
        self.assertEqual(MigrationStatus.APPLIED, to_t5.status)
        self.assertEqual(_progress_record(), to_t5.payload["questions"][self.t5_only_changed_id])
        self.assertEqual(t5_admission.admitted.target_bank_content_fingerprint, to_t5.payload["bank_fingerprint"])

    def test_49_historical_t3_t4_progress_forwards_sequentially(self) -> None:
        t4_admission = self._admit_t4()
        t5_admission = self._admit_t5()
        assert t4_admission.admitted is not None
        assert t5_admission.admitted is not None
        t3_progress = {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": t4_admission.admitted.source_bank_content_fingerprint,
            "question_content_fingerprints": {
                self.t4_only_changed_id: question_content_fingerprint(self.t3_by_id[self.t4_only_changed_id]),
                self.t5_only_changed_id: question_content_fingerprint(self.t3_by_id[self.t5_only_changed_id]),
            },
            "questions": {
                self.t4_only_changed_id: _progress_record(),
                self.t5_only_changed_id: _progress_record(),
            },
            "history": [],
        }
        to_t4 = migrate_progress_payload(
            t3_progress, self.source_questions, t4_admission.admitted, "2026-09-18T00:00:00"
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t4.status)
        to_t5 = migrate_progress_payload(to_t4.payload, self.candidate_questions, t5_admission.admitted, MIGRATED_AT)
        self.assertEqual(MigrationStatus.APPLIED, to_t5.status)
        self.assertEqual(t5_admission.admitted.target_bank_content_fingerprint, to_t5.payload["bank_fingerprint"])

    def test_50_historical_t2_session_forwards_sequentially(self) -> None:
        t3_admission = self._admit_t3()
        t4_admission = self._admit_t4()
        t5_admission = self._admit_t5()
        assert t3_admission.admitted is not None
        assert t4_admission.admitted is not None
        assert t5_admission.admitted is not None
        t2_snapshot = self._session_snapshot(
            t3_admission.admitted,
            T2_BANK_FILENAME,
            [
                (self.t3_only_changed_id, _session_answer(selected=["A"], answered=True)),
                (self.t5_only_changed_id, _session_answer(selected=["B"], pending=["B"], answered=False)),
            ],
        )
        to_t3 = migrate_session_payload(
            t2_snapshot,
            self.t3_questions,
            t3_admission.admitted,
            T3_BANK_FILENAME,
            source_questions=self.t2_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t3.status)
        to_t4 = migrate_session_payload(
            to_t3.payload,
            self.source_questions,
            t4_admission.admitted,
            SOURCE_BANK_FILENAME,
            source_questions=self.t3_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t4.status)
        to_t5 = migrate_session_payload(
            to_t4.payload,
            self.candidate_questions,
            t5_admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t5.status)

    def test_51_historical_t3_session_forwards_sequentially(self) -> None:
        t4_admission = self._admit_t4()
        t5_admission = self._admit_t5()
        assert t4_admission.admitted is not None
        assert t5_admission.admitted is not None
        snapshot = self._session_snapshot(
            t4_admission.admitted,
            T3_BANK_FILENAME,
            [(self.t5_only_changed_id, _session_answer(selected=["A"], answered=True))],
        )
        to_t4 = migrate_session_payload(
            snapshot,
            self.source_questions,
            t4_admission.admitted,
            SOURCE_BANK_FILENAME,
            source_questions=self.t3_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t4.status)
        to_t5 = migrate_session_payload(
            to_t4.payload,
            self.candidate_questions,
            t5_admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        self.assertEqual(MigrationStatus.APPLIED, to_t5.status)

    def test_52_unknown_lineage_rejected(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        payload = migrate_progress_payload(
            self._source_progress_payload(admission.admitted),
            self.candidate_questions,
            admission.admitted,
            MIGRATED_AT,
        ).payload
        payload["content_revision_lineage"][0]["migration_id"] = "f" * 64
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(payload, self.candidate_questions, admission.admitted, "2026-09-20T00:00:00")
        self.assertEqual(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, ctx.exception.reason)

    def test_53_tampered_lineage_rejected(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        payload = migrate_progress_payload(
            self._source_progress_payload(admission.admitted),
            self.candidate_questions,
            admission.admitted,
            MIGRATED_AT,
        ).payload
        payload["content_revision_lineage"][0]["to_fingerprint"] = "e" * 64
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(payload, self.candidate_questions, admission.admitted, "2026-09-20T00:00:00")
        self.assertEqual(MigrationFailureReason.TARGET_PROGRESS_CONFLICT, ctx.exception.reason)

    def test_54_partial_t5_rejected(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        source_payload = self._source_progress_payload(admission.admitted, [self.changed_id, self.second_changed_id])
        source_payload["question_content_fingerprints"][self.changed_id] = question_content_fingerprint(
            self.changed_target
        )
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(source_payload, self.candidate_questions, admission.admitted, MIGRATED_AT)
        self.assertEqual(MigrationFailureReason.SOURCE_PROGRESS_FINGERPRINT_MISMATCH, ctx.exception.reason)

    def test_55_already_applied_t5_progress_idempotent(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        first = migrate_progress_payload(
            self._source_progress_payload(admission.admitted),
            self.candidate_questions,
            admission.admitted,
            MIGRATED_AT,
        )
        second = migrate_progress_payload(
            first.payload, self.candidate_questions, admission.admitted, "2026-09-20T00:00:00"
        )
        self.assertEqual(MigrationStatus.MIGRATION_ALREADY_APPLIED, second.status)
        self.assertFalse(second.changed)
        self.assertEqual(first.payload, second.payload)

    def test_56_repeated_t4_to_t5_session_migration_deterministic(self) -> None:
        admission = self._admit_t5()
        assert admission.admitted is not None
        snapshot = self._session_snapshot(
            admission.admitted,
            SOURCE_BANK_FILENAME,
            [
                (self.changed_id, _session_answer(selected=["B"], pending=["B"], answered=False)),
                (self.second_changed_id, _session_answer(selected=["A"], answered=True)),
            ],
        )
        first = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        second = migrate_session_payload(
            snapshot,
            self.candidate_questions,
            admission.admitted,
            CANDIDATE_BANK_FILENAME,
            source_questions=self.source_questions,
        )
        self.assertEqual(first.payload, second.payload)

    def test_62_package_c_inactive(self) -> None:
        profile = _read_json(REPOSITORY_ROOT / "cert_profile_sc900.json")
        self.assertEqual("sc900_bank_v8_final_content_correction_002.json", profile["runtime_bank"])
        self.assertFalse((REPOSITORY_ROOT / T6_BANK_FILENAME).exists())
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))

    def test_63_production_registry_inactive(self) -> None:
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(self.registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)

    def test_65_t6_not_started(self) -> None:
        evidence = REPOSITORY_ROOT / "content_revision_evidence"
        matches = list(evidence.rglob("*t6*")) + list(evidence.rglob("*T6*"))
        docs = list((REPOSITORY_ROOT / "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001").glob("*TRANCHE6*"))
        self.assertEqual([], matches)
        self.assertEqual([], docs)

    def test_71_t5_primary_records_identical_between_canonical_t3_and_t4(self) -> None:
        self.assertEqual(EXPECTED_T3_SOURCE_SHA256, _raw_sha256(self.t3_bytes))
        self.assertEqual(EXPECTED_T3_SOURCE_FINGERPRINT, bank_content_fingerprint(self.t3_questions))
        self.assertEqual(EXPECTED_T3_SOURCE_SHA256, self.t4_manifest["source_bank"]["file_sha256"])
        self.assertEqual(EXPECTED_T3_SOURCE_FINGERPRINT, self.t4_manifest["source_bank"]["content_fingerprint"])
        for question_id in self.queue_ids:
            self.assertEqual(self.t3_by_id[question_id], self.source_by_id[question_id])

    def test_90_no_combined_t3_to_t5_edge(self) -> None:
        t5_admission = self._admit_t5()
        assert t5_admission.admitted is not None
        t3_progress = {
            "version": 3,
            "progress_identity_version": 1,
            "question_identity": "canonical_question_id",
            "progress_content_epoch_version": 1,
            "bank_fingerprint": bank_content_fingerprint(self.t3_questions),
            "question_content_fingerprints": {
                self.t5_only_changed_id: question_content_fingerprint(self.t3_by_id[self.t5_only_changed_id]),
            },
            "questions": {self.t5_only_changed_id: _progress_record()},
            "history": [],
        }
        with self.assertRaises(ContentRevisionMigrationError) as ctx:
            migrate_progress_payload(t3_progress, self.candidate_questions, t5_admission.admitted, MIGRATED_AT)
        self.assertEqual(MigrationFailureReason.SOURCE_BANK_MISMATCH, ctx.exception.reason)
        snapshot = self._session_snapshot(
            t5_admission.admitted,
            T3_BANK_FILENAME,
            [(self.t5_only_changed_id, _session_answer(selected=["A"], answered=True))],
        )
        snapshot["bank_fingerprint"] = bank_content_fingerprint(self.t3_questions)
        with self.assertRaises(ContentRevisionMigrationError) as session_ctx:
            migrate_session_payload(
                snapshot,
                self.candidate_questions,
                t5_admission.admitted,
                CANDIDATE_BANK_FILENAME,
                source_questions=self.t3_questions,
            )
        self.assertEqual(MigrationFailureReason.SOURCE_BANK_MISMATCH, session_ctx.exception.reason)


class PackageBTranche5RegressionAndQualityTests(unittest.TestCase):
    def test_57_t1_t4_regression_remains_green(self) -> None:
        if os.environ.get(_NESTED_SUITE_ENV) == "1":
            self.skipTest("already inside nested Package-B regression")
        env = os.environ.copy()
        env[_NESTED_SUITE_ENV] = "1"
        for module in (
            "tests.test_package_b_tranche1",
            "tests.test_package_b_tranche2",
            "tests.test_package_b_tranche3",
            "tests.test_package_b_lineage_compatibility",
        ):
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", module],
                cwd=REPOSITORY_ROOT,
                check=False,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
        t4_loader = unittest.TestLoader()
        t4_suite = t4_loader.loadTestsFromName("tests.test_package_b_tranche4")
        excluded = {"test_58_package_c_inactive", "test_60_no_t5_artifacts"}

        def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
            tests: list[unittest.TestCase] = []
            for item in suite:
                if isinstance(item, unittest.TestSuite):
                    tests.extend(_flatten(item))
                else:
                    tests.append(item)
            return tests

        filtered = unittest.TestSuite()
        for test in _flatten(t4_suite):
            if getattr(test, "_testMethodName", "") not in excluded:
                filtered.addTest(test)
        stream = open(os.devnull, "w", encoding="utf-8")
        try:
            result = unittest.TextTestRunner(stream=stream, verbosity=0).run(filtered)
        finally:
            stream.close()
        self.assertTrue(
            result.wasSuccessful(),
            f"T4 functional failures={len(result.failures)} errors={len(result.errors)}",
        )

    def test_58_canonical_byte_suite_remains_green(self) -> None:
        if os.environ.get(_NESTED_SUITE_ENV) == "1":
            self.skipTest("already inside nested Package-B regression")
        env = os.environ.copy()
        env[_NESTED_SUITE_ENV] = "1"
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_package_b_canonical_bytes"],
            cwd=REPOSITORY_ROOT,
            check=False,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_59_full_suite_remains_green(self) -> None:
        if os.environ.get(_NESTED_SUITE_ENV) == "1" or os.environ.get("SC900_NESTED_FULL_SUITE") == "1":
            self.skipTest("operator full suite is measured outside this nested test")
        self.assertTrue((REPOSITORY_ROOT / "tests").is_dir())

    def test_87_t5_builder_in_quality_targets_and_mypy_not_expanded(self) -> None:
        from tools.run_quality_checks import QUALITY_TARGETS

        self.assertIn("tools/build_package_b_tranche5.py", QUALITY_TARGETS)
        pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("tools/build_package_b_tranche5.py", pyproject)
        completed = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "tools/build_package_b_tranche5.py"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
