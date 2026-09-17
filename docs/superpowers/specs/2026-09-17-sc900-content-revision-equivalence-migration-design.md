# SC-900 Content-Revision Equivalence Migration — Final Reconciled Design

**Work ID:** `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001`

**Repository:** `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`

**Design branch:** `design/sc900-content-revision-equivalence-migration-001`

**Implementation base:** `23d440b6976b9f6bbb3b77285bf0d11effc2513f`

**Status:** FINAL / USER-APPROVED / PRE-IMPLEMENTATION

This document is the single authoritative design for Package A. It incorporates the approved Sections 1–5 and the pre-execution review corrections. The former review-errata document is historical only after reconciliation and no longer overrides this spec.

## Scope and non-authorization

This design authorizes only Package A infrastructure planning/execution after an implementation plan is followed. It does **not** authorize:

- production question wording changes;
- production bank activation;
- production equivalence manifests/review evidence;
- EXE rebuild;
- PR #13 modification or merge;
- protected recovery-ref/tag modification;
- merge to `main`.

The current production bank must remain byte-for-byte unchanged in Package A.

---

# Section 1 — Full-Continuity Equivalence Architecture

## 1.1 Problem

Current learner-history safety is intentionally fail-closed. Question content is bound by durable fingerprints. A same-ID question whose durable content changes is treated as `CHANGED_CONTENT`, so prior learner state does not silently attach to revised content. Canonical saved sessions also bind to the exact bank fingerprint.

That behavior blocks safe wording-only repairs, including the answer-length leakage repair, even when the intended proposition and answer authority are unchanged.

The new contract must permit continuity only for an explicitly reviewed, exact, meaning-preserving revision while retaining all existing strict behavior for every unapproved content change.

## 1.2 Selected continuity policy

`FULL_CONTINUITY` is the approved policy.

For an exact reviewed wording-only revision, prior progress, history-derived learning signals, mastery/confidence state, Smart Practice evidence, and compatible saved-session state may continue across the revision.

Continuity is authorized only through an exact directed source->target equivalence edge. There is no fuzzy similarity, ID-only fallback, runtime LLM judgment, or inferred reverse equivalence.

## 1.3 Exact directed equivalence edges

Each changed question is represented by:

```text
question_id
from_content_fingerprint
to_content_fingerprint
```

Edges are directional. `V1 -> V2` does not imply `V2 -> V1`.

A historical event from `V1` may be recognized at `V3` only when the complete approved chain exists:

```text
V1 -> V2 -> V3
```

Version-1 live-state migration remains limited to one direct bank edge per execution.

## 1.4 Historical events are immutable

Historical events retain their original:

```text
question_content_fingerprint
selected_texts
correct_texts
correctness
confidence
timing
context/timestamps
```

Migration never rewrites old events to pretend they occurred under the target wording.

## 1.5 Full semantic equivalence covers every answer choice

Full continuity requires preservation of the proposition represented by every choice, not merely preservation of the correct letter.

For a changed question:

```text
PROMPT_MEANING_PRESERVED = YES
CORRECT_PROPOSITION_PRESERVED = YES
CHOICE_A_SEMANTICS_PRESERVED = YES
CHOICE_B_SEMANTICS_PRESERVED = YES
CHOICE_C_SEMANTICS_PRESERVED = YES
CHOICE_D_SEMANTICS_PRESERVED = YES
DISTRACTOR_ROLE_PRESERVED = YES
```

A distractor may not be replaced by a different wrong concept simply because it remains wrong.

## 1.6 Letter mapping and correct key remain stable

Version 1 requires:

```text
CHOICE_LETTER_MAPPING_UNCHANGED = YES
CORRECT_KEY_UNCHANGED = YES
```

No choice reordering or cross-letter concept remapping is admitted.

## 1.7 Progress may rebind, with lineage

For an admitted revision, active learner metrics remain intact while the active question-content binding advances to the target fingerprint.

Migration provenance is append-only and records at least:

```text
question_id
from_fingerprint
to_fingerprint
manifest_sha256
migration_id
migrated_at
```

Previously quarantined state is not automatically resurrected.

## 1.8 Saved sessions use stricter migration

A saved session may migrate only when every referenced question still exists and is either fingerprint-identical or covered by the exact admitted edge, with stable answer-letter mapping and correct key.

The target session receives a new bank fingerprint and regenerated canonical session/restore signatures. Old historical answer events stay bound to the content actually experienced.

## 1.9 Exact bank binding

Every equivalence package binds the exact source and target banks:

```text
SOURCE_BANK_FILENAME
SOURCE_BANK_FILE_SHA256
SOURCE_BANK_CONTENT_FINGERPRINT
TARGET_BANK_FILENAME
TARGET_BANK_FILE_SHA256
TARGET_BANK_CONTENT_FINGERPRINT
QUESTION_EQUIVALENCE_EDGES[]
MANIFEST_SHA256
```

No new signing/PKI system is required. Repository-controlled hash-bound evidence is sufficient for this application.

## 1.10 Existing strict APIs stay strict

The existing baseline behavior remains authoritative. Do not introduce a generic bypass such as `allow_changed_content=True`.

Conceptual new APIs are explicit:

```text
validate_content_revision_manifest(...)
admit_content_revision(...)
migrate_progress_across_approved_revision(...)
migrate_session_across_approved_revision(...)
history_event_matches_approved_revision(...)
```

Without an admitted revision, existing `CHANGED_CONTENT` and session-bank mismatch behavior is unchanged.

---

# Section 2 — Exact Manifest and Fail-Closed Admission

## 2.1 Manifest model

The governed manifest contains:

```text
schema_version = 1
manifest_kind = sc900_content_revision_equivalence
work_id
continuity_policy = FULL_CONTINUITY
source_bank { filename, file_sha256, content_fingerprint, question_count }
target_bank { filename, file_sha256, content_fingerprint, question_count }
permitted_change_class = WORDING_ONLY_LENGTH_REBALANCE
edges[]
payload_sha256
```

Each edge contains:

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
choice_semantics[A-D]
review_status
review_artifact
review_artifact_sha256
authority_refs[]
```

Manifest booleans are evidence metadata only. The validator independently recomputes the actual invariants from the banks.

## 2.2 Version-1 permitted change surface

Only keyed answer-choice wording may differ:

```text
choices[A]
choices[B]
choices[C]
choices[D]
```

All other question fields must remain unchanged for continuity admission.

Repository-real calibration fields are:

```text
exam_calibration_tier
exam_simulation_eligible
```

`study_focus` is also immutable but is not a substitute for `exam_calibration_tier`.

Version 1 specifically requires the following to remain unchanged:

```text
canonical question ID
question_number
prompt
correct answer letters
choice-label set
choice-letter/concept association
question_type
objective_code
domain
topics
exam_calibration_tier
exam_simulation_eligible
study_focus
chapter
subtitle
general_explanation
choice_explanations
reasoning_steps
calibration_version
all other non-choice durable/runtime/classification fields
```

If answer wording would require an explanation change, that question is excluded from the tranche.

## 2.3 Global invariant checking occurs before edge admission

The validator compares **every** canonical source/target question pair, not only fingerprint-different questions.

This is required because the existing content fingerprint can be blind to some keyed-choice permutations or classification/runtime fields.

Mandatory global checks include:

```text
canonical ID unchanged
correct key unchanged
choice-label set unchanged
prompt unchanged
question type unchanged
objective_code unchanged
domain unchanged
topics unchanged
exam_calibration_tier unchanged
exam_simulation_eligible unchanged
study_focus unchanged
explanations unchanged
all other non-choice fields unchanged
```

Specific finite reasons are used where defined; otherwise `NONPERMITTED_FIELD_CHANGED`.

### Choice-permutation protection

Even when:

```text
SOURCE_FP == TARGET_FP
```

if keyed choices differ in a way that remaps concepts across letters, admission fails:

```text
SOURCE_FP == TARGET_FP
AND source["choices"] != target["choices"]
AND change is a cross-letter permutation/remap
    -> CHOICE_LETTER_MAPPING_CHANGED
```

A pure B/C text swap therefore cannot hide behind fingerprint equality.

## 2.4 Closed-world changed-question set

After global invariant checking, compute the actual fingerprint-different question set and require:

```text
ACTUAL_CHANGED_QUESTION_ID_SET
==
MANIFEST_EDGE_QUESTION_ID_SET
```

An undeclared content change rejects the revision. An edge for an unchanged question also rejects the revision. No partial bank migration is admitted.

## 2.5 Bank-level metadata is immutable in version 1

The source and target bank JSON objects are compared after duplicate-safe parsing. All top-level bank content other than the `questions` array must be semantically equal.

Formatting/whitespace differences are irrelevant. A changed bank title, version, or other top-level metadata fails `NONPERMITTED_FIELD_CHANGED`.

## 2.6 Review artifacts

Every changed question receives a separate review artifact containing at least:

```text
question_id
from_content_fingerprint
to_content_fingerprint
before choices A-D
after choices A-D
semantic_review A-D
correct_key_before
correct_key_after
authority_refs[]
disposition = APPROVED_FOR_FULL_CONTINUITY
```

The manifest stores the raw SHA-256 of each review artifact.

Review JSON uses the same duplicate-key-safe parser as manifest JSON. Duplicate authority-bearing keys fail closed rather than using last-key-wins behavior.

## 2.7 Microsoft Learn authority syntax

For SC-900 semantic approval, both the manifest edge and its bound review artifact must contain at least one normalized authority reference beginning with:

```text
https://learn.microsoft.com/
```

Runtime does not fetch the URL. This is deterministic syntax validation only.

Empty refs or non-Microsoft-only refs fail `AUTHORITY_EVIDENCE_MISSING`.

## 2.8 Canonical manifest hashing

Manifest hashing is based on parsed canonical JSON, not pretty-printing:

```text
UTF-8
duplicate keys rejected
supported JSON types only
lexicographic object-key order
compact deterministic serialization
SHA-256
```

Conceptually:

```python
json.dumps(payload_without_payload_sha256, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
```

Bank and review `file_sha256` values use raw file bytes.

## 2.9 Governed evidence paths

Runtime authority material is release-controlled under:

```text
content_revision_evidence/
    manifests/
    reviews/
```

Registry paths and `review_artifact` paths must be nonempty relative paths contained under the intended governed root. Absolute paths and `..` traversal are rejected before reading.

User-writable runtime directories and arbitrary downloaded files do not confer authority.

## 2.10 Registered runtime source/target filenames must differ in version 1

The version-1 runtime resolver locates the source bank beside the installed target bank. Therefore:

```text
source_bank.filename != target_bank.filename
```

is mandatory for registered runtime migration.

Package B/C must keep the exact source bank file available beside the target bank during the migration window. Same-filename migration requires a future separately designed source-evidence location.

## 2.11 Exact source/target admission algorithm

Admission order is deterministic:

```text
1. Parse manifest duplicate-safely.
2. Validate schema/types/unknown/missing fields.
3. Validate canonical manifest hash.
4. Validate authority/evidence path containment.
5. Read/parse source and target bank JSON duplicate-safely.
6. Validate raw source/target file SHA-256.
7. Require source question count = 454.
8. Require target question count = 454.
9. Validate canonical question-ID uniqueness and identical ID sets.
10. Compare top-level bank metadata excluding questions.
11. Compare all global per-question non-choice and letter-mapping invariants.
12. Compute source/target bank content fingerprints.
13. Require exact manifest bank content fingerprints.
14. Compute actual fingerprint-different question-ID set.
15. Require exact equality with edge-ID set.
16. Validate exact edge from/to fingerprints.
17. Validate review artifact existence/hash/schema/exact before-after binding.
18. Require every A-D semantic disposition = EQUIVALENT.
19. Require Microsoft Learn authority syntax.
20. Admit the complete bank revision only if every edge passes.
```

## 2.12 Duplicate-safe parsing domain

Duplicate-key protection applies to:

- manifest JSON;
- review artifacts;
- bank JSON used as admission authority.

Malformed/wrong-type authority structures fail deterministically rather than relying on Python truthiness or coercion.

Required shape checks include:

```text
edges is a list
bank objects are mappings
question_count is an integer
choice_semantics is exact A-D mapping
authority_refs is a list of strings
boolean assertion fields are literal booleans
review before/after are exact A-D mappings
review semantic_review is exact A-D mapping
hash/fingerprint fields are nonblank valid hex
```

## 2.13 Finite failure domain

The admission result is:

```text
status = PASS | FAIL
reasons = finite ordered tuple/list
```

There is no `PASS_WITH_WARNING`.

Initial reasons include:

```text
SCHEMA_UNSUPPORTED
UNKNOWN_FIELD
MISSING_FIELD
DUPLICATE_JSON_KEY
MANIFEST_HASH_MISMATCH
SOURCE_BANK_FILE_HASH_MISMATCH
TARGET_BANK_FILE_HASH_MISMATCH
SOURCE_BANK_FINGERPRINT_MISMATCH
TARGET_BANK_FINGERPRINT_MISMATCH
QUESTION_COUNT_MISMATCH
QUESTION_ID_SET_MISMATCH
DUPLICATE_QUESTION_ID
UNDECLARED_CONTENT_CHANGE
EXTRA_EQUIVALENCE_EDGE
DUPLICATE_EQUIVALENCE_EDGE
FROM_FINGERPRINT_MISMATCH
TO_FINGERPRINT_MISMATCH
CORRECT_KEY_CHANGED
CHOICE_LABEL_SET_CHANGED
CHOICE_LETTER_MAPPING_CHANGED
PROMPT_CHANGED
OBJECTIVE_CHANGED
DOMAIN_CHANGED
TOPICS_CHANGED
TIER_CHANGED
EXAM_ELIGIBILITY_CHANGED
QUESTION_TYPE_CHANGED
NONPERMITTED_FIELD_CHANGED
SEMANTIC_REVIEW_MISSING
SEMANTIC_REVIEW_HASH_MISMATCH
SEMANTIC_EQUIVALENCE_NOT_APPROVED
CHOICE_SEMANTICS_CHANGED
AUTHORITY_EVIDENCE_MISSING
UNREGISTERED_MANIFEST
REGISTRY_HASH_MISMATCH
LINEAGE_INCOMPLETE
LINEAGE_CONFLICT
```

Missing/unreadable registered evidence maps deterministically:

```text
registered manifest absent/unreadable -> REGISTRY_HASH_MISMATCH
source bank absent/unreadable          -> SOURCE_BANK_FILE_HASH_MISMATCH
target bank absent/unreadable          -> TARGET_BANK_FILE_HASH_MISMATCH
review artifact absent/unreadable      -> SEMANTIC_REVIEW_MISSING
unsafe authority path                  -> SCHEMA_UNSUPPORTED
```

Underlying detail may be retained for logs, but the external reason remains finite.

---

# Section 3 — Runtime Migration Semantics

## 3.1 Admission and migration are separate

```text
ADMISSION DECIDES WHETHER CONTINUITY IS ALLOWED.
MIGRATION DOES NOT RE-JUDGE SEMANTICS.
```

Runtime receives only an `AdmittedRevision` object.

Runtime state contract:

```text
self.content_revision_authority: AdmittedRevision | None
```

An `AdmissionResult` must never be stored as runtime authority.

Handling is:

```text
None -> no authority
FAIL -> authority remains None; fail closed for attempted registered migration
PASS -> require result.admitted; store only result.admitted
```

## 3.2 Source-bank loading must restore target global registration

`question_bank.load_bank()` registers the loaded bank globally for progress identity. Reading a source bank during target authority resolution must not leave the source bank registered.

Required pattern:

```text
capture current target questions
try:
    load source bank
finally:
    register target questions again
```

The restoration must occur even if source loading fails.

## 3.3 Active progress migration

For a source-bound progress payload:

```text
payload.bank_fingerprint == revision.source_bank_content_fingerprint
```

requirements are strict:

```text
unchanged active question -> stored FP equals common source/target FP
changed active question   -> stored FP equals edge.from exactly
```

A source-bank payload that already contains `edge.to` for a changed active question is a conflicting partial state and fails `SOURCE_PROGRESS_FINGERPRINT_MISMATCH`.

Only a payload already bound to the exact target bank may enter the idempotent target-verification path.

Migration preserves learner metrics, changes only active fingerprint/bank binding, appends immutable migration provenance, leaves historical events untouched, and does not resurrect quarantined records.

## 3.4 Unexpected target progress state fails closed

If a target progress file exists and its bank fingerprint is neither exact source nor exact target:

```text
FAIL CLOSED
preserve target and source
progress_write_blocked = true
no fallthrough to ordinary target content-epoch migration
```

If both source and target progress files exist, source never overwrites target unless the target itself is verified as exact source-bound state under the admitted revision.

## 3.5 Explicit migration reads are non-mutating

Explicit content-revision migration must not use ordinary helpers that rename malformed JSON to `.bad.json`.

Progress/session migration reads source bytes/text directly and parses non-mutatingly. On malformed/unreadable input:

```text
source path remains present
source bytes remain unchanged
error is returned/fail-closed
```

Ordinary non-revision loading may retain current quarantine behavior.

## 3.6 Historical joins

Existing strict history matching remains unchanged.

The revision-aware resolver first attempts the strict match. If strict match fails, it requires:

```text
same canonical question ID
nonblank historical fingerprint
complete exact directed lineage from historical FP to current FP
```

Without authority, behavior is identical to the current strict path.

## 3.7 All direct history consumers must be covered

Revision-aware history applies consistently to history consumers, including:

- analytics;
- game/reward stability paths;
- session builder / Smart Practice paths;
- `TestingEngineApp.question_volatility(...)` in `app.py`;
- other direct strict-history consumers discovered during implementation.

The strict function in `question_identity.py` is not weakened.

## 3.8 Saved-session migration

A canonical source session is strictly validated against the source bank. The migrated target session:

- preserves ordered question IDs and compatible state;
- preserves completed selections;
- clears pending/selected state only for changed unanswered questions;
- preserves historical session-answer events unchanged;
- binds target bank fingerprint;
- regenerates `session_signature` and `restore_signature`;
- receives the target canonical filename/path.

## 3.9 Session idempotence and recovery do not depend on a stored migration ID

Current `SessionSnapshot` does not store a content-revision migration ID, and Package A does not expand that schema.

If a target session already exists:

```text
1. derive migration_id from admitted revision
2. strictly validate source session
3. recompute exact expected migrated target payload from source + revision
4. read/strictly validate existing target non-mutatingly
5. compare normalized existing target to expected migrated target
6. exact equality -> already applied / finish source archival cleanup
7. any difference -> conflict; preserve both; fail closed
```

Archive filenames may include the derived migration-ID prefix.

## 3.10 Transactional persistence

Progress migration:

```text
read non-mutatingly
validate
transform in memory
validate target
archive source
safe/atomic write target
re-read and verify target
```

Session migration:

```text
read non-mutatingly
validate
build exact target in memory
validate target identity/signatures
write target safely
re-read and verify
archive source
remove source from resumable surface only after verified target
```

A failed authorized migration must not be reclassified as corrupt ordinary JSON and moved aside.

## 3.11 Idempotence

Progress migration uses a deterministic migration ID derived from:

```text
manifest_sha256
source_bank_content_fingerprint
target_bank_content_fingerprint
```

A fully verified target-bound progress payload returns a deterministic no-op and does not duplicate attempts, history, lineage, or backups.

Saved-session idempotence is established by exact expected-target equality as described above.

---

# Section 4 — Adversarial Proof Obligations

Package A is not proven by a positive migration alone. Every positive case receives a negative twin.

## 4.1 Authority/schema tests

Required coverage includes:

```text
valid canonical manifest -> PASS
unsupported schema -> SCHEMA_UNSUPPORTED
missing field -> MISSING_FIELD
unknown field -> UNKNOWN_FIELD
duplicate manifest key -> DUPLICATE_JSON_KEY
duplicate review key -> DUPLICATE_JSON_KEY
duplicate bank authority key -> DUPLICATE_JSON_KEY
manifest tamper after hash -> MANIFEST_HASH_MISMATCH
JSON key order/whitespace change -> same canonical manifest hash
wrong field types -> SCHEMA_UNSUPPORTED
blank/malformed hashes -> SCHEMA_UNSUPPORTED
unsafe absolute/../ evidence paths -> SCHEMA_UNSUPPORTED
```

## 4.2 Exact bank tests

```text
correct source+target -> PASS
wrong source raw SHA -> SOURCE_BANK_FILE_HASH_MISMATCH
wrong target raw SHA -> TARGET_BANK_FILE_HASH_MISMATCH
wrong source fingerprint -> SOURCE_BANK_FINGERPRINT_MISMATCH
wrong target fingerprint -> TARGET_BANK_FINGERPRINT_MISMATCH
source/target count != 454 -> QUESTION_COUNT_MISMATCH
duplicate canonical ID -> DUPLICATE_QUESTION_ID
different ID set -> QUESTION_ID_SET_MISMATCH
bank top-level metadata change -> NONPERMITTED_FIELD_CHANGED
same runtime source/target filename -> fail closed for registered runtime resolution
```

## 4.3 Closed-world/global-invariant tests

```text
undeclared changed question -> UNDECLARED_CONTENT_CHANGE
edge for unchanged question -> EXTRA_EQUIVALENCE_EDGE
duplicate edge -> DUPLICATE_EQUIVALENCE_EDGE
wrong edge FROM -> FROM_FINGERPRINT_MISMATCH
wrong edge TO -> TO_FINGERPRINT_MISMATCH
correct key change -> CORRECT_KEY_CHANGED
choice-label change -> CHOICE_LABEL_SET_CHANGED
B/C keyed swap even with equal fingerprint -> CHOICE_LETTER_MAPPING_CHANGED
prompt change -> PROMPT_CHANGED
objective change -> OBJECTIVE_CHANGED
domain change -> DOMAIN_CHANGED
topics change -> TOPICS_CHANGED
exam_calibration_tier change -> TIER_CHANGED
exam_simulation_eligible change -> EXAM_ELIGIBILITY_CHANGED
question_type change -> QUESTION_TYPE_CHANGED
study_focus/reasoning_steps/calibration_version/explanation/other non-choice change -> NONPERMITTED_FIELD_CHANGED
```

## 4.4 Semantic-review tests

```text
missing review -> SEMANTIC_REVIEW_MISSING
review SHA mismatch -> SEMANTIC_REVIEW_HASH_MISMATCH
review QID/from/to mismatch -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
before/after choices mismatch -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
correct keys mismatch -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
choice AMBIGUOUS/SUBSTANTIVELY_CHANGED -> CHOICE_SEMANTICS_CHANGED
missing Microsoft Learn authority -> AUTHORITY_EVIDENCE_MISSING
non-Microsoft-only authority -> AUTHORITY_EVIDENCE_MISSING
review disposition not approved -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
manifest review status not approved -> SEMANTIC_EQUIVALENCE_NOT_APPROVED
```

## 4.5 Global-registration safety tests

After successful and failed source-bank authority resolution, the globally registered progress-identity bank remains the target bank.

## 4.6 Progress tests

Prove:

```text
learner metrics preserved
active target fingerprint advanced
history deep-equal to source
quarantine deep-equal to source
lineage appended once
source-bound changed record already at edge.to -> fail partial-state conflict
unexpected target bank fingerprint -> fail closed
pre-existing quarantine not resurrected
second application -> verified no-op
malformed migration source remains byte-for-byte in place
```

## 4.7 History tests

```text
strict same FP match
approved old->new match
no authority -> no cross-revision match
different ID -> no match
reverse-only edge -> no match
complete chain -> match
missing middle -> no match
returned event retains old text/fingerprint
failed AdmissionResult cannot act as authority
question_volatility uses approved lineage when authority active
```

## 4.8 Saved-session tests

Prove:

```text
completed changed answer preserved
changed unanswered pending selection locally reset
unchanged/flagged/reward/quest/builder/current-index/elapsed state preserved
session-answer history immutable
target bank/signatures/path regenerated
source mismatch -> fail
unknown target question -> fail
no edge -> fail
invalid source signatures -> fail
malformed source remains in place
existing exact expected target -> idempotent recovery
existing different target -> preserve both, fail closed
```

## 4.9 Persistence/crash tests

Fault-inject around:

```text
archive creation
serialization
safe write
target verification
source cleanup
```

Only acceptable terminal states are:

```text
SOURCE AUTHORITATIVE / TARGET NOT ACTIVE
```

or:

```text
VERIFIED TARGET AUTHORITATIVE
```

Never a half-migrated learner state.

## 4.10 Existing regression wall

Without an admitted revision:

```text
changed content -> CHANGED_CONTENT
changed-fingerprint history -> does not attach
bank-mismatched canonical saved session -> rejected
```

Existing canonical identity/session/adversarial tests must continue to pass unchanged.

---

# Section 5 — Component Ownership and Rollout

## 5.1 Existing strict identity layer

`question_identity.py` remains the strict baseline authority and is intentionally not modified for generic equivalence acceptance.

## 5.2 New pure authority module

`content_revision_authority.py` owns:

```text
manifest/review schema validation
canonical manifest hash
finite admission reasons
exact source/target bank validation
global non-choice/letter-mapping invariants
closed-world changed-ID proof
review binding and Microsoft Learn syntax checks
immutable admitted edges
lineage traversal
```

It is deterministic and performs no learner-state mutation.

## 5.3 New pure migration module

`content_revision_migration.py` owns:

```text
migration_id derivation
progress transform
session transform
revision-aware history matching/filtering
idempotence target verification
```

It receives only an `AdmittedRevision`.

## 5.4 Registry module

`content_revision_registry.py` owns the code-controlled registry and registered-target resolver.

Package A production registry remains exactly empty.

Registered evidence resolution must:

- enforce contained relative paths;
- require distinct source/target filenames;
- validate registered canonical manifest hash before use;
- restore target progress-identity registration after any source-bank load attempt;
- map missing/unreadable evidence to finite reasons.

## 5.5 RuntimePersistence remains I/O owner

`runtime_persistence.py` owns archive/write/re-read/verification mechanics for explicit approved migration. Explicit migration source reads are non-mutating.

Ordinary loading/quarantine helpers remain available for non-revision behavior.

## 5.6 App integration stays thin

`app.py` and persistence/session mixins orchestrate an already-admitted revision. They do not perform semantic review.

`self.content_revision_authority` stores only `AdmittedRevision | None`.

## 5.7 Common history resolver

All revision-aware consumers call the common resolver rather than duplicating equivalence logic. This includes analytics, game/reward stability, Smart Practice/session builder, and the direct `question_volatility` path.

## 5.8 Evidence surface

Governed release evidence lives under:

```text
content_revision_evidence/
    manifests/
    reviews/
```

Package A adds no production manifest or review file.

## 5.9 Package decomposition

### Package A — migration infrastructure

Contains:

```text
authority parser/validator
registry/lineage
progress/session transforms
transactional persistence
runtime orchestration
history-consumer integration
adversarial tests
quality/regression verification
```

Production question wording changes = 0.

### Package B — candidate bank and semantic evidence

Requires separate plan/authorization. It may create candidate wording, Microsoft Learn review receipts, manifest, and leakage metrics, but does not activate production by itself.

### Package C — controlled production activation

Requires separate explicit authorization and exact candidate identity. It owns activation, final full regression, Windows QA build, and production EXE refresh.

## 5.10 Relationship to stopped answer-length Tranche 1

The prior Tranche-1 result remains valid:

```text
ordinary wording mutation
-> CHANGED_CONTENT
-> rewrite blocked
```

Package A creates the governed continuity mechanism. It does not retroactively erase the blocker or mutate production content.

## 5.11 Version-1 limits and non-goals

Version 1 does not implement:

```text
generic arbitrary question editing
prompt rewriting
explanation rewriting
answer-key changes
answer-letter reordering
new/deleted question continuity
objective/domain/tier migration
quarantine resurrection
runtime semantic comparison
runtime web access
user-imported authority
trust-this-revision UI
signing-key/PKI infrastructure
multi-hop live-state migration in one operation
automatic reverse migration
same-filename registered runtime source/target migration
PR #13 changes
recovery-ref changes
unrelated refactoring
```

## 5.12 Rollout sequence

```text
1. Read this spec and the reconciled Package-A implementation plan from the exact design head.
2. Start implementation from exact main SHA 23d440b6976b9f6bbb3b77285bf0d11effc2513f.
3. Implement Package A test-first on an isolated branch/worktree.
4. Keep production registry empty and production bank unchanged.
5. Run focused adversarial tests and existing identity/session regression wall.
6. Run full repository tests/quality/bank lint/installation verification.
7. Record exact observed verification evidence.
8. Stop for external review.
9. Do not begin Package B without separate authorization.
```

## 5.13 Final governing invariant

```text
SAME CONTENT
    -> ordinary strict continuity

DIFFERENT CONTENT
+ exact admitted directed equivalence
+ exact source/target banks
+ exact declared change set
+ global non-choice and letter-mapping invariants
+ all choice propositions semantically equivalent
+ hash-bound review evidence
+ Microsoft Learn authority
    -> FULL CONTINUITY

ANY MISSING OR CONFLICTING CONDITION
    -> EXISTING FAIL-CLOSED BEHAVIOR
```

The core safety rule remains:

```text
UNREVIEWED CONTENT CHANGE NEVER INHERITS LEARNER AUTHORITY
```

---

# Reconciliation status

The pre-execution review findings have been incorporated into this specification. No separate errata layer is required to interpret the architecture.

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

FINAL_SPEC_COMPLETE = YES
USER_WRITTEN_SPEC_APPROVED = YES
IMPLEMENTATION_PLAN_REQUIRED = YES
```
