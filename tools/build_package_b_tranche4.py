from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import (
    CHOICE_LABELS,
    CONTINUITY_POLICY,
    MANIFEST_KIND,
    MS_LEARN_PREFIX,
    PERMITTED_CHANGE_CLASS,
    REQUIRED_QUESTION_COUNT,
    REVIEW_DISPOSITION_APPROVED,
    REVIEW_STATUS_APPROVED,
    SEMANTIC_EQUIVALENT,
    AdmissionStatus,
    admit_content_revision,
    canonical_manifest_sha256,
    sha256_file,
)
from package_b_canonical_json import write_canonical_package_b_json
from question_identity import (
    bank_content_fingerprint,
    canonical_question_id,
    question_content_fingerprint,
)

REVIEW_DIRECTORY = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T4"
T1_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t1.json"
T2_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t2.json"
T3_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t3.json"
T4_CANDIDATE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t4.json"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
T3_MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t3.json"
EXPECTED_T3_SOURCE_SHA256 = "0b0cdf3bf4c8b7885acf0b3b19381dd9f19ee38944fc6af6934b11b5b14588bd"
EXPECTED_T3_SOURCE_FINGERPRINT = "83a8644cce462cf231f2c795746ab4d8ca1d71246fea8fbfb2982ddc7961f8a2"
REJECTED_T3_CRLF_SHA256 = "d4cb07c1c6fe15b52553af2893b445b85d957b7a074b0747b75ca0f11cbf977b"
EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA = "4b9eab410da68bd348b4ae40946cf54a45b1da98bf04d68baaf6a57e3de15338"
EXPECTED_T4_SEMANTIC_REVIEW_SHA256 = "468cc71acedcc39e1b1f849dbbb775f6145923116e2a37fb2633855259c4703a"
T1_SKIP_QUESTION_IDS = frozenset(
    {
        "sc900_mlc_q173",
        "sc900_mlc_q070",
        "sc900_mlc_q116",
        "sc900_mlc_q085",
        "sc900_mlc_q253",
        "sc900_mlc_q075",
        "sc900_mlc_q155",
    }
)
T2_SKIP_QUESTION_IDS = frozenset({"sc900_mlc_q046"})
T4_DESIGN_QUEUE = (
    "sc900_p2_q025",
    "sc900_p3_q095",
    "sc900_mlc_q129",
    "sc900_mlc_q030",
    "sc900_p3_q038",
    "sc900_p3_q049",
    "sc900_mlc_q169",
    "sc900_p3_q091",
    "sc900_mlc_q063",
    "sc900_mlc_q180",
    "sc900_mlc_q025",
    "sc900_mlc_q017",
    "sc900_p1_q042",
    "sc900_mlc_q018",
    "sc900_p3_q077",
    "sc900_p3_q075",
    "sc900_p1_q048",
    "sc900_mlc_q224",
    "sc900_mlc_q195",
    "sc900_mlc_q077",
    "sc900_mlc_q052",
    "sc900_p3_q033",
    "sc900_mlc_q130",
    "sc900_p3_q093",
    "sc900_p3_q036",
    "sc900_mlc_q212",
    "sc900_p3_q064",
    "sc900_p3_q089",
    "sc900_mlc_q049",
    "sc900_mlc_q015",
    "sc900_p1_q031",
    "sc900_p2_q041",
    "sc900_p3_q024",
    "sc900_p3_q018",
    "sc900_mlc_q274",
    "sc900_mlc_q104",
    "sc900_p3_q045",
    "sc900_p2_q031",
    "sc900_mlc_q255",
    "sc900_mlc_q298",
    "sc900_mlc_q272",
    "sc900_p2_q015",
    "sc900_mlc_q031",
    "sc900_mlc_q123",
    "sc900_mlc_q256",
    "sc900_mlc_q172",
    "sc900_mlc_q222",
    "sc900_mlc_q261",
    "sc900_p3_q023",
    "sc900_mlc_q073",
    "sc900_mlc_q283",
    "sc900_mlc_q131",
    "sc900_mlc_q241",
    "sc900_mlc_q284",
    "sc900_mlc_q174",
    "sc900_mlc_q179",
    "sc900_mlc_q265",
    "sc900_mlc_q133",
    "sc900_mlc_q275",
    "sc900_mlc_q171",
    "sc900_mlc_q197",
    "sc900_mlc_q226",
    "sc900_mlc_q249",
    "sc900_mlc_q269",
)
T4_EDIT_IDS = frozenset(T4_DESIGN_QUEUE[:55])
T4_SKIP_QUESTION_IDS = frozenset(T4_DESIGN_QUEUE[55:61])
T4_SEPARATE_CORRECTION_IDS = frozenset(T4_DESIGN_QUEUE[61:])
_SEMANTIC_REVIEW_FIELDS = {"work_id", "source_bank", "candidate_bank", "review_queue"}
_EDIT_FIELDS = {
    "question_id",
    "disposition",
    "after",
    "semantic_review",
    "authority_refs",
    "review_note",
}
_SKIP_FIELDS = {"question_id", "disposition", "review_note"}
_SEPARATE_FIELDS = {"question_id", "disposition", "review_note"}
_FROZEN_OUTPUT_FILENAMES = {
    T1_SOURCE_BANK_FILENAME,
    T2_SOURCE_BANK_FILENAME,
    T3_SOURCE_BANK_FILENAME,
    PRODUCTION_BANK_FILENAME,
}
_REPO_ROOT = Path(__file__).resolve().parents[1]


class PackageBTranche4BuildError(ValueError):
    """Raised when reviewed input cannot produce an admissible Package-B T4 package."""


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageBTranche4BuildError(f"{label} is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PackageBTranche4BuildError(f"{label} must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_canonical_package_b_json(path, payload)


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def _exact_ad_string_mapping(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(CHOICE_LABELS)
        and all(isinstance(value[letter], str) for letter in CHOICE_LABELS)
    )


def _keyed_choices(question: Mapping[str, Any]) -> dict[str, str]:
    choices = question.get("choices")
    if not _exact_ad_string_mapping(choices):
        raise PackageBTranche4BuildError(
            f"question {canonical_question_id(question)!r} must have exact string A-D choices"
        )
    return {letter: choices[letter] for letter in CHOICE_LABELS}


def _correct_key_list(question: Mapping[str, Any]) -> list[str]:
    correct = question.get("correct")
    if isinstance(correct, str):
        return [correct]
    if isinstance(correct, list) and all(isinstance(item, str) for item in correct):
        return sorted(correct)
    raise PackageBTranche4BuildError(f"edited question {canonical_question_id(question)!r} has an invalid correct key")


def _normalized_authority_refs(value: Any, question_id: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise PackageBTranche4BuildError(f"EDIT {question_id!r} requires authority_refs")
    refs: list[str] = []
    for ref in value:
        if not isinstance(ref, str) or not ref.strip():
            raise PackageBTranche4BuildError(f"EDIT {question_id!r} has an invalid authority ref")
        refs.append(ref.strip())
    if not any(ref.startswith(MS_LEARN_PREFIX) for ref in refs):
        raise PackageBTranche4BuildError(f"EDIT {question_id!r} requires Microsoft Learn authority evidence")
    return refs


def _validate_review_artifact_question_id(question_id: str) -> None:
    if question_id in {".", ".."} or "/" in question_id or "\\" in question_id:
        raise PackageBTranche4BuildError(f"question ID {question_id!r} cannot be used as a contained review filename")


def _index_source_questions(questions: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(questions, list):
        raise PackageBTranche4BuildError("source bank questions must be a list")
    if len(questions) != REQUIRED_QUESTION_COUNT:
        raise PackageBTranche4BuildError(f"source bank must contain exactly {REQUIRED_QUESTION_COUNT} questions")
    indexed: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        if not isinstance(question, Mapping):
            raise PackageBTranche4BuildError("every source question must be an object")
        question_id = canonical_question_id(question)
        if not question_id:
            raise PackageBTranche4BuildError("every source question requires a canonical ID")
        if question_id in indexed:
            raise PackageBTranche4BuildError(f"duplicate source question ID: {question_id}")
        indexed[question_id] = question
    return indexed


def _verify_tracked_t3_git_blob() -> None:
    tracked = _REPO_ROOT / T3_SOURCE_BANK_FILENAME
    try:
        worktree = tracked.read_bytes()
    except OSError as exc:
        raise PackageBTranche4BuildError("tracked T3 worktree could not be read") from exc
    try:
        head_bytes = subprocess.check_output(["git", "show", f"HEAD:{T3_SOURCE_BANK_FILENAME}"], cwd=_REPO_ROOT)
        worktree_blob = subprocess.check_output(["git", "hash-object", str(tracked)], cwd=_REPO_ROOT).decode().strip()
        head_blob = (
            subprocess.check_output(["git", "rev-parse", f"HEAD:{T3_SOURCE_BANK_FILENAME}"], cwd=_REPO_ROOT)
            .decode()
            .strip()
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PackageBTranche4BuildError("tracked T3 Git blob could not be read") from exc
    if head_bytes != worktree:
        raise PackageBTranche4BuildError("tracked T3 Git blob does not equal worktree bytes")
    if worktree_blob != head_blob:
        raise PackageBTranche4BuildError("tracked T3 Git blob hash does not equal worktree hash-object")
    if hashlib.sha256(worktree).hexdigest() != EXPECTED_T3_SOURCE_SHA256:
        raise PackageBTranche4BuildError("tracked T3 worktree SHA-256 is not the canonical LF identity")


def _verify_parent_manifest() -> None:
    manifest_path = _REPO_ROOT / T3_MANIFEST_RELATIVE_PATH
    payload = _load_json_object(manifest_path, "parent T3 manifest")
    if payload.get("payload_sha256") != EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA:
        raise PackageBTranche4BuildError("parent T3 manifest payload SHA is not the expected canonical identity")
    target_bank = payload.get("target_bank")
    if not isinstance(target_bank, Mapping):
        raise PackageBTranche4BuildError("parent T3 manifest target_bank is invalid")
    if target_bank.get("filename") != T3_SOURCE_BANK_FILENAME:
        raise PackageBTranche4BuildError("parent T3 manifest target filename is not canonical")
    if target_bank.get("file_sha256") != EXPECTED_T3_SOURCE_SHA256:
        raise PackageBTranche4BuildError("parent T3 manifest target SHA is not the canonical LF identity")
    if target_bank.get("content_fingerprint") != EXPECTED_T3_SOURCE_FINGERPRINT:
        raise PackageBTranche4BuildError("parent T3 manifest target fingerprint is not canonical")
    if "alias" in json.dumps(payload):
        raise PackageBTranche4BuildError("parent T3 manifest unexpectedly contains alias data")


def _assert_canonical_t3_source(source_bank_path: Path, source_bytes: bytes) -> None:
    if source_bank_path.name != T3_SOURCE_BANK_FILENAME:
        raise PackageBTranche4BuildError("canonical T3 source filename is required")
    raw_sha = hashlib.sha256(source_bytes).hexdigest()
    if raw_sha == REJECTED_T3_CRLF_SHA256:
        raise PackageBTranche4BuildError("historical T3 CRLF SHA-256 is rejected")
    if b"\r\n" in source_bytes:
        raise PackageBTranche4BuildError("source bank contains CRLF bytes")
    if not source_bytes.endswith(b"\n"):
        raise PackageBTranche4BuildError("source bank must end with a terminal LF")
    try:
        payload = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PackageBTranche4BuildError(f"source bank is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise PackageBTranche4BuildError("source bank must contain a questions list")
    fingerprint = bank_content_fingerprint(payload["questions"])
    if raw_sha != EXPECTED_T3_SOURCE_SHA256:
        if fingerprint == EXPECTED_T3_SOURCE_FINGERPRINT:
            raise PackageBTranche4BuildError(
                "T3 source SHA-256 mismatch; fingerprint equality does not override raw-SHA mismatch"
            )
        raise PackageBTranche4BuildError("T3 source SHA-256 does not match the admitted T3 candidate identity")
    if fingerprint != EXPECTED_T3_SOURCE_FINGERPRINT:
        raise PackageBTranche4BuildError("T3 source fingerprint does not match the admitted T3 candidate identity")
    _verify_tracked_t3_git_blob()
    _verify_parent_manifest()


def _validated_review_rows(
    semantic_review: Mapping[str, Any],
    source_index: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], set[str], set[str]]:
    if set(semantic_review) != _SEMANTIC_REVIEW_FIELDS:
        raise PackageBTranche4BuildError("semantic-review input has missing or unknown fields")
    queue = semantic_review.get("review_queue")
    if not isinstance(queue, list):
        raise PackageBTranche4BuildError("semantic-review review_queue must be a list")
    edits: dict[str, dict[str, Any]] = {}
    skipped: set[str] = set()
    separates: set[str] = set()
    seen: set[str] = set()
    for row in queue:
        if not isinstance(row, Mapping):
            raise PackageBTranche4BuildError("every review_queue row must be an object")
        question_id = row.get("question_id")
        if not _nonblank(question_id):
            raise PackageBTranche4BuildError("every review_queue row requires a question_id")
        question_id = question_id.strip()
        if question_id in seen:
            raise PackageBTranche4BuildError(f"duplicate review_queue question ID: {question_id}")
        seen.add(question_id)
        if question_id not in source_index:
            raise PackageBTranche4BuildError(f"unknown review_queue question ID: {question_id}")
        if not _nonblank(row.get("review_note")):
            raise PackageBTranche4BuildError(f"review_note must be nonblank for {question_id}")
        disposition = row.get("disposition")
        if disposition == "SKIP":
            if set(row) != _SKIP_FIELDS:
                raise PackageBTranche4BuildError(f"SKIP {question_id!r} has an invalid schema")
            skipped.add(question_id)
            continue
        if disposition == "SEPARATE_CONTENT_CORRECTION":
            if set(row) != _SEPARATE_FIELDS:
                raise PackageBTranche4BuildError(f"SEPARATE {question_id!r} has an invalid schema")
            separates.add(question_id)
            continue
        if disposition != "EDIT":
            raise PackageBTranche4BuildError(f"invalid disposition for {question_id}: {disposition!r}")
        if question_id in T1_SKIP_QUESTION_IDS:
            raise PackageBTranche4BuildError(f"T1 SKIP question {question_id!r} cannot appear as an EDIT")
        if question_id in T2_SKIP_QUESTION_IDS:
            raise PackageBTranche4BuildError(f"T2 SKIP question {question_id!r} cannot appear as an EDIT")
        if set(row) != _EDIT_FIELDS:
            raise PackageBTranche4BuildError(f"EDIT {question_id!r} has an invalid schema")
        after = row.get("after")
        if not _exact_ad_string_mapping(after):
            raise PackageBTranche4BuildError(f"EDIT {question_id!r} after must be exact string A-D")
        semantics = row.get("semantic_review")
        if not _exact_ad_string_mapping(semantics) or any(
            semantics[letter] != SEMANTIC_EQUIVALENT for letter in CHOICE_LABELS
        ):
            raise PackageBTranche4BuildError(f"EDIT {question_id!r} must mark every A-D choice EQUIVALENT")
        source_question = source_index[question_id]
        source_choices = _keyed_choices(source_question)
        normalized_after = {letter: after[letter] for letter in CHOICE_LABELS}
        if normalized_after == source_choices:
            raise PackageBTranche4BuildError(f"EDIT {question_id!r} does not change any choice")
        if _correct_key_list(source_question) != _correct_key_list({**source_question, "choices": normalized_after}):
            raise PackageBTranche4BuildError(f"EDIT {question_id!r} cannot change the correct key")
        _validate_review_artifact_question_id(question_id)
        edits[question_id] = {
            "after": normalized_after,
            "semantic_review": {letter: SEMANTIC_EQUIVALENT for letter in CHOICE_LABELS},
            "authority_refs": _normalized_authority_refs(row.get("authority_refs"), question_id),
        }
    if seen != set(T4_DESIGN_QUEUE):
        missing = sorted(set(T4_DESIGN_QUEUE) - seen)
        extra = sorted(seen - set(T4_DESIGN_QUEUE))
        raise PackageBTranche4BuildError(
            "T4 design queue is unresolved or altered: " f"missing={missing!r} extra={extra!r}"
        )
    if set(edits) != T4_EDIT_IDS:
        raise PackageBTranche4BuildError("T4 EDIT ID set does not match the frozen closed world")
    if skipped != T4_SKIP_QUESTION_IDS:
        raise PackageBTranche4BuildError("T4 SKIP ID set does not match the frozen closed world")
    if separates != T4_SEPARATE_CORRECTION_IDS:
        raise PackageBTranche4BuildError("T4 SEPARATE ID set does not match the frozen closed world")
    return edits, skipped, separates


def _verify_candidate(
    source_payload: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
    edited_ids: set[str],
    skipped_ids: set[str],
    separate_ids: set[str],
) -> None:
    source_questions = source_payload["questions"]
    target_questions = candidate_payload["questions"]
    if len(target_questions) != REQUIRED_QUESTION_COUNT:
        raise PackageBTranche4BuildError("candidate question count changed")
    source_meta = {key: value for key, value in source_payload.items() if key != "questions"}
    target_meta = {key: value for key, value in candidate_payload.items() if key != "questions"}
    if source_meta != target_meta:
        raise PackageBTranche4BuildError("candidate top-level metadata changed")
    source_index = {canonical_question_id(question): question for question in source_questions}
    target_index = {canonical_question_id(question): question for question in target_questions}
    if set(source_index) != set(target_index):
        raise PackageBTranche4BuildError("candidate question-ID set changed")
    for question_id in sorted(source_index):
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        if question_id not in edited_ids:
            if source_question != target_question:
                raise PackageBTranche4BuildError(f"non-edited question changed: {question_id}")
            continue
        source_nonchoices = {key: value for key, value in source_question.items() if key != "choices"}
        target_nonchoices = {key: value for key, value in target_question.items() if key != "choices"}
        if source_nonchoices != target_nonchoices:
            raise PackageBTranche4BuildError(f"non-choice fields changed: {question_id}")
        if _keyed_choices(source_question) == _keyed_choices(target_question):
            raise PackageBTranche4BuildError(f"edited question did not transition: {question_id}")
        if _correct_key_list(source_question) != _correct_key_list(target_question):
            raise PackageBTranche4BuildError(f"edited question changed the correct key: {question_id}")
        if question_content_fingerprint(source_question) == question_content_fingerprint(target_question):
            raise PackageBTranche4BuildError(f"edited question has no content-fingerprint transition: {question_id}")
    for question_id in skipped_ids | separate_ids:
        if source_index[question_id] != target_index[question_id]:
            raise PackageBTranche4BuildError(f"non-EDIT queue question changed: {question_id}")


def build_package_b_tranche4(
    source_bank_path: Path,
    semantic_review_path: Path,
    candidate_bank_path: Path,
    review_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Build and admit deterministic Package-B T4 candidate evidence from human review."""
    source_bank_path = Path(source_bank_path)
    semantic_review_path = Path(semantic_review_path)
    candidate_bank_path = Path(candidate_bank_path)
    review_root = Path(review_root)
    manifest_path = Path(manifest_path)
    if source_bank_path.name == candidate_bank_path.name:
        raise PackageBTranche4BuildError("source and candidate bank filenames must differ")
    if candidate_bank_path.name in _FROZEN_OUTPUT_FILENAMES:
        raise PackageBTranche4BuildError("candidate bank filename must not overwrite a frozen bank")
    if _same_path(source_bank_path, candidate_bank_path) or _same_path(source_bank_path, manifest_path):
        raise PackageBTranche4BuildError("output paths must not overwrite the source bank")
    if _same_path(candidate_bank_path, manifest_path):
        raise PackageBTranche4BuildError("candidate and manifest output paths must differ")

    source_bytes_before = source_bank_path.read_bytes()
    _assert_canonical_t3_source(source_bank_path, source_bytes_before)
    source_payload = _load_json_object(source_bank_path, "source bank")
    source_questions = source_payload.get("questions")
    source_index = _index_source_questions(source_questions)
    semantic_bytes = semantic_review_path.read_bytes()
    if hashlib.sha256(semantic_bytes).hexdigest() != EXPECTED_T4_SEMANTIC_REVIEW_SHA256:
        raise PackageBTranche4BuildError("semantic-review SHA-256 does not match the prepared T4 packet")
    semantic_review = _load_json_object(semantic_review_path, "semantic review")
    if semantic_review.get("source_bank") != source_bank_path.name:
        raise PackageBTranche4BuildError("semantic-review source_bank filename does not match")
    if semantic_review.get("candidate_bank") != candidate_bank_path.name:
        raise PackageBTranche4BuildError("semantic-review candidate_bank filename does not match")
    if not _nonblank(semantic_review.get("work_id")):
        raise PackageBTranche4BuildError("semantic-review work_id must be nonblank")
    edits, skipped_ids, separate_ids = _validated_review_rows(semantic_review, source_index)
    protected_paths = {
        source_bank_path.resolve(),
        semantic_review_path.resolve(),
        candidate_bank_path.resolve(),
        manifest_path.resolve(),
    }
    for question_id in edits:
        receipt_path = review_root / REVIEW_DIRECTORY / f"{question_id}.json"
        if receipt_path.resolve() in protected_paths:
            raise PackageBTranche4BuildError("review receipt path collides with a package input or output")

    candidate_payload = copy.deepcopy(source_payload)
    target_questions = candidate_payload["questions"]
    target_index = {canonical_question_id(question): question for question in target_questions}
    for question_id in sorted(edits):
        target_index[question_id]["choices"] = copy.deepcopy(edits[question_id]["after"])
    edited_ids = set(edits)
    _verify_candidate(source_payload, candidate_payload, edited_ids, skipped_ids, separate_ids)
    if source_bank_path.read_bytes() != source_bytes_before:
        raise PackageBTranche4BuildError("source bank bytes changed before package materialization")

    _write_json(candidate_bank_path, candidate_payload)
    receipt_hashes: dict[str, str] = {}
    for question_id in sorted(edits):
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        receipt = {
            "question_id": question_id,
            "from_content_fingerprint": question_content_fingerprint(source_question),
            "to_content_fingerprint": question_content_fingerprint(target_question),
            "before": _keyed_choices(source_question),
            "after": _keyed_choices(target_question),
            "semantic_review": copy.deepcopy(edits[question_id]["semantic_review"]),
            "correct_key_before": _correct_key_list(source_question),
            "correct_key_after": _correct_key_list(target_question),
            "authority_refs": list(edits[question_id]["authority_refs"]),
            "disposition": REVIEW_DISPOSITION_APPROVED,
        }
        relative_path = Path(REVIEW_DIRECTORY) / f"{question_id}.json"
        receipt_path = review_root / relative_path
        _write_json(receipt_path, receipt)
        receipt_hashes[question_id] = sha256_file(receipt_path)

    source_file_sha256 = sha256_file(source_bank_path)
    target_file_sha256 = sha256_file(candidate_bank_path)
    source_fingerprint = bank_content_fingerprint(source_questions)
    target_fingerprint = bank_content_fingerprint(target_questions)
    edges: list[dict[str, Any]] = []
    for question_id in sorted(edits):
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        edges.append(
            {
                "question_id": question_id,
                "from_content_fingerprint": question_content_fingerprint(source_question),
                "to_content_fingerprint": question_content_fingerprint(target_question),
                "correct_key_unchanged": True,
                "choice_letter_mapping_unchanged": True,
                "prompt_unchanged": True,
                "objective_unchanged": True,
                "tier_unchanged": True,
                "exam_eligibility_unchanged": True,
                "choice_semantics": copy.deepcopy(edits[question_id]["semantic_review"]),
                "review_status": REVIEW_STATUS_APPROVED,
                "review_artifact": f"{REVIEW_DIRECTORY}/{question_id}.json",
                "review_artifact_sha256": receipt_hashes[question_id],
                "authority_refs": list(edits[question_id]["authority_refs"]),
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "manifest_kind": MANIFEST_KIND,
        "work_id": semantic_review["work_id"].strip(),
        "continuity_policy": CONTINUITY_POLICY,
        "source_bank": {
            "filename": source_bank_path.name,
            "file_sha256": source_file_sha256,
            "content_fingerprint": source_fingerprint,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "target_bank": {
            "filename": candidate_bank_path.name,
            "file_sha256": target_file_sha256,
            "content_fingerprint": target_fingerprint,
            "question_count": REQUIRED_QUESTION_COUNT,
        },
        "permitted_change_class": PERMITTED_CHANGE_CLASS,
        "edges": edges,
        "payload_sha256": "",
    }
    manifest["payload_sha256"] = canonical_manifest_sha256(manifest)
    _write_json(manifest_path, manifest)

    admission = admit_content_revision(
        manifest,
        source_questions=source_questions,
        target_questions=target_questions,
        source_bank_path=source_bank_path,
        target_bank_path=candidate_bank_path,
        review_root=review_root,
    )
    if admission.status != AdmissionStatus.PASS or admission.reasons != () or admission.admitted is None:
        reasons = ", ".join(reason.value for reason in admission.reasons) or "unknown rejection"
        raise PackageBTranche4BuildError(f"Package-A admission failed: {reasons}")
    if source_bank_path.read_bytes() != source_bytes_before:
        raise PackageBTranche4BuildError("source bank bytes changed during package build")

    return {
        "edited_question_ids": sorted(edits),
        "skipped_question_ids": sorted(skipped_ids),
        "separate_question_ids": sorted(separate_ids),
        "source_file_sha256": source_file_sha256,
        "target_file_sha256": target_file_sha256,
        "source_bank_content_fingerprint": source_fingerprint,
        "target_bank_content_fingerprint": target_fingerprint,
        "manifest_sha256": manifest["payload_sha256"],
        "review_count": len(edits),
        "admission_status": admission.status.value,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build deterministic Package-B tranche-4 evidence.")
    parser.add_argument("--source-bank", required=True, type=Path)
    parser.add_argument("--semantic-review", required=True, type=Path)
    parser.add_argument("--candidate-bank", required=True, type=Path)
    parser.add_argument("--review-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = build_package_b_tranche4(
            args.source_bank,
            args.semantic_review,
            args.candidate_bank,
            args.review_root,
            args.manifest,
        )
    except PackageBTranche4BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
