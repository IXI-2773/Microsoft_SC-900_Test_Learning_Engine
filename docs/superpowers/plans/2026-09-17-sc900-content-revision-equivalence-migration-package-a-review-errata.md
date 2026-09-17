# SC-900 Content-Revision Equivalence Migration — Package A Pre-Execution Review Errata

**Work ID:** `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001 / PACKAGE-A / PRE-EXECUTION-REVIEW`

**Applies to:**
- `docs/superpowers/specs/2026-09-17-sc900-content-revision-equivalence-migration-design.md`
- `docs/superpowers/plans/2026-09-17-sc900-content-revision-equivalence-migration-package-a-implementation.md`

**Authority rule:** This file is a mandatory pre-execution correction layer. Where it conflicts with the Package-A implementation plan, this file controls. It does not authorize Package B, production-bank mutation, production activation, EXE rebuild, PR #13 changes, recovery-ref changes, or merge.

## Review result

The Package-A architecture remains valid, but repository review found several implementation-level hazards that must be corrected before execution. These corrections close gaps against the current codebase; they do not weaken the approved fail-closed design.

---

## R1 — Cursor execution is explicitly allowed

The plan's prior line forbidding the user's desktop/local terminal is superseded for this handoff.

Cursor may use its normal repository-local terminal and Git worktree/branch operations to execute the plan. It must not touch unrelated user files, unrelated repositories, protected refs, PR #13, or recovery refs/tags.

If the `superpowers:*` skills named in the plan are unavailable in Cursor, execute the plan directly task-by-task while preserving the same TDD sequence and review gates.

---

## R2 — Read design authority from the design head, implement from exact main

Current exact authorities at review time:

```text
MAIN_SHA = 23d440b6976b9f6bbb3b77285bf0d11effc2513f
DESIGN_REVIEW_HEAD = <fill from final handoff message>
DESIGN_BRANCH = design/sc900-content-revision-equivalence-migration-001
```

The implementation branch still starts from exact `MAIN_SHA`, not from the design branch.

Before creating/switching to the implementation worktree, Cursor must read the spec, plan, and this errata from the exact design head, for example with `git show <DESIGN_REVIEW_HEAD>:<path>` or by reading them while checked out on the design branch. Do not assume these docs exist in the implementation branch based on `MAIN_SHA`.

Task-10 diff-boundary checks remain relative to `MAIN_SHA`; the spec/plan/errata are design-authority documents, not required implementation-branch changes.

---

## R3 — Use the repository's actual calibration/eligibility field names

The current repository uses:

```text
exam_calibration_tier
exam_simulation_eligible
```

Do **not** implement or test invented fields such as:

```text
exam_eligible
```

For Task 2:

```text
exam_calibration_tier change -> TIER_CHANGED
exam_simulation_eligible change -> EXAM_ELIGIBILITY_CHANGED
study_focus change -> NONPERMITTED_FIELD_CHANGED
reasoning_steps change -> NONPERMITTED_FIELD_CHANGED
calibration_version change -> NONPERMITTED_FIELD_CHANGED
```

The 454-question synthetic fixture must use `exam_calibration_tier` and `exam_simulation_eligible` so the named invariant tests exercise the real schema.

---

## R4 — Close the fingerprint-blind choice-permutation gap

`question_content_fingerprint()` intentionally treats choice text identity independently of presentation letter order. Therefore a pure B/C text swap can retain the same content fingerprint even though version-1 continuity forbids answer-letter/concept remapping.

Before computing/accepting the fingerprint-based changed-ID set, admission must compare source and target keyed choices for **every canonical question**, not only questions whose fingerprints differ.

Required rule:

```text
SOURCE_FP == TARGET_FP
AND source["choices"] != target["choices"]
    -> CHOICE_LETTER_MAPPING_CHANGED
    -> reject entire revision
```

Also require choice-label sets to be identical for every question.

Add an adversarial test where B and C texts are swapped on a question whose fingerprint remains equal; admission must fail `CHOICE_LETTER_MAPPING_CHANGED` and must not classify the question as unchanged.

This is a required implementation of the already-approved `CHOICE_LETTER_MAPPING_UNCHANGED` invariant.

---

## R5 — Enforce non-choice invariants globally, including fields outside the current content fingerprint

The current content fingerprint does not cover every classification/runtime field named by the approved design. In particular, admission must not rely on fingerprint inequality to notice changes to `exam_calibration_tier` or `exam_simulation_eligible`.

For **every** canonical source/target question pair, before edge admission:

```text
canonical ID unchanged
prompt unchanged
correct key unchanged
choice-label set unchanged
question type unchanged
objective_code unchanged
domain unchanged
topics unchanged
exam_calibration_tier unchanged
exam_simulation_eligible unchanged
study_focus unchanged
explanations unchanged
all other non-choice question fields unchanged
```

Only keyed `choices[A-D]` text may differ.

Use the specific failure reason where one exists; otherwise use `NONPERMITTED_FIELD_CHANGED`.

Then require the actual fingerprint-different question-ID set to equal the manifest edge-ID set.

---

## R6 — Compare bank-level metadata, not only normalized question rows

Version 1 permits only answer-choice wording changes. `admit_content_revision(...)` must therefore also parse the source and target bank JSON objects and require all top-level bank content other than the `questions` array to be semantically equal.

Required test:

```text
same question revision + changed bank title/version/other top-level metadata
    -> NONPERMITTED_FIELD_CHANGED
```

JSON formatting/whitespace alone is not a semantic metadata difference.

This prevents a manifest from authorizing unrelated bank-level changes merely because the exact raw target hash was listed.

---

## R7 — Duplicate-key-safe parsing applies to review artifacts too

The duplicate-key protection is not manifest-only.

Review JSON must be parsed with the same duplicate-key-safe object hook. Add a test where a review artifact contains a duplicate authority-bearing key; admission must fail closed with `DUPLICATE_JSON_KEY` rather than silently accepting the last value.

Bank authority JSON parsed specifically for R6 should also fail closed on duplicate top-level/object keys rather than silently last-key-wins.

---

## R8 — Microsoft Learn authority must be mechanically recognizable

The approved design makes Microsoft Learn the factual authority for SC-900 semantic review. `authority_refs` must not pass merely because a list is nonempty.

Require at least one normalized reference beginning with:

```text
https://learn.microsoft.com/
```

in both the manifest edge and its bound review artifact. Runtime does not fetch the URL; this is deterministic syntax validation only.

Add negative tests for empty refs and for non-Microsoft-only refs; both fail `AUTHORITY_EVIDENCE_MISSING`.

---

## R9 — Registered source-bank loading must not leave the source bank globally registered

`question_bank.load_bank()` calls `register_progress_identity_bank(...)` as a side effect. Using it to read the manifest's source bank after the target bank has loaded can accidentally replace the target bank's global progress identity authority.

The Task-3/Task-7 resolver must restore the target registration in a `finally` block after any source-bank load attempt.

Required behavior:

```python
current_target_questions = tuple(target_questions)
try:
    source_questions = load_bank(source_path)["questions"]
finally:
    register_progress_identity_bank(current_target_questions)
```

Equivalent code is acceptable, but the restore must happen even if source loading raises.

Add a regression test proving `registered_progress_identity_bank()` is still the target bank after successful and failed authority resolution.

---

## R10 — Explicit migration reads must be non-mutating on failure

Do **not** use `storage_utils.load_json_or_backup(...)` to read the source of an explicitly authorized content-revision migration. That helper renames unreadable JSON to a `.bad.json` file, violating the migration contract's requirement to preserve the source on failure.

For `migrate_progress_across_approved_revision(...)` and `migrate_session_file_across_approved_revision(...)`, read source bytes/text directly and parse with `json.loads` without renaming or moving the source. Return the error while leaving source bytes/path unchanged.

Ordinary non-revision loading may continue using existing quarantine behavior.

Add tests for malformed/unreadable migration source files proving the original path remains present and byte-for-byte unchanged.

---

## R11 — Source-bound progress may not contain a partially target-bound changed record

Tighten Task-4 progress migration.

When `payload.bank_fingerprint == revision.source_bank_content_fingerprint`:

```text
unchanged active question -> stored FP must equal the common source/target FP
changed active question   -> stored FP must equal edge.from_content_fingerprint exactly
```

A changed active record already carrying `edge.to_content_fingerprint` while the payload still claims the source bank is a conflicting partial state and must fail `SOURCE_PROGRESS_FINGERPRINT_MISMATCH` (or the plan's equivalent finite failure), not silently pass through.

Only a payload already bound to the target bank may enter the idempotent-target verification path.

Add the negative test explicitly.

---

## R12 — `self.content_revision_authority` stores only an admitted revision, never an AdmissionResult

Runtime type contract:

```text
self.content_revision_authority: AdmittedRevision | None
```

Registry resolution may return `AdmissionResult | None`, but the app must handle it as:

```text
None       -> no authority; retain current behavior
FAIL       -> authority remains None; fail closed / block the attempted migration
PASS       -> require result.admitted is not None; store result.admitted
```

History consumers receive `AdmittedRevision | None`, never `AdmissionResult`.

Add a test that a failed admission cannot leak into history matching as an authority object.

---

## R13 — Include the direct strict-history consumer in `app.py`

Repository review found a direct call in `TestingEngineApp.question_volatility(...)`:

```text
history_event_matches_question(event, q)
```

Task 8 must update this path to the shared revision-aware match logic when an admitted authority is active, while retaining strict behavior when authority is `None`.

Add `app.py` to Task-8 touched files and to the Task-8 commit.

Add a regression proving an approved V1 event contributes to `question_volatility` for V2, while the same event does not attach without authority.

Do not alter the strict function in `question_identity.py`.

---

## R14 — Session idempotence/recovery uses exact expected-target equivalence, not an unstored session migration ID

The current `SessionSnapshot` schema does not store a content-revision `migration_id`, and `migrate_session_snapshot(...)` reconstructs only its known schema fields. Package A does not need to expand that schema.

Therefore, when a target session already exists, determine idempotence/recovery as follows:

```text
1. Derive migration_id from the currently admitted revision.
2. Strictly validate source session.
3. Recompute the exact expected migrated target payload from the source + admitted revision.
4. Read and strictly validate the existing target non-mutatingly.
5. Compare the normalized existing target payload to the expected migrated payload.
6. Exact equality -> treat as already applied / finish source archival cleanup.
7. Any difference -> conflict; preserve both; fail closed.
```

Do not claim the target session itself stores `migration_id` unless a later separately approved schema revision adds that field.

Archive filenames may continue to include the derived migration-ID prefix.

Add crash-recovery/idempotence tests around this exact comparison.

---

## R15 — Handle unexpected target progress state explicitly

Task 7 must include this case:

```text
target progress file exists
AND bank_fingerprint is neither exact source nor exact target
    -> FAIL CLOSED
    -> preserve target and source files
    -> progress_write_blocked = true
    -> do not fall through to ordinary target content-epoch migration
```

If both source and target progress files exist, the target file is never overwritten from the source unless the target is itself verified as exact source-bound state under the admitted revision.

Add tests for both conditions.

---

## R16 — Version-1 registered runtime migration requires distinct source/target bank filenames

The current Task-3 resolver locates the source bank as:

```text
target_bank_path.parent / manifest.source_bank.filename
```

With the same source and target filename, an installed target bank would hide the exact old source bytes needed for admission. Package A must therefore fail closed when a registered runtime manifest declares the same source and target filename.

Version-1 release requirement:

```text
source_bank.filename != target_bank.filename
```

Package B/C must keep the exact source bank file available beside the target bank for the migration window, or a future design must add an explicit bundled source-bank evidence path.

Add an admission/registry test for same-filename runtime resolution failure.

---

## R17 — Authority/evidence paths must be contained under the governed evidence root

Manifest registry relative paths and per-edge `review_artifact` paths must be relative, nonempty, and resolve inside their intended governed directories. Reject absolute paths and any `..` traversal.

Use a deterministic fail-closed schema/authority reason; do not read outside `content_revision_evidence/` because a manifest requested it.

Add traversal tests for both manifest-registry and review-artifact paths.

---

## R18 — Exact finite failure mapping for missing/unreadable registered evidence

Do not allow raw `FileNotFoundError`/`UnicodeError`/`JSONDecodeError` to leak as an ambiguous successful path.

Use deterministic mappings:

```text
registered manifest absent/unreadable -> REGISTRY_HASH_MISMATCH
source bank absent/unreadable          -> SOURCE_BANK_FILE_HASH_MISMATCH
target bank absent/unreadable          -> TARGET_BANK_FILE_HASH_MISMATCH
review artifact absent/unreadable      -> SEMANTIC_REVIEW_MISSING
unsafe authority path                  -> SCHEMA_UNSUPPORTED
```

The exact error object may retain the underlying detail, but the externally asserted reason is finite and stable.

---

## R19 — Add wrong-type/schema-shape adversarial coverage

In addition to missing/unknown fields, Task 2 must test malformed field types for authority-bearing structures, including:

```text
edges not a list
bank object not a mapping
choice_semantics not an A-D mapping
authority_refs not a list of strings
question_count not an integer
boolean assertion fields not literal true/false
review before/after not A-D mappings
review semantic_review not an A-D mapping
hash/fingerprint fields blank or malformed
```

Reject with `SCHEMA_UNSUPPORTED` (or a more specific already-defined finite reason when appropriate). Do not rely on Python truthiness of strings such as `"false"`.

---

## R20 — Final closure diff/review must include this errata as authority, not as implementation output

The implementation worktree is still based on exact `MAIN_SHA`. This errata remains on the design-authority branch and does not need to appear in the Package-A implementation diff.

At final handoff, record both:

```text
DESIGN_REVIEW_HEAD
IMPLEMENTATION_HEAD
```

and state that implementation was checked against the spec, plan, and this pre-execution errata.

---

# Pre-execution review disposition

```text
ARCHITECTURE_REOPENED = NO
PACKAGE_A_SCOPE_CHANGED = NO
FAIL_CLOSED_POLICY_WEAKENED = NO
PRODUCTION_CONTENT_AUTHORIZED = NO
PRODUCTION_ACTIVATION_AUTHORIZED = NO
EXE_REBUILD_AUTHORIZED = NO
PR13_MODIFIED = NO
RECOVERY_REFS_MODIFIED = NO
MERGE_AUTHORIZED = NO

CURSOR_HANDOFF_STATUS = READY_AFTER_EXACT_HEAD_IS_FILLED
```
