# SC-900 Content-Revision Equivalence Migration — Package A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Package-A migration infrastructure that can admit an exact, governed content-revision equivalence, preserve learner progress/history/session state across that admitted revision, and otherwise preserve the current fail-closed behavior unchanged.

**Architecture:** Keep `question_identity.py` and ordinary `session_store.py` semantics strict. Add a pure authority layer (`content_revision_authority.py`), a pure transform/history layer (`content_revision_migration.py`), and an initially empty release registry (`content_revision_registry.py`). `RuntimePersistence` owns transactional file I/O; application mixins only orchestrate an already-admitted revision. Package A uses synthetic test revisions only and does not change production question wording, activate a new bank, register a production manifest, rebuild the EXE, or merge anything.

**Tech Stack:** Python 3.11, stdlib `dataclasses`, `enum.StrEnum`, `hashlib`, `json`, `pathlib`, `unittest`, existing SC-900 identity/session/persistence modules, Ruff, Black, mypy.

**Spec:** `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

## Global Constraints

- Authorized implementation scope is **Package A — migration infrastructure only**.
- Implementation must start from exact `main` SHA `23d440b6976b9f6bbb3b77285bf0d11effc2513f`; if `main` differs, stop and reconcile before editing.
- Use an isolated worktree/branch at execution time via `superpowers:using-git-worktrees`; recommended branch: `implementation/sc900-content-revision-equivalence-migration-A-001`.
- Do not use the user's desktop or local terminal. Use the authorized repository/cloud execution environment.
- Python target remains 3.11.
- `question_identity.py` strict content fingerprinting and `CHANGED_CONTENT` semantics remain authoritative when no admitted revision is supplied.
- Do not add a generic bypass such as `allow_changed_content=True`.
- Ordinary `migrate_session_snapshot(...)` bank-fingerprint mismatch behavior remains strict.
- Live-state migration version 1 supports one direct source-bank -> target-bank edge per execution.
- Historical events remain immutable: do not rewrite their old `question_content_fingerprint`, `selected_texts`, `correct_texts`, correctness, confidence, timing, or timestamps.
- Existing quarantined progress is never automatically resurrected.
- Package A production question wording changes = **0**.
- Package A production bank activation = **NO**.
- `AUTHORIZED_CONTENT_REVISION_MANIFESTS` remains empty in Package A.
- No production manifest/review files under `content_revision_evidence/` are added in Package A.
- No production EXE change or rebuild is authorized in Package A.
- Do not modify or merge PR #13.
- Do not modify protected recovery refs/tags.
- No merge is authorized by this plan.
- TDD order is mandatory for each behavior: failing test -> verify RED -> minimal implementation -> verify GREEN -> commit.
- Existing identity/session/adversarial tests remain regression authority and must not be weakened to accommodate the new feature.
- Final verification must include focused Package-A tests, existing canonical identity/session tests, full unittest discovery, `python -m tools.run_quality_checks`, `python -m tools.lint_bank --allow-warnings sc900_bank_v8_final.json`, and `python -m tools.verify_installation`.

---

## File Map

### New source files

- `content_revision_authority.py` — schema parsing, canonical manifest hashing, finite rejection reasons, source/target bank admission, semantic-review receipt validation, exact directed edge/lineage representation.
- `content_revision_migration.py` — pure progress transform, pure session transform, migration ID, idempotence state, revision-aware history matching/filtering.
- `content_revision_registry.py` — code-controlled registry of bundled manifests and registered-manifest loader; registry remains empty in Package A.

### New tests

- `tests/test_content_revision_authority.py` — schema/hash/admission/closed-world/mechanical/semantic/registry/lineage adversarial tests.
- `tests/test_content_revision_migration.py` — progress, history, session, pending-selection, idempotence, quarantine-non-resurrection tests.
- `tests/test_content_revision_app_integration.py` — `RuntimePersistence`, session discovery/restore integration, history consumers, no-authority regression behavior.

### Existing source files to modify

- `runtime_persistence.py` — add explicit transactional progress/session migration operations; ordinary loading stays strict.
- `app_session_persistence_mixin.py` — add orchestration for an already-admitted revision before ordinary bank-mismatch quarantine; no semantic policy lives here.
- `app_analytics_mixin.py` — route history lookups through the shared revision-aware resolver.
- `app_game_mixin.py` — route history lookups through the shared revision-aware resolver.
- `app_session_builder_mixin.py` — route history lookups through the shared revision-aware resolver.
- `pyproject.toml` — register new first-party modules and mypy targets.
- `tools/run_quality_checks.py` — add new maintained modules to `QUALITY_TARGETS`.

### Existing source files intentionally not modified

- `question_identity.py` — strict baseline fingerprint/history/content-epoch behavior remains unchanged.
- `session_store.py` — ordinary canonical session validation remains unchanged; Package A uses it as the strict validator before/after explicit migration.
- `session_identity.py` — reuse existing `canonical_session_signature(...)`.
- `session_models.py` — no schema expansion is needed for Package A; revision provenance is stored in progress top-level metadata, not historical event mutation.
- `sc900_bank_v8_final.json` — must remain byte-for-byte unchanged.

### Implementation evidence

- Create at final verification: `docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md`.

---

### Task 1: Define manifest types, duplicate-safe parsing, and canonical hashing

**Files:**
- Create: `content_revision_authority.py`
- Create: `tests/test_content_revision_authority.py`

**Interfaces:**
- Produces: `RevisionFailureReason`, `ContentRevisionManifestError`, `RevisionEdge`, `AdmittedRevision`, `AdmissionResult`, `parse_manifest_json(raw: str) -> dict[str, Any]`, `canonical_manifest_sha256(payload: Mapping[str, Any]) -> str`, `sha256_file(path: Path) -> str`.
- `AdmittedRevision` fields used by later tasks:
  - `manifest_sha256: str`
  - `source_bank_filename: str`
  - `source_bank_file_sha256: str`
  - `source_bank_content_fingerprint: str`
  - `target_bank_filename: str`
  - `target_bank_file_sha256: str`
  - `target_bank_content_fingerprint: str`
  - `edges: tuple[RevisionEdge, ...]`
  - method `edge_for(question_id: str) -> RevisionEdge | None`
  - method `changed_question_ids() -> frozenset[str]`
- `RevisionEdge` fields:
  - `question_id: str`
  - `from_content_fingerprint: str`
  - `to_content_fingerprint: str`
  - `review_artifact: str`
  - `review_artifact_sha256: str`

- [ ] **Step 1: Establish exact execution baseline before the first code edit**

Run:

```bash
git rev-parse HEAD
git rev-parse origin/main
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment2_session_identity tests.test_backlog1_segment3_adversarial_closure -v
```

Expected:

```text
HEAD == 23d440b6976b9f6bbb3b77285bf0d11effc2513f
origin/main == 23d440b6976b9f6bbb3b77285bf0d11effc2513f
existing focused identity/session tests PASS (display-dependent skips allowed only where already expected)
```

If either SHA differs, stop without implementation.

- [ ] **Step 2: Write RED tests for canonical hashing and duplicate-key rejection**

Add tests equivalent to:

```python
import json
import unittest

from content_revision_authority import (
    ContentRevisionManifestError,
    RevisionFailureReason,
    canonical_manifest_sha256,
    parse_manifest_json,
)


class ContentRevisionAuthorityParsingTests(unittest.TestCase):
    def test_manifest_hash_ignores_json_key_order_and_whitespace(self):
        payload_a = {"schema_version": 1, "manifest_kind": "sc900_content_revision_equivalence", "payload_sha256": "ignored"}
        payload_b = {"payload_sha256": "different", "manifest_kind": "sc900_content_revision_equivalence", "schema_version": 1}
        self.assertEqual(canonical_manifest_sha256(payload_a), canonical_manifest_sha256(payload_b))

    def test_duplicate_json_key_fails_closed(self):
        raw = '{"schema_version":1,"schema_version":1}'
        with self.assertRaises(ContentRevisionManifestError) as ctx:
            parse_manifest_json(raw)
        self.assertEqual(RevisionFailureReason.DUPLICATE_JSON_KEY, ctx.exception.reason)
```

Also add tests that unsupported JSON top-level type and malformed JSON fail closed with finite reasons, not arbitrary success.

- [ ] **Step 3: Run the new tests and verify RED**

Run:

```bash
python -m unittest tests.test_content_revision_authority.ContentRevisionAuthorityParsingTests -v
```

Expected: FAIL because `content_revision_authority` and its interfaces do not yet exist.

- [ ] **Step 4: Implement the minimal authority types and parser**

Implement these concrete definitions:

```python
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any


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
        super().__init__(reason if not detail else f"{reason}: {detail}")


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
    status: str
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

Do not implement admission yet.

- [ ] **Step 5: Run parsing tests and verify GREEN**

Run:

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

### Task 2: Implement exact bank admission, mechanical invariants, and semantic-review validation

**Files:**
- Modify: `content_revision_authority.py`
- Modify: `tests/test_content_revision_authority.py`

**Interfaces:**
- Consumes: Task-1 types and hashes; existing `canonical_question_id`, `question_content_fingerprint`, `bank_content_fingerprint` from `question_identity.py`.
- Produces:

```python
def admit_content_revision(
    manifest: Mapping[str, Any],
    *,
    source_questions: Sequence[Mapping[str, Any]],
    target_questions: Sequence[Mapping[str, Any]],
    source_bank_path: Path,
    target_bank_path: Path,
    review_root: Path,
) -> AdmissionResult: ...
```

- Manifest schema is exact/closed-world.
- Review artifact schema is exact/closed-world.
- Review artifact SHA is raw-file SHA-256; manifest canonical hash remains formatting-independent.

- [ ] **Step 1: Add synthetic question/manifest helpers and RED positive-admission test**

Use a four-choice helper so letter mapping is testable:

```python
def question(qid: str, choices: dict[str, str] | None = None, **overrides):
    row = {
        "id": qid,
        "question_number": 1,
        "prompt": "Which statement is correct?",
        "choices": choices or {"A": "Alpha long wording", "B": "Beta", "C": "Gamma", "D": "Delta"},
        "correct": ["A"],
        "general_explanation": "Because.",
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
```

Create source `Q1` and target `Q1` where only the text of choice `A` is shortened. Write source/target banks as JSON files in `TemporaryDirectory`, create an exact review artifact with:

```json
{
  "question_id": "Q1",
  "from_content_fingerprint": "<computed source fp>",
  "to_content_fingerprint": "<computed target fp>",
  "before": {"A":"...","B":"...","C":"...","D":"..."},
  "after": {"A":"...","B":"...","C":"...","D":"..."},
  "semantic_review": {"A":"EQUIVALENT","B":"EQUIVALENT","C":"EQUIVALENT","D":"EQUIVALENT"},
  "correct_key_before": ["A"],
  "correct_key_after": ["A"],
  "authority_refs": ["https://learn.microsoft.com/example"],
  "disposition": "APPROVED_FOR_FULL_CONTINUITY"
}
```

Construct the manifest using actual raw bank hashes, actual bank content fingerprints, actual review raw-file hash, and `payload_sha256=canonical_manifest_sha256(manifest_without_hash)`.

Assert `admit_content_revision(...).status == "PASS"` and that the returned `AdmittedRevision.edge_for("Q1")` carries the exact from/to fingerprints.

- [ ] **Step 2: Add RED adversarial tests for every mechanical class**

Add individual tests with exact expected reasons for:

```text
wrong source file SHA -> SOURCE_BANK_FILE_HASH_MISMATCH
wrong target file SHA -> TARGET_BANK_FILE_HASH_MISMATCH
wrong source content fingerprint -> SOURCE_BANK_FINGERPRINT_MISMATCH
wrong target content fingerprint -> TARGET_BANK_FINGERPRINT_MISMATCH
453/455 question count -> QUESTION_COUNT_MISMATCH
different canonical ID set -> QUESTION_ID_SET_MISMATCH
undeclared changed question -> UNDECLARED_CONTENT_CHANGE
extra edge for unchanged question -> EXTRA_EQUIVALENCE_EDGE
duplicate edge -> DUPLICATE_EQUIVALENCE_EDGE
wrong FROM fingerprint -> FROM_FINGERPRINT_MISMATCH
wrong TO fingerprint -> TO_FINGERPRINT_MISMATCH
correct key mutation -> CORRECT_KEY_CHANGED
choice label set mutation -> CHOICE_LABEL_SET_CHANGED
B/C content swap -> CHOICE_LETTER_MAPPING_CHANGED
prompt mutation -> PROMPT_CHANGED
objective mutation -> OBJECTIVE_CHANGED
domain mutation -> DOMAIN_CHANGED
topics mutation -> TOPICS_CHANGED
study_focus mutation -> TIER_CHANGED
exam_eligible mutation -> EXAM_ELIGIBILITY_CHANGED
question_type mutation -> QUESTION_TYPE_CHANGED
explanation or any other non-choice mutation -> NONPERMITTED_FIELD_CHANGED
```

Use the exact source/target 454 count in production-oriented count tests by generating 454 synthetic rows; do not read or mutate the production bank for these unit tests.

- [ ] **Step 3: Add RED semantic/review tests**

Add cases:

```text
missing review file -> SEMANTIC_REVIEW_MISSING
review hash mismatch -> SEMANTIC_REVIEW_HASH_MISMATCH
review wrong QID/from/to -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
one choice AMBIGUOUS -> CHOICE_SEMANTICS_CHANGED
empty authority_refs -> AUTHORITY_EVIDENCE_MISSING
wrong disposition -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
unknown manifest/review field -> UNKNOWN_FIELD
missing manifest/review required field -> MISSING_FIELD
```

- [ ] **Step 4: Run admission tests and verify RED**

Run:

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: parsing tests PASS; new admission tests FAIL because `admit_content_revision` does not exist.

- [ ] **Step 5: Implement exact schema constants and validation order**

Define exact field sets:

```python
_MANIFEST_FIELDS = {
    "schema_version", "manifest_kind", "work_id", "continuity_policy",
    "source_bank", "target_bank", "permitted_change_class", "edges", "payload_sha256",
}
_BANK_FIELDS = {"filename", "file_sha256", "content_fingerprint", "question_count"}
_EDGE_FIELDS = {
    "question_id", "from_content_fingerprint", "to_content_fingerprint",
    "correct_key_unchanged", "choice_letter_mapping_unchanged", "prompt_unchanged",
    "objective_unchanged", "tier_unchanged", "exam_eligibility_unchanged",
    "choice_semantics", "review_status", "review_artifact", "review_artifact_sha256",
    "authority_refs",
}
_REVIEW_FIELDS = {
    "question_id", "from_content_fingerprint", "to_content_fingerprint", "before", "after",
    "semantic_review", "correct_key_before", "correct_key_after", "authority_refs", "disposition",
}
_CHOICE_LABELS = ("A", "B", "C", "D")
```

Validation order must be deterministic:

```text
schema/unknown/missing fields
manifest payload hash
raw source/target file hashes
question count + canonical-ID set
bank content fingerprints
actual changed-ID set == edge-ID set
per-edge from/to + mechanical invariants
review file existence/hash/schema
per-choice EQUIVALENT + authority refs + APPROVED disposition
```

Return one deterministic `AdmissionResult(status="FAIL", reasons=(first_reason,), admitted=None)` per first blocking failure in version 1; do not return `PASS_WITH_WARNING`.

- [ ] **Step 6: Implement mechanical comparison helpers**

Use source/target question dictionaries directly:

```python
def _without_choices(question: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(question)
    row.pop("choices", None)
    return row
```

Before generic `NONPERMITTED_FIELD_CHANGED`, check named fields in the exact order from the finite reason domain. Require choice keys to be exactly `A/B/C/D` for an admitted changed question. Require each letter's source proposition to remain associated with the same letter; the semantic review is the authority that says revised wording is equivalent, while a literal cross-letter swap is rejected mechanically.

- [ ] **Step 7: Implement review validation and create `AdmittedRevision`**

For each edge:

```python
review_path = review_root / edge_payload["review_artifact"]
actual_review_sha = sha256_file(review_path)
```

Parse review JSON with the same duplicate-safe parser. Require exact `question_id`, exact from/to fingerprints, exact before/after choice maps, exact correct keys, all A-D `EQUIVALENT`, nonempty `authority_refs`, and `APPROVED_FOR_FULL_CONTINUITY`.

On success create immutable `RevisionEdge` objects and one `AdmittedRevision` whose bank fields come from the validated manifest.

- [ ] **Step 8: Run full authority tests and verify GREEN**

Run:

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: PASS.

- [ ] **Step 9: Run existing strict identity regressions**

Run:

```bash
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment3_adversarial_closure -v
```

Expected: PASS; especially existing changed-content tests still quarantine/reject without the new authority.

- [ ] **Step 10: Commit Task 2**

```bash
git add content_revision_authority.py tests/test_content_revision_authority.py
git commit -m "feat: validate exact content revision authority"
```

---

### Task 3: Add the empty production registry and directed lineage resolution

**Files:**
- Create: `content_revision_registry.py`
- Modify: `content_revision_authority.py`
- Modify: `tests/test_content_revision_authority.py`

**Interfaces:**
- Produces:

```python
AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {}

def admit_registered_revision(
    manifest_path: Path,
    *,
    source_questions: Sequence[Mapping[str, Any]],
    target_questions: Sequence[Mapping[str, Any]],
    source_bank_path: Path,
    target_bank_path: Path,
    evidence_root: Path,
    registry: Mapping[str, str] = AUTHORIZED_CONTENT_REVISION_MANIFESTS,
) -> AdmissionResult: ...
```

- `AdmittedRevision` gains:

```python
def permits_fingerprint_transition(self, question_id: str, from_fp: str, to_fp: str) -> bool: ...
```

- Produces lineage helper:

```python
def approved_lineage(
    revisions: Sequence[AdmittedRevision],
    *,
    question_id: str,
    from_fingerprint: str,
    to_fingerprint: str,
) -> tuple[RevisionEdge, ...] | None: ...
```

- [ ] **Step 1: Write RED registry tests**

Add tests proving:

```text
registry is empty by default
unregistered manifest -> UNREGISTERED_MANIFEST
registered path with wrong expected canonical hash -> REGISTRY_HASH_MISMATCH
registered exact canonical hash -> proceeds to ordinary admission
placing a JSON file under content_revision_evidence without a registry entry -> no authority
```

Tests pass a temporary `registry={relative_manifest_path: expected_hash}` mapping; Package A must not populate the module-level registry.

- [ ] **Step 2: Write RED direct/chain lineage tests**

Use synthetic `AdmittedRevision` objects:

```text
Q1 V1->V2 only: permits V1->V2, rejects V2->V1
Q1 V1->V2 + V2->V3: approved_lineage(V1,V3) returns two edges
missing V2->V3: returns None
conflicting two next edges from same QID/from FP: LINEAGE_CONFLICT
cycle V1->V2 + V2->V1: reject traversal as conflict rather than looping
```

- [ ] **Step 3: Run registry/lineage tests and verify RED**

Run:

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: new tests FAIL.

- [ ] **Step 4: Implement registry loader**

`content_revision_registry.py` must contain:

```python
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from content_revision_authority import (
    AdmissionResult,
    RevisionFailureReason,
    admit_content_revision,
    canonical_manifest_sha256,
    parse_manifest_json,
)

AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {}
```

Normalize manifest registry keys as repository-relative POSIX paths, require exact entry, parse manifest, compare canonical hash with registry value, then call `admit_content_revision(...)`. The `review_root` passed to admission is `evidence_root / "reviews"`.

- [ ] **Step 5: Implement deterministic lineage traversal**

Use exact tuple edges and a visited-fingerprint set. Return `None` for no complete path. Raise/return `LINEAGE_CONFLICT` through a dedicated `ContentRevisionManifestError` when two edges for the same question share the same `from_content_fingerprint` but disagree on destination.

No lexical, ID-only, or fuzzy fallback is allowed.

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
- Consumes: `AdmittedRevision`; existing `canonical_question_id`, `question_content_fingerprint`, `history_event_matches_question`, `canonical_question_history_map`.
- Produces:

```python
class MigrationStatus(StrEnum):
    APPLIED = "APPLIED"
    MIGRATION_ALREADY_APPLIED = "MIGRATION_ALREADY_APPLIED"

@dataclass(frozen=True, slots=True)
class PayloadMigrationResult:
    payload: dict[str, Any]
    changed: bool
    status: MigrationStatus
    migration_id: str


def derive_migration_id(revision: AdmittedRevision) -> str: ...

def migrate_progress_payload(
    payload: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    *,
    migrated_at: str,
) -> PayloadMigrationResult: ...

def history_event_matches_approved_revision(
    event: Mapping[str, Any] | None,
    question: Mapping[str, Any] | None,
    revision: AdmittedRevision | Sequence[AdmittedRevision] | None,
) -> bool: ...

def history_events_for_question_revision_aware(
    history_map: Mapping[str, list[Mapping[str, Any]]],
    question: Mapping[str, Any] | None,
    revision: AdmittedRevision | Sequence[AdmittedRevision] | None = None,
) -> list[Mapping[str, Any]]: ...
```

- Progress lineage is stored at top level as `content_revision_migrations: list[dict[str, str]]`; historical `history` rows are untouched.

- [ ] **Step 1: Write RED progress-preservation test**

Build a canonical source payload containing:

```python
{
    "progress_identity_version": 1,
    "question_identity": "canonical_question_id",
    "progress_content_epoch_version": 1,
    "bank_fingerprint": revision.source_bank_content_fingerprint,
    "question_content_fingerprints": {"Q1": edge.from_content_fingerprint, "Q2": target_q2_fp},
    "questions": {
        "Q1": {"attempts": 7, "correct": 5, "confidence": "Sure", "flagged": True, "suspended": False},
        "Q2": {"attempts": 3},
    },
    "history": [{
        "question_id": "Q1",
        "question_content_fingerprint": edge.from_content_fingerprint,
        "selected_texts": ["old B"],
        "correct_texts": ["old A"],
        "correct": False,
        "confidence": "Sure",
    }],
    "quarantined_questions": {"Q-OLD": {"reason": "CHANGED_CONTENT", "record": {"attempts": 99}}},
}
```

Assert migration:

```text
keeps every Q1/Q2 learner value
sets bank_fingerprint to target bank FP
sets Q1 stored fingerprint to edge.to FP
leaves unchanged Q2 stored fingerprint unchanged
leaves history event dictionary byte-for-structure equal
leaves quarantined Q-OLD quarantined
appends exactly one lineage record with exact question/from/to/manifest/migration_id/migrated_at
```

- [ ] **Step 2: Add RED progress rejection/idempotence tests**

Cases:

```text
payload bank FP not equal revision source -> fail closed
changed Q1 stored FP not equal edge.from -> fail closed
unregistered changed QID -> fail closed
question missing from target -> fail closed
already-target payload with same migration_id -> MIGRATION_ALREADY_APPLIED and changed=False
apply exact migration twice -> attempts/history/lineage counts unchanged
pre-existing quarantined Q1 -> remains quarantined; not moved into active questions
```

Use a dedicated `ContentRevisionMigrationError(ValueError)` with finite reason strings:

```text
SOURCE_PROGRESS_BANK_MISMATCH
SOURCE_PROGRESS_FINGERPRINT_MISMATCH
TARGET_QUESTION_MISSING
UNAUTHORIZED_PROGRESS_TRANSITION
MIGRATION_LINEAGE_CONFLICT
```

- [ ] **Step 3: Add RED historical immutability/revision-aware match tests**

Assert:

```text
same QID + same FP -> strict match
same QID + approved old->new FP -> match
same QID + no edge -> no match
different QID -> no match
reverse edge -> no match
V1->V2->V3 complete sequence -> match
missing middle edge -> no match
returned event object/value remains original V1 FP/text
```

- [ ] **Step 4: Run migration tests and verify RED**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: FAIL because module/functions do not yet exist.

- [ ] **Step 5: Implement migration ID and progress transform**

Use a labeled deterministic payload rather than raw concatenation ambiguity:

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

Progress transform steps:

```text
1. Deep-copy source payload.
2. If exact migration record already exists and bank FP already equals target, return verified no-op.
3. Require source bank FP exactly equals revision.source_bank_content_fingerprint.
4. Build target question FP map by canonical ID.
5. For each active progress record:
   - target question must exist;
   - if stored FP == target FP, preserve;
   - else require exact revision edge where stored FP == edge.from and target FP == edge.to;
   - set stored FP to target FP.
6. Do not move anything out of quarantined_questions.
7. Do not edit history.
8. Set bank_fingerprint to revision.target_bank_content_fingerprint.
9. Append one migration record per changed active question, with common migration_id and migrated_at.
10. Return APPLIED/changed=True.
```

- [ ] **Step 6: Implement revision-aware history matching**

First call existing `history_event_matches_question(...)`. Only if strict match is false, require same canonical ID, nonblank historical fingerprint, and exact approved lineage to current `question_content_fingerprint(question)`. If `revision is None`, return strict result unchanged.

- [ ] **Step 7: Run migration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: PASS.

- [ ] **Step 8: Run existing history/identity adversarial regressions**

```bash
python -m unittest tests.test_backlog1_segment3_adversarial_closure -v
```

Expected: PASS unchanged.

- [ ] **Step 9: Commit Task 4**

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
- Consumes: `migrate_session_snapshot`, `canonical_session_signature`, `ordered_question_ids`, target questions, and `AdmittedRevision`.
- Produces:

```python
def migrate_session_payload(
    saved: Mapping[str, Any],
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    *,
    target_bank_file: str,
) -> PayloadMigrationResult: ...
```

- Session history rows remain untouched.
- Completed answer state remains untouched.
- On changed unanswered question only: if `selected` or `pending` nonempty, clear both.

- [ ] **Step 1: Write RED positive session-migration test**

Build a valid source snapshot with existing `build_session_snapshot(...)` using source bank fingerprint and IDs `Q1/Q2/Q3`:

```text
Q1 changed + answered=True + selected/pending=["B"]
Q2 changed + answered=False + selected/pending=["B"]
Q3 unchanged + flagged=True
session_answer_history contains Q1 old content fingerprint/text
current_index, elapsed_seconds, builder_context, quests/rewards populated
```

Assert migrated target:

```text
Q1 completed B preserved
Q2 selected/pending cleared, answered remains false
Q3 state preserved
question IDs/order preserved
history old FP/text unchanged
current_index/elapsed/builder/quests/rewards preserved
bank_file == target_bank_file
bank_fingerprint == target FP
session_signature recomputed from target FP + saved question_ids
restore_signature recomputed from target FP + saved restore_question_ids
```

- [ ] **Step 2: Add RED rejection tests**

Cases:

```text
source snapshot bank FP != revision source -> reject
invalid source session signature -> reject
unknown/removed question ID -> reject
changed question with no edge -> reject
current target question FP does not equal edge.to -> reject
correct/letter-map safety is inherited only from admitted revision; do not add runtime fuzzy fallback
```

- [ ] **Step 3: Run session tests and verify RED**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: new session cases FAIL.

- [ ] **Step 4: Implement strict source validation and target rewrite**

Call existing `migrate_session_snapshot(...)` first with:

```python
source_ids = [str(value) for value in saved["question_ids"]]
source_restore_ids = [str(value) for value in saved["restore_question_ids"]]
source_qnums = list(saved.get("question_numbers") or [])
validated = migrate_session_snapshot(
    saved,
    str(saved.get("mode") or ""),
    source_qnums,
    bank_fingerprint=revision.source_bank_content_fingerprint,
    question_ids=source_ids,
    restore_question_ids=source_restore_ids,
    available_question_ids=ordered_question_ids(target_questions),
)
```

Then deep-copy `validated`, apply only pending-selection reset on changed unanswered questions, set `bank_file`, set target bank fingerprint, recompute both signatures, and revalidate by calling `migrate_session_snapshot(...)` again with the target fingerprint.

Do not rewrite `session_answer_history`.

- [ ] **Step 5: Run session migration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_migration -v
```

Expected: PASS.

- [ ] **Step 6: Run existing canonical session tests**

```bash
python -m unittest tests.test_backlog1_segment2_session_identity tests.test_backlog1_segment2_session_app_integration -v
```

Expected: PASS unchanged.

- [ ] **Step 7: Commit Task 5**

```bash
git add content_revision_migration.py tests/test_content_revision_migration.py
git commit -m "feat: migrate approved saved sessions to target bank identity"
```

---

### Task 6: Add transactional persistence for approved progress/session migrations

**Files:**
- Modify: `runtime_persistence.py`
- Modify: `tests/test_content_revision_app_integration.py`

**Interfaces:**
- Consumes: `migrate_progress_payload`, `migrate_session_payload`, `AdmittedRevision`.
- Produces:

```python
def migrate_progress_across_approved_revision(
    self,
    source_path: Path,
    target_path: Path,
    *,
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    migrated_at: str,
) -> tuple[dict[str, Any] | None, Path | None, Exception | None]: ...


def migrate_session_file_across_approved_revision(
    self,
    source_path: Path,
    target_path: Path,
    *,
    target_questions: Sequence[Mapping[str, Any]],
    revision: AdmittedRevision,
    target_bank_file: str,
) -> tuple[dict[str, Any] | None, Path | None, Exception | None]: ...
```

- Add deterministic helper:

```python
def content_revision_archive_path(self, source_path: Path, *, migration_id: str, label: str) -> Path:
    return self.backup_dir / f"{source_path.stem}_{label}_{migration_id[:12]}.json"
```

- [ ] **Step 1: Create `tests/test_content_revision_app_integration.py` with RED progress atomicity tests**

Use `TemporaryDirectory` and real files. Tests:

```text
successful progress migration creates exact deterministic pre-migration backup and verified target
backup failure leaves source bytes unchanged and creates no target rewrite
write failure leaves source bytes unchanged and returns backup path + error
conflicting existing target with different migration lineage -> fail closed, preserve both
already-applied target -> no-op, no second backup
```

Patch `RuntimePersistence.backup_progress_file` and `write_json` for failure injection using `unittest.mock`.

- [ ] **Step 2: Add RED session atomicity/crash-recovery tests**

Tests:

```text
successful migration writes verified target path then archives source
source is never removed before target re-read validation
existing verified target with same migration ID -> finish source archival/no duplicate target
existing conflicting target -> preserve both and return error
write failure -> source remains
archive/copy failure after verified target -> return recoverable error while verified target remains
```

- [ ] **Step 3: Run persistence tests and verify RED**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: FAIL because methods do not exist.

- [ ] **Step 4: Implement progress persistence operation**

Use `load_json_or_backup(source_path)` directly, not ordinary target-bank `load_progress_with_identity_migration`, because the source is deliberately bound to the previous admitted bank. Call pure transform first. If status is `MIGRATION_ALREADY_APPLIED`, do not back up again.

Before writing:

```text
compute deterministic backup destination with migration_id
if backup destination already exists, require bytes equal source or fail closed
create backup
write target with safe_write_json through self.write_json
re-read target with load_json_or_backup
require target payload bank_fingerprint == revision.target_bank_content_fingerprint
require exact migration_id in content_revision_migrations
```

If source and target paths are identical, backup must be complete before replacement.

- [ ] **Step 5: Implement session persistence operation**

Read source JSON, call pure `migrate_session_payload`, derive `migration_id`, validate/handle an existing target, write target, re-read target, verify target fingerprint/signatures by calling pure transform/strict session validation as appropriate, then archive source to deterministic `content_revision_archive_path(..., label="session_before_content_revision")`.

If `source_path == target_path`, do not unlink after target write; the pre-migration backup is the source archive. If paths differ, remove the old resumable source only after verified target and verified archive copy exist.

- [ ] **Step 6: Run persistence tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: persistence cases PASS.

- [ ] **Step 7: Run existing persistence regressions**

```bash
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment1_adversarial_review tests.test_sc900_engine_regression -v
```

Expected: PASS except only pre-existing display-dependent skips.

- [ ] **Step 8: Commit Task 6**

```bash
git add runtime_persistence.py tests/test_content_revision_app_integration.py
git commit -m "feat: persist approved content revision migrations atomically"
```

---

### Task 7: Integrate admitted revisions into session restore and all history consumers

**Files:**
- Modify: `app_session_persistence_mixin.py`
- Modify: `app_analytics_mixin.py`
- Modify: `app_game_mixin.py`
- Modify: `app_session_builder_mixin.py`
- Modify: `tests/test_content_revision_app_integration.py`

**Interfaces:**
- Application-level optional authority remains explicit:

```python
revision = getattr(self, "content_revision_authority", None)
```

No Package-A code populates this attribute in production.
- Consumers call only:

```python
history_events_for_question_revision_aware(history_map, question, revision)
```

- Session restore helper:

```python
def _try_migrate_session_across_content_revision(
    self,
    path: Path,
    saved: Mapping[str, Any],
    desired_builder_identity: Mapping[str, Any],
) -> tuple[Path, Mapping[str, Any]] | None: ...
```

- [ ] **Step 1: Write RED no-authority history-consumer regression test**

Create a fake app using the existing mixin style. With no `content_revision_authority` attribute, prove old-fingerprint history does not contribute and current-fingerprint history still does. This test must cover at least one analytics path and one session-builder/game stability path.

- [ ] **Step 2: Write RED admitted-authority history-consumer test**

Set `app.content_revision_authority = synthetic_admitted_revision`. Feed an old V1 event and current V2 question. Assert the existing calculation receives that event while the event object retains old FP/text.

- [ ] **Step 3: Write RED app session-restore migration test**

Extend the existing fake `SessionPersistenceMixin` pattern. Put a valid source-bank canonical session at the current resumable-session path. With no authority, assert current behavior remains rejection/quarantine. With synthetic admitted authority, assert the helper migrates to target identity, preserves completed state, clears changed pending state, and returns the target session for normal restore.

Also assert a migration-transform failure preserves the source file and does not quarantine it as corrupt JSON; authorized migration failure is not the same as malformed-session quarantine.

- [ ] **Step 4: Run app integration tests and verify RED**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: new integration cases FAIL.

- [ ] **Step 5: Replace direct history calls with the shared resolver**

In `app_analytics_mixin.py`, `app_game_mixin.py`, and `app_session_builder_mixin.py`:

```python
from content_revision_migration import history_events_for_question_revision_aware
```

At each existing `history_events_for_question(...)` call, replace with:

```python
history_events_for_question_revision_aware(
    question_history_map,
    question,
    getattr(self, "content_revision_authority", None),
)
```

Use the local variable name already present (`q`, `current_q`, or `question`). Do not alter the event contents or downstream analytics formulas.

- [ ] **Step 6: Add explicit session migration orchestration before bank-mismatch quarantine**

In `app_session_persistence_mixin.py`, add `_try_migrate_session_across_content_revision(...)` that:

```text
returns None immediately if no authority
requires saved bank_fingerprint == revision.source_bank_content_fingerprint
requires current_bank_fingerprint() == revision.target_bank_content_fingerprint
computes target canonical session path using existing session_file_for_bank/current builder identity
calls RuntimePersistence.migrate_session_file_across_approved_revision(...)
returns verified target path/payload on success
returns None without quarantining source on migration failure
```

In `find_resumable_session_for_builder(...)`, when ordinary `migrate_session_snapshot(...)` raises specifically because source bank fingerprint differs, attempt the helper before existing invalid-session quarantine. Only malformed/invalid ordinary snapshots remain eligible for `quarantine_invalid_runtime_file(...)`.

Do not broaden `skip_identity_check` or legacy-session behavior.

- [ ] **Step 7: Run app integration tests and verify GREEN**

```bash
python -m unittest tests.test_content_revision_app_integration -v
```

Expected: PASS.

- [ ] **Step 8: Run all directly affected existing tests**

```bash
python -m unittest \
  tests.test_backlog1_segment2_session_app_integration \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment3_adversarial_closure \
  tests.test_backlog2_confidence_epistemics \
  -v
```

Expected: PASS; no-authority behavior is unchanged.

- [ ] **Step 9: Commit Task 7**

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

### Task 8: Put new modules under repository quality/type authority

**Files:**
- Modify: `pyproject.toml`
- Modify: `tools/run_quality_checks.py`
- Modify: `tests/test_content_revision_authority.py`

**Interfaces:**
- No runtime behavior change.
- New maintained modules become Ruff/Black/mypy targets.

- [ ] **Step 1: Write RED quality-target assertion**

Add a small test that imports `tools.run_quality_checks.QUALITY_TARGETS` and asserts:

```python
for required in (
    "content_revision_authority.py",
    "content_revision_migration.py",
    "content_revision_registry.py",
):
    self.assertIn(required, QUALITY_TARGETS)
```

Also read `pyproject.toml` in the test and assert all three names appear in `[tool.mypy].files` and Ruff `known-first-party`.

- [ ] **Step 2: Run the quality-target test and verify RED**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: FAIL for missing quality-target registrations.

- [ ] **Step 3: Update Ruff/mypy and repository quality target lists**

In `pyproject.toml` add alphabetically/consistently:

```text
content_revision_authority
content_revision_migration
content_revision_registry
```

to `known-first-party`, and add:

```text
content_revision_authority.py
content_revision_migration.py
content_revision_registry.py
```

to `[tool.mypy].files`.

In `tools/run_quality_checks.py`, add the same three `.py` files to `QUALITY_TARGETS`.

- [ ] **Step 4: Run quality-target test and verify GREEN**

```bash
python -m unittest tests.test_content_revision_authority -v
```

Expected: PASS.

- [ ] **Step 5: Run quality tools on the new/modified modules**

```bash
python -m ruff check \
  content_revision_authority.py content_revision_migration.py content_revision_registry.py \
  runtime_persistence.py app_session_persistence_mixin.py app_analytics_mixin.py app_game_mixin.py app_session_builder_mixin.py \
  tests/test_content_revision_authority.py tests/test_content_revision_migration.py tests/test_content_revision_app_integration.py
python -m black --check \
  content_revision_authority.py content_revision_migration.py content_revision_registry.py \
  runtime_persistence.py app_session_persistence_mixin.py app_analytics_mixin.py app_game_mixin.py app_session_builder_mixin.py \
  tests/test_content_revision_authority.py tests/test_content_revision_migration.py tests/test_content_revision_app_integration.py
python -m mypy
```

Expected: PASS. If Black reports formatting differences, run Black only on the listed touched files, then rerun checks; do not reformat unrelated repository files.

- [ ] **Step 6: Commit Task 8**

```bash
git add pyproject.toml tools/run_quality_checks.py tests/test_content_revision_authority.py
git commit -m "chore: add content revision modules to quality gates"
```

---

### Task 9: Execute Package-A closure verification and write the evidence receipt

**Files:**
- Create: `docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md`
- No production code changes are allowed in this task unless verification exposes a defect; if a defect is found, return to the owning task's TDD cycle and create a separate fix commit before re-running closure.

**Interfaces:**
- Produces: exact Package-A terminal evidence; does not authorize Package B or production activation.

- [ ] **Step 1: Verify exact diff boundary before tests**

Run:

```bash
git diff --name-status 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD
git status --short
```

Expected changed paths are limited to:

```text
content_revision_authority.py
content_revision_migration.py
content_revision_registry.py
runtime_persistence.py
app_session_persistence_mixin.py
app_analytics_mixin.py
app_game_mixin.py
app_session_builder_mixin.py
pyproject.toml
tools/run_quality_checks.py
tests/test_content_revision_authority.py
tests/test_content_revision_migration.py
tests/test_content_revision_app_integration.py
docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md
```

The verification receipt itself will not exist until Step 7. No bank JSON, EXE, PR13, recovery-ref, or unrelated source path may appear.

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

Expected: PASS; existing `CHANGED_CONTENT` and ordinary bank mismatch behavior remains unchanged when no authority is supplied.

- [ ] **Step 4: Run full repository unittest discovery**

```bash
python -m unittest discover -s tests -v
```

Expected: zero failures/errors. Existing environment-specific Tk/display skips are acceptable only when clearly reported as skips.

- [ ] **Step 5: Run quality, bank lint, and installation verification**

```bash
python -m tools.run_quality_checks
python -m tools.lint_bank --allow-warnings sc900_bank_v8_final.json
python -m tools.verify_installation
```

Expected:

```text
quality PASS
bank lint PASS with the current 454-question bank and only the already-known allowed warning profile
installation verification PASS
```

- [ ] **Step 6: Prove production bank and production EXE immutability**

Run:

```bash
python - <<'PY'
from hashlib import sha256
from pathlib import Path

for path in (Path("sc900_bank_v8_final.json"), Path("SC900TestLearningEngine.exe")):
    if path.exists():
        print(path, sha256(path.read_bytes()).hexdigest())
PY
```

Required production bank SHA-256:

```text
177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
```

If the root production EXE is present, its SHA-256 must remain the pre-Package-A value:

```text
9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558
```

If the EXE is intentionally absent from the isolated checkout, record `EXE_PRESENT = NO`; do not build or modify it.

- [ ] **Step 7: Write the Package-A verification receipt with actual command evidence**

Create the file with this exact section structure and replace each evidence field only with values observed in Steps 1-6:

```markdown
# Package A Verification — Content-Revision Equivalence Migration

WORK_ID = SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 / PACKAGE-A
START_MAIN_SHA = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
IMPLEMENTATION_HEAD = <actual HEAD>

## Scope

PRODUCTION_QUESTION_WORDING_CHANGES = 0
PRODUCTION_BANK_ACTIVATION = NO
AUTHORIZED_CONTENT_REVISION_MANIFESTS_COUNT = 0
PR13_MODIFIED = NO
RECOVERY_REFS_MODIFIED = NO
PRODUCTION_EXE_CHANGED = NO
MERGED = NO

## Focused verification

PACKAGE_A_TESTS = <actual result/count>
IDENTITY_SESSION_REGRESSION_WALL = <actual result/count>
FULL_UNITTEST_DISCOVERY = <actual result/count/skips>
QUALITY_CHECKS = <actual result>
BANK_LINT = <actual result>
INSTALLATION_VERIFICATION = <actual result>

## Production immutability

PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
PRODUCTION_EXE_PRESENT = <YES|NO>
PRODUCTION_EXE_SHA256 = <actual hash or N/A>

## Contract proof

NO_AUTHORITY_BEHAVIOR = CURRENT_FAIL_CLOSED_BEHAVIOR_PRESERVED
ADMITTED_SYNTHETIC_REVISION = FULL_CONTINUITY_PASS
HISTORICAL_EVENTS_REWRITTEN = NO
QUARANTINE_RESURRECTION = NO
PENDING_SELECTION_ON_CHANGED_UNANSWERED_QUESTION = LOCAL_RESET
MIGRATION_IDEMPOTENCE = PASS
ATOMIC_BACKUP_WRITE_RECOVERY = PASS

## Disposition

PACKAGE_A = PASS / READY_FOR_EXTERNAL_REVIEW
PACKAGE_B_AUTHORIZED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
```

Do not write PASS for any field that was not observed.

- [ ] **Step 8: Re-run the focused Package-A tests after adding the receipt**

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

- [ ] **Step 10: Final exact-head review gate**

Run:

```bash
git status --short
git log -1 --oneline
git diff --stat 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD
```

Required terminal state:

```text
working tree clean
Package A only
production bank unchanged
registry empty
no production manifest/review evidence
no EXE change
no merge
```

Stop and return the exact implementation head SHA plus the verification receipt for external review. Do not start Package B in the same authorization.

---

## Plan Self-Review Checklist

Before executing this plan, the executor must preserve these mappings from spec to tasks:

```text
Section 1 strict identity / directed edges -> Tasks 1-4
Section 2 manifest/hash/closed-world/semantic admission -> Tasks 1-3
Section 3 progress/history/session continuity + pending reset + idempotence -> Tasks 4-6
Section 4 adversarial proof obligations -> Tasks 2-7 and Task 9
Section 5 component ownership -> Tasks 1-8
Section 5 three-package boundary -> this plan is Package A only; Package B/C require separate plans and authorization
```

No Package-A task authorizes production content changes, candidate generation, Microsoft Learn per-question production review, production manifest registration, default-bank switching, EXE rebuild, PR merge, PR #13 changes, or recovery-ref changes.
