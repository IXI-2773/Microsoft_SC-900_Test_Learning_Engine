from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionStatus,
    admit_content_revision,
    canonical_manifest_sha256,
    sha256_file,
)
from content_revision_registry import AUTHORIZED_CONTENT_REVISION_MANIFESTS
from tools.build_package_b_tranche1 import build_package_b_tranche1
from tools.run_quality_checks import QUALITY_TARGETS


QUESTION_COUNT = 454
CHOICE_LABELS = ("A", "B", "C", "D")
MS_LEARN_REF = "https://learn.microsoft.com/en-us/security/zero-trust/"
WORK_ID = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / PACKAGE-B / TRANCHE-1"
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
        self.assertEqual({}, AUTHORIZED_CONTENT_REVISION_MANIFESTS)
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


if __name__ == "__main__":
    unittest.main()
