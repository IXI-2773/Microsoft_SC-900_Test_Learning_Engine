# SC-900 Content-Revision Equivalence Migration — Package A Reconciled Implementation Plan

> **Execution target:** Cursor or another repository-capable coding agent.
>
> **Method:** Execute task-by-task with TDD: RED -> verify failure -> minimal GREEN -> verify -> commit. Review each task before advancing.

**Work ID:** `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 / PACKAGE-A`

**Goal:** Implement only the migration infrastructure that admits an exact governed wording-only revision, preserves approved learner continuity, and otherwise retains the current fail-closed identity/session behavior unchanged.

**Design authority:** `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`

**Implementation base:** exact `main` SHA `23d440b6976b9f6bbb3b77285bf0d11effc2513f`.

Cursor must read this plan and the design spec from the exact design-review head supplied in the handoff message, then create the implementation worktree/branch from the exact implementation base above. The design documents are authority inputs; they are not implementation-branch changes.

---

# Global constraints

- Package A only.
- Cursor may use its repository-local terminal, normal Git commands, worktrees, and test runners.
- Recommended implementation branch: `implementation/sc900-content-revision-equivalence-migration-A-001`.
- If current `main` is not exactly `23d440b6976b9f6bbb3b77285bf0d11effc2513f`, stop and reconcile before editing.
- Python target remains 3.11.
- `question_identity.py` strict `CHANGED_CONTENT` behavior remains the default and must not be weakened.
- Do not add generic `allow_changed_content=True` or equivalent bypasses.
- `session_store.py` ordinary bank-fingerprint mismatch behavior remains strict.
- `self.content_revision_authority` is strictly `AdmittedRevision | None`, never `AdmissionResult`.
- Historical events are immutable.
- Existing quarantined progress is never automatically resurrected.
- Live-state migration v1 handles one direct source-bank -> target-bank edge per execution.
- Registered runtime v1 requires distinct source and target bank filenames.
- Production registry remains empty in Package A.
- Production question wording changes = 0.
- Production bank activation = NO.
- No production manifest/review evidence is added.
- No EXE rebuild/change is authorized.
- Do not modify or merge PR #13.
- Do not modify protected recovery refs/tags.
- No merge is authorized by this plan.
- Existing identity/session/adversarial tests must not be weakened.
- Explicit migration reads must be non-mutating on parse/read failure.
- The production bank SHA-256 must remain `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c`.

---

# File map

## New source files

- `content_revision_authority.py`
  - duplicate-safe JSON parsing;
  - canonical manifest hashing;
  - exact schema/type validation;
  - bank/review admission;
  - global non-choice/letter-map invariants;
  - finite failure reasons;
  - immutable admitted edges/lineage.

- `content_revision_migration.py`
  - deterministic migration ID;
  - pure progress transform;
  - pure session transform;
  - revision-aware history matching/filtering;
  - idempotence verification.

- `content_revision_registry.py`
  - empty production registry;
  - contained evidence-path resolution;
  - exact registered-target admission;
  - target progress-identity registration restoration.

## New tests

- `tests/test_content_revision_authority.py`
- `tests/test_content_revision_migration.py`
- `tests/test_content_revision_app_integration.py`

## Existing source files to modify

- `runtime_persistence.py`
- `app.py`
- `app_session_persistence_mixin.py`
- `app_analytics_mixin.py`
- `app_game_mixin.py`
- `app_session_builder_mixin.py`
- `pyproject.toml`
- `tools/run_quality_checks.py`

## Existing source files intentionally not modified

- `question_identity.py`
- `session_store.py`
- `session_identity.py`
- `session_models.py`
- `sc900_bank_v8_final.json`

## Final verification evidence

Create only at closure:

`docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md`

---

# Task 0 — Establish exact execution authority

## Files

No repository changes.

## Steps

1. Read the design spec and this plan from the exact design-review head supplied in the handoff.
2. Create/switch to an isolated implementation worktree/branch based on exact main SHA.
3. Run:

```bash
git rev-parse HEAD
git rev-parse origin/main
python -m unittest \
  tests.test_backlog1_progress_identity_migration \
  tests.test_backlog1_segment2_session_identity \
  tests.test_backlog1_segment3_adversarial_closure \
  -v
```

Required:

```text
HEAD = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
origin/main = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
focused baseline tests = PASS
```

If either SHA differs or baseline tests fail unexpectedly, stop.

---

# Task 1 — Authority primitives, duplicate-safe parsing, canonical hashes

## Files

Create:

- `content_revision_authority.py`
- `tests/test_content_revision_authority.py`

## Required interfaces

```python
class AdmissionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"

class RevisionFailureReason(StrEnum): ...
class ContentRevisionManifestError(ValueError): ...

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

@dataclass(frozen=True, slots=True)
class AdmissionResult:
    status: AdmissionStatus
    reasons: tuple[RevisionFailureReason, ...]
    admitted: AdmittedRevision | None
```

Add:

```python
parse_json_duplicate_safe(raw: str) -> dict[str, Any]
canonical_manifest_sha256(payload: Mapping[str, Any]) -> str
sha256_file(path: Path) -> str
```

Use the duplicate-safe parser for manifests, review artifacts, and bank JSON used as admission authority.

## RED tests

Write tests for:

- equivalent JSON key order/whitespace gives identical canonical manifest hash;
- stored `payload_sha256` is excluded from self-hash;
- duplicate manifest key -> `DUPLICATE_JSON_KEY`;
- duplicate review authority key -> `DUPLICATE_JSON_KEY`;
- duplicate bank authority key -> `DUPLICATE_JSON_KEY`;
- malformed JSON -> `SCHEMA_UNSUPPORTED`;
- non-object top-level manifest/review/bank authority object -> `SCHEMA_UNSUPPORTED`.

Run and verify RED before creating implementation.

## GREEN implementation

- `sha256_file` uses raw file bytes.
- canonical manifest hash uses UTF-8 compact sorted JSON excluding `payload_sha256`.
- no admission behavior yet.

Run focused tests, verify GREEN, then commit:

```text
feat: add content revision authority primitives
```

---

# Task 2 — Exact 454-question bank admission and semantic evidence

## Files

Modify:

- `content_revision_authority.py`
- `tests/test_content_revision_authority.py`

## Required interface

```python
def admit_content_revision(
    manifest: Mapping[str, Any],
    *,
    source_questions: Sequence[Mapping[str, Any]],
    target_questions: Sequence[Mapping[str, Any]],
    source_bank_path: Path,
    target_bank_path: Path,
    review_root: Path,
) -> AdmissionResult:
    ...
```

## Exact schema/constants

Manifest top-level fields:

```text
schema_version
manifest_kind
work_id
continuity_policy
source_bank
target_bank
permitted_change_class
edges
payload_sha256
```

Bank binding fields:

```text
filename
file_sha256
content_fingerprint
question_count
```

Edge fields:

```text
question_id
from_content_fingerprint
to_content_fingerprint
correct_key_unchanged
choice_letter_mapping_unchanged
prompt_unchanged
objective_unchanged
tier_unchanged
exam_eligibility_unchanged
choice_semantics
review_status
review_artifact
review_artifact_sha256
authority_refs
```

Review fields:

```text
question_id
from_content_fingerprint
to_content_fingerprint
before
after
semantic_review
correct_key_before
correct_key_after
authority_refs
disposition
```

Choice labels are exactly A-D for this contract.

## Synthetic fixture requirements

Use exactly 454 synthetic canonical questions.

Use repository-real fields:

```text
exam_calibration_tier
exam_simulation_eligible
study_focus
reasoning_steps
calibration_version
```

Do **not** invent `exam_eligible`.

## Deterministic validation order

Implement this order:

```text
1. schema types / unknown / missing fields
2. canonical manifest hash
3. contained evidence paths
4. duplicate-safe source/target bank JSON parse
5. raw source/target file hashes
6. exact question counts and canonical-ID sets
7. bank-level metadata equality excluding questions
8. global per-question non-choice + choice-label/letter-map invariants
9. bank content fingerprints
10. actual fingerprint-different IDs == edge IDs
11. exact edge from/to fingerprints
12. review existence/hash/schema/exact before-after binding
13. A-D semantic equivalence
14. Microsoft Learn authority refs
15. bank-level PASS only if all checks pass
```

Return the first deterministic blocking reason. No warning-success state.

## Global invariant implementation

For **every** source/target canonical question pair, before changed-ID classification:

- canonical ID unchanged;
- correct key unchanged -> else `CORRECT_KEY_CHANGED`;
- choice label set unchanged -> else `CHOICE_LABEL_SET_CHANGED`;
- prompt unchanged -> `PROMPT_CHANGED`;
- question type unchanged -> `QUESTION_TYPE_CHANGED`;
- objective unchanged -> `OBJECTIVE_CHANGED`;
- domain unchanged -> `DOMAIN_CHANGED`;
- topics unchanged -> `TOPICS_CHANGED`;
- `exam_calibration_tier` unchanged -> `TIER_CHANGED`;
- `exam_simulation_eligible` unchanged -> `EXAM_ELIGIBILITY_CHANGED`;
- keyed choice concept/letter mapping unchanged;
- all remaining non-choice fields unchanged -> `NONPERMITTED_FIELD_CHANGED`.

Only keyed `choices[A-D]` text may differ.

### Fingerprint-blind swap guard

Add a specific adversarial case where B/C texts are swapped but current `question_content_fingerprint()` remains equal. Admission must reject `CHOICE_LETTER_MAPPING_CHANGED` before treating the row as unchanged.

## Bank-level metadata guard

Duplicate-safely parse both bank JSON objects and deep-compare all top-level fields except `questions`.

Changed bank title/version/other metadata -> `NONPERMITTED_FIELD_CHANGED`.

Formatting/whitespace-only differences must not fail this semantic metadata check.

## Semantic-review requirements

For each changed question:

- review file must be contained under `review_root`;
- raw review SHA must match;
- review QID/from/to fingerprint must match edge;
- review `before` equals exact source keyed choices;
- review `after` equals exact target keyed choices;
- review correct keys equal exact source/target correct keys;
- semantic statuses A-D all exactly `EQUIVALENT`;
- disposition exactly `APPROVED_FOR_FULL_CONTINUITY`;
- edge `review_status` exactly `APPROVED`;
- both edge and review refs contain at least one string beginning `https://learn.microsoft.com/`.

## RED adversarial matrix

Add separate tests for:

```text
unsupported schema/version/kind/policy/change-class
unknown/missing fields at every object level
wrong field types
edges not list
bank binding not mapping
question_count not integer
choice_semantics not exact A-D mapping
authority_refs not list[str]
boolean assertions not bool
blank/malformed hash/fingerprint fields
review before/after not exact A-D mappings
review semantic_review not exact A-D mapping
manifest hash mismatch
source/target raw hash mismatch
source/target content fingerprint mismatch
source/target count != 454
duplicate canonical ID
question-ID set mismatch
bank-level metadata change
undeclared changed question
extra edge for unchanged question
duplicate edge
wrong edge from/to FP
correct-key change
choice-label change
B/C keyed swap with equal FP
prompt/objective/domain/topics change
exam_calibration_tier change
exam_simulation_eligible change
question_type change
study_focus/reasoning_steps/calibration_version/explanation/other non-choice change
missing/unreadable review
review hash mismatch
review QID/from/to mismatch
review before/after mismatch
review correct-key mismatch
AMBIGUOUS/SUBSTANTIVELY_CHANGED choice
empty authority refs
non-Microsoft-only authority refs
unapproved review disposition/status
absolute review path
`..` review traversal
```

Run RED, implement minimally, run GREEN.

Then run the existing strict identity regression wall and commit:

```text
feat: validate exact content revision authority
```

---

# Task 3 — Empty release registry, contained resolution, directed lineage

## Files

Create:

- `content_revision_registry.py`

Modify:

- `content_revision_authority.py`
- `tests/test_content_revision_authority.py`

## Registry constants

```python
AUTHORIZED_CONTENT_REVISION_MANIFESTS: dict[str, str] = {}
CONTENT_REVISION_EVIDENCE_ROOT = Path(__file__).resolve().parent / "content_revision_evidence"
```

Production registry must remain exactly empty in Package A.

## Required interfaces

```python
AdmittedRevision.permits_fingerprint_transition(question_id, from_fp, to_fp) -> bool
approved_lineage(revisions, question_id, from_fingerprint, to_fingerprint) -> tuple[RevisionEdge, ...] | None
resolve_registered_revision_for_target(...) -> AdmissionResult | None
```

## Resolution rules

- registry paths are nonempty relative paths;
- reject absolute or `..` traversal;
- compare canonical manifest hash to registry-pinned hash before using metadata;
- select only target filename matches;
- zero matches -> `None`;
- more than one target match -> `LINEAGE_CONFLICT`;
- registered source/target filenames must differ;
- source bank path is located beside target bank for v1;
- missing/unreadable registered manifest -> `REGISTRY_HASH_MISMATCH`;
- missing/unreadable source bank -> `SOURCE_BANK_FILE_HASH_MISMATCH`;
- missing/unreadable target bank -> `TARGET_BANK_FILE_HASH_MISMATCH`.

## Global progress-identity registration restoration

`question_bank.load_bank()` mutates the registered progress-identity bank. Source-bank loading must restore target registration in `finally` even when source loading raises.

Add tests for successful and failed source-bank resolution proving the registered bank remains the target bank afterward.

## Lineage rules

Use exact `(question_id, from_fp)` indexing and a visited-fingerprint set.

Tests:

```text
direct V1->V2 allowed
reverse V2->V1 rejected
V1->V2 + V2->V3 yields exact two-edge chain
missing middle -> no lineage
conflicting next edges -> LINEAGE_CONFLICT
cycle does not loop and is rejected as conflict when traversal would be ambiguous
```

Run GREEN and commit:

```text
feat: add registered content revision lineage authority
```

---

# Task 4 — Pure progress migration and revision-aware history

## Files

Create:

- `content_revision_migration.py`
- `tests/test_content_revision_migration.py`

## Required interfaces

```python
class MigrationStatus(StrEnum):
    APPLIED = "APPLIED"
    MIGRATION_ALREADY_APPLIED = "MIGRATION_ALREADY_APPLIED"

class MigrationFailureReason(StrEnum): ...
class ContentRevisionMigrationError(ValueError): ...

@dataclass(frozen=True, slots=True)
class PayloadMigrationResult:
    payload: dict[str, Any]
    changed: bool
    status: MigrationStatus
    migration_id: str

derive_migration_id(revision) -> str
migrate_progress_payload(payload, target_questions, revision, migrated_at) -> PayloadMigrationResult
history_event_matches_approved_revision(event, question, revision_or_sequence) -> bool
history_events_for_question_revision_aware(history_map, question, revision_or_sequence=None) -> list[Mapping[str, Any]]
```

## Migration ID

Use canonical labeled JSON over:

```text
kind = sc900_content_revision_migration_v1
manifest_sha256
source_bank_content_fingerprint
target_bank_content_fingerprint
```

## Progress transform rules

When payload bank FP equals source:

- unchanged active record FP must equal common source/target FP exactly;
- changed active record FP must equal exact `edge.from`;
- a changed record already carrying `edge.to` is a partial/conflicting source state and fails;
- every active question must exist in target;
- changed active question requires exact edge from stored FP to target FP;
- update only active binding and bank FP;
- preserve all learner metrics;
- leave `history` deep-equal;
- leave `quarantined_questions` deep-equal;
- append exactly one lineage row per transitioned active question.

When payload bank FP already equals target:

- verify complete target binding;
- verify expected lineage for previously transitioned active questions;
- exact complete state -> `MIGRATION_ALREADY_APPLIED`, `changed=False`;
- partial/conflicting target state -> fail.

## History rules

- call existing strict matcher first;
- if strict match fails, require same canonical ID plus exact approved direct/chained lineage to current question FP;
- `revision=None` reproduces current strict behavior;
- never rewrite returned historical event data.

## RED tests

Cover:

```text
full learner metric preservation
history immutability
quarantine non-resurrection
source bank mismatch
source active FP mismatch
source-bank payload containing edge.to partial state
missing target question
unauthorized transition
idempotent target no-op
incomplete/conflicting target lineage
strict same-FP history
approved old->new history
no-authority no attachment
different ID no attachment
reverse-only no attachment
complete chain attachment
missing middle no attachment
historical old text/fingerprint retained
```

Run GREEN and existing segment-3 adversarial regressions.

Commit:

```text
feat: preserve progress across approved content revisions
```

---

# Task 5 — Pure canonical saved-session migration

## Files

Modify:

- `content_revision_migration.py`
- `tests/test_content_revision_migration.py`

## Required interface

```python
migrate_session_payload(saved, target_questions, revision, target_bank_file) -> PayloadMigrationResult
```

Reuse existing `migrate_session_snapshot`, `canonical_session_signature`, and `ordered_question_ids`; do not modify `session_store.py` or `session_models.py`.

## Rules

1. Require saved bank FP = exact source bank FP.
2. Strictly validate source canonical session/signatures.
3. Require every saved/restore question ID exists in target.
4. For changed IDs, require target FP = exact edge.to.
5. Deep-copy validated snapshot.
6. For changed unanswered question with nonempty selected/pending, clear only selected/pending.
7. Preserve completed answers.
8. Preserve `session_answer_history` deep-equal.
9. Preserve current index, elapsed, builder context, quests/rewards/checkpoints/flags/confidence and compatible state.
10. Set target bank file/fingerprint.
11. Regenerate canonical session/restore signatures.
12. Strictly validate the target snapshot.

## Important idempotence design

Do **not** add a session migration-ID field.

The current session schema does not store one. Existing-target idempotence/recovery is established later by recomputing the exact expected migrated target payload and comparing normalized equality.

## RED tests

Cover:

```text
completed changed selection preserved
changed unanswered pending selection reset
unchanged question state preserved
history unchanged
signatures and bank identity regenerated
source bank FP mismatch
invalid source session/restore signatures
unknown target question
changed target FP mismatch
changed question missing edge
```

Run existing canonical session tests and commit:

```text
feat: migrate approved sessions to target bank identity
```

---

# Task 6 — Transactional persistence and non-mutating migration reads

## Files

Modify:

- `runtime_persistence.py`

Create/extend:

- `tests/test_content_revision_app_integration.py`

## Required interfaces

```python
content_revision_archive_path(source_path, migration_id, label) -> Path
migrate_progress_across_approved_revision(...) -> tuple[dict[str, Any] | None, Path | None, Exception | None]
migrate_session_file_across_approved_revision(...) -> tuple[dict[str, Any] | None, Path | None, Exception | None]
```

## Non-mutating read rule

Do **not** use `load_json_or_backup(...)` for explicit content-revision source reads. It renames bad JSON, which violates this contract.

Explicit migration must:

```text
read bytes/text directly
json.loads directly
on failure preserve source path and bytes exactly
return error/fail closed
```

Ordinary non-revision loading remains unchanged.

## Deterministic archive

Archive name may include migration-ID prefix. If deterministic archive already exists, require byte-for-byte equality before reusing it.

## Progress persistence rules

- pure-transform before mutating source;
- already-applied verified target -> no new backup;
- archive source before same-path replacement;
- safe write target;
- re-read non-mutatingly and verify target FP + expected lineage;
- unexpected existing target bank FP (neither source nor target) -> preserve all, fail closed;
- if source and target both exist, never overwrite target from source unless target is verified exact source-bound state under this revision.

## Session persistence rules

- compute expected target from strictly validated source;
- if target already exists, read/validate non-mutatingly and compare normalized target to exact expected migrated target;
- exact equality -> already applied / finish source archival cleanup;
- any difference -> conflict, preserve both;
- write/verify target before source removal;
- source archive exists before removal;
- if cleanup fails after verified target, return recoverable error with target + archive intact.

## RED fault-injection tests

Progress:

```text
success
archive failure
write failure
same-path safety
already-applied no-op
conflicting target
unexpected target bank FP
malformed source remains path+bytes unchanged
```

Session:

```text
success source!=target
archive failure before target write
write failure preserves source
cleanup failure after verified target is recoverable
restart with exact expected target finishes cleanup
existing differing target fails preserving both
same-path safety
malformed source remains path+bytes unchanged
```

Run existing persistence regressions and commit:

```text
feat: persist approved content revision migrations atomically
```

---

# Task 7 — Resolve registered authority during bank load and migrate progress before ordinary binding

## Files

Modify:

- `app.py`
- `tests/test_content_revision_app_integration.py`

## Runtime contract

Initialize:

```python
self.content_revision_authority: AdmittedRevision | None = None
```

Registry resolution returns `AdmissionResult | None`, handled exactly as:

```text
None -> no authority; current behavior
FAIL -> authority remains None; block attempted registered migration
PASS -> require admitted != None; store only admitted object
```

A failed `AdmissionResult` must never reach history consumers as authority.

## Target registration restoration

When resolver loads source bank through `load_bank`, restore target progress identity registration in `finally`.

## Progress source selection

After target bank parse and before ordinary target content-epoch processing:

```text
target progress absent + source progress exists
    -> explicit source->target migration

target progress exists and stored bank FP == source
    -> migrate that exact target path in-place

target progress exists and stored bank FP == target
    -> ordinary current-bank load

target progress exists and stored bank FP is neither source nor target
    -> fail closed, preserve files, block writes

both source and target progress exist
    -> never overwrite target from source unless target is verified exact source-bound state
```

On explicit migration error:

- preserve source/target files;
- `progress_write_blocked = True`;
- log/warn;
- do not fall through to ordinary target changed-content migration.

## RED tests

Cover:

- empty registry preserves current ordinary load path;
- different source/target bank filenames migrate source progress to target path;
- same runtime progress path case archives before replacement;
- invalid registered authority blocks migration and preserves state;
- unexpected target progress bank FP fails closed;
- both source and conflicting target files remain preserved;
- failed admission cannot leak into `self.content_revision_authority`;
- target global registration remains target after successful/failed source authority resolution.

Run existing final-bank activation migration regressions and commit:

```text
feat: migrate approved progress before target bank binding
```

---

# Task 8 — Cross-filename session discovery and complete history-consumer integration

## Files

Modify:

- `app_session_persistence_mixin.py`
- `app_analytics_mixin.py`
- `app_game_mixin.py`
- `app_session_builder_mixin.py`
- `app.py`
- `tests/test_content_revision_app_integration.py`

## Session discovery

Add source-bank session glob pattern only when exact admitted authority is active. Deduplicate candidates.

Attempt explicit revision migration **before** ordinary bank-mismatch quarantine only when:

```text
saved bank FP == authority.source bank FP
current bank FP == authority.target bank FP
```

On migration failure, preserve source session and skip it without classifying the authorized migration failure as corrupt JSON.

Malformed unrelated ordinary JSON continues through existing quarantine behavior.

## History-consumer integration

Use the common revision-aware resolver in all directly affected consumers:

- `app_analytics_mixin.py`;
- `app_game_mixin.py`;
- `app_session_builder_mixin.py`;
- `TestingEngineApp.question_volatility(...)` in `app.py`.

Search the repository for remaining direct `history_event_matches_question(...)` / `history_events_for_question(...)` calls in learner-history consumers. Any equivalent runtime consumer discovered must either be switched to the shared resolver or documented/tested as intentionally strict.

Do not alter the strict functions in `question_identity.py`.

## RED tests

Cover:

```text
source-bank canonical session discovered only with matching authority
successful migration returns target canonical path
source resumable file archived/removed only after verified target
no authority retains current mismatch behavior
migration failure preserves source and avoids corrupt-file quarantine
malformed unrelated JSON retains existing quarantine behavior
approved V1 event contributes to AnalyticsMixin under V2
approved V1 event contributes to GameRewardsMixin stability under V2
approved V1 event contributes to SessionBuilderMixin/Smart Practice under V2
approved V1 event contributes to question_volatility under V2
without authority the same old event does not attach
historical selected_texts/correct_texts remain original downstream values
```

Run affected existing session/confidence/identity tests and commit:

```text
feat: integrate approved revision continuity into runtime consumers
```

---

# Task 9 — Repository quality/type authority

## Files

Modify:

- `pyproject.toml`
- `tools/run_quality_checks.py`
- `tests/test_content_revision_authority.py`

## Required configuration

Add first-party modules:

```text
content_revision_authority
content_revision_migration
content_revision_registry
```

Add source files to maintained quality/mypy target lists.

## RED/GREEN test

Add a test asserting the three modules appear in `QUALITY_TARGETS`, Ruff known-first-party, and mypy files.

Then run:

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

If Black reports only touched-file formatting, format only touched files and rerun.

Commit:

```text
chore: add content revision modules to quality gates
```

---

# Task 10 — Package-A closure verification and exact evidence

## Files

Create:

`docs/research/SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001/01-PACKAGE-A-VERIFICATION.md`

No production code edits are allowed in this task unless verification exposes a defect. If a defect is found, return to the owning task's RED/GREEN cycle, fix in a separate commit, and restart closure.

## 10.1 Diff boundary

Run:

```bash
git diff --name-status 23d440b6976b9f6bbb3b77285bf0d11effc2513f...HEAD
git status --short
```

Before receipt creation, allowed implementation paths are only:

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

No bank JSON, EXE, production evidence, PR13 artifact, recovery artifact, or unrelated source path may appear.

## 10.2 Focused Package-A tests

```bash
python -m unittest \
  tests.test_content_revision_authority \
  tests.test_content_revision_migration \
  tests.test_content_revision_app_integration \
  -v
```

Required: PASS.

## 10.3 Existing identity/session regression wall

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

Required: PASS; existing no-authority fail-closed behavior remains unchanged.

## 10.4 Full repository tests

```bash
python -m unittest discover -s tests -v
```

Required: zero failures/errors. Existing environment-specific Tk/display skips are acceptable only when reported as skips.

## 10.5 Repository quality/bank/install verification

```bash
python -m tools.run_quality_checks
python -m tools.lint_bank --allow-warnings sc900_bank_v8_final.json
python -m tools.verify_installation
```

Required: PASS.

## 10.6 Production immutability

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

Required production bank SHA:

```text
177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
```

If root production EXE is present, required unchanged SHA:

```text
9c5d6cdfa46e4b6a49dd5ff1760f1f1d1640b4e1e889009547b682ecd54f7558
```

If absent, record absence; do not build it.

## 10.7 Verification receipt

Populate only observed results. Include:

```text
WORK_ID
DESIGN_REVIEW_HEAD
START_MAIN_SHA
IMPLEMENTATION_HEAD

PRODUCTION_QUESTION_WORDING_CHANGES
PRODUCTION_BANK_ACTIVATION
AUTHORIZED_CONTENT_REVISION_MANIFESTS_COUNT
PR13_MODIFIED
RECOVERY_REFS_MODIFIED
PRODUCTION_EXE_CHANGED
MERGED

PACKAGE_A_TESTS
IDENTITY_SESSION_REGRESSION_WALL
FULL_UNITTEST_DISCOVERY
QUALITY_CHECKS
BANK_LINT
INSTALLATION_VERIFICATION

PRODUCTION_BANK_SHA256
PRODUCTION_EXE_PRESENT
PRODUCTION_EXE_SHA256

NO_AUTHORITY_BEHAVIOR
ADMITTED_SYNTHETIC_REVISION
HISTORICAL_EVENTS_REWRITTEN
QUARANTINE_RESURRECTION
PENDING_SELECTION_ON_CHANGED_UNANSWERED_QUESTION
MIGRATION_IDEMPOTENCE
ATOMIC_BACKUP_WRITE_RECOVERY
TARGET_REGISTRATION_RESTORED
NONMUTATING_MIGRATION_READS

PACKAGE_A
PACKAGE_B_AUTHORIZED
PRODUCTION_ACTIVATION_AUTHORIZED
MERGE_AUTHORIZED
```

Constant values only where verified by scope/tests:

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

Test counts, implementation head, EXE presence/hash, and PASS results must come from observed command output.

After adding the receipt, rerun focused Package-A tests and commit:

```text
docs: record package A migration verification
```

## 10.8 Final exact-head review

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
Package-A paths only
production bank unchanged
module-level production registry empty
no production manifest/review evidence
no EXE change
no merge
```

Stop and return exact implementation head + verification receipt. Do not begin Package B.

---

# Plan self-review checklist

Before Cursor starts implementation, this plan is considered reconciled only if all statements below remain true:

```text
real fields used: exam_calibration_tier / exam_simulation_eligible
fingerprint-blind keyed choice swaps independently rejected
all non-choice fields globally constrained
bank-level metadata constrained
manifest/review/bank authority JSON duplicate-safe
Microsoft Learn authority syntax mechanically checked
target identity registration restored after source bank load
explicit migration reads non-mutating on failure
source-bound progress cannot be partially target-bound
runtime authority stores AdmittedRevision only
question_volatility included in history integration
session recovery uses exact expected-target equality, not stored migration ID
unexpected target progress state fails closed
registered runtime source/target filenames distinct
evidence paths contained under governed roots
missing/unreadable evidence mapped to finite reasons
wrong-type authority structures adversarially tested
production registry empty
production content unchanged
EXE unchanged
PR13 untouched
recovery refs untouched
merge unauthorized
```

Package B and Package C require separate plans and separate authorization.
