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
from tools.build_package_b_tranche4 import T4_EDIT_IDS

REVIEW_DIRECTORY = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T5"
T1_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t1.json"
T2_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t2.json"
T3_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t3.json"
T4_SOURCE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t4.json"
T5_CANDIDATE_BANK_FILENAME = "sc900_bank_v8_length_rebalanced_t5.json"
PRODUCTION_BANK_FILENAME = "sc900_bank_v8_final.json"
T4_MANIFEST_RELATIVE_PATH = "content_revision_evidence/manifests/sc900_answer_length_rebalance_t4.json"
EXPECTED_T4_SOURCE_SHA256 = "c40f919bb10cf2a5b965e1525b4771572a7f36fd63ef8749e277d988a04688b4"
EXPECTED_T4_SOURCE_FINGERPRINT = "99db6d4cbec9a722ef85280debb80f7c60c7acc0e7dba7d9663f2e1744bdae3c"
EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA = "83482105c1cb820292e14524b268ae8660e9ba9c493c055e920d22579b1639cb"
EXPECTED_T5_SEMANTIC_REVIEW_SHA256 = "84266440b8fb8b2168c1c51ae388fba2c15ab22d32a833d4a914769302c8f67c"
EXPECTED_QUESTION_COUNT = REQUIRED_QUESTION_COUNT
T5_DESIGN_QUEUE = (
    "sc900_mlc_q246",
    "sc900_mlc_q223",
    "sc900_mlc_q108",
    "sc900_mlc_q292",
    "sc900_mlc_q044",
    "sc900_mlc_q078",
    "sc900_mlc_q151",
    "sc900_mlc_q024",
    "sc900_mlc_q106",
    "sc900_mlc_q162",
    "sc900_mlc_q038",
    "sc900_mlc_q199",
    "sc900_p1_q018",
    "sc900_mlc_q237",
    "sc900_p3_q037",
    "sc900_p2_q043",
    "sc900_mlc_q260",
    "sc900_p1_q049",
    "sc900_mlc_q036",
    "sc900_mlc_q245",
    "sc900_mlc_q168",
    "sc900_mlc_q068",
    "sc900_mlc_q263",
    "sc900_p1_q020",
    "sc900_p1_q023",
    "sc900_mlc_q094",
    "sc900_p3_q030",
    "sc900_p3_q035",
    "sc900_mlc_q158",
    "sc900_mlc_q042",
    "sc900_p1_q038",
    "sc900_mlc_q240",
    "sc900_mlc_q139",
    "sc900_mlc_q057",
    "sc900_p3_q026",
    "sc900_mlc_q051",
    "sc900_mlc_q120",
    "sc900_p1_q015",
    "sc900_mlc_q065",
    "sc900_p2_q021",
    "sc900_p3_q013",
    "sc900_mlc_q090",
    "sc900_mlc_q040",
    "sc900_mlc_q003",
    "sc900_p2_q024",
    "sc900_mlc_q013",
    "sc900_p1_q007",
    "sc900_mlc_q213",
    "sc900_p1_q045",
    "sc900_mlc_q207",
    "sc900_p1_q046",
    "sc900_mlc_q001",
    "sc900_mlc_q093",
    "sc900_mlc_q210",
    "sc900_mlc_q211",
    "sc900_mlc_q007",
    "sc900_p1_q022",
    "sc900_mlc_q293",
    "sc900_mlc_q118",
    "sc900_mlc_q219",
    "sc900_mlc_q198",
    "sc900_mlc_q150",
    "sc900_mlc_q064",
    "sc900_mlc_q242",
)
T5_EDIT_IDS = frozenset(T5_DESIGN_QUEUE[:57])
T5_SKIP_QUESTION_IDS = frozenset(T5_DESIGN_QUEUE[57:58])
T5_SEPARATE_CORRECTION_IDS = frozenset(T5_DESIGN_QUEUE[58:])
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
    T4_SOURCE_BANK_FILENAME,
    PRODUCTION_BANK_FILENAME,
}
_REPO_ROOT = Path(__file__).resolve().parents[1]


class PackageBTranche5BuildError(ValueError):
    """Raised when reviewed input cannot produce an admissible Package-B T5 package."""


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageBTranche5BuildError(f"{label} is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PackageBTranche5BuildError(f"{label} must be a JSON object")
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
        raise PackageBTranche5BuildError(
            f"question {canonical_question_id(question)!r} must have exact string A-D choices"
        )
    return {letter: choices[letter] for letter in CHOICE_LABELS}


def _correct_key_list(question: Mapping[str, Any]) -> list[str]:
    correct = question.get("correct")
    if isinstance(correct, str):
        return [correct]
    if isinstance(correct, list) and all(isinstance(item, str) for item in correct):
        return sorted(correct)
    raise PackageBTranche5BuildError(f"edited question {canonical_question_id(question)!r} has an invalid correct key")


def _normalized_authority_refs(value: Any, question_id: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise PackageBTranche5BuildError(f"EDIT {question_id!r} requires authority_refs")
    refs: list[str] = []
    for ref in value:
        if not isinstance(ref, str) or not ref.strip():
            raise PackageBTranche5BuildError(f"EDIT {question_id!r} has an invalid authority ref")
        refs.append(ref.strip())
    if not any(ref.startswith(MS_LEARN_PREFIX) for ref in refs):
        raise PackageBTranche5BuildError(f"EDIT {question_id!r} requires Microsoft Learn authority evidence")
    if any(not ref.startswith(MS_LEARN_PREFIX) for ref in refs):
        raise PackageBTranche5BuildError(f"EDIT {question_id!r} rejects non-Learn implementation authority")
    return refs


def _validate_review_artifact_question_id(question_id: str) -> None:
    if question_id in {".", ".."} or "/" in question_id or "\\" in question_id:
        raise PackageBTranche5BuildError(f"question ID {question_id!r} cannot be used as a contained review filename")


def _index_source_questions(questions: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(questions, list):
        raise PackageBTranche5BuildError("source bank questions must be a list")
    if len(questions) != REQUIRED_QUESTION_COUNT:
        raise PackageBTranche5BuildError(f"source bank must contain exactly {REQUIRED_QUESTION_COUNT} questions")
    indexed: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        if not isinstance(question, Mapping):
            raise PackageBTranche5BuildError("every source question must be an object")
        question_id = canonical_question_id(question)
        if not question_id:
            raise PackageBTranche5BuildError("every source question requires a canonical ID")
        if question_id in indexed:
            raise PackageBTranche5BuildError(f"duplicate source question ID: {question_id}")
        indexed[question_id] = question
    return indexed


def _verify_tracked_t4_git_blob() -> None:
    tracked = _REPO_ROOT / T4_SOURCE_BANK_FILENAME
    try:
        worktree = tracked.read_bytes()
    except OSError as exc:
        raise PackageBTranche5BuildError("tracked T4 worktree could not be read") from exc
    try:
        head_bytes = subprocess.check_output(["git", "show", f"HEAD:{T4_SOURCE_BANK_FILENAME}"], cwd=_REPO_ROOT)
        worktree_blob = subprocess.check_output(["git", "hash-object", str(tracked)], cwd=_REPO_ROOT).decode().strip()
        head_blob = (
            subprocess.check_output(["git", "rev-parse", f"HEAD:{T4_SOURCE_BANK_FILENAME}"], cwd=_REPO_ROOT)
            .decode()
            .strip()
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PackageBTranche5BuildError("tracked T4 Git blob could not be read") from exc
    if head_bytes != worktree:
        raise PackageBTranche5BuildError("tracked T4 Git blob does not equal worktree bytes")
    if worktree_blob != head_blob:
        raise PackageBTranche5BuildError("tracked T4 Git blob hash does not equal worktree hash-object")
    if hashlib.sha256(worktree).hexdigest() != EXPECTED_T4_SOURCE_SHA256:
        raise PackageBTranche5BuildError("tracked T4 worktree SHA-256 is not the canonical LF identity")


def _verify_parent_manifest() -> None:
    manifest_path = _REPO_ROOT / T4_MANIFEST_RELATIVE_PATH
    payload = _load_json_object(manifest_path, "parent T4 manifest")
    if payload.get("payload_sha256") != EXPECTED_PARENT_MANIFEST_PAYLOAD_SHA:
        raise PackageBTranche5BuildError("parent T4 manifest payload SHA is not the expected canonical identity")
    target_bank = payload.get("target_bank")
    if not isinstance(target_bank, Mapping):
        raise PackageBTranche5BuildError("parent T4 manifest target_bank is invalid")
    if target_bank.get("filename") != T4_SOURCE_BANK_FILENAME:
        raise PackageBTranche5BuildError("parent T4 manifest target filename is not canonical")
    if target_bank.get("file_sha256") != EXPECTED_T4_SOURCE_SHA256:
        raise PackageBTranche5BuildError("parent T4 manifest target SHA is not the canonical LF identity")
    if target_bank.get("content_fingerprint") != EXPECTED_T4_SOURCE_FINGERPRINT:
        raise PackageBTranche5BuildError("parent T4 manifest target fingerprint is not canonical")
    serialized = json.dumps(payload)
    if "alias" in serialized or "historical_aliases" in serialized:
        raise PackageBTranche5BuildError("parent T4 manifest unexpectedly contains alias data")


def _assert_canonical_t4_source(source_bank_path: Path, source_bytes: bytes) -> None:
    if source_bank_path.name == T3_SOURCE_BANK_FILENAME:
        raise PackageBTranche5BuildError("T3 cannot be supplied as the T5 source bank")
    if source_bank_path.name == T5_CANDIDATE_BANK_FILENAME:
        raise PackageBTranche5BuildError("T5 cannot be supplied as the T5 source bank")
    if source_bank_path.name != T4_SOURCE_BANK_FILENAME:
        raise PackageBTranche5BuildError("canonical T4 source filename is required")
    raw_sha = hashlib.sha256(source_bytes).hexdigest()
    if b"\r\n" in source_bytes:
        raise PackageBTranche5BuildError("source bank contains CRLF bytes")
    if not source_bytes.endswith(b"\n"):
        raise PackageBTranche5BuildError("source bank must end with a terminal LF")
    try:
        payload = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PackageBTranche5BuildError(f"source bank is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise PackageBTranche5BuildError("source bank must contain a questions list")
    fingerprint = bank_content_fingerprint(payload["questions"])
    if raw_sha != EXPECTED_T4_SOURCE_SHA256:
        if fingerprint == EXPECTED_T4_SOURCE_FINGERPRINT:
            raise PackageBTranche5BuildError(
                "T4 source SHA-256 mismatch; fingerprint equality does not override raw-SHA mismatch"
            )
        raise PackageBTranche5BuildError("T4 source SHA-256 does not match the admitted T4 candidate identity")
    if fingerprint != EXPECTED_T4_SOURCE_FINGERPRINT:
        raise PackageBTranche5BuildError("T4 source fingerprint does not match the admitted T4 candidate identity")
    _verify_tracked_t4_git_blob()
    _verify_parent_manifest()


def _validated_review_rows(
    semantic_review: Mapping[str, Any],
    source_index: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], set[str], set[str]]:
    if set(semantic_review) != _SEMANTIC_REVIEW_FIELDS:
        raise PackageBTranche5BuildError("semantic-review input has missing or unknown fields")
    queue = semantic_review.get("review_queue")
    if not isinstance(queue, list):
        raise PackageBTranche5BuildError("semantic-review review_queue must be a list")
    edits: dict[str, dict[str, Any]] = {}
    skipped: set[str] = set()
    separates: set[str] = set()
    seen: set[str] = set()
    for row in queue:
        if not isinstance(row, Mapping):
            raise PackageBTranche5BuildError("every review_queue row must be an object")
        question_id = row.get("question_id")
        if not _nonblank(question_id):
            raise PackageBTranche5BuildError("every review_queue row requires a question_id")
        question_id = question_id.strip()
        if question_id in seen:
            raise PackageBTranche5BuildError(f"duplicate review_queue question ID: {question_id}")
        seen.add(question_id)
        if question_id not in source_index:
            raise PackageBTranche5BuildError(f"unknown review_queue question ID: {question_id}")
        if not _nonblank(row.get("review_note")):
            raise PackageBTranche5BuildError(f"review_note must be nonblank for {question_id}")
        disposition = row.get("disposition")
        if disposition == "SKIP":
            if set(row) != _SKIP_FIELDS:
                raise PackageBTranche5BuildError(f"SKIP {question_id!r} has an invalid schema")
            skipped.add(question_id)
            continue
        if disposition == "SEPARATE_CONTENT_CORRECTION":
            if set(row) != _SEPARATE_FIELDS:
                raise PackageBTranche5BuildError(f"SEPARATE {question_id!r} has an invalid schema")
            separates.add(question_id)
            continue
        if disposition != "EDIT":
            raise PackageBTranche5BuildError(f"invalid disposition for {question_id}: {disposition!r}")
        if question_id in T4_EDIT_IDS:
            raise PackageBTranche5BuildError(f"T4 EDIT question {question_id!r} cannot appear as a T5 EDIT")
        if set(row) != _EDIT_FIELDS:
            raise PackageBTranche5BuildError(f"EDIT {question_id!r} has an invalid schema")
        after = row.get("after")
        if not _exact_ad_string_mapping(after):
            raise PackageBTranche5BuildError(f"EDIT {question_id!r} after must be exact string A-D")
        semantics = row.get("semantic_review")
        if not _exact_ad_string_mapping(semantics) or any(
            semantics[letter] != SEMANTIC_EQUIVALENT for letter in CHOICE_LABELS
        ):
            raise PackageBTranche5BuildError(f"EDIT {question_id!r} must mark every A-D choice EQUIVALENT")
        source_question = source_index[question_id]
        source_choices = _keyed_choices(source_question)
        normalized_after = {letter: after[letter] for letter in CHOICE_LABELS}
        if normalized_after == source_choices:
            raise PackageBTranche5BuildError(f"EDIT {question_id!r} does not change any choice")
        if _correct_key_list(source_question) != _correct_key_list({**source_question, "choices": normalized_after}):
            raise PackageBTranche5BuildError(f"EDIT {question_id!r} cannot change the correct key")
        _validate_review_artifact_question_id(question_id)
        edits[question_id] = {
            "after": normalized_after,
            "semantic_review": {letter: SEMANTIC_EQUIVALENT for letter in CHOICE_LABELS},
            "authority_refs": _normalized_authority_refs(row.get("authority_refs"), question_id),
        }
    if seen != set(T5_DESIGN_QUEUE):
        missing = sorted(set(T5_DESIGN_QUEUE) - seen)
        extra = sorted(seen - set(T5_DESIGN_QUEUE))
        raise PackageBTranche5BuildError(
            "T5 design queue is unresolved or altered: " f"missing={missing!r} extra={extra!r}"
        )
    if set(edits) != T5_EDIT_IDS:
        raise PackageBTranche5BuildError("T5 EDIT ID set does not match the frozen closed world")
    if skipped != T5_SKIP_QUESTION_IDS:
        raise PackageBTranche5BuildError("T5 SKIP ID set does not match the frozen closed world")
    if separates != T5_SEPARATE_CORRECTION_IDS:
        raise PackageBTranche5BuildError("T5 SEPARATE ID set does not match the frozen closed world")
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
        raise PackageBTranche5BuildError("candidate question count changed")
    source_meta = {key: value for key, value in source_payload.items() if key != "questions"}
    target_meta = {key: value for key, value in candidate_payload.items() if key != "questions"}
    if source_meta != target_meta:
        raise PackageBTranche5BuildError("candidate top-level metadata changed")
    source_ids = [canonical_question_id(question) for question in source_questions]
    target_ids = [canonical_question_id(question) for question in target_questions]
    if source_ids != target_ids:
        raise PackageBTranche5BuildError("candidate question order or ID set changed")
    source_index = {canonical_question_id(question): question for question in source_questions}
    target_index = {canonical_question_id(question): question for question in target_questions}
    for question_id in source_ids:
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        if question_id not in edited_ids:
            if source_question != target_question:
                raise PackageBTranche5BuildError(f"non-edited question changed: {question_id}")
            continue
        source_nonchoices = {key: value for key, value in source_question.items() if key != "choices"}
        target_nonchoices = {key: value for key, value in target_question.items() if key != "choices"}
        if source_nonchoices != target_nonchoices:
            raise PackageBTranche5BuildError(f"non-choice fields changed: {question_id}")
        if _keyed_choices(source_question) == _keyed_choices(target_question):
            raise PackageBTranche5BuildError(f"edited question did not transition: {question_id}")
        if _correct_key_list(source_question) != _correct_key_list(target_question):
            raise PackageBTranche5BuildError(f"edited question changed the correct key: {question_id}")
        if question_content_fingerprint(source_question) == question_content_fingerprint(target_question):
            raise PackageBTranche5BuildError(f"edited question has no content-fingerprint transition: {question_id}")
    for question_id in skipped_ids | separate_ids | T4_EDIT_IDS:
        if source_index[question_id] != target_index[question_id]:
            raise PackageBTranche5BuildError(f"protected question changed: {question_id}")


def build_package_b_tranche5(
    source_bank_path: Path,
    semantic_review_path: Path,
    candidate_bank_path: Path,
    review_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Build and admit deterministic Package-B T5 candidate evidence from human review."""
    source_bank_path = Path(source_bank_path)
    semantic_review_path = Path(semantic_review_path)
    candidate_bank_path = Path(candidate_bank_path)
    review_root = Path(review_root)
    manifest_path = Path(manifest_path)
    if source_bank_path.name == candidate_bank_path.name:
        raise PackageBTranche5BuildError("source and candidate bank filenames must differ")
    if candidate_bank_path.name in _FROZEN_OUTPUT_FILENAMES:
        raise PackageBTranche5BuildError("candidate bank filename must not overwrite a frozen bank")
    if candidate_bank_path.name != T5_CANDIDATE_BANK_FILENAME:
        raise PackageBTranche5BuildError("candidate bank filename must be the canonical T5 name")
    if _same_path(source_bank_path, candidate_bank_path) or _same_path(source_bank_path, manifest_path):
        raise PackageBTranche5BuildError("output paths must not overwrite the source bank")
    if _same_path(candidate_bank_path, manifest_path):
        raise PackageBTranche5BuildError("candidate and manifest output paths must differ")

    source_bytes_before = source_bank_path.read_bytes()
    _assert_canonical_t4_source(source_bank_path, source_bytes_before)
    source_payload = _load_json_object(source_bank_path, "source bank")
    source_questions = source_payload.get("questions")
    source_index = _index_source_questions(source_questions)
    semantic_bytes = semantic_review_path.read_bytes()
    if hashlib.sha256(semantic_bytes).hexdigest() != EXPECTED_T5_SEMANTIC_REVIEW_SHA256:
        raise PackageBTranche5BuildError("semantic-review SHA-256 does not match the prepared T5 packet")
    semantic_review = _load_json_object(semantic_review_path, "semantic review")
    if semantic_review.get("source_bank") != source_bank_path.name:
        raise PackageBTranche5BuildError("semantic-review source_bank filename does not match")
    if semantic_review.get("candidate_bank") != candidate_bank_path.name:
        raise PackageBTranche5BuildError("semantic-review candidate_bank filename does not match")
    if not _nonblank(semantic_review.get("work_id")):
        raise PackageBTranche5BuildError("semantic-review work_id must be nonblank")
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
            raise PackageBTranche5BuildError("review receipt path collides with a package input or output")

    candidate_payload = copy.deepcopy(source_payload)
    target_questions = candidate_payload["questions"]
    target_index = {canonical_question_id(question): question for question in target_questions}
    for question_id in sorted(edits):
        target_index[question_id]["choices"] = copy.deepcopy(edits[question_id]["after"])
    edited_ids = set(edits)
    _verify_candidate(source_payload, candidate_payload, edited_ids, skipped_ids, separate_ids)
    if source_bank_path.read_bytes() != source_bytes_before:
        raise PackageBTranche5BuildError("source bank bytes changed before package materialization")

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
        raise PackageBTranche5BuildError(f"Package-A admission failed: {reasons}")
    if source_bank_path.read_bytes() != source_bytes_before:
        raise PackageBTranche5BuildError("source bank bytes changed during package build")

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
    parser = argparse.ArgumentParser(description="Build deterministic Package-B tranche-5 evidence.")
    parser.add_argument("--source-bank", required=True, type=Path)
    parser.add_argument("--semantic-review", required=True, type=Path)
    parser.add_argument("--candidate-bank", required=True, type=Path)
    parser.add_argument("--review-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = build_package_b_tranche5(
            args.source_bank,
            args.semantic_review,
            args.candidate_bank,
            args.review_root,
            args.manifest,
        )
    except PackageBTranche5BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
