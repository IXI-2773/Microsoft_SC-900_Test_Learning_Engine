# SC-900 Content-Revision Equivalence Migration — Package A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Package-A migration infrastructure that admits only an exact governed content revision, preserves learner progress/history/session state across that admitted revision, and leaves current fail-closed behavior unchanged when no authority is present.

**Architecture:** Keep `question_identity.py` and ordinary `session_store.py` semantics strict. Add a pure authority layer (`content_revision_authority.py`), a pure transform/history layer (`content_revision_migration.py`), and an initially empty release registry (`content_revision_registry.py`). `RuntimePersistence` owns transactional file I/O. `TestingEngineApp` and session/history mixins only orchestrate an already-admitted revision. Package A uses synthetic revisions only and does not change production question wording, activate a new bank, register a production manifest, rebuild the EXE, or merge anything.

**Tech Stack:** Python 3.11, stdlib `dataclasses`, `enum.StrEnum`, `hashlib`, `json`, `pathlib`, `unittest`, existing SC-900 identity/session/persistence modules, Ruff, Black, mypy.

**Spec:** `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

## Global Constraints

- Authorized scope is **Package A — migration infrastructure only**.
- Execution must start from exact `main` SHA `23d440b6976b9f6bbb3b77285bf0d11effc2513f`; if `main` differs, stop and reconcile before editing.
- Use an isolated worktree/branch at execution time via `superpowers:using-git-worktrees`; branch name: `implementation/sc900-content-revision-equivalence-migration-A-001`.
- Do not use the user's desktop or local terminal. Use the authorized repository/cloud execution environment.
- Python target remains 3.11.
- `question_identity.py` strict content fingerprinting and `CHANGED_CONTENT` behavior remain authoritative when no admitted revision is supplied.
- Do not add a generic bypass such as `allow_changed_content=True`.
- Ordinary `migrate_session_snapshot(...)` bank-fingerprint mismatch behavior remains strict.
- Live-state migration version 1 supports one direct source-bank -> target-bank edge per execution.
- Historical events are immutable: do not rewrite old `question_content_fingerprint`, `selected_texts`, `correct_texts`, correctness, confidence, timing, or timestamps.
- Existing quarantined progress is never automatically resurrected.
- Package A production question wording changes = **0**.
- Package A production bank activation = **NO**.
- `AUTHORIZED_CONTENT_REVISION_MANIFESTS` remains empty in Package A.
- No production manifest/review file is added under `content_revision_evidence/` in Package A.
- No production EXE change or rebuild is authorized in Package A.
- Do not modify or merge PR #13.
- Do not modify protected recovery refs/tags.
- No merge is authorized by this plan.
- TDD order is mandatory for each behavior: failing test -> verify RED -> minimal implementation -> verify GREEN -> commit.
- Existing identity/session/adversarial tests remain regression authority and must not be weakened.
- Final verification must include focused Package-A tests, existing canonical identity/session tests, full unittest discovery, `python -m tools.run_quality_checks`, `python -m tools.lint_bank --allow-warnings sc900_bank_v8_final.json`, and `python -m tools.verify_installation`.
- The existing production bank SHA-256 must remain `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.

---

## File Map

### New source files

- `content_revision_authority.py` — exact manifest/review parsing, canonical manifest hashing, finite rejection reasons, source/target bank admission, mechanical invariants, semantic-review validation, exact directed edges/lineage.
- `content_revision_migration.py` — pure progress transform, pure session transform, deterministic migration ID, idempotence, revision-aware history matching/filtering.
- `content_revision_registry.py` — code-controlled registry of bundled manifests and registered-manifest resolver; module-level registry stays empty in Package A.

### New tests

- `tests/test_content_revision_authority.py` — schema/hash/admission/closed-world/mechanical/semantic/registry/lineage adversarial tests.
- `tests/test_content_revision_migration.py` — progress/history/session/pending-selection/idempotence/quarantine-non-resurrection tests.
- `tests/test_content_revision_app_integration.py` — persistence atomicity, progress-load integration, cross-filename session discovery/restore, history consumers, no-authority regression behavior.

### Existing source files to modify

- `runtime_persistence.py` — explicit transactional progress/session migration operations; ordinary loading remains strict.
- `app.py` — resolve an optional registered revision after loading a bank, migrate progress before ordinary content-epoch handling, and otherwise preserve current progress-load behavior.
- `app_session_persistence_mixin.py` — include admitted source-bank session filename patterns and attempt explicit session migration before ordinary bank-mismatch quarantine.
- `app_analytics_mixin.py` — route question-history lookups through the common revision-aware resolver.
- `app_game_mixin.py` — route question-history lookups through the common revision-aware resolver.
- `app_session_builder_mixin.py` — route question-history lookups through the common revision-aware resolver.
- `pyproject.toml` — register new first-party modules and mypy targets.
- `tools/run_quality_checks.py` — add new maintained modules to `QUALITY_TARGETS`.

### Existing source files intentionally not modified

- `question_identity.py` — strict baseline fingerprint/history/content-epoch behavior stays unchanged.
- `session_store.py` — ordinary canonical session validation stays unchanged; explicit migration calls it before and after transformation.
- `session_identity.py` — reuse existing `canonical_session_signature(...)` and `ordered_question_ids(...)`.
- `session_models.py` — no historical event schema rewrite; progress migration provenance is stored in progress top-level metadata.
- `sc900_bank_v8_final.json` — byte-for-byte unchanged.

### Implementation evidence

- Create at final verification: `docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md`.

---

### Task 1: Define authority types, duplicate-safe JSON parsing, and canonical manifest hashing

**Files:**
- Create: `content_revision_authority.py`
- Create: `tests/test_content_revision_authority.py`

**Interfaces:**
- Define `AdmissionStatus(StrEnum)` with exact values `PASS` and `FAIL`.
- Define `RevisionFailureReason(StrEnum)` with the finite reasons listed in the approved spec plus `UNREGISTERED_MANIFEST`, `REGISTRY_HASH_MISMATCH`, `LINEAGE_INCOMPLETE`, and `LINEAGE_CONFLICT`.
- Define `ContentRevisionManifestError(ValueError)` exposing `.reason` and `.detail`.
- Define frozen dataclass `RevisionEdge` with `question_id`, `from_content_fingerprint`, `to_content_fingerprint`, `review_artifact`, `review_artifact_sha256`.
- Define frozen dataclass `AdmittedRevision` with manifest/source/target hashes/fingerprints/filenames and `edges: tuple[RevisionEdge, ...]`.
- Define frozen dataclass `AdmissionResult` with `status: AdmissionStatus`, `reasons: tuple[RevisionFailureReason, ...]`, `admitted: AdmittedRevision | None`.
- Define `parse_manifest_json(raw: str) -> dict[str, Any]`.
- Define `canonical_manifest_sha256(payload: Mapping[str, Any]) -> str`.
- Define `sha256_file(path: Path) -> str` using raw file bytes.

- [ ] **Step 1: Establish exact execution baseline before the first code edit**

Run:

```bash
git rev-parse HEAD
git rev-parse origin/main
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment3_adversarial_closure \
  -v
```

Expected:

```text
HEAD = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
origin/main = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
focused identity/session regression set passes
```

If either SHA differs, stop without implementation.

- [ ] **Step 2: Write RED tests for canonical hashing and duplicate-key rejection**

Add tests equivalent to:

```python
import unittest

from content_revision_authority import (
    ContentRevisionManifestError,
    RevisionFailureReason,
    canonical_manifest_sha256,
    parse_manifest_json,
)


class ContentRevisionAuthorityParsingTests(unittest.TestCase):
    def test_manifest_hash_ignores_key_order_whitespace_and_stored_digest(self):
        first = {
            "schema_version": 1,
            "manifest_kind": "sc900_content_revision_equivalence",
            "payload_sha256": "first",
        }
        second = {
            "payload_sha256": "second",
            "manifest_kind": "sc900_content_revision_equivalence",
            "schema_version": 1,
        }
        self.assertEqual(canonical_manifest_sha256(first), canonical_manifest_sha256(second))

    def test_duplicate_json_key_fails_closed(self):
        raw = '{"schema_version":1,"schema_version":1}'
        with self.assertRaises(ContentRevisionManifestError) as ctx:
            parse_manifest_json(raw)
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, ctx.exception.reason)
```

Also add tests for malformed JSON and non-object top-level JSON. Both must fail with `SCHEMA_UNSUPPORTED`.

- [ ] **Step 3: Run the new tests and verify RED**

```bash
python -m unittest tests.test_content_revision_authority.ContentRevisionAuthorityParsingTests -v
```

Expected: import failure because `content_revision_authority.py` does not exist.

- [ ] **Step 4: Implement the minimal authority primitives**

Implement this exact shape:

```python
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class AdmissionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class RevisionFailureReason(StrEnum):
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    MISSING_FIELD = "MISSING_FIELD"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    MANIFEST_HASH_MISMATCH = "MANIFEST_HASH_MISMATCH"
    SOURCE_BANK_FILE_HASH_MISMATCH = "SOURCE_BANK_FILE_HASH_MISMATCH"
    TARGET_BANK_FILE_HASH_MISMATCH = "TARGET_BANK_FILE_HASH_MISMATCH"
    SOURCE_BANK_FINGERPRINT_MISMATCH = "SOURCE_BANK_FINGERPRINT_MISMATCH"
    TARGET_BANK_FINGERPRINT_MISMATCH = "TARGET_BANK_FINGERPRINT_MISMATCH"
    QUESTION_COUNT_MISMATCH = "QUESTION_COUNT_MISMATCH"
    QUESTION_ID_SET_MISMATCH = "QUESTION_ID_SET_MISMATCH"
    DUPLICATE_QUESTION_ID = "DUPLICATE_QUESTION_ID"
    UNDECLARED_CONTENT_CHANGE = "UNDECLARED_CONTENT_CHANGE"
    EXTRA_EQUIVALENCE_EDGE = "EXTRA_EQUIVALENCE_EDGE"
    DUPLICATE_EQUIVALENCE_EDGE = "DUPLICATE_EQUIVALENCE_EDGE"
    FROM_FINGERPRINT_MISMATCH = "FROM_FINGERPRINT_MISMATCH"
    TO_FINGERPRINT_MISMATCH = "TO_FINGERPRINT_MISMATCH"
    CORRECT_KEY_CHANGED = "CORRECT_KEY_CHANGED"
    CHOICE_LABEL_SET_CHANGED = "CHOICE_LABEL_SET_CHANGED"
    CHOICE_LETTER_MAPPING_CHANGED = "CHOICE_LETTER_MAPPING_CHANGED"
    PROMPT_CHANGED = "PROMPT_CHANGED"
    OBJECTIVE_CHANGED = "OBJECTIVE_CHANGED"
    DOMAIN_CHANGED = "DOMAIN_CHANGED"
    TOPICS_CHANGED = "TOPICS_CHANGED"
    TIER_CHANGED = "TIER_CHANGED"
    EXAM_ELIGIBILITY_CHANGED = "EXAM_ELIGIBILITY_CHANGED"
    QUESTION_TYPE_CHANGED = "QUESTION_TYPE_CHANGED"
    NONPERMITTED_FIELD_CHANGED = "NONPERMITTED_FIELD_CHANGED"
    SEMANTIC_REVIEW_MISSING = "SEMANTIC_REVIEW_MISSING"
    SEMANTIC_REVIEW_HASH_MISMATCH = "SEMANTIC_REVIEW_HASH_MISMATCH"
    SEMANTIC_EQUIVALENCE_NOT_APPROVED = "SEMANTIC_EQUIVALENCE_NOT_APPROVED"
    CHOICE_SEMANTICS_CHANGED = "CHOICE_SEMANTICS_CHANGED"
    AUTHORITY_EVIDENCE_MISSING = "AUTHORITY_EVIDENCE_MISSING"
    UNREGISTERED_MANIFEST = "UNREGISTERED_MANIFEST"
    REGISTRY_HASH_MISMATCH = "REGISTRY_HASH_MISMATCH"
    LINEAGE_INCOMPLETE = "LINEAGE_INCOMPLETE"
    LINEAGE_CONFLICT = "LINEAGE_CONFLICT"


class ContentRevisionManifestError(ValueError):
    def __init__(self, reason: RevisionFailureReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        message = reason.value if not detail else f"{reason.value}: {detail}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RevisionEdge:
    question_id: str
    from_content_fingerprint: str
    to_content_fingerprint: str
    review_artifact: str
    review_artifact_sha256: str


@dataclass(frozen=True, slots=True)
class AdmittedRevision:
    manifest_sha256: str
    source_bank_filename: str
    source_bank_file_sha256: str
    source_bank_content_fingerprint: str
    target_bank_filename: str
    target_bank_file_sha256: str
    target_bank_content_fingerprint: str
    edges: tuple[RevisionEdge, ...]

    def edge_for(self, question_id: str) -> RevisionEdge | None:
        qid = str(question_id or "").strip()
        return next((edge for edge in self.edges if edge.question_id == qid), None)

    def changed_question_ids(self) -> frozenset[str]:
        return frozenset(edge.question_id for edge in self.edges)


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    status: AdmissionStatus
    reasons: tuple[RevisionFailureReason, ...]
    admitted: AdmittedRevision | None


def _duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContentRevisionManifestError(RevisionFailureReason.DUPLICATE_JSON_KEY, key)
        result[key] = value
    return result


def parse_manifest_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw, object_pairs_hook=_duplicate_safe_object)
    except ContentRevisionManifestError:
        raise
    except json.JSONDecodeError as exc:
        raise ContentRevisionManifestError(RevisionFailureReason.SCHEMA_UNSUPPORTED, str(exc)) from exc
    if not isinstance(payload, dict):
        raise ContentRevisionManifestError(RevisionFailureReason.SCHEMA_UNSUPPORTED, "manifest must be a JSON object")
    return payload


def canonical_manifest_sha256(payload: Mapping[str, Any]) -> str:
    materialized = dict(payload)
    materialized.pop("payload_sha256", None)
    raw = json.dumps(materialized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
```

- [ ] **Step 5: Run parsing tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_authority.ContentRevisionAuthorityParsingTests -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add content_revision_authority.py tests/test_content_revision_authority.py
git commit -m "feat: add content revision manifest primitives"
```

---

### Task 2: Implement exact 454-question bank admission, mechanical invariants, and semantic-review validation

**Files:**
- Modify: `content_revision_authority.py`
- Modify: `tests/test_content_revision_authority.py`

**Interfaces:**
- Add `admit_content_revision(manifest, source_questions, target_questions, source_bank_path, target_bank_path, review_root) -> AdmissionResult` using keyword-only source/target/path arguments.
- Reuse existing `canonical_question_id`, `question_content_fingerprint`, `bank_content_fingerprint`, and canonical-ID validation from `question_identity.py`.
- Manifest/review schemas are closed-world.
- Manifest digest uses canonical JSON excluding its own `payload_sha256`; bank/review file digests use raw bytes.

- [ ] **Step 1: Add a 454-question synthetic fixture and RED positive-admission test**

Use this helper pattern:

```python
def synthetic_question(index: int, choices: dict[str, str] | None = None, **overrides):
    qid = f"Q{index:04d}"
    row = {
        "id": qid,
        "question_number": index,
        "prompt": f"Prompt {index}",
        "choices": choices or {
            "A": f"Alpha long wording {index}",
            "B": f"Beta {index}",
            "C": f"Gamma {index}",
            "D": f"Delta {index}",
        },
        "correct": ["A"],
        "general_explanation": f"Explanation {index}",
        "choice_explanations": {"A": "A", "B": "B", "C": "C", "D": "D"},
        "domain": "Identity",
        "chapter": "1",
        "subtitle": "Basics",
        "question_type": "multiple_choice",
        "topics": ["Entra"],
        "objective_code": "1.1",
        "study_focus": "Core",
        "exam_eligible": True,
    }
    row.update(overrides)
    return row


def synthetic_bank():
    return [synthetic_question(index) for index in range(1, 455)]
```

Change only `Q0001` target choice `A` from `"Alpha long wording 1"` to `"Alpha 1"`. Write source/target JSON bank files in a `TemporaryDirectory`. Build a review JSON directly from computed source/target choice maps and computed fingerprints. Give all A-D semantic statuses `EQUIVALENT`, both correct keys `['A']`, one nonempty Microsoft Learn URL, and disposition `APPROVED_FOR_FULL_CONTINUITY`.

Build the manifest from actual computed raw file hashes, actual bank content fingerprints, actual review file hash, and a computed canonical `payload_sha256`. Assert PASS and exact edge from/to fingerprints.

- [ ] **Step 2: Add RED schema/hash/bank-population tests**

Add separate tests for:

```text
unsupported schema_version
wrong manifest_kind
wrong continuity_policy
wrong permitted_change_class
unknown field at top level, bank object, edge object, review object
missing required field at each object level
manifest payload hash mismatch
source raw file hash mismatch
target raw file hash mismatch
source bank content fingerprint mismatch
target bank content fingerprint mismatch
source question count != 454
target question count != 454
duplicate canonical question ID
different canonical question-ID set
```

Assert the exact finite reason for each case.

- [ ] **Step 3: Add RED closed-world and per-edge tests**

Add separate tests for:

```text
actual changed IDs contain an undeclared question -> UNDECLARED_CONTENT_CHANGE
manifest contains edge for unchanged question -> EXTRA_EQUIVALENCE_EDGE
duplicate edge question ID -> DUPLICATE_EQUIVALENCE_EDGE
wrong edge from fingerprint -> FROM_FINGERPRINT_MISMATCH
wrong edge to fingerprint -> TO_FINGERPRINT_MISMATCH
```

- [ ] **Step 4: Add RED mechanical-invariant tests**

For a declared changed question, mutate one property at a time and assert:

```text
correct key -> CORRECT_KEY_CHANGED
choice label set -> CHOICE_LABEL_SET_CHANGED
literal cross-letter swap of source B/C texts -> CHOICE_LETTER_MAPPING_CHANGED
prompt -> PROMPT_CHANGED
objective_code -> OBJECTIVE_CHANGED
domain -> DOMAIN_CHANGED
topics -> TOPICS_CHANGED
study_focus -> TIER_CHANGED
exam_eligible -> EXAM_ELIGIBILITY_CHANGED
question_type -> QUESTION_TYPE_CHANGED
general_explanation -> NONPERMITTED_FIELD_CHANGED
choice_explanations -> NONPERMITTED_FIELD_CHANGED
chapter/subtitle/question_number/extra durable field -> NONPERMITTED_FIELD_CHANGED
```

The validator may permit only the values under `choices[A]`, `choices[B]`, `choices[C]`, `choices[D]` to differ after named invariant checks.

- [ ] **Step 5: Add RED semantic/review tests**

Add separate cases:

```text
review file missing -> SEMANTIC_REVIEW_MISSING
review raw SHA mismatch -> SEMANTIC_REVIEW_HASH_MISMATCH
review QID mismatch -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
review from/to FP mismatch -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
review before choices do not exactly equal source keyed choices -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
review after choices do not exactly equal target keyed choices -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
review correct keys do not exactly equal source/target correct keys -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
one choice status AMBIGUOUS -> CHOICE_SEMANTICS_CHANGED
one choice status SUBSTANTIVELY_CHANGED -> CHOICE_SEMANTICS_CHANGED
review authority_refs empty -> AUTHORITY_EVIDENCE_MISSING
manifest edge authority_refs empty -> AUTHORITY_EVIDENCE_MISSING
review disposition not APPROVED_FOR_FULL_CONTINUITY -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
manifest review_status not APPROVED -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
```

- [ ] **Step 6: Run authority tests and verify RED**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: Task-1 parsing tests PASS; admission tests FAIL because admission is not implemented.

- [ ] **Step 7: Implement exact schema constants and deterministic validation order**

Use these exact closed-world field sets:

```python
_MANIFEST_FIELDS = {
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
_BANK_FIELDS = {"filename", "file_sha256", "content_fingerprint", "question_count"}
_EDGE_FIELDS = {
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
_REVIEW_FIELDS = {
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
_CHOICE_LABELS = ("A", "B", "C", "D")
```

Validation order is fixed:

```text
schema/unknown/missing fields
canonical manifest hash
raw source/target file hashes
question counts and canonical-ID set
bank content fingerprints
actual changed-ID set == edge-ID set
per-edge from/to fingerprints
named mechanical invariants
review existence/hash/schema/exact before-after binding
per-choice EQUIVALENT + authority refs + approved disposition
```

Version 1 returns the first deterministic blocking reason as `AdmissionResult(status=FAIL, reasons=(reason,), admitted=None)`. There is no warning-success state.

- [ ] **Step 8: Implement mechanical comparison and review binding**

For each declared changed question:

```text
require source/target choice keys exactly A,B,C,D
compare named invariant fields first for specific reasons
reject a literal cross-letter swap before semantic review
make deep copies of source/target rows and replace target `choices` with source `choices`; if the remaining rows differ, emit NONPERMITTED_FIELD_CHANGED
require review.before == source choices keyed by letter
require review.after == target choices keyed by letter
require review.semantic_review == {A:EQUIVALENT,B:EQUIVALENT,C:EQUIVALENT,D:EQUIVALENT}
require review correct keys exact
require nonempty authority_refs in manifest edge and review
```

On success create immutable `RevisionEdge` objects and one `AdmittedRevision` from the validated manifest.

- [ ] **Step 9: Run authority tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: PASS.

- [ ] **Step 10: Run strict identity regression wall**

```bash
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_backlog1_segment3_adversarial_closure \
  -v
```

Expected: PASS; changed content still fails closed without the new authority.

- [ ] **Step 11: Commit Task 2**

```bash
git add content_revision_authority.py tests/test_content_revision_authority.py
git commit -m "feat: validate exact content revision authority"
```

---

### Task 3: Add the empty release registry, registered-target resolution, and directed lineage

**Files:**
- Create: `content_revision_registry.py`
- Modify: `content_revision_authority.py`
- Modify: `tests/test_content_revision_authority.py`

**Interfaces:**
- Module constant: `AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {}`.
- Module constant: `CONTENT_REVISION_EVIDENCE_ROOT = Path(__file__).resolve().parent / "content_revision_evidence"`.
- Add `AdmittedRevision.permits_fingerprint_transition(question_id, from_fp, to_fp) -> bool`.
- Add `approved_lineage(revisions, question_id, from_fingerprint, to_fingerprint) -> tuple[RevisionEdge, ...] | None`.
- Add `resolve_registered_revision_for_target(target_bank_path, target_questions, load_questions, evidence_root, registry) -> AdmissionResult | None`, where `load_questions(Path)` returns a sequence of question mappings.

- [ ] **Step 1: Write RED registry tests**

Prove:

```text
module-level registry is exactly empty
file under content_revision_evidence without registry entry is ignored
registered manifest with wrong canonical registry hash -> REGISTRY_HASH_MISMATCH
registered manifest for another target filename is ignored
exact registered manifest + exact source/target bank files -> delegates to admission and PASS
more than one registered manifest matching the same target filename -> LINEAGE_CONFLICT
```

Tests use a temporary evidence directory and pass an explicit registry mapping. Do not mutate the module-level production registry in source.

- [ ] **Step 2: Write RED lineage tests**

Use synthetic admitted revisions:

```text
Q1 V1->V2 permits direct transition
Q1 V1->V2 rejects V2->V1
Q1 V1->V2 and V2->V3 yields a two-edge V1->V3 lineage
missing V2->V3 yields None
conflicting two Q1 edges sharing one from FP but different to FPs -> LINEAGE_CONFLICT
cycle V1->V2 and V2->V1 does not loop and is rejected as conflict for traversal beyond the cycle
```

- [ ] **Step 3: Run registry/lineage tests and verify RED**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: new registry/lineage tests FAIL.

- [ ] **Step 4: Implement registered-target resolution**

`content_revision_registry.py` must:

```text
sort registry entries by relative manifest path
read each registered manifest from evidence_root / relative path
parse duplicate-safely
compare canonical manifest hash to registry value before using its metadata
select entries whose manifest.target_bank.filename == target_bank_path.name
return None for zero matches
return LINEAGE_CONFLICT failure for more than one match
resolve source bank path as target_bank_path.parent / manifest.source_bank.filename
load source questions with the injected load_questions callback
call admit_content_revision with source path, target path, target_questions, and evidence_root / "reviews"
```

Any missing/unreadable registered manifest or source bank fails closed with the corresponding finite hash/schema reason; it must not become implicit authority.

- [ ] **Step 5: Implement direct and chained lineage traversal**

Use exact `(question_id, from_fp)` indexing and a visited fingerprint set. No lexical/ID-only fallback. A conflicting next edge raises `ContentRevisionManifestError(LINEAGE_CONFLICT, ...)`.

- [ ] **Step 6: Run authority tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add content_revision_authority.py content_revision_registry.py tests/test_content_revision_authority.py
git commit -m "feat: add registered revision lineage authority"
```

---

### Task 4: Implement pure progress migration and revision-aware historical joins

**Files:**
- Create: `content_revision_migration.py`
- Create: `tests/test_content_revision_migration.py`

**Interfaces:**
- Define `MigrationStatus(StrEnum)` values `APPLIED` and `MIGRATION_ALREADY_APPLIED`.
- Define `MigrationFailureReason(StrEnum)` values `SOURCE_PROGRESS_BANK_MISMATCH`, `SOURCE_PROGRESS_FINGERPRINT_MISMATCH`, `TARGET_QUESTION_MISSING`, `UNAUTHORIZED_PROGRESS_TRANSITION`, `MIGRATION_LINEAGE_CONFLICT`, `SOURCE_SESSION_BANK_MISMATCH`, `TARGET_SESSION_QUESTION_MISMATCH`.
- Define `ContentRevisionMigrationError(ValueError)` exposing `.reason` and `.detail`.
- Define frozen `PayloadMigrationResult` with `payload: dict[str, Any]`, `changed: bool`, `status: MigrationStatus`, `migration_id: str`.
- Add `derive_migration_id(revision) -> str`.
- Add `migrate_progress_payload(payload, target_questions, revision, migrated_at) -> PayloadMigrationResult`.
- Add `history_event_matches_approved_revision(event, question, revision_or_sequence) -> bool`.
- Add `history_events_for_question_revision_aware(history_map, question, revision_or_sequence=None) -> list[Mapping[str, Any]]`.
- Store progress lineage at top-level `content_revision_migrations: list[dict[str, str]]`; never edit historical event rows.

- [ ] **Step 1: Write RED progress-preservation test**

Build a canonical source progress payload bound to `revision.source_bank_content_fingerprint` with active Q1/Q2 records, exact `question_content_fingerprints`, one old Q1 history event containing old text/fingerprint, and one pre-existing `quarantined_questions` record.

Assert an admitted Q1 revision:

```text
preserves every learner metric in Q1/Q2 records
sets active bank fingerprint to target
sets Q1 stored FP from exact edge.from to exact edge.to
keeps unchanged Q2 stored FP unchanged
leaves the history list deep-equal to source
leaves the quarantined mapping deep-equal to source
appends one migration lineage row for Q1 containing exact question/from/to/manifest/migration_id/migrated_at
```

- [ ] **Step 2: Add RED rejection/idempotence tests**

Prove:

```text
payload source bank FP mismatch -> SOURCE_PROGRESS_BANK_MISMATCH
changed active record stored FP mismatch -> SOURCE_PROGRESS_FINGERPRINT_MISMATCH
active record needs a transition but no edge exists -> UNAUTHORIZED_PROGRESS_TRANSITION
active question absent from target bank -> TARGET_QUESTION_MISSING
pre-existing quarantined Q1 is not restored to active questions
already-target payload with the complete expected migration lineage -> MIGRATION_ALREADY_APPLIED and changed=False
second exact application does not duplicate attempts/history/lineage
bank target but incomplete/conflicting lineage -> MIGRATION_LINEAGE_CONFLICT
```

- [ ] **Step 3: Add RED historical immutability and revision-aware match tests**

Prove:

```text
same QID + same FP -> strict match
same QID + approved old->new FP -> match
same QID + no approved edge -> no match
different QID -> no match
reverse-only edge -> no match
complete V1->V2->V3 sequence -> match
missing middle edge -> no match
returned event retains original old FP and old selected/correct text
revision=None reproduces existing strict matcher behavior
```

- [ ] **Step 4: Run migration tests and verify RED**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: module import failure.

- [ ] **Step 5: Implement deterministic migration ID**

Use labeled canonical JSON:

```python
def derive_migration_id(revision: AdmittedRevision) -> str:
    material = {
        "kind": "sc900_content_revision_migration_v1",
        "manifest_sha256": revision.manifest_sha256,
        "source_bank_content_fingerprint": revision.source_bank_content_fingerprint,
        "target_bank_content_fingerprint": revision.target_bank_content_fingerprint,
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

- [ ] **Step 6: Implement progress transform**

Algorithm:

```text
1. Deep-copy input.
2. Build target question fingerprint map by canonical ID.
3. Derive migration_id.
4. If bank FP is already target, require every changed active question to be target-bound and every expected changed-active lineage row with this migration_id to exist; then return verified no-op. Any partial/conflicting target state fails MIGRATION_LINEAGE_CONFLICT.
5. Otherwise require bank FP == revision.source bank FP.
6. For each active record, require target question exists.
7. If stored FP == target FP, preserve.
8. Otherwise require exact edge where stored FP == edge.from and target FP == edge.to; update stored FP.
9. Never move or rewrite quarantined records.
10. Never edit history.
11. Set bank FP to target.
12. Append exactly one lineage row for each changed active question transitioned in this operation.
13. Return APPLIED/changed=True.
```

- [ ] **Step 7: Implement revision-aware history matching**

Call existing `history_event_matches_question(...)` first. If strict match is false, require same canonical ID, nonblank historical FP, and an exact approved direct/chained lineage to `question_content_fingerprint(question)`. With no revision argument, return strict behavior only.

- [ ] **Step 8: Run migration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: PASS.

- [ ] **Step 9: Run existing history/identity adversarial tests**

```bash
python -m unittest tests.test_backlog1_segment3_adversarial_closure -v
```

Expected: PASS unchanged.

- [ ] **Step 10: Commit Task 4**

```bash
git add content_revision_migration.py tests/test_content_revision_migration.py
git commit -m "feat: preserve progress across approved content revisions"
```

---

### Task 5: Implement pure canonical saved-session migration

**Files:**
- Modify: `content_revision_migration.py`
- Modify: `tests/test_content_revision_migration.py`

**Interfaces:**
- Add `migrate_session_payload(saved, target_questions, revision, target_bank_file) -> PayloadMigrationResult`.
- Use existing `migrate_session_snapshot(...)`, `canonical_session_signature(...)`, and `ordered_question_ids(...)` for strict source/target validation.
- Do not modify `session_store.py`.

- [ ] **Step 1: Write RED positive session-migration test**

Build a valid source snapshot with `build_session_snapshot(...)` containing:

```text
Q1 changed, answered=True, selected/pending=["B"]
Q2 changed, answered=False, selected/pending=["B"]
Q3 unchanged, flagged=True
session_answer_history with Q1 old content fingerprint and old text
nonzero current_index and elapsed_seconds
nonempty builder_context, current_quests, session_rewards, unlocked_rewards
```

Assert migrated target:

```text
Q1 completed selection remains B
Q2 selected/pending becomes empty while answered remains false
Q3 state remains unchanged
ordered question IDs and restore IDs remain unchanged
session answer history remains deep-equal to source
current index, elapsed, builder context, quests, rewards remain unchanged
bank_file becomes revision.target_bank_filename/explicit target_bank_file
bank_fingerprint becomes target fingerprint
session_signature is canonical_session_signature(mode, target_fp, question_ids)
restore_signature is canonical_session_signature(mode, target_fp, restore_question_ids)
```

- [ ] **Step 2: Add RED rejection tests**

Prove:

```text
source snapshot bank FP mismatch -> SOURCE_SESSION_BANK_MISMATCH
invalid source session_signature -> existing strict ValueError propagated/wrapped as migration failure
invalid source restore_signature -> strict failure
unknown session question ID in target -> TARGET_SESSION_QUESTION_MISMATCH
changed question target FP does not equal edge.to -> TARGET_SESSION_QUESTION_MISMATCH
changed question has no edge -> TARGET_SESSION_QUESTION_MISMATCH
```

- [ ] **Step 3: Run session migration tests and verify RED**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: new session tests FAIL.

- [ ] **Step 4: Implement strict source validation then target rebinding**

Implementation sequence:

```text
read source IDs/restore IDs/question_numbers from snapshot
require saved bank_fingerprint == revision.source bank FP
call migrate_session_snapshot with source bank FP and available target IDs to validate source identity/signatures/cardinality
build target question FP map
for every saved/restore ID: require target question exists; for changed IDs require target FP == exact edge.to
copy validated snapshot
for each answer row on a changed question: if answered is false and selected or pending is nonempty, clear selected and pending only
leave completed answers unchanged
leave session_answer_history unchanged
set bank_file and target bank FP
recompute session_signature and restore_signature
call migrate_session_snapshot again with target bank FP to validate final canonical snapshot
return APPLIED result with deterministic migration_id
```

- [ ] **Step 5: Run session migration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: PASS.

- [ ] **Step 6: Run existing canonical session tests**

```bash
python -m unittest \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment2_session_app_integration \
  -v
```

Expected: PASS unchanged.

- [ ] **Step 7: Commit Task 5**

```bash
git add content_revision_migration.py tests/test_content_revision_migration.py
git commit -m "feat: migrate approved saved sessions to target bank identity"
```

---

### Task 6: Add transactional persistence and crash-safe archive semantics

**Files:**
- Modify: `runtime_persistence.py`
- Create: `tests/test_content_revision_app_integration.py`

**Interfaces:**
- Add `content_revision_archive_path(source_path, migration_id, label) -> Path`.
- Add `migrate_progress_across_approved_revision(source_path, target_path, target_questions, revision, migrated_at) -> tuple[dict[str, Any] | None, Path | None, Exception | None]`.
- Add `migrate_session_file_across_approved_revision(source_path, target_path, target_questions, revision, target_bank_file) -> tuple[dict[str, Any] | None, Path | None, Exception | None]`.

- [ ] **Step 1: Write RED progress atomicity tests**

Using real temporary files and `unittest.mock`, prove:

```text
successful migration creates deterministic pre-migration archive and verified target
backup failure leaves source bytes unchanged and no target replacement occurs
write failure leaves source bytes unchanged and returns archive path + error
same source/target path is safe because archive exists before replacement
existing target with exact already-applied migration -> no-op, no duplicate archive
existing target with conflicting migration lineage -> fail closed and preserve both files
```

- [ ] **Step 2: Write RED session atomicity/crash-recovery tests**

Prove:

```text
successful source!=target migration writes and verifies target before source removal
source archive exists before source removal
write failure preserves source
archive failure before target write prevents migration
post-target source-removal failure returns recoverable error while verified target and archive remain
restart with verified target + matching migration ID finishes source archival/removal without duplicate target
existing target + conflicting migration identity preserves both and fails
source==target uses pre-migration archive and does not unlink the newly written target
```

- [ ] **Step 3: Run persistence tests and verify RED**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: FAIL because new persistence methods do not exist.

- [ ] **Step 4: Implement deterministic archive path**

Use:

```python
def content_revision_archive_path(self, source_path: Path, *, migration_id: str, label: str) -> Path:
    source = Path(source_path)
    safe_label = str(label or "content_revision").strip().replace(" ", "_")
    return self.backup_dir / f"{source.stem}_{safe_label}_{migration_id[:12]}{source.suffix}"
```

If an archive path already exists, require byte-for-byte equality with the source before treating it as reusable.

- [ ] **Step 5: Implement progress persistence operation**

Use `load_json_or_backup(source_path)` directly. Do not call ordinary target-bank `load_progress_with_identity_migration(...)` on the source. Call the pure transform first. If already applied, return without another backup. Otherwise archive source, write target through `self.write_json`, re-read target, and verify target bank FP plus complete migration lineage.

If `source_path == target_path`, the deterministic archive is mandatory before replacement.

- [ ] **Step 6: Implement session persistence operation**

Read source JSON, call pure session transform, derive migration ID, reject conflicting target, write target, re-read and strictly validate target, create/verify source archive, then remove old source only when source and target paths differ. Do not classify a failed authorized migration as malformed JSON.

- [ ] **Step 7: Run persistence tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: persistence tests PASS.

- [ ] **Step 8: Run existing persistence regressions**

```bash
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_backlog1_segment1_adversarial_review \
  tests.test_sc900_engine_regression \
  -v
```

Expected: PASS except already-established display-dependent skips.

- [ ] **Step 9: Commit Task 6**

```bash
git add runtime_persistence.py tests/test_content_revision_app_integration.py
git commit -m "feat: persist approved content revision migrations atomically"
```

---

### Task 7: Resolve registered authority in bank load and migrate progress before ordinary content-epoch handling

**Files:**
- Modify: `app.py`
- Modify: `tests/test_content_revision_app_integration.py`

**Interfaces:**
- `TestingEngineApp.content_revision_authority` is initialized to `None`.
- Add `_resolve_content_revision_authority_for_loaded_bank() -> AdmissionResult | None`.
- Add `_load_progress_with_content_revision_if_needed() -> tuple[dict[str, Any] | None, Path | None, Exception | None]`.
- Reuse `resolve_registered_revision_for_target(...)` with `load_questions=lambda bank_path: load_bank(bank_path)["questions"]`.

- [ ] **Step 1: Write RED no-registry progress-load regression**

Create a lightweight app fixture around `load_progress_if_present()` with empty registry. Assert it calls the existing ordinary progress-load path and preserves current `CHANGED_CONTENT` behavior exactly.

- [ ] **Step 2: Write RED cross-filename progress migration test**

Use temporary target bank filename `target_bank.json`, source bank filename `source_bank.json`, and user-data progress files derived from both stems. Patch/inject a synthetic registry mapping and exact evidence. Assert:

```text
registered target revision is admitted after target bank data is loaded
source progress path is derived from revision.source_bank_filename
when target progress path is absent and source progress exists, source -> target migration occurs
source archive exists
target progress loads with target bank FP and preserved learner state
```

- [ ] **Step 3: Write RED in-place progress migration test**

Set source/target progress paths equal by using equal runtime bank stems in the test fixture while keeping distinct source/target bank files for authority admission. Assert pre-migration archive exists before target replacement and final data loads normally.

- [ ] **Step 4: Write RED invalid-registered-authority fail-closed test**

With a registry entry present but corrupted manifest/source/review evidence, assert:

```text
progress source is preserved
progress_write_blocked becomes true
a warning/log path is exercised
ordinary changed-content migration is not run afterward against the target bank
```

- [ ] **Step 5: Run app progress integration tests and verify RED**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: new app progress cases FAIL.

- [ ] **Step 6: Initialize optional authority and resolve it after bank parsing**

In `TestingEngineApp.__init__`, initialize:

```python
self.content_revision_authority = None
```

In `load_from_path`, `self.data = load_bank(path)` already occurs before `load_progress_if_present()`. Keep that order. At the start of `load_progress_if_present()`, call `_resolve_content_revision_authority_for_loaded_bank()` using `self.data["questions"]` as target questions and `load_bank(source_path)["questions"]` through the injected resolver callback.

With empty production registry, resolution returns `None` and current behavior is unchanged.

- [ ] **Step 7: Implement explicit progress-source selection before ordinary load**

When an admitted revision is present:

```text
current target progress path = self.progress_path
source progress path = self.progress_file_for_bank(Path(revision.source_bank_filename))
if target progress exists and its stored bank FP is target -> use ordinary current-bank load
if target progress exists and its stored bank FP is source -> migrate target path in-place
if target progress absent and source progress exists -> migrate source path to target path
if neither exists -> keep blank progress
if migration errors -> block writes, preserve source, report warning, do not run ordinary target content-epoch migration afterward
```

Pass `now_iso()` as `migrated_at`.

After a successful explicit migration, feed the returned migrated dict into the existing progress normalization/application flow without re-running changed-content migration against the source.

- [ ] **Step 8: Run app progress integration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: progress integration cases PASS.

- [ ] **Step 9: Run current progress-load regressions**

```bash
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_sc900_final_bank_activation_migration \
  -v
```

Expected: PASS.

- [ ] **Step 10: Commit Task 7**

```bash
git add app.py tests/test_content_revision_app_integration.py
git commit -m "feat: migrate approved progress before target bank binding"
```

---

### Task 8: Integrate cross-filename session discovery and the common history resolver

**Files:**
- Modify: `app_session_persistence_mixin.py`
- Modify: `app_analytics_mixin.py`
- Modify: `app_game_mixin.py`
- Modify: `app_session_builder_mixin.py`
- Modify: `tests/test_content_revision_app_integration.py`

**Interfaces:**
- Add `_session_builder_glob_patterns(mode) -> tuple[str, ...]` that includes the current target-bank pattern and, when an authority is active, the source-bank stem pattern.
- Add `_try_migrate_session_across_content_revision(path, saved, desired_builder_identity) -> tuple[Path, Mapping[str, Any]] | None`.
- All history consumers call `history_events_for_question_revision_aware(...)` with `getattr(self, "content_revision_authority", None)`.

- [ ] **Step 1: Write RED source-bank session discovery test**

Use different source/target bank filenames and a valid source canonical session whose filename uses the source bank stem. Assert `find_resumable_session_for_builder(...)` discovers it only when a matching admitted revision is active, migrates it to the target canonical filename, archives/removes the old source resumable file after verification, and returns the target path.

- [ ] **Step 2: Write RED no-authority and failed-authority session tests**

Prove:

```text
no authority -> current bank-mismatch behavior remains
admitted authority but transform/persistence failure -> source session remains and is not quarantined as corrupt JSON
a malformed JSON/session unrelated to revision migration -> existing quarantine behavior remains
```

- [ ] **Step 3: Write RED history-consumer tests**

Cover at least:

```text
AnalyticsMixin path: old approved event contributes under V2
GameRewardsMixin stability path: old approved event contributes under V2
SessionBuilderMixin stability/mastery path: old approved event contributes under V2
without authority, same old event does not attach
historical selected_texts/correct_texts remain old values in downstream input
```

- [ ] **Step 4: Run app integration tests and verify RED**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: new session/history cases FAIL.

- [ ] **Step 5: Implement dual-pattern session discovery**

Refactor the existing single `_session_builder_glob_pattern(mode)` use into `_session_builder_glob_patterns(mode)` while retaining the current target pattern. When authority exists, add:

```python
source_stem = runtime_bank_stem(Path(revision.source_bank_filename))
source_pattern = f"{source_stem}_{safe_mode}_session_*.json"
```

Deduplicate paths before evaluating candidates.

- [ ] **Step 6: Attempt explicit migration before mismatch quarantine**

When ordinary `migrate_session_snapshot(...)` fails because `saved.bank_fingerprint` differs from the current target:

```text
if no authority -> current fail-closed path
if saved bank FP != authority.source -> current fail-closed path
if current bank FP != authority.target -> current fail-closed path
otherwise compute target canonical session path using current bank + saved IDs/builder context
call RuntimePersistence.migrate_session_file_across_approved_revision
on success continue candidate evaluation with migrated payload/path
on migration failure preserve source and skip candidate without corrupt-file quarantine
```

Do not broaden legacy `allow_legacy` behavior.

- [ ] **Step 7: Replace all direct history lookups in the three consumers**

Import:

```python
from content_revision_migration import history_events_for_question_revision_aware
```

Replace each existing `history_events_for_question(history_map, question)` call in `app_analytics_mixin.py`, `app_game_mixin.py`, and `app_session_builder_mixin.py` with the common resolver and the optional authority. Do not change downstream formulas or mutate events.

- [ ] **Step 8: Run app integration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: PASS.

- [ ] **Step 9: Run directly affected existing tests**

```bash
python -m unittest \
  tests.test_backlog1_segment2_session_app_integration \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment3_adversarial_closure \
  tests.test_backlog2_confidence_epistemics \
  -v
```

Expected: PASS; no-authority behavior remains unchanged.

- [ ] **Step 10: Commit Task 8**

```bash
git add \
  app_session_persistence_mixin.py \
  app_analytics_mixin.py \
  app_game_mixin.py \
  app_session_builder_mixin.py \
  tests/test_content_revision_app_integration.py
git commit -m "feat: integrate approved revision continuity into runtime consumers"
```

---

### Task 9: Add new modules to repository quality/type authority

**Files:**
- Modify: `pyproject.toml`
- Modify: `tools/run_quality_checks.py`
- Modify: `tests/test_content_revision_authority.py`

**Interfaces:**
- No runtime behavior change.
- New maintained modules become Ruff/Black/mypy targets.

- [ ] **Step 1: Write RED quality-target assertion**

Add a test that imports `tools.run_quality_checks.QUALITY_TARGETS` and asserts the three new source files are present. Read `pyproject.toml` and assert the module names occur in Ruff `known-first-party` and the `.py` files occur in mypy `files`.

- [ ] **Step 2: Run authority tests and verify RED**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: quality-target assertion FAIL.

- [ ] **Step 3: Update quality/type configuration**

Add these module names to Ruff `known-first-party`:

```text
content_revision_authority
content_revision_migration
content_revision_registry
```

Add these source files to `[tool.mypy].files` and `tools/run_quality_checks.py` `QUALITY_TARGETS`:

```text
content_revision_authority.py
content_revision_migration.py
content_revision_registry.py
```

- [ ] **Step 4: Run authority tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: PASS.

- [ ] **Step 5: Run targeted formatting/lint/type checks**

Run:

```bash
python -m ruff check \
  content_revision_authority.py content_revision_migration.py content_revision_registry.py \
  runtime_persistence.py app.py app_session_persistence_mixin.py app_analytics_mixin.py app_game_mixin.py app_session_builder_mixin.py \
  tests/test_content_revision_authority.py tests/test_content_revision_migration.py tests/test_content_revision_app_integration.py
python -m black --check \
  content_revision_authority.py content_revision_migration.py content_revision_registry.py \
  runtime_persistence.py app.py app_session_persistence_mixin.py app_analytics_mixin.py app_game_mixin.py app_session_builder_mixin.py \
  tests/test_content_revision_authority.py tests/test_content_revision_migration.py tests/test_content_revision_app_integration.py
python -m mypy
```

Expected: PASS. If Black reports formatting differences, run Black only on the listed touched files, then rerun these checks. Do not reformat unrelated files.

- [ ] **Step 6: Commit Task 9**

```bash
git add pyproject.toml tools/run_quality_checks.py tests/test_content_revision_authority.py
git commit -m "chore: add content revision modules to quality gates"
```

---

### Task 10: Execute Package-A closure verification and record exact evidence

**Files:**
- Create: `docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md`
- No production code edit is allowed in this task unless verification exposes a defect; if a defect is found, return to the owning task's RED/GREEN cycle and make a separate fix commit before restarting closure.

**Interfaces:**
- Produces exact Package-A terminal evidence.
- Does not authorize Package B or production activation.

- [ ] **Step 1: Verify exact diff boundary before closure tests**

Run:

```bash
git diff --name-status 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD
git status --short
```

Before the verification receipt is created, the only allowed changed paths are:

```text
content_revision_authority.py
content_revision_migration.py
content_revision_registry.py
runtime_persistence.py
app.py
app_session_persistence_mixin.py
app_analytics_mixin.py
app_game_mixin.py
app_session_builder_mixin.py
pyproject.toml
tools/run_quality_checks.py
tests/test_content_revision_authority.py
tests/test_content_revision_migration.py
tests/test_content_revision_app_integration.py
```

No bank JSON, EXE, PR13, recovery-ref artifact, production manifest, or unrelated source path may appear.

- [ ] **Step 2: Run focused new Package-A tests**

```bash
python -m unittest \
  tests.test_content_revision_authority \
  tests.test_content_revision_migration \
  tests.test_content_revision_app_integration \
  -v
```

Expected: PASS.

- [ ] **Step 3: Run canonical identity/session regression wall**

```bash
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_backlog1_segment1_adversarial_review \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment2_session_app_integration \
  tests.test_backlog1_segment3_adversarial_closure \
  tests.test_sc900_final_bank_activation_migration \
  -v
```

Expected: PASS; existing `CHANGED_CONTENT` and ordinary bank mismatch behavior remain unchanged with empty registry/no authority.

- [ ] **Step 4: Run full repository unittest discovery**

```bash
python -m unittest discover -s tests -v
```

Expected: zero failures/errors. Environment-specific Tk/display skips are acceptable only when reported as skips.

- [ ] **Step 5: Run repository quality, bank lint, and installation verification**

```bash
python -m tools.run_quality_checks
python -m tools.lint_bank --allow-warnings sc900_bank_v8_final.json
python -m tools.verify_installation
```

Expected: all commands PASS. Bank lint must still report the current 454-question production bank and only the already-known allowed warning profile.

- [ ] **Step 6: Prove production bank and EXE immutability**

Run:

```bash
python - <<'PY'
from hashlib import sha256
from pathlib import Path

bank = Path("sc900_bank_v8_final.json")
print("BANK", sha256(bank.read_bytes()).hexdigest())
exe = Path("SC900TestLearningEngine.exe")
print("EXE_PRESENT", exe.exists())
if exe.exists():
    print("EXE", sha256(exe.read_bytes()).hexdigest())
PY
```

Required bank SHA-256:

```text
177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
```

If the root production EXE is present, required unchanged SHA-256:

```text
9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558
```

If the EXE is absent from the isolated checkout, record that absence; do not build it.

- [ ] **Step 7: Write the verification receipt using only observed evidence**

Create `docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md` with these headings and fields, each populated directly from the command outputs just observed:

```text
# Package A Verification — Content-Revision Equivalence Migration

WORK_ID
START_MAIN_SHA
IMPLEMENTATION_HEAD

## Scope
PRODUCTION_QUESTION_WORDING_CHANGES
PRODUCTION_BANK_ACTIVATION
AUTHORIZED_CONTENT_REVISION_MANIFESTS_COUNT
PR13_MODIFIED
RECOVERY_REFS_MODIFIED
PRODUCTION_EXE_CHANGED
MERGED

## Focused verification
PACKAGE_A_TESTS
IDENTITY_SESSION_REGRESSION_WALL
FULL_UNITTEST_DISCOVERY
QUALITY_CHECKS
BANK_LINT
INSTALLATION_VERIFICATION

## Production immutability
PRODUCTION_BANK_SHA256
PRODUCTION_EXE_PRESENT
PRODUCTION_EXE_SHA256

## Contract proof
NO_AUTHORITY_BEHAVIOR
ADMITTED_SYNTHETIC_REVISION
HISTORICAL_EVENTS_REWRITTEN
QUARANTINE_RESURRECTION
PENDING_SELECTION_ON_CHANGED_UNANSWERED_QUESTION
MIGRATION_IDEMPOTENCE
ATOMIC_BACKUP_WRITE_RECOVERY

## Disposition
PACKAGE_A
PACKAGE_B_AUTHORIZED
PRODUCTION_ACTIVATION_AUTHORIZED
MERGE_AUTHORIZED
```

Required constant values where the commands/tests support them:

```text
WORK_ID = SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 / PACKAGE-A
START_MAIN_SHA = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
PRODUCTION_QUESTION_WORDING_CHANGES = 0
PRODUCTION_BANK_ACTIVATION = NO
AUTHORIZED_CONTENT_REVISION_MANIFESTS_COUNT = 0
PR13_MODIFIED = NO
RECOVERY_REFS_MODIFIED = NO
PRODUCTION_EXE_CHANGED = NO
MERGED = NO
NO_AUTHORITY_BEHAVIOR = CURRENT_FAIL_CLOSED_BEHAVIOR_PRESERVED
HISTORICAL_EVENTS_REWRITTEN = NO
QUARANTINE_RESURRECTION = NO
PENDING_SELECTION_ON_CHANGED_UNANSWERED_QUESTION = LOCAL_RESET
PACKAGE_B_AUTHORIZED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
```

For test counts, implementation head, EXE presence/hash, and PASS disposition, write only the values actually observed; do not infer or pre-fill them.

- [ ] **Step 8: Re-run focused Package-A tests after the receipt is added**

```bash
python -m unittest \
  tests.test_content_revision_authority \
  tests.test_content_revision_migration \
  tests.test_content_revision_app_integration \
  -v
```

Expected: PASS.

- [ ] **Step 9: Commit the verification receipt**

```bash
git add docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md
git commit -m "docs: record package A migration verification"
```

- [ ] **Step 10: Perform final exact-head review gate**

Run:

```bash
git status --short
git log -1 --oneline
git diff --stat 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD
git diff --name-only 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD
```

Required terminal state:

```text
working tree clean
Package A paths only
production bank unchanged
module-level production registry empty
no production manifest/review evidence
no EXE change
no merge
```

Stop and return the exact implementation head SHA plus the verification receipt for external review. Do not begin Package B under this authorization.

---

## Plan Self-Review Result

Spec coverage mapping:

```text
Section 1 strict identity + directed equivalence -> Tasks 1, 3, 4
Section 2 manifest/hash/closed-world/semantic admission -> Tasks 1, 2, 3
Section 3 progress/history/session continuity, pending reset, atomicity, idempotence -> Tasks 4, 5, 6, 7, 8
Section 4 adversarial proof obligations -> Tasks 2 through 8 and closure Task 10
Section 5 component ownership -> source-file split in Tasks 1 through 9
Section 5 Package A/B/C boundary -> this plan stops after Package A external-review handoff
```

Self-review findings resolved in this plan:

```text
positive admission fixture uses exactly 454 synthetic questions
runtime progress migration is wired before ordinary target content-epoch handling
source and target bank filenames may differ for both progress and session discovery
registered authority resolution requires both exact bank files and exact registry hash
question_identity.py and session_store.py stay strict and unmodified
no unused imports are specified in implementation snippets
no production registry entry is added
no production content/EXE/activation/merge is authorized
verification receipt requires observed values rather than predeclared PASS values
```

Package B candidate generation and semantic production evidence, and Package C activation/release work, require separate implementation plans and separate authorization.
