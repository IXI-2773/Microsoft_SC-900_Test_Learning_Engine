from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionStatus,
    AdmittedRevision,
    ContentRevisionManifestError,
    RevisionEdge,
    RevisionFailureReason,
    admit_content_revision,
    approved_lineage,
    canonical_manifest_sha256,
    parse_json_duplicate_safe,
    sha256_file,
)
from content_revision_registry import (
    AUTHORIZED_CONTENT_REVISION_MANIFESTS,
    resolve_registered_revision_for_target,
)
from question_bank import load_bank
from question_identity import (
    bank_content_fingerprint,
    canonical_question_id,
    question_content_fingerprint,
    registered_progress_identity_bank,
)

QUESTION_COUNT = 454
MS_LEARN_REF = "https://learn.microsoft.com/en-us/security/zero-trust/"
CHOICE_LABELS = ("A", "B", "C", "D")
MANIFEST_FIELDS = (
    "schema_version",
    "manifest_kind",
    "work_id",
    "continuity_policy",
    "source_bank",
    "target_bank",
    "permitted_change_class",
    "edges",
    "payload_sha256",
)
BANK_BINDING_FIELDS = ("filename", "file_sha256", "content_fingerprint", "question_count")
EDGE_FIELDS = (
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
)
REVIEW_FIELDS = (
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
)


def _question(index: int) -> dict[str, Any]:
    qid = f"sc900_syn_{index:03d}"
    return {
        "id": qid,
        "question_id": qid,
        "question_number": index + 1,
        "prompt": f"Prompt for {qid}",
        "choices": {
            "A": f"{qid} alpha",
            "B": f"{qid} beta",
            "C": f"{qid} gamma",
            "D": f"{qid} delta",
        },
        "correct": ["A"],
        "general_explanation": f"Because {qid}",
        "choice_explanations": {
            "A": f"{qid} A",
            "B": f"{qid} B",
            "C": f"{qid} C",
            "D": f"{qid} D",
        },
        "domain": "Identity",
        "chapter": "1",
        "subtitle": "Basics",
        "question_type": "single",
        "topics": ["Entra"],
        "objective_code": "1.1",
        "study_focus": "Core",
        "exam_calibration_tier": "FUNDAMENTALS_CORE",
        "exam_simulation_eligible": True,
        "reasoning_steps": 1,
        "calibration_version": "sc900-exam-calibration-2026-09-12-v1",
    }


def _bank(questions: list[dict[str, Any]], **meta: Any) -> dict[str, Any]:
    payload = {"title": "SC-900 Synthetic", "version": 1, "questions": questions}
    payload.update(meta)
    return payload


def _keyed_choices(question: Mapping[str, Any]) -> dict[str, str]:
    choices = question["choices"]
    return {letter: str(choices[letter]) for letter in CHOICE_LABELS}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _review_payload(source: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "question_id": source["id"],
        "from_content_fingerprint": question_content_fingerprint(source),
        "to_content_fingerprint": question_content_fingerprint(target),
        "before": _keyed_choices(source),
        "after": _keyed_choices(target),
        "semantic_review": {letter: "EQUIVALENT" for letter in CHOICE_LABELS},
        "correct_key_before": list(source["correct"]),
        "correct_key_after": list(target["correct"]),
        "authority_refs": [MS_LEARN_REF],
        "disposition": "APPROVED_FOR_FULL_CONTINUITY",
    }


def _edge_payload(
    source: Mapping[str, Any], target: Mapping[str, Any], review_name: str, review_sha: str
) -> dict[str, Any]:
    return {
        "question_id": source["id"],
        "from_content_fingerprint": question_content_fingerprint(source),
        "to_content_fingerprint": question_content_fingerprint(target),
        "correct_key_unchanged": True,
        "choice_letter_mapping_unchanged": True,
        "prompt_unchanged": True,
        "objective_unchanged": True,
        "tier_unchanged": True,
        "exam_eligibility_unchanged": True,
        "choice_semantics": {letter: "EQUIVALENT" for letter in CHOICE_LABELS},
        "review_status": "APPROVED",
        "review_artifact": review_name,
        "review_artifact_sha256": review_sha,
        "authority_refs": [MS_LEARN_REF],
    }


class RevisionPackage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.source_path = root / "source_bank.json"
        self.target_path = root / "target_bank.json"
        self.review_root = root / "reviews"
        self.source_questions = [_question(index) for index in range(QUESTION_COUNT)]
        self.target_questions = copy.deepcopy(self.source_questions)
        self.target_questions[0]["choices"]["B"] = "sc900_syn_000 beta rebalanced"
        self.review_name = "syn_000.json"
        self.manifest: dict[str, Any] = {}

    def materialize(self) -> None:
        self.source_questions = [_question(index) for index in range(QUESTION_COUNT)]
        self.target_questions = copy.deepcopy(self.source_questions)
        self.target_questions[0]["choices"]["B"] = "sc900_syn_000 beta rebalanced"
        _write_json(self.source_path, _bank(self.source_questions))
        _write_json(self.target_path, _bank(self.target_questions))
        review = _review_payload(self.source_questions[0], self.target_questions[0])
        review_path = self.review_root / self.review_name
        _write_json(review_path, review)
        self.manifest = {
            "schema_version": 1,
            "manifest_kind": "sc900_content_revision_equivalence",
            "work_id": "SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001",
            "continuity_policy": "FULL_CONTINUITY",
            "source_bank": {
                "filename": self.source_path.name,
                "file_sha256": sha256_file(self.source_path),
                "content_fingerprint": bank_content_fingerprint(self.source_questions),
                "question_count": QUESTION_COUNT,
            },
            "target_bank": {
                "filename": self.target_path.name,
                "file_sha256": sha256_file(self.target_path),
                "content_fingerprint": bank_content_fingerprint(self.target_questions),
                "question_count": QUESTION_COUNT,
            },
            "permitted_change_class": "WORDING_ONLY_LENGTH_REBALANCE",
            "edges": [
                _edge_payload(
                    self.source_questions[0],
                    self.target_questions[0],
                    self.review_name,
                    sha256_file(review_path),
                )
            ],
            "payload_sha256": "",
        }
        self.manifest["payload_sha256"] = canonical_manifest_sha256(self.manifest)

    def admit(self) -> Any:
        return admit_content_revision(
            self.manifest,
            source_questions=self.source_questions,
            target_questions=self.target_questions,
            source_bank_path=self.source_path,
            target_bank_path=self.target_path,
            review_root=self.review_root,
        )

    def rewrite_banks(self) -> None:
        _write_json(self.source_path, _bank(self.source_questions))
        _write_json(self.target_path, _bank(self.target_questions))


def _reason(result: Any) -> RevisionFailureReason:
    return result.reasons[0]


class ContentRevisionAuthorityPrimitiveTests(unittest.TestCase):
    def test_equivalent_json_key_order_and_whitespace_share_canonical_hash(self) -> None:
        compact = '{"work_id":"SC900","schema_version":1,"edges":[]}'
        reordered = '{"schema_version": 1, "edges": [], "work_id": "SC900"}'
        pretty = """
        {
          "edges": [],
          "work_id": "SC900",
          "schema_version": 1
        }
        """
        hashes = {
            canonical_manifest_sha256(parse_json_duplicate_safe(compact)),
            canonical_manifest_sha256(parse_json_duplicate_safe(reordered)),
            canonical_manifest_sha256(parse_json_duplicate_safe(pretty)),
        }
        self.assertEqual(1, len(hashes))

    def test_stored_payload_sha256_is_excluded_from_self_hash(self) -> None:
        payload = {"schema_version": 1, "work_id": "SC900", "edges": []}
        hashed = dict(payload)
        hashed["payload_sha256"] = "deadbeef"
        self.assertEqual(canonical_manifest_sha256(payload), canonical_manifest_sha256(hashed))

    def _parse_reason(self, raw: str) -> RevisionFailureReason:
        with self.assertRaises(ContentRevisionManifestError) as ctx:
            parse_json_duplicate_safe(raw)
        return ctx.exception.reason

    def test_duplicate_manifest_key_fails_closed(self) -> None:
        raw = '{"schema_version":1,"work_id":"SC900","work_id":"OTHER"}'
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._parse_reason(raw))

    def test_duplicate_review_authority_key_fails_closed(self) -> None:
        raw = '{"question_id":"q1","question_id":"q2","disposition":"APPROVED_FOR_FULL_CONTINUITY"}'
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._parse_reason(raw))

    def test_duplicate_bank_authority_key_fails_closed(self) -> None:
        raw = '{"title":"bank","questions":[],"title":"other"}'
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._parse_reason(raw))

    def test_malformed_json_is_schema_unsupported(self) -> None:
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._parse_reason("{not json"))

    def test_non_object_top_level_manifest_review_and_bank_are_schema_unsupported(self) -> None:
        for raw in ("[]", "null", '"string"', "1", "true"):
            with self.subTest(raw=raw):
                self.assertEqual(
                    RevisionFailureReason.SCHEMA_UNSUPPORTED,
                    self._parse_reason(raw),
                )

    def test_sha256_file_hashes_raw_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"abc\r\n")
            self.assertEqual(hashlib.sha256(b"abc\r\n").hexdigest(), sha256_file(path))


class ContentRevisionAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.pkg = RevisionPackage(Path(self._tmp.name))
        self.pkg.materialize()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _fail_reason(self) -> RevisionFailureReason:
        result = self.pkg.admit()
        self.assertEqual(AdmissionStatus.FAIL, result.status)
        self.assertIsNone(result.admitted)
        self.assertTrue(result.reasons)
        return _reason(result)

    def _rehash(self) -> None:
        self.pkg.manifest["payload_sha256"] = canonical_manifest_sha256(self.pkg.manifest)

    def test_valid_canonical_manifest_passes(self) -> None:
        result = self.pkg.admit()
        self.assertEqual(AdmissionStatus.PASS, result.status)
        self.assertIsNotNone(result.admitted)
        assert result.admitted is not None
        self.assertEqual(self.pkg.manifest["payload_sha256"], result.admitted.manifest_sha256)
        self.assertEqual(1, len(result.admitted.edges))
        self.assertEqual("sc900_syn_000", result.admitted.edges[0].question_id)

    def test_whitespace_only_bank_metadata_does_not_fail(self) -> None:
        compact = json.dumps(_bank(self.pkg.target_questions), ensure_ascii=False, separators=(",", ":"))
        self.pkg.target_path.write_text(compact, encoding="utf-8")
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self._rehash()
        result = self.pkg.admit()
        self.assertEqual(AdmissionStatus.PASS, result.status)

    def test_unsupported_schema_constants(self) -> None:
        cases = {
            "schema_version": 2,
            "manifest_kind": "other_kind",
            "continuity_policy": "PARTIAL",
            "permitted_change_class": "PROMPT_REWRITE",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                self.pkg.materialize()
                self.pkg.manifest[field] = value
                self._rehash()
                self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())

    def test_unknown_fields_at_every_object_level(self) -> None:
        mutations: list[tuple[str, Callable[[], None]]] = [
            ("manifest", lambda: self.pkg.manifest.__setitem__("unexpected", 1)),
            ("source_bank", lambda: self.pkg.manifest["source_bank"].__setitem__("unexpected", 1)),
            ("target_bank", lambda: self.pkg.manifest["target_bank"].__setitem__("unexpected", 1)),
            ("edge", lambda: self.pkg.manifest["edges"][0].__setitem__("unexpected", 1)),
        ]
        for label, mutate in mutations:
            with self.subTest(label=label):
                self.pkg.materialize()
                mutate()
                self._rehash()
                self.assertEqual(RevisionFailureReason.UNKNOWN_FIELD, self._fail_reason())
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        review["unexpected"] = 1
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.UNKNOWN_FIELD, self._fail_reason())

    def test_missing_fields_at_every_object_level(self) -> None:
        for field in MANIFEST_FIELDS:
            if field == "payload_sha256":
                continue
            with self.subTest(manifest=field):
                self.pkg.materialize()
                del self.pkg.manifest[field]
                if field != "payload_sha256":
                    self.pkg.manifest["payload_sha256"] = canonical_manifest_sha256(self.pkg.manifest)
                self.assertEqual(RevisionFailureReason.MISSING_FIELD, self._fail_reason())
        for field in BANK_BINDING_FIELDS:
            with self.subTest(source_bank=field):
                self.pkg.materialize()
                del self.pkg.manifest["source_bank"][field]
                self._rehash()
                self.assertEqual(RevisionFailureReason.MISSING_FIELD, self._fail_reason())
        for field in EDGE_FIELDS:
            with self.subTest(edge=field):
                self.pkg.materialize()
                del self.pkg.manifest["edges"][0][field]
                self._rehash()
                self.assertEqual(RevisionFailureReason.MISSING_FIELD, self._fail_reason())
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        del review["disposition"]
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.MISSING_FIELD, self._fail_reason())

    def test_wrong_field_types(self) -> None:
        cases: list[tuple[str, Callable[[], None]]] = [
            ("schema_version_str", lambda: self.pkg.manifest.__setitem__("schema_version", "1")),
            ("edges_not_list", lambda: self.pkg.manifest.__setitem__("edges", {})),
            ("source_bank_not_mapping", lambda: self.pkg.manifest.__setitem__("source_bank", [])),
            ("question_count_str", lambda: self.pkg.manifest["source_bank"].__setitem__("question_count", "454")),
            ("choice_semantics_list", lambda: self.pkg.manifest["edges"][0].__setitem__("choice_semantics", ["A"])),
            ("authority_refs_str", lambda: self.pkg.manifest["edges"][0].__setitem__("authority_refs", MS_LEARN_REF)),
            ("boolean_str", lambda: self.pkg.manifest["edges"][0].__setitem__("prompt_unchanged", "true")),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                self.pkg.materialize()
                mutate()
                self._rehash()
                self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        review["before"] = ["A"]
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())
        self.pkg.materialize()
        review = parse_json_duplicate_safe((self.pkg.review_root / self.pkg.review_name).read_text(encoding="utf-8"))
        review["semantic_review"] = {"A": "EQUIVALENT"}
        _write_json(self.pkg.review_root / self.pkg.review_name, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(
            self.pkg.review_root / self.pkg.review_name
        )
        self._rehash()
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())

    def test_blank_and_malformed_hash_fields(self) -> None:
        self.pkg.manifest["payload_sha256"] = ""
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["source_bank"]["file_sha256"] = "not-a-hash"
        self._rehash()
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["edges"][0]["from_content_fingerprint"] = "abc"
        self._rehash()
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())

    def test_manifest_hash_mismatch(self) -> None:
        self.pkg.manifest["payload_sha256"] = "0" * 64
        self.assertEqual(RevisionFailureReason.MANIFEST_HASH_MISMATCH, self._fail_reason())

    def test_source_and_target_raw_hash_mismatch(self) -> None:
        self.pkg.manifest["source_bank"]["file_sha256"] = "a" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["target_bank"]["file_sha256"] = "b" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.TARGET_BANK_FILE_HASH_MISMATCH, self._fail_reason())

    def test_source_and_target_fingerprint_mismatch(self) -> None:
        self.pkg.manifest["source_bank"]["content_fingerprint"] = "c" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.SOURCE_BANK_FINGERPRINT_MISMATCH, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["target_bank"]["content_fingerprint"] = "d" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.TARGET_BANK_FINGERPRINT_MISMATCH, self._fail_reason())

    def test_question_count_not_454(self) -> None:
        self.pkg.source_questions = self.pkg.source_questions[:453]
        self.pkg.target_questions = copy.deepcopy(self.pkg.source_questions)
        self.pkg.target_questions[0]["choices"]["B"] = "sc900_syn_000 beta rebalanced"
        self.pkg.rewrite_banks()
        self.pkg.materialize()
        self.pkg.source_questions = [_question(index) for index in range(453)]
        self.pkg.target_questions = copy.deepcopy(self.pkg.source_questions)
        self.pkg.target_questions[0]["choices"]["B"] = "sc900_syn_000 beta rebalanced"
        self.pkg.rewrite_banks()
        review = _review_payload(self.pkg.source_questions[0], self.pkg.target_questions[0])
        _write_json(self.pkg.review_root / self.pkg.review_name, review)
        self.pkg.manifest["source_bank"]["question_count"] = 453
        self.pkg.manifest["target_bank"]["question_count"] = 453
        self.pkg.manifest["source_bank"]["file_sha256"] = sha256_file(self.pkg.source_path)
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self.pkg.manifest["source_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.source_questions)
        self.pkg.manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.target_questions)
        self.pkg.manifest["edges"] = [
            _edge_payload(
                self.pkg.source_questions[0],
                self.pkg.target_questions[0],
                self.pkg.review_name,
                sha256_file(self.pkg.review_root / self.pkg.review_name),
            )
        ]
        self._rehash()
        self.assertEqual(RevisionFailureReason.QUESTION_COUNT_MISMATCH, self._fail_reason())

    def test_duplicate_canonical_id(self) -> None:
        self.pkg.target_questions[1]["id"] = self.pkg.target_questions[0]["id"]
        self.pkg.target_questions[1]["question_id"] = self.pkg.target_questions[0]["id"]
        self.pkg.rewrite_banks()
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.DUPLICATE_QUESTION_ID, self._fail_reason())

    def test_question_id_set_mismatch(self) -> None:
        self.pkg.target_questions[1]["id"] = "sc900_syn_replaced"
        self.pkg.target_questions[1]["question_id"] = "sc900_syn_replaced"
        self.pkg.rewrite_banks()
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self.pkg.manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.target_questions)
        self._rehash()
        self.assertEqual(RevisionFailureReason.QUESTION_ID_SET_MISMATCH, self._fail_reason())

    def test_bank_level_metadata_change(self) -> None:
        _write_json(self.pkg.target_path, _bank(self.pkg.target_questions, title="Changed Title"))
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.NONPERMITTED_FIELD_CHANGED, self._fail_reason())

    def test_undeclared_changed_question(self) -> None:
        self.pkg.target_questions[1]["choices"]["C"] = "undeclared wording"
        self.pkg.rewrite_banks()
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self.pkg.manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.target_questions)
        self._rehash()
        self.assertEqual(RevisionFailureReason.UNDECLARED_CONTENT_CHANGE, self._fail_reason())

    def test_extra_edge_for_unchanged_question(self) -> None:
        extra_review = _review_payload(self.pkg.source_questions[1], self.pkg.target_questions[1])
        extra_name = "syn_001.json"
        _write_json(self.pkg.review_root / extra_name, extra_review)
        extra_edge = _edge_payload(
            self.pkg.source_questions[1],
            self.pkg.target_questions[1],
            extra_name,
            sha256_file(self.pkg.review_root / extra_name),
        )
        extra_edge["from_content_fingerprint"] = question_content_fingerprint(self.pkg.source_questions[1])
        extra_edge["to_content_fingerprint"] = "e" * 64
        self.pkg.manifest["edges"].append(extra_edge)
        self._rehash()
        self.assertEqual(RevisionFailureReason.EXTRA_EQUIVALENCE_EDGE, self._fail_reason())

    def test_duplicate_edge(self) -> None:
        self.pkg.manifest["edges"].append(copy.deepcopy(self.pkg.manifest["edges"][0]))
        self._rehash()
        self.assertEqual(RevisionFailureReason.DUPLICATE_EQUIVALENCE_EDGE, self._fail_reason())

    def test_wrong_edge_from_and_to_fingerprints(self) -> None:
        self.pkg.manifest["edges"][0]["from_content_fingerprint"] = "f" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.FROM_FINGERPRINT_MISMATCH, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["edges"][0]["to_content_fingerprint"] = "1" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.TO_FINGERPRINT_MISMATCH, self._fail_reason())

    def _mutate_target_field(self, field: str, value: Any) -> None:
        self.pkg.target_questions[0][field] = value
        self.pkg.rewrite_banks()
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self.pkg.manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.target_questions)
        self.pkg.manifest["edges"][0]["to_content_fingerprint"] = question_content_fingerprint(
            self.pkg.target_questions[0]
        )
        review = _review_payload(self.pkg.source_questions[0], self.pkg.target_questions[0])
        _write_json(self.pkg.review_root / self.pkg.review_name, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(
            self.pkg.review_root / self.pkg.review_name
        )
        self._rehash()

    def test_correct_key_change(self) -> None:
        self._mutate_target_field("correct", ["B"])
        self.assertEqual(RevisionFailureReason.CORRECT_KEY_CHANGED, self._fail_reason())

    def test_choice_label_change(self) -> None:
        self.pkg.target_questions[0]["choices"] = {
            "A": "sc900_syn_000 alpha",
            "B": "sc900_syn_000 beta rebalanced",
            "C": "sc900_syn_000 gamma",
        }
        self.pkg.rewrite_banks()
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self.pkg.manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.target_questions)
        self.pkg.manifest["edges"][0]["to_content_fingerprint"] = question_content_fingerprint(
            self.pkg.target_questions[0]
        )
        self._rehash()
        self.assertEqual(RevisionFailureReason.CHOICE_LABEL_SET_CHANGED, self._fail_reason())

    def test_fingerprint_blind_bc_swap_rejected(self) -> None:
        source = self.pkg.source_questions[0]
        swapped = copy.deepcopy(source)
        swapped["choices"]["B"], swapped["choices"]["C"] = swapped["choices"]["C"], swapped["choices"]["B"]
        swapped["choice_explanations"]["B"], swapped["choice_explanations"]["C"] = (
            swapped["choice_explanations"]["C"],
            swapped["choice_explanations"]["B"],
        )
        self.assertEqual(question_content_fingerprint(source), question_content_fingerprint(swapped))
        self.pkg.target_questions[0] = swapped
        self.pkg.rewrite_banks()
        self.pkg.manifest["edges"] = []
        self.pkg.manifest["target_bank"]["file_sha256"] = sha256_file(self.pkg.target_path)
        self.pkg.manifest["target_bank"]["content_fingerprint"] = bank_content_fingerprint(self.pkg.target_questions)
        self._rehash()
        self.assertEqual(RevisionFailureReason.CHOICE_LETTER_MAPPING_CHANGED, self._fail_reason())

    def test_prompt_objective_domain_topics_and_type_changes(self) -> None:
        cases = {
            "prompt": ("prompt", "mutated prompt", RevisionFailureReason.PROMPT_CHANGED),
            "objective": ("objective_code", "9.9", RevisionFailureReason.OBJECTIVE_CHANGED),
            "domain": ("domain", "Governance", RevisionFailureReason.DOMAIN_CHANGED),
            "topics": ("topics", ["Defender"], RevisionFailureReason.TOPICS_CHANGED),
            "type": ("question_type", "multi", RevisionFailureReason.QUESTION_TYPE_CHANGED),
        }
        for label, (field, value, expected) in cases.items():
            with self.subTest(label=label):
                self.pkg.materialize()
                self._mutate_target_field(field, value)
                self.assertEqual(expected, self._fail_reason())

    def test_exam_calibration_tier_change(self) -> None:
        self._mutate_target_field("exam_calibration_tier", "FUNDAMENTALS_STRETCH")
        self.assertEqual(RevisionFailureReason.TIER_CHANGED, self._fail_reason())

    def test_exam_simulation_eligible_change(self) -> None:
        self._mutate_target_field("exam_simulation_eligible", False)
        self.assertEqual(RevisionFailureReason.EXAM_ELIGIBILITY_CHANGED, self._fail_reason())

    def test_non_choice_field_changes(self) -> None:
        cases = {
            "study_focus": "Advanced",
            "reasoning_steps": 9,
            "calibration_version": "other",
            "general_explanation": "changed explanation",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                self.pkg.materialize()
                self._mutate_target_field(field, value)
                self.assertEqual(RevisionFailureReason.NONPERMITTED_FIELD_CHANGED, self._fail_reason())

    def test_missing_and_unreadable_review(self) -> None:
        (self.pkg.review_root / self.pkg.review_name).unlink()
        self.assertEqual(RevisionFailureReason.SEMANTIC_REVIEW_MISSING, self._fail_reason())
        self.pkg.materialize()
        review_path = self.pkg.review_root / self.pkg.review_name
        review_path.unlink()
        review_path.mkdir()
        self.assertEqual(RevisionFailureReason.SEMANTIC_REVIEW_MISSING, self._fail_reason())

    def test_review_hash_mismatch(self) -> None:
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = "2" * 64
        self._rehash()
        self.assertEqual(RevisionFailureReason.SEMANTIC_REVIEW_HASH_MISMATCH, self._fail_reason())

    def test_review_qid_from_to_mismatch(self) -> None:
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        review["question_id"] = "other"
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED, self._fail_reason())

    def test_review_before_after_and_correct_key_mismatch(self) -> None:
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        review["before"]["B"] = "not the source text"
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED, self._fail_reason())
        self.pkg.materialize()
        review = parse_json_duplicate_safe((self.pkg.review_root / self.pkg.review_name).read_text(encoding="utf-8"))
        review["correct_key_after"] = ["B"]
        _write_json(self.pkg.review_root / self.pkg.review_name, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(
            self.pkg.review_root / self.pkg.review_name
        )
        self._rehash()
        self.assertEqual(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED, self._fail_reason())

    def test_ambiguous_or_substantive_choice_semantics(self) -> None:
        for status in ("AMBIGUOUS", "SUBSTANTIVELY_CHANGED"):
            with self.subTest(status=status):
                self.pkg.materialize()
                review_path = self.pkg.review_root / self.pkg.review_name
                review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
                review["semantic_review"]["B"] = status
                _write_json(review_path, review)
                self.pkg.manifest["edges"][0]["choice_semantics"]["B"] = status
                self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
                self._rehash()
                self.assertEqual(RevisionFailureReason.CHOICE_SEMANTICS_CHANGED, self._fail_reason())

    def test_authority_refs_empty_or_non_microsoft_only(self) -> None:
        self.pkg.manifest["edges"][0]["authority_refs"] = []
        self._rehash()
        self.assertEqual(RevisionFailureReason.AUTHORITY_EVIDENCE_MISSING, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["edges"][0]["authority_refs"] = [MS_LEARN_REF, "https://example.com/other"]
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        review["authority_refs"] = [MS_LEARN_REF, "https://example.com/other"]
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.AUTHORITY_EVIDENCE_MISSING, self._fail_reason())

    def test_unapproved_review_disposition_and_status(self) -> None:
        review_path = self.pkg.review_root / self.pkg.review_name
        review = parse_json_duplicate_safe(review_path.read_text(encoding="utf-8"))
        review["disposition"] = "REJECTED"
        _write_json(review_path, review)
        self.pkg.manifest["edges"][0]["review_artifact_sha256"] = sha256_file(review_path)
        self._rehash()
        self.assertEqual(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["edges"][0]["review_status"] = "PENDING"
        self._rehash()
        self.assertEqual(RevisionFailureReason.SEMANTIC_EQUIVALENCE_NOT_APPROVED, self._fail_reason())

    def test_absolute_and_traversal_review_paths(self) -> None:
        self.pkg.manifest["edges"][0]["review_artifact"] = str((self.pkg.review_root / self.pkg.review_name).resolve())
        self._rehash()
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())
        self.pkg.materialize()
        self.pkg.manifest["edges"][0]["review_artifact"] = "../secrets.json"
        self._rehash()
        self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, self._fail_reason())

    def test_duplicate_bank_json_during_admission(self) -> None:
        self.pkg.source_path.write_text(
            '{"title":"SC-900 Synthetic","title":"dup","version":1,"questions":[]}',
            encoding="utf-8",
        )
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, self._fail_reason())


def _lineage_edge(question_id: str, from_fp: str, to_fp: str) -> RevisionEdge:
    return RevisionEdge(question_id, from_fp, to_fp, "review.json", "a" * 64)


def _lineage_revision(*edges: RevisionEdge) -> AdmittedRevision:
    return AdmittedRevision("m" * 64, "source.json", "s" * 64, "sf" * 64, "target.json", "t" * 64, "tf" * 64, edges)


class ContentRevisionRegistryAndLineageTests(unittest.TestCase):
    def test_production_registry_is_empty(self) -> None:
        self.assertEqual({}, AUTHORIZED_CONTENT_REVISION_MANIFESTS)

    def test_empty_registry_resolves_to_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target_bank.json"
            target.write_text("{}", encoding="utf-8")
            self.assertIsNone(resolve_registered_revision_for_target(target, registry={}))

    def test_direct_and_chained_lineage(self) -> None:
        qid = "sc900_syn_000"
        v1, v2, v3 = "1" * 64, "2" * 64, "3" * 64
        first = _lineage_edge(qid, v1, v2)
        second = _lineage_edge(qid, v2, v3)
        revision = _lineage_revision(first)
        self.assertTrue(revision.permits_fingerprint_transition(qid, v1, v2))
        self.assertFalse(revision.permits_fingerprint_transition(qid, v2, v1))
        self.assertEqual((first,), approved_lineage([revision], qid, v1, v2))
        self.assertIsNone(approved_lineage([revision], qid, v2, v1))
        chained = approved_lineage([_lineage_revision(first), _lineage_revision(second)], qid, v1, v3)
        self.assertEqual((first, second), chained)
        self.assertIsNone(
            approved_lineage(
                [_lineage_revision(first), _lineage_revision(_lineage_edge(qid, "4" * 64, v3))], qid, v1, v3
            )
        )

    def test_conflicting_and_cyclic_lineage(self) -> None:
        qid = "sc900_syn_000"
        v1, v2, v3 = "1" * 64, "2" * 64, "3" * 64
        with self.assertRaises(ContentRevisionManifestError) as ctx:
            approved_lineage(
                [_lineage_revision(_lineage_edge(qid, v1, v2), _lineage_edge(qid, v1, v3))],
                qid,
                v1,
                v3,
            )
        self.assertEqual(RevisionFailureReason.LINEAGE_CONFLICT, ctx.exception.reason)
        with self.assertRaises(ContentRevisionManifestError) as ctx:
            approved_lineage(
                [_lineage_revision(_lineage_edge(qid, v1, v2), _lineage_edge(qid, v2, v1))],
                qid,
                v1,
                v3,
            )
        self.assertEqual(RevisionFailureReason.LINEAGE_CONFLICT, ctx.exception.reason)

    def test_registered_resolution_restores_target_bank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = RevisionPackage(Path(tmp))
            pkg.materialize()
            evidence = Path(tmp) / "content_revision_evidence"
            manifest_rel = "manifests/rev.json"
            _write_json(evidence / manifest_rel, pkg.manifest)
            registry = {manifest_rel: pkg.manifest["payload_sha256"]}
            load_bank(pkg.target_path)
            target_ids = [canonical_question_id(row) for row in registered_progress_identity_bank()]
            result = resolve_registered_revision_for_target(
                pkg.target_path,
                evidence_root=evidence,
                review_root=pkg.review_root,
                registry=registry,
            )
            self.assertEqual(AdmissionStatus.PASS, result.status)
            restored_ids = [canonical_question_id(row) for row in registered_progress_identity_bank()]
            self.assertEqual(target_ids, restored_ids)
            self.assertNotEqual(pkg.source_path.name, pkg.target_path.name)

    def test_failed_source_resolution_restores_target_bank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = RevisionPackage(Path(tmp))
            pkg.materialize()
            evidence = Path(tmp) / "content_revision_evidence"
            manifest_rel = "manifests/rev.json"
            _write_json(evidence / manifest_rel, pkg.manifest)
            registry = {manifest_rel: pkg.manifest["payload_sha256"]}
            load_bank(pkg.target_path)
            target_ids = [canonical_question_id(row) for row in registered_progress_identity_bank()]
            pkg.source_path.unlink()
            result = resolve_registered_revision_for_target(
                pkg.target_path,
                evidence_root=evidence,
                review_root=pkg.review_root,
                registry=registry,
            )
            self.assertEqual(AdmissionStatus.FAIL, result.status)
            self.assertEqual(RevisionFailureReason.SOURCE_BANK_FILE_HASH_MISMATCH, result.reasons[0])
            restored_ids = [canonical_question_id(row) for row in registered_progress_identity_bank()]
            self.assertEqual(target_ids, restored_ids)

    def test_same_source_target_filename_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = RevisionPackage(Path(tmp))
            pkg.materialize()
            pkg.manifest["source_bank"]["filename"] = pkg.manifest["target_bank"]["filename"]
            pkg.manifest["payload_sha256"] = canonical_manifest_sha256(pkg.manifest)
            evidence = Path(tmp) / "content_revision_evidence"
            manifest_rel = "manifests/rev.json"
            _write_json(evidence / manifest_rel, pkg.manifest)
            result = resolve_registered_revision_for_target(
                pkg.target_path,
                evidence_root=evidence,
                review_root=pkg.review_root,
                registry={manifest_rel: pkg.manifest["payload_sha256"]},
            )
            self.assertEqual(AdmissionStatus.FAIL, result.status)
            self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, result.reasons[0])

    def test_missing_registered_manifest_maps_to_registry_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target_bank.json"
            target.write_text("{}", encoding="utf-8")
            result = resolve_registered_revision_for_target(
                target,
                evidence_root=Path(tmp),
                registry={"manifests/missing.json": "a" * 64},
            )
            self.assertEqual(AdmissionStatus.FAIL, result.status)
            self.assertEqual(RevisionFailureReason.REGISTRY_HASH_MISMATCH, result.reasons[0])

    def test_unsafe_registry_path_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target_bank.json"
            target.write_text("{}", encoding="utf-8")
            result = resolve_registered_revision_for_target(
                target,
                evidence_root=Path(tmp),
                registry={"../escape.json": "a" * 64},
            )
            self.assertEqual(AdmissionStatus.FAIL, result.status)
            self.assertEqual(RevisionFailureReason.SCHEMA_UNSUPPORTED, result.reasons[0])


class ContentRevisionQualityGateTests(unittest.TestCase):
    MODULES = (
        "content_revision_authority",
        "content_revision_migration",
        "content_revision_registry",
    )

    def test_quality_gates_include_content_revision_modules(self) -> None:
        import tomllib

        from tools.run_quality_checks import QUALITY_TARGETS

        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        first_party = set(pyproject["tool"]["ruff"]["lint"]["isort"]["known-first-party"])
        mypy_files = set(pyproject["tool"]["mypy"]["files"])
        quality = set(QUALITY_TARGETS)
        for module in self.MODULES:
            with self.subTest(module=module):
                self.assertIn(module, first_party)
                self.assertIn(f"{module}.py", quality)
                self.assertIn(f"{module}.py", mypy_files)


if __name__ == "__main__":
    unittest.main()
