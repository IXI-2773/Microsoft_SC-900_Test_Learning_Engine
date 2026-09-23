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

from answer_length_audit import audit_questions
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
from question_identity import question_content_fingerprint
from session_identity import canonical_session_signature
from session_store import build_session_snapshot
from tools.build_package_b_tranche1 import build_package_b_tranche1
from tools.run_quality_checks import QUALITY_TARGETS

QUESTION_COUNT = 454
CHOICE_LABELS = ("A", "B", "C", "D")
MS_LEARN_REF = "https://learn.microsoft.com/en-us/security/zero-trust/"
WORK_ID = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / PACKAGE-B / TRANCHE-1"
TASK5_WORK_ID = "SC900-PACKAGE-B-TRANCHE1-TASK5-REAL-CANDIDATE-CONTINUITY-LEAKAGE-001"
SOURCE_BANK_FILENAME = "sc900_bank_v8_final.json"
CANDIDATE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t1.json"
MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t1.json"
REVIEW_ROOT_RELATIVE_PATH = "content_revision_evidence/reviews"
BASELINE_METRICS_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/08-PACKAGE-B-TRANCHE1-BASELINE.json"
)
CANDIDATE_METRICS_RELATIVE_PATH = (
    "docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/10-PACKAGE-B-TRANCHE1-CANDIDATE-METRICS.json"
)
LEAKAGE_METRIC_KEYS = (
    "strict_longest_correct",
    "strict_shortest_correct",
    "unique_longest_heuristic",
    "unique_shortest_heuristic",
)
EXPECTED_BASELINE_STRICT_LONGEST_COUNT = 291
EXPECTED_CANDIDATE_STRICT_LONGEST_COUNT = 287
EXPECTED_STRICT_LONGEST_DENOMINATOR = 449
EXPECTED_STRICT_LONGEST_DELTA = -4
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


def _question(index: int) -> dict[str, Any]:
    question_id = f"sc900_syn_{index:03d}"
    correct = CHOICE_LABELS[(index - 1) % len(CHOICE_LABELS)]
    return {
        "id": question_id,
        "question_number": index,
        "prompt": f"Which synthetic statement is correct for {question_id}?",
        "choices": {
            "A": f"{question_id} alpha statement",
            "B": f"{question_id} beta statement",
            "C": f"{question_id} gamma statement",
            "D": f"{question_id} delta statement",
        },
        "correct": [correct],
        "general_explanation": f"Synthetic explanation for {question_id}.",
        "choice_explanations": {
            "A": f"Explanation A for {question_id}.",
            "B": f"Explanation B for {question_id}.",
            "C": f"Explanation C for {question_id}.",
            "D": f"Explanation D for {question_id}.",
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
        "title": "SC-900 Synthetic Package-B Bank",
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


def build_package_b_tranche1_candidate_metrics(
    source_questions: list[dict[str, Any]],
    candidate_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_audit = audit_questions(source_questions)
    candidate_audit = audit_questions(candidate_questions)
    baseline_metrics = _metric_subset(baseline_audit)
    candidate_metrics = _metric_subset(candidate_audit)
    delta = _metric_delta(baseline_metrics, candidate_metrics)
    closure_result = "PASS" if delta["strict_longest_correct_count"] < 0 else "FAIL"
    return {
        "analyzable_single_answer": candidate_audit["analyzable_single_answer"],
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "candidate_bank": CANDIDATE_BANK_FILENAME,
        "closure_result": closure_result,
        "delta": delta,
        "question_count": candidate_audit["question_count"],
        "skipped_question_ids": list(candidate_audit["skipped_question_ids"]),
        "source_bank": SOURCE_BANK_FILENAME,
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


class PackageBTranche1BuilderTests(unittest.TestCase):
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
        return build_package_b_tranche1(
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
        self.assertEqual(2, summary["review_count"])
        self.assertEqual(AdmissionStatus.PASS.value, summary["admission_status"])
        self.assertNotEqual(source_before, self.candidate_path.read_bytes())
        self.assertEqual(source_before, self.source_path.read_bytes())
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        json.dumps(summary, sort_keys=True)

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

        manifest = _read_json(self.manifest_path)
        self.assertEqual(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            self.manifest_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(MANIFEST_FIELDS, set(manifest))
        self.assertEqual(manifest["payload_sha256"], canonical_manifest_sha256(manifest))
        self.assertEqual(manifest["payload_sha256"], summary["manifest_sha256"])
        self.assertEqual(manifest["source_bank"]["file_sha256"], summary["source_file_sha256"])
        self.assertEqual(manifest["target_bank"]["file_sha256"], summary["target_file_sha256"])
        self.assertEqual(
            manifest["source_bank"]["content_fingerprint"],
            summary["source_bank_content_fingerprint"],
        )
        self.assertEqual(
            manifest["target_bank"]["content_fingerprint"],
            summary["target_bank_content_fingerprint"],
        )
        self.assertEqual(
            ["sc900_syn_001", "sc900_syn_002"],
            [edge["question_id"] for edge in manifest["edges"]],
        )
        for edge in manifest["edges"]:
            self.assertEqual(EDGE_FIELDS, set(edge))
            self.assertFalse(Path(edge["review_artifact"]).is_absolute())
            self.assertEqual(
                f"SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1/{edge['question_id']}.json",
                edge["review_artifact"],
            )
            receipt_path = self.review_root / edge["review_artifact"]
            receipt = _read_json(receipt_path)
            self.assertEqual(
                json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                receipt_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(RECEIPT_FIELDS, set(receipt))
            self.assertNotIn("review_note", receipt)
            self.assertEqual(sha256_file(receipt_path), edge["review_artifact_sha256"])
        receipt_dir = self.review_root / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1"
        self.assertEqual(2, len(list(receipt_dir.glob("*.json"))))

        admission = admit_content_revision(
            manifest,
            source_questions=source["questions"],
            target_questions=candidate["questions"],
            source_bank_path=self.source_path,
            target_bank_path=self.candidate_path,
            review_root=self.review_root,
        )
        self.assertEqual(AdmissionStatus.PASS, admission.status)
        self.assertEqual((), admission.reasons)
        self.assertIsNotNone(admission.admitted)

        first_bytes = {
            "candidate": self.candidate_path.read_bytes(),
            "manifest": self.manifest_path.read_bytes(),
            **{
                edge["question_id"]: (self.review_root / edge["review_artifact"]).read_bytes()
                for edge in manifest["edges"]
            },
        }
        self.assertEqual(summary, self._build())
        self.assertEqual(first_bytes["candidate"], self.candidate_path.read_bytes())
        self.assertEqual(first_bytes["manifest"], self.manifest_path.read_bytes())
        for edge in manifest["edges"]:
            self.assertEqual(
                first_bytes[edge["question_id"]],
                (self.review_root / edge["review_artifact"]).read_bytes(),
            )

    def test_source_and_candidate_filename_must_differ(self) -> None:
        review = self._semantic_review()
        same_name_candidate = self.root / "nested" / self.source_path.name
        review["candidate_bank"] = same_name_candidate.name
        self._write_semantic_review(review)
        with self.assertRaises(ValueError):
            build_package_b_tranche1(
                self.source_path,
                self.semantic_path,
                same_name_candidate,
                self.review_root,
                self.manifest_path,
            )
        self.assertFalse(same_name_candidate.exists())

    def test_output_path_cannot_overwrite_source(self) -> None:
        self._write_semantic_review(self._semantic_review())
        source_before = self.source_path.read_bytes()
        with self.assertRaises(ValueError):
            build_package_b_tranche1(
                self.source_path,
                self.semantic_path,
                self.candidate_path,
                self.review_root,
                self.source_path,
            )
        self.assertEqual(source_before, self.source_path.read_bytes())
        self.assertFalse(self.candidate_path.exists())

    def test_duplicate_review_queue_id_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"].append(copy.deepcopy(review["review_queue"][0]))
        self._assert_build_fails(review)

    def test_unknown_question_id_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["question_id"] = "sc900_syn_999"
        self._assert_build_fails(review)

    def test_edit_requires_microsoft_learn_authority(self) -> None:
        for authority_refs in (None, [], ["https://example.com/reference"]):
            with self.subTest(authority_refs=authority_refs):
                review = self._semantic_review()
                row = review["review_queue"][0]
                if authority_refs is None:
                    del row["authority_refs"]
                else:
                    row["authority_refs"] = authority_refs
                self._assert_build_fails(review)

    def test_non_equivalent_semantic_review_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["semantic_review"]["D"] = "CHANGED"
        self._assert_build_fails(review)

    def test_unchanged_edit_fails(self) -> None:
        review = self._semantic_review()
        question = self.source_payload["questions"][1]
        review["review_queue"][0]["after"] = copy.deepcopy(question["choices"])
        self._assert_build_fails(review)

    def test_edit_after_must_be_exact_ad_string_mapping(self) -> None:
        invalid_after_values = []
        missing = _after(self.source_payload["questions"][1])
        del missing["D"]
        invalid_after_values.append(missing)
        extra = _after(self.source_payload["questions"][1])
        extra["E"] = "extra"
        invalid_after_values.append(extra)
        non_string = _after(self.source_payload["questions"][1])
        non_string["A"] = 1
        invalid_after_values.append(non_string)
        for after in invalid_after_values:
            with self.subTest(after=after):
                review = self._semantic_review()
                review["review_queue"][0]["after"] = after
                self._assert_build_fails(review)

    def test_edit_review_note_must_be_nonblank(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["review_note"] = "  "
        self._assert_build_fails(review)

    def test_skip_review_note_must_be_nonblank(self) -> None:
        review = self._semantic_review()
        review["review_queue"][1]["review_note"] = ""
        self._assert_build_fails(review)

    def test_invalid_disposition_fails(self) -> None:
        review = self._semantic_review()
        review["review_queue"][1]["disposition"] = "APPROVE"
        self._assert_build_fails(review)

    def test_source_question_count_must_be_454(self) -> None:
        self.source_payload["questions"].pop()
        _write_json(self.source_path, self.source_payload)
        review = self._semantic_review()
        self._assert_build_fails(review)

    def test_duplicate_source_canonical_id_fails(self) -> None:
        questions = self.source_payload["questions"]
        questions[-1]["id"] = questions[0]["id"]
        _write_json(self.source_path, self.source_payload)
        review = self._semantic_review()
        self._assert_build_fails(review)

    def test_semantic_review_source_filename_binding_must_match(self) -> None:
        review = self._semantic_review()
        review["source_bank"] = "wrong_source.json"
        self._assert_build_fails(review)

    def test_semantic_review_candidate_filename_binding_must_match(self) -> None:
        review = self._semantic_review()
        review["candidate_bank"] = "wrong_candidate.json"
        self._assert_build_fails(review)

    def test_failed_build_after_semantic_parse_does_not_mutate_source(self) -> None:
        review = self._semantic_review()
        review["review_queue"][0]["semantic_review"]["A"] = "NOT_EQUIVALENT"
        self._write_semantic_review(review)
        source_before = self.source_path.read_bytes()
        with self.assertRaises(ValueError):
            self._build()
        self.assertEqual(source_before, self.source_path.read_bytes())

    def test_builder_is_in_repository_quality_targets(self) -> None:
        self.assertIn("tools/build_package_b_tranche1.py", QUALITY_TARGETS)


class PackageBTranche1CliTests(unittest.TestCase):
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
            "tools.build_package_b_tranche1",
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
            self.assertEqual(
                json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                completed.stdout,
            )
            self.assertEqual("PASS", summary["admission_status"])
            self.assertEqual(["sc900_syn_001", "sc900_syn_002"], summary["edited_question_ids"])
            self.assertEqual(2, summary["review_count"])
            self.assertTrue(candidate_path.exists())
            self.assertTrue(manifest_path.exists())
            for question_id in summary["edited_question_ids"]:
                self.assertTrue(
                    (review_root / "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1" / f"{question_id}.json").exists()
                )

            source = _read_json(source_path)
            candidate = _read_json(candidate_path)
            admission = admit_content_revision(
                _read_json(manifest_path),
                source_questions=source["questions"],
                target_questions=candidate["questions"],
                source_bank_path=source_path,
                target_bank_path=candidate_path,
                review_root=review_root,
            )
            self.assertEqual(AdmissionStatus.PASS, admission.status)

    def test_cli_summary_is_deterministic_for_equivalent_clean_roots(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = self._run_cli(*self._materialize_package(Path(first_directory)))
            second = self._run_cli(*self._materialize_package(Path(second_directory)))

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))

    def test_cli_returns_nonzero_and_no_manifest_for_invalid_semantic_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self._materialize_package(Path(temporary_directory))
            semantic_review = _read_json(paths[1])
            semantic_review["review_queue"][0]["semantic_review"]["A"] = "CHANGED"
            _write_json(paths[1], semantic_review)

            completed = self._run_cli(*paths)

            self.assertEqual(2, completed.returncode)
            self.assertTrue(completed.stderr.strip())
            self.assertFalse(paths[4].exists())

    def test_cli_requires_all_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self._materialize_package(Path(temporary_directory))

            completed = self._run_cli(*paths, include_manifest=False)

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("--manifest", completed.stderr)


class PackageBTranche1RealCandidateClosureTests(unittest.TestCase):
    SOURCE_BANK_PATH = REPOSITORY_ROOT / SOURCE_BANK_FILENAME
    CANDIDATE_BANK_PATH = REPOSITORY_ROOT / CANDIDATE_BANK_FILENAME
    MANIFEST_PATH = REPOSITORY_ROOT / MANIFEST_RELATIVE_PATH
    REVIEW_ROOT = REPOSITORY_ROOT / REVIEW_ROOT_RELATIVE_PATH
    BASELINE_METRICS_PATH = REPOSITORY_ROOT / BASELINE_METRICS_RELATIVE_PATH
    CANDIDATE_METRICS_PATH = REPOSITORY_ROOT / CANDIDATE_METRICS_RELATIVE_PATH

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry_before = copy.deepcopy(AUTHORIZED_CONTENT_REVISION_MANIFESTS)
        cls.source_bytes = cls.SOURCE_BANK_PATH.read_bytes()
        cls.candidate_bytes = cls.CANDIDATE_BANK_PATH.read_bytes()
        cls.manifest_bytes = cls.MANIFEST_PATH.read_bytes()
        cls.receipt_bytes = {
            path.relative_to(cls.REVIEW_ROOT).as_posix(): path.read_bytes()
            for path in sorted(cls.REVIEW_ROOT.rglob("*.json"))
        }
        cls.source_payload = json.loads(cls.source_bytes.decode("utf-8"))
        cls.candidate_payload = json.loads(cls.candidate_bytes.decode("utf-8"))
        cls.manifest = json.loads(cls.manifest_bytes.decode("utf-8"))
        cls.source_questions = cls.source_payload["questions"]
        cls.candidate_questions = cls.candidate_payload["questions"]
        cls.source_by_id = {question["id"]: question for question in cls.source_questions}
        cls.candidate_by_id = {question["id"]: question for question in cls.candidate_questions}
        cls.changed_ids = [edge["question_id"] for edge in cls.manifest["edges"]]
        changed = set(cls.changed_ids)
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
        self.assertEqual(self.manifest_bytes, self.MANIFEST_PATH.read_bytes())
        self.assertEqual(
            self.receipt_bytes,
            {
                path.relative_to(self.REVIEW_ROOT).as_posix(): path.read_bytes()
                for path in sorted(self.REVIEW_ROOT.rglob("*.json"))
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
        return admit_content_revision(
            self.manifest if manifest is None else manifest,
            source_questions=self.source_questions,
            target_questions=self.candidate_questions,
            source_bank_path=self.SOURCE_BANK_PATH if source_path is None else source_path,
            target_bank_path=self.CANDIDATE_BANK_PATH if target_path is None else target_path,
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

    def test_real_package_admission_passes_without_activating_registry(self) -> None:
        admission = self._admit()

        self.assertEqual(AdmissionStatus.PASS, admission.status)
        self.assertEqual((), admission.reasons)
        self.assertIsNotNone(admission.admitted)
        assert admission.admitted is not None
        self.assertEqual(SOURCE_BANK_FILENAME, admission.admitted.source_bank_filename)
        self.assertEqual(CANDIDATE_BANK_FILENAME, admission.admitted.target_bank_filename)
        self.assertEqual(self.changed_ids, [edge.question_id for edge in admission.admitted.edges])
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))
        self.assertEqual(self.registry_before, AUTHORIZED_CONTENT_REVISION_MANIFESTS)

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
        self.assertTrue(
            revision.permits_fingerprint_transition(
                self.changed_id,
                changed_from_fp,
                first.payload["question_content_fingerprints"][self.changed_id],
            )
        )
        self.assertEqual(1, len(first.payload["content_revision_lineage"]))
        lineage = first.payload["content_revision_lineage"][0]
        self.assertEqual(self.changed_id, lineage["question_id"])
        self.assertEqual(changed_from_fp, lineage["from_fingerprint"])
        self.assertEqual(first.payload["question_content_fingerprints"][self.changed_id], lineage["to_fingerprint"])
        self.assertEqual(revision.manifest_sha256, lineage["manifest_sha256"])
        self.assertEqual(first.migration_id, lineage["migration_id"])

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

    def test_real_session_continuity(self) -> None:
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
        self.assertTrue(answers[self.unchanged_id]["flagged"])
        self.assertFalse(answers[self.changed_id]["answered"])
        self.assertEqual([], answers[self.changed_id]["selected"])
        self.assertEqual([], answers[self.changed_id]["pending"])
        self.assertEqual(snapshot["session_answer_history"], result.payload["session_answer_history"])
        self.assertEqual(1, result.payload["current_index"])
        self.assertEqual(42, result.payload["elapsed_seconds"])
        self.assertEqual(["cp1"], result.payload["checkpoints_saved"])
        self.assertEqual(["r1"], result.payload["session_rewards"])
        self.assertEqual(["u1"], result.payload["unlocked_rewards"])
        self.assertEqual(7, result.payload["session_xp_gained"])
        self.assertEqual(CANDIDATE_BANK_FILENAME, result.payload["bank_file"])
        self.assertEqual(revision.target_bank_content_fingerprint, result.payload["bank_fingerprint"])
        self.assertEqual(
            canonical_session_signature(MODE_PRACTICE, revision.target_bank_content_fingerprint, question_ids),
            result.payload["session_signature"],
        )
        self.assertEqual(
            canonical_session_signature(MODE_PRACTICE, revision.target_bank_content_fingerprint, question_ids),
            result.payload["restore_signature"],
        )
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
            self.assertIn(RevisionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH, admission.reasons)
            self.assertIsNone(admission.admitted)
        self.assertEqual(
            self.receipt_bytes[self.manifest["edges"][0]["review_artifact"]],
            (self.REVIEW_ROOT / self.manifest["edges"][0]["review_artifact"]).read_bytes(),
        )

    def test_missing_review_receipt_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path, candidate_path, _, review_root = self._materialize_real_package(Path(temporary_directory))
            receipt_path = review_root / self.manifest["edges"][0]["review_artifact"]
            receipt_path.unlink()

            admission = self._admit(source_path=source_path, target_path=candidate_path, review_root=review_root)

            self.assertEqual(AdmissionStatus.FAIL, admission.status)
            self.assertIn(RevisionFailureReason.SEMANTIC_REVIEW_MISSING, admission.reasons)
            self.assertIsNone(admission.admitted)

    def test_partial_inconsistent_transition_fails_closed_before_migration(self) -> None:
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
            self.assertTrue(failed.reasons)
            self.assertIsNone(failed.admitted)
            self.assertEqual(original_payload, source_payload)

    def test_candidate_leakage_metrics_improve_strict_longest_and_match_artifact(self) -> None:
        computed = build_package_b_tranche1_candidate_metrics(self.source_questions, self.candidate_questions)
        baseline_file = _read_json(self.BASELINE_METRICS_PATH)
        serialized = serialize_candidate_metrics(computed)

        self.assertEqual(
            EXPECTED_BASELINE_STRICT_LONGEST_COUNT,
            computed["baseline"]["strict_longest_correct"]["count"],
        )
        self.assertEqual(
            EXPECTED_STRICT_LONGEST_DENOMINATOR,
            computed["baseline"]["strict_longest_correct"]["denominator"],
        )
        self.assertEqual(
            baseline_file["strict_longest_correct"],
            computed["baseline"]["strict_longest_correct"],
        )
        self.assertEqual(baseline_file["skipped_question_ids"], computed["skipped_question_ids"])
        self.assertEqual(
            EXPECTED_CANDIDATE_STRICT_LONGEST_COUNT,
            computed["candidate"]["strict_longest_correct"]["count"],
        )
        self.assertEqual(
            EXPECTED_STRICT_LONGEST_DENOMINATOR,
            computed["candidate"]["strict_longest_correct"]["denominator"],
        )
        self.assertEqual(EXPECTED_STRICT_LONGEST_DELTA, computed["delta"]["strict_longest_correct_count"])
        self.assertEqual("PASS", computed["closure_result"])
        self.assertEqual(serialized, self.CANDIDATE_METRICS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(computed, _read_json(self.CANDIDATE_METRICS_PATH))
        self.assertEqual(10, len(AUTHORIZED_CONTENT_REVISION_MANIFESTS))


if __name__ == "__main__":
    unittest.main()
