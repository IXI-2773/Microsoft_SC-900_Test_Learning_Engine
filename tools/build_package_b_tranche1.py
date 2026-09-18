from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionStatus,
    CHOICE_LABELS,
    CONTINUITY_POLICY,
    MANIFEST_KIND,
    MS_LEARN_PREFIX,
    PERMITTED_CHANGE_CLASS,
    REQUIRED_QUESTION_COUNT,
    REVIEW_DISPOSITION_APPROVED,
    REVIEW_STATUS_APPROVED,
    SEMANTIC_EQUIVALENT,
    admit_content_revision,
    canonical_manifest_sha256,
    sha256_file,
)
from question_identity import (
    bank_content_fingerprint,
    canonical_question_id,
    question_content_fingerprint,
)


REVIEW_DIRECTORY = "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001-T1"
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


class PackageBTranche1BuildError(ValueError):
    """Raised when reviewed input cannot produce an admissible Package-B package."""


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageBTranche1BuildError(f"{label} is unreadable or invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PackageBTranche1BuildError(f"{label} must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")


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
        raise PackageBTranche1BuildError(
            f"question {canonical_question_id(question)!r} must have exact string A-D choices"
        )
    return {letter: choices[letter] for letter in CHOICE_LABELS}


def _correct_key_list(question: Mapping[str, Any]) -> list[str]:
    correct = question.get("correct")
    if isinstance(correct, str):
        return [correct]
    if isinstance(correct, list) and all(isinstance(item, str) for item in correct):
        return sorted(correct)
    raise PackageBTranche1BuildError(
        f"edited question {canonical_question_id(question)!r} has an invalid correct key"
    )


def _normalized_authority_refs(value: Any, question_id: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise PackageBTranche1BuildError(f"EDIT {question_id!r} requires authority_refs")
    refs: list[str] = []
    for ref in value:
        if not isinstance(ref, str) or not ref.strip():
            raise PackageBTranche1BuildError(f"EDIT {question_id!r} has an invalid authority ref")
        refs.append(ref.strip())
    if not any(ref.startswith(MS_LEARN_PREFIX) for ref in refs):
        raise PackageBTranche1BuildError(
            f"EDIT {question_id!r} requires Microsoft Learn authority evidence"
        )
    return refs


def _validate_review_artifact_question_id(question_id: str) -> None:
    if question_id in {".", ".."} or "/" in question_id or "\\" in question_id:
        raise PackageBTranche1BuildError(
            f"question ID {question_id!r} cannot be used as a contained review filename"
        )


def _index_source_questions(questions: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(questions, list):
        raise PackageBTranche1BuildError("source bank questions must be a list")
    if len(questions) != REQUIRED_QUESTION_COUNT:
        raise PackageBTranche1BuildError(
            f"source bank must contain exactly {REQUIRED_QUESTION_COUNT} questions"
        )
    indexed: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        if not isinstance(question, Mapping):
            raise PackageBTranche1BuildError("every source question must be an object")
        question_id = canonical_question_id(question)
        if not question_id:
            raise PackageBTranche1BuildError("every source question requires a canonical ID")
        if question_id in indexed:
            raise PackageBTranche1BuildError(f"duplicate source question ID: {question_id}")
        indexed[question_id] = question
    return indexed


def _validated_review_rows(
    semantic_review: Mapping[str, Any],
    source_index: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    if set(semantic_review) != _SEMANTIC_REVIEW_FIELDS:
        raise PackageBTranche1BuildError("semantic-review input has missing or unknown fields")
    queue = semantic_review.get("review_queue")
    if not isinstance(queue, list):
        raise PackageBTranche1BuildError("semantic-review review_queue must be a list")
    edits: dict[str, dict[str, Any]] = {}
    skipped: set[str] = set()
    seen: set[str] = set()
    for row in queue:
        if not isinstance(row, Mapping):
            raise PackageBTranche1BuildError("every review_queue row must be an object")
        question_id = row.get("question_id")
        if not _nonblank(question_id):
            raise PackageBTranche1BuildError("every review_queue row requires a question_id")
        question_id = question_id.strip()
        if question_id in seen:
            raise PackageBTranche1BuildError(f"duplicate review_queue question ID: {question_id}")
        seen.add(question_id)
        if question_id not in source_index:
            raise PackageBTranche1BuildError(f"unknown review_queue question ID: {question_id}")
        if not _nonblank(row.get("review_note")):
            raise PackageBTranche1BuildError(f"review_note must be nonblank for {question_id}")
        disposition = row.get("disposition")
        if disposition == "SKIP":
            if set(row) != _SKIP_FIELDS:
                raise PackageBTranche1BuildError(f"SKIP {question_id!r} has an invalid schema")
            skipped.add(question_id)
            continue
        if disposition != "EDIT":
            raise PackageBTranche1BuildError(f"invalid disposition for {question_id}: {disposition!r}")
        if set(row) != _EDIT_FIELDS:
            raise PackageBTranche1BuildError(f"EDIT {question_id!r} has an invalid schema")
        after = row.get("after")
        if not _exact_ad_string_mapping(after):
            raise PackageBTranche1BuildError(f"EDIT {question_id!r} after must be exact string A-D")
        semantics = row.get("semantic_review")
        if not _exact_ad_string_mapping(semantics) or any(
            semantics[letter] != SEMANTIC_EQUIVALENT for letter in CHOICE_LABELS
        ):
            raise PackageBTranche1BuildError(
                f"EDIT {question_id!r} must mark every A-D choice EQUIVALENT"
            )
        source_choices = _keyed_choices(source_index[question_id])
        normalized_after = {letter: after[letter] for letter in CHOICE_LABELS}
        if normalized_after == source_choices:
            raise PackageBTranche1BuildError(f"EDIT {question_id!r} does not change any choice")
        _validate_review_artifact_question_id(question_id)
        edits[question_id] = {
            "after": normalized_after,
            "semantic_review": {letter: SEMANTIC_EQUIVALENT for letter in CHOICE_LABELS},
            "authority_refs": _normalized_authority_refs(row.get("authority_refs"), question_id),
        }
    return edits, skipped


def _verify_candidate(
    source_payload: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
    edited_ids: set[str],
    skipped_ids: set[str],
) -> None:
    source_questions = source_payload["questions"]
    target_questions = candidate_payload["questions"]
    if len(target_questions) != REQUIRED_QUESTION_COUNT:
        raise PackageBTranche1BuildError("candidate question count changed")
    source_meta = {key: value for key, value in source_payload.items() if key != "questions"}
    target_meta = {key: value for key, value in candidate_payload.items() if key != "questions"}
    if source_meta != target_meta:
        raise PackageBTranche1BuildError("candidate top-level metadata changed")
    source_index = {canonical_question_id(question): question for question in source_questions}
    target_index = {canonical_question_id(question): question for question in target_questions}
    if set(source_index) != set(target_index):
        raise PackageBTranche1BuildError("candidate question-ID set changed")
    for question_id in sorted(source_index):
        source_question = source_index[question_id]
        target_question = target_index[question_id]
        if question_id not in edited_ids:
            if source_question != target_question:
                raise PackageBTranche1BuildError(f"non-edited question changed: {question_id}")
            continue
        source_nonchoices = {key: value for key, value in source_question.items() if key != "choices"}
        target_nonchoices = {key: value for key, value in target_question.items() if key != "choices"}
        if source_nonchoices != target_nonchoices:
            raise PackageBTranche1BuildError(f"non-choice fields changed: {question_id}")
        if _keyed_choices(source_question) == _keyed_choices(target_question):
            raise PackageBTranche1BuildError(f"edited question did not transition: {question_id}")
        if question_content_fingerprint(source_question) == question_content_fingerprint(target_question):
            raise PackageBTranche1BuildError(
                f"edited question has no content-fingerprint transition: {question_id}"
            )
    for question_id in skipped_ids:
        if source_index[question_id] != target_index[question_id]:
            raise PackageBTranche1BuildError(f"SKIP question changed: {question_id}")


def build_package_b_tranche1(
    source_bank_path: Path,
    semantic_review_path: Path,
    candidate_bank_path: Path,
    review_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Build and admit deterministic Package-B candidate evidence from human review."""
    source_bank_path = Path(source_bank_path)
    semantic_review_path = Path(semantic_review_path)
    candidate_bank_path = Path(candidate_bank_path)
    review_root = Path(review_root)
    manifest_path = Path(manifest_path)
    if source_bank_path.name == candidate_bank_path.name:
        raise PackageBTranche1BuildError("source and candidate bank filenames must differ")
    if _same_path(source_bank_path, candidate_bank_path) or _same_path(source_bank_path, manifest_path):
        raise PackageBTranche1BuildError("output paths must not overwrite the source bank")
    if _same_path(candidate_bank_path, manifest_path):
        raise PackageBTranche1BuildError("candidate and manifest output paths must differ")

    source_bytes_before = source_bank_path.read_bytes()
    source_payload = _load_json_object(source_bank_path, "source bank")
    source_questions = source_payload.get("questions")
    source_index = _index_source_questions(source_questions)
    semantic_review = _load_json_object(semantic_review_path, "semantic review")
    if semantic_review.get("source_bank") != source_bank_path.name:
        raise PackageBTranche1BuildError("semantic-review source_bank filename does not match")
    if semantic_review.get("candidate_bank") != candidate_bank_path.name:
        raise PackageBTranche1BuildError("semantic-review candidate_bank filename does not match")
    if not _nonblank(semantic_review.get("work_id")):
        raise PackageBTranche1BuildError("semantic-review work_id must be nonblank")
    edits, skipped_ids = _validated_review_rows(semantic_review, source_index)
    protected_paths = {
        source_bank_path.resolve(),
        semantic_review_path.resolve(),
        candidate_bank_path.resolve(),
        manifest_path.resolve(),
    }
    for question_id in edits:
        receipt_path = review_root / REVIEW_DIRECTORY / f"{question_id}.json"
        if receipt_path.resolve() in protected_paths:
            raise PackageBTranche1BuildError("review receipt path collides with a package input or output")

    candidate_payload = copy.deepcopy(source_payload)
    target_questions = candidate_payload["questions"]
    target_index = {canonical_question_id(question): question for question in target_questions}
    for question_id in sorted(edits):
        target_index[question_id]["choices"] = copy.deepcopy(edits[question_id]["after"])
    edited_ids = set(edits)
    _verify_candidate(source_payload, candidate_payload, edited_ids, skipped_ids)
    if source_bank_path.read_bytes() != source_bytes_before:
        raise PackageBTranche1BuildError("source bank bytes changed before package materialization")

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
    if (
        admission.status != AdmissionStatus.PASS
        or admission.reasons != ()
        or admission.admitted is None
    ):
        reasons = ", ".join(reason.value for reason in admission.reasons) or "unknown rejection"
        raise PackageBTranche1BuildError(f"Package-A admission failed: {reasons}")
    if source_bank_path.read_bytes() != source_bytes_before:
        raise PackageBTranche1BuildError("source bank bytes changed during package build")

    return {
        "edited_question_ids": sorted(edits),
        "source_file_sha256": source_file_sha256,
        "target_file_sha256": target_file_sha256,
        "source_bank_content_fingerprint": source_fingerprint,
        "target_bank_content_fingerprint": target_fingerprint,
        "manifest_sha256": manifest["payload_sha256"],
        "review_count": len(edits),
        "admission_status": admission.status.value,
    }
