# SC-900 Content-Revision Equivalence Migration Design

**Work ID:** `SC900-CONTENT-REVISION-EQUIVALENCE-MIGRATION-001`  
**Repository:** `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`  
**Design branch:** `design/sc900-content-revision-equivalence-migration-001`  
**Authoritative design base:** `23d440b6976b9f6bbb3b77285bf0d11effc2513f`  
**Status:** `INTERIM DESIGN / SECTIONS 1-3 APPROVED / SECTION 4+ PENDING`  
**Implementation authorized:** `NO`

## Purpose

The answer-length leakage repair proved that wording-only changes to durable question content currently change the per-question content fingerprint, quarantine prior learner progress as `CHANGED_CONTENT`, and invalidate canonical saved-session bank identity. That fail-closed behavior is intentional and must remain the default.

This design introduces a separate, explicit continuity authority for a narrow class of already-reviewed, meaning-preserving wording revisions. It does **not** weaken the existing content fingerprint, canonical question identity, changed-content quarantine, or saved-session bank-fingerprint protections.

The selected policy is:

```text
CONTINUITY_POLICY = FULL_CONTINUITY
```

Full continuity is permitted only through an exact, governed, hash-bound equivalence admission. Unknown or unreviewed content changes continue to fail closed.

## Global design boundaries

This design does not authorize:

- answer-length question rewrites yet;
- production-bank activation;
- mutation of the current production bank;
- weakening `question_content_fingerprint`;
- question-ID-only continuity;
- fuzzy or probabilistic runtime semantic matching;
- an `allow_changed_content=True` bypass;
- resurrection of arbitrary pre-existing quarantined learner state;
- answer-key changes;
- choice-letter remapping;
- PR #13 mutation or merge;
- recovery-ref mutation;
- production EXE changes;
- merge of any implementation package.

The runtime must remain fail closed unless all conditions described below are satisfied.

---

# Section 1 — Core Full-Continuity Equivalence Architecture

## 1.1 Existing identity remains authoritative

The existing durable-content fingerprint remains unchanged. It continues to bind meaning-bearing question content and to detect content mutation.

The normal rule remains:

```text
SAME CONTENT FINGERPRINT
    -> continuity under existing architecture

DIFFERENT CONTENT FINGERPRINT
    -> CHANGED_CONTENT quarantine / bank-session mismatch
```

The new system adds a narrow exception authority layered **on top** of this rule. It does not redefine what counts as durable content.

## 1.2 Separate directed equivalence ledger

The fundamental continuity authority is an explicit directed edge:

```text
QUESTION_ID
FROM_CONTENT_FINGERPRINT
TO_CONTENT_FINGERPRINT
```

Conceptually:

```text
question version V1
      |
      | APPROVED_SEMANTIC_EQUIVALENCE
      v
question version V2
```

An approved `V1 -> V2` edge does not automatically authorize `V2 -> V1`.

For multiple revisions:

```text
V1 -> V2 -> V3
```

continuity from V1 to V3 is permitted only when the complete directed lineage is independently valid. No transitive equivalence is inferred merely from question ID, lexical similarity, answer key, or model judgment.

## 1.3 Runtime semantic inference is forbidden

Runtime code must never decide that two questions “look equivalent.”

Forbidden runtime authorities include:

- string similarity;
- embeddings;
- LLM judgment;
- unchanged canonical ID alone;
- unchanged correct letter alone;
- unchanged objective alone;
- “both are wrong distractors” reasoning;
- heuristic matching.

Runtime may only consume an already-admitted exact equivalence edge and verify its hashes and identities.

## 1.4 Historical events remain immutable

Historical learner events preserve the exact content identity and answer text the learner actually experienced.

An event created under V1 remains bound to V1:

```text
question_id = Q1
question_content_fingerprint = FP_V1
selected_texts = texts actually seen at V1
correct_texts = texts actually authoritative at V1
```

Migration must not rewrite historical-event fingerprints from `FP_V1` to `FP_V2` and must not rewrite the old selected/correct text to the new wording.

Instead, consumers that need current-question history may use an explicit equivalence-aware join:

```text
event FP == current FP
    -> normal match

event FP != current FP
    -> exact approved lineage from event FP to current FP?
         YES -> eligible historical match
         NO  -> no match
```

This preserves auditability while allowing approved continuity.

## 1.5 Every answer choice must preserve semantics

Full continuity requires semantic equivalence for every choice, not only for the correct answer.

For each option label A/B/C/D:

```text
CHOICE_SEMANTICS = EQUIVALENT
```

must be explicitly reviewed.

A distractor cannot be replaced with a different wrong concept merely because both answers are incorrect. Previous learner mistakes and analytics may depend on which proposition was selected.

Therefore the contract requires:

```text
PROMPT_MEANING_PRESERVED = YES
CORRECT_PROPOSITION_PRESERVED = YES
CHOICE_A_SEMANTICS_PRESERVED = YES
CHOICE_B_SEMANTICS_PRESERVED = YES
CHOICE_C_SEMANTICS_PRESERVED = YES
CHOICE_D_SEMANTICS_PRESERVED = YES
DISTRACTOR_ROLE_PRESERVED = YES
EXPLANATION_MEANING_PRESERVED = YES
```

For the first contract, Section 2 narrows the actual permitted field changes further.

## 1.6 Choice-letter mapping is stable in version 1

The first equivalence contract requires:

```text
CHOICE_LABEL_SET_UNCHANGED = YES
CHOICE_LETTER_MAPPING_UNCHANGED = YES
CORRECT_KEY_UNCHANGED = YES
```

An old B concept must remain the revised B concept. Reordering concepts across letters is not admitted in this version, even if the proposition texts are otherwise equivalent.

This requirement protects in-progress session state that persists selected/pending answer letters.

## 1.7 Progress may rebind with lineage

For an approved edge:

```text
Q1 / FP_V1
     |
     | approved equivalence
     v
Q1 / FP_V2
```

the current active learner record may preserve accumulated state while its active content binding advances to `FP_V2`.

Preserved state includes, where present:

- attempts;
- correctness counts;
- mastery/weakness state;
- confidence evidence;
- review/due state;
- Smart Practice state;
- flags/suspension state;
- other accumulated learner metrics.

The migration also records immutable lineage such as:

```text
question_id
from_fingerprint
to_fingerprint
equivalence_manifest_sha256
migration_id
```

Full continuity must not erase evidence that the learner state originated under prior wording.

## 1.8 Saved sessions require bank-level authorization

Canonical saved sessions are bound to a whole-bank fingerprint. A changed bank therefore needs a governed source-bank -> target-bank migration, not a per-question bypass.

A saved session may migrate only when:

1. the exact source and target banks match the admitted manifest;
2. every referenced canonical question still exists;
3. every referenced question is either fingerprint-identical or linked by an approved equivalence path;
4. choice labels/mappings remain stable;
5. correct keys remain stable;
6. session/builder identity remains otherwise valid.

Unapproved bank differences continue to fail closed.

## 1.9 Existing strict functions remain strict by default

Existing strict identity behavior must not be changed into a permissive optional mode.

The architecture must not introduce a generic bypass such as:

```text
allow_changed_content = true
```

Instead, approved-revision behavior is exposed through an explicit, narrow revision authority and migration path. Existing changed-content adversarial protections remain valid when no admitted revision authority is supplied.

## 1.10 Section 1 controlling invariant

```text
SAME FINGERPRINT
    -> existing continuity

DIFFERENT FINGERPRINT
+ same canonical question
+ exact approved directed equivalence edge/chain
+ unchanged answer authority
+ unchanged choice-letter mapping
+ preserved choice propositions
+ exact bank-revision authority where required
    -> FULL CONTINUITY

OTHERWISE
    -> existing fail-closed behavior
```

---

# Section 2 — Exact Equivalence Manifest and Fail-Closed Admission

## 2.1 Manifest scope

The manifest is closed-world, hash-bound, and specific to one exact source-bank -> target-bank revision.

Conceptual top-level shape:

```json
{
  "schema_version": 1,
  "manifest_kind": "sc900_content_revision_equivalence",
  "work_id": "SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001",
  "continuity_policy": "FULL_CONTINUITY",
  "source_bank": {
    "filename": "sc900_bank_v8_final.json",
    "file_sha256": "<64 hex>",
    "content_fingerprint": "<64 hex>",
    "question_count": 454
  },
  "target_bank": {
    "filename": "<candidate filename>",
    "file_sha256": "<64 hex>",
    "content_fingerprint": "<64 hex>",
    "question_count": 454
  },
  "permitted_change_class": "WORDING_ONLY_LENGTH_REBALANCE",
  "edges": [],
  "payload_sha256": "<canonical payload digest>"
}
```

The final implementation schema may use typed objects or equivalent field names, but it must preserve the semantics and proof obligations in this design.

## 2.2 Version-1 permitted change surface

For the first equivalence contract, only answer-choice wording may change:

```text
choices[A]
choices[B]
choices[C]
choices[D]
```

All other meaning-bearing or classification fields remain unchanged for continuity admission, including:

```text
canonical question ID
prompt
correct answer letters
choice-letter/concept association
question type
objective code
domain
topics
exam calibration tier
exam eligibility
study-focus metadata
```

The existing explanations are also held unchanged in version 1. If a wording edit makes an explanation inaccurate or inconsistent, that question is excluded from the equivalence tranche rather than expanding this contract.

## 2.3 Per-question edge

Each changed question has exactly one direct edge for the source/target revision:

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

Manifest booleans are assertions/evidence metadata. They are not trusted in place of recomputation. Mechanical invariants are independently recomputed from source and target banks.

## 2.4 Per-choice semantic review

Each changed choice must be classified as semantically equivalent.

An acceptable edit may shorten or normalize wording while preserving the same proposition.

A different product, capability, condition, scope, exception, or distractor concept is not equivalent merely because it remains incorrect.

Admission requires:

```text
ALL_CHANGED_CHOICES = EQUIVALENT
CORRECT_PROPOSITION = EQUIVALENT
DISTRACTOR_PROPOSITIONS = EQUIVALENT
```

Any `AMBIGUOUS`, `SUBSTANTIVELY_CHANGED`, or `UNVERIFIED` choice rejects that question edge.

## 2.5 Review artifacts

Each changed question receives a separate human-auditable review artifact containing at least:

```text
question_id
before choice text A-D
after choice text A-D
per-choice semantic disposition
correct key before
correct key after
authority references
disposition
```

The main manifest stores the SHA-256 of each review artifact. Changing an approved review artifact therefore invalidates manifest admission.

For SC-900 factual claims, Microsoft Learn remains the factual authority. If current official authority is insufficient to establish a safe meaning-preserving revision, that question is excluded rather than forced through admission.

## 2.6 Canonical manifest hashing

The manifest payload is hashed deterministically after parse and validation, not by relying on pretty-print formatting.

Required properties:

```text
UTF-8
JSON parsed successfully
duplicate object keys rejected
supported JSON types only
lexicographic object-key order
compact deterministic serialization
SHA-256
```

Conceptually equivalent canonical serialization:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

`payload_sha256` is calculated over the canonical manifest payload excluding the self-referential `payload_sha256` field.

## 2.7 Trusted origin

Continuity authority must not come from a user-writable runtime directory or arbitrary downloaded file.

Approved manifest/review material is release-controlled repository/package content, conceptually under a dedicated authority surface such as:

```text
content_revision_authority/
    manifests/
    reviews/
```

The exact final path will be chosen during the implementation plan.

Runtime does not provide a user override such as “trust this changed bank.”

## 2.8 Global admission algorithm

Before learner state may cross source -> target:

```text
1. Validate manifest schema.
2. Validate manifest canonical payload hash.
3. Hash actual source bank file.
4. Hash actual target bank file.
5. Compute actual source/target bank content fingerprints.
6. Require exact manifest source/target bank matches.
7. Require source question count = 454.
8. Require target question count = 454.
9. Require identical canonical question-ID sets.
10. Compare every source question to its target question.
```

For every question:

```text
SOURCE_FP == TARGET_FP
    -> no equivalence edge required

SOURCE_FP != TARGET_FP
    -> exactly one manifest edge required with exact:
       question_id
       from_content_fingerprint
       to_content_fingerprint
```

Zero matching edges fails.

Duplicate/conflicting matching edges fail.

An equivalence edge for a question whose fingerprint did not actually change fails.

## 2.9 Closed-world changed-question set

The manifest must describe exactly the actual changed-question population:

```text
ACTUAL_CHANGED_QUESTION_ID_SET
==
MANIFEST_EDGE_QUESTION_ID_SET
```

An undeclared changed question rejects the entire revision.

An extra manifest edge for an unchanged question also rejects the entire revision.

No partial migration is admitted.

## 2.10 Mechanical edge validation

For every changed question the validator independently proves:

```text
QUESTION_ID_UNCHANGED = YES
QUESTION_ID_UNIQUE = YES
CORRECT_KEY_UNCHANGED = YES
CHOICE_LABEL_SET_UNCHANGED = YES
CHOICE_LETTER_MAPPING_UNCHANGED = YES
PROMPT_UNCHANGED = YES
OBJECTIVE_UNCHANGED = YES
DOMAIN_UNCHANGED = YES
TOPICS_UNCHANGED = YES
TIER_UNCHANGED = YES
EXAM_ELIGIBILITY_UNCHANGED = YES
QUESTION_TYPE_UNCHANGED = YES
ONLY_PERMITTED_FIELDS_CHANGED = YES
```

The source/target bank data, not the manifest assertion, decides each mechanical invariant.

## 2.11 Semantic admission

Every changed question additionally requires:

```text
SEMANTIC_REVIEW_STATUS = APPROVED
REVIEW_ARTIFACT_HASH = VALID
ALL_CHOICES = EQUIVALENT
OFFICIAL_AUTHORITY = PRESENT
```

If any changed question fails semantic review, the bank-level revision is rejected. The repair process may remove the uncertain question from the candidate, regenerate the candidate and manifest, and re-run admission.

## 2.12 Finite failure domain

Admission failures are machine-readable, finite reasons rather than arbitrary free-form success states.

Initial reason domain:

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
```

The validator returns conceptually:

```text
status = PASS | FAIL
reasons = finite ordered list
```

There is no `PASS_WITH_WARNING` continuity admission state.

## 2.13 Atomic bank-level decision

The bank revision is admitted only when all required edges pass.

Forbidden behavior:

```text
48 questions migrated
2 questions quarantined
continue anyway
```

Required behavior:

```text
ALL REQUIRED EDGES PASS
    -> manifest admitted

ANY REQUIRED EDGE FAILS
    -> manifest rejected
       existing CHANGED_CONTENT/session mismatch behavior remains authoritative
```

## 2.14 Revision-chain semantics

Manifests are directed bank-revision edges:

```text
BANK V8 --M1--> BANK V9
BANK V9 --M2--> BANK V10
```

A direct V8 -> V10 continuity operation requires validation of the complete approved chain. Neither bank nor question equivalence is inferred from IDs or similarity.

The first implementation may support only one direct production-bank -> target-bank revision while preserving this chain model for future compatibility.

## 2.15 Section 2 controlling invariant

```text
FULL_CONTINUITY_AUTHORIZATION =
    EXACT SOURCE BANK
  + EXACT TARGET BANK
  + EXACT DECLARED CHANGE SET
  + EXACT FROM/TO QUESTION FINGERPRINTS
  + UNCHANGED ANSWER AUTHORITY
  + UNCHANGED CHOICE LETTER MAPPING
  + ALL CHOICE PROPOSITIONS SEMANTICALLY EQUIVALENT
  + HASH-BOUND REVIEW EVIDENCE
  + MICROSOFT LEARN AUTHORITY
  + VALID MANIFEST HASH
```

Anything less provides no equivalence authority and therefore falls back to existing fail-closed behavior.

---

# Section 3 — Runtime Migration Semantics

## 3.1 Admission and migration are separate responsibilities

```text
ADMISSION DECIDES WHETHER CONTINUITY IS ALLOWED.
MIGRATION DOES NOT RE-JUDGE SEMANTICS.
```

Runtime migration accepts only a manifest/revision authority that has already passed Section 2 validation.

## 3.2 Active progress: preserve learner state, advance binding

For an admitted edge:

```text
Q1 / FP_V1
     |
     | approved equivalence
     v
Q1 / FP_V2
```

the active progress record preserves accumulated learner state while the active question-content binding advances to `FP_V2`.

Preserved values include, where present:

- attempts;
- correct/incorrect counts;
- mastery;
- confidence evidence;
- weak-question state;
- review scheduling/due state;
- Smart Practice state;
- flags/suspension state;
- other accumulated learning metrics.

The progress payload's active bank fingerprint advances from the exact source bank to the exact target bank.

The migration appends provenance such as:

```text
content_revision_migrations[]:
  question_id
  from_fingerprint
  to_fingerprint
  manifest_sha256
  migration_id
  timestamp
```

This provenance records that full continuity was explicitly authorized rather than pretending all state originated under the target wording.

## 3.3 Existing quarantine is not automatically resurrected

Version 1 distinguishes active source state from previously quarantined state.

```text
ACTIVE SOURCE RECORD
+ approved edge
    -> eligible for preservation/rebind

ALREADY QUARANTINED RECORD
    -> remains quarantined
```

Restoring arbitrary pre-existing quarantine is outside this package and would require a separate governed restoration contract.

## 3.4 Historical learner events remain immutable

Historical events retain:

```text
original question_content_fingerprint
original selected_texts
original correct_texts
original correctness/confidence/timing/context
```

Migration does not rewrite old event fingerprints or old text.

This preserves what the learner actually experienced.

## 3.5 Explicit equivalence-aware history resolver

The existing strict history matcher remains strict.

Approved cross-revision history is resolved through a separate explicit equivalence-aware path, conceptually:

```text
history_event_matches_approved_revision(event, current_question, admitted_revision)
```

Decision:

```text
event.question_id != current.question_id
    -> NO MATCH

event.fp == current.fp
    -> MATCH

event.fp != current.fp
    -> complete exact approved lineage event.fp -> current.fp?
         YES -> MATCH
         NO  -> NO MATCH
```

This avoids weakening the default strict matcher.

## 3.6 Smart Practice, analytics and other history consumers

When an admitted revision is active, history consumers that currently use fingerprint-bound question history may use the equivalence-aware resolver.

Approved old events may continue contributing to:

- weakness detection;
- confidence calibration;
- mastery estimation;
- due/review scheduling;
- Smart Practice selection;
- analytics and learning signals.

Historical text-derived analytics must continue to analyze the historical text stored in the event. They do not substitute current target-bank wording for old `selected_texts` or `correct_texts`.

Thus:

```text
IDENTITY JOIN
    -> may follow approved lineage

EVENT CONTENT
    -> remains historical
```

## 3.7 Saved-session migration preconditions

Canonical saved sessions may cross source-bank -> target-bank only when every referenced question satisfies:

```text
same canonical question ID
AND
(
    same fingerprint
    OR
    exact approved equivalence path
)
AND
same choice-letter mapping
AND
same correct key
```

Any referenced question failure rejects the entire saved-session migration.

There is no partial ordinary-session restore.

## 3.8 Session state preserved

Because Section 2 prohibits answer-letter remapping, admitted saved-session migration may preserve:

- ordered canonical question IDs;
- session question order;
- completed selected letters;
- completed answer state;
- flags;
- confidence;
- miss reason;
- elapsed time;
- current index;
- session quests;
- Smart Practice state;
- session rewards;
- checkpoint state;
- session answer history;
- builder context and other compatible runtime state.

Historical session-answer events remain bound to the revision actually experienced.

## 3.9 Target session identity is regenerated

The following source-session identity values are not copied unchanged:

```text
bank_fingerprint
session_signature
restore_signature
canonical session filename/path identity
```

Migration conceptually performs:

```text
VALID SOURCE SESSION
        |
        v
verify admitted source -> target revision
        |
        v
copy admissible learner/session state
        |
        v
bind TARGET BANK FINGERPRINT
        |
        v
recompute session signature
        |
        v
recompute restore signature
        |
        v
write new canonical target session
```

The old signatures deliberately authenticate the source-bank identity and therefore cannot simply be copied to the target revision.

## 3.10 Unanswered and pending questions

An unanswered question with no active selection simply renders the admitted target wording after migration.

For a changed question with an incomplete pending selection:

```text
answered = false
pending/selected != empty
```

version 1 clears the local pending/selected state for that question only.

Reason: the learner began an uncommitted interaction while viewing old wording. Restarting that one question under target wording is safer than silently converting an incomplete epistemic event.

Therefore:

```text
COMPLETED ANSWER
    -> preserve

UNANSWERED + NO SELECTION
    -> preserve blank state

UNANSWERED + PENDING SELECTION + CHANGED QUESTION
    -> clear local pending/selected state only
```

No completed learner-history event is lost by this rule.

## 3.11 Progress persistence is transactional

Progress migration is designed as:

```text
1. Read source payload.
2. Validate source payload and admitted revision.
3. Produce complete target payload in memory.
4. Validate complete target payload.
5. Back up source.
6. Atomically replace/install target state.
7. Re-read target and verify.
```

The source remains authoritative until the complete target has been validated.

## 3.12 Session persistence is transactional

Because target canonical session identity changes, session migration is designed as:

```text
1. Read source session.
2. Validate source session and complete migration eligibility.
3. Build complete target session in memory.
4. Validate target bank identity/signatures.
5. Write target temporary file.
6. Re-read and verify target temporary file.
7. Atomically install target canonical path.
8. Archive source session as migrated.
```

The source session is never deleted before verified target installation.

## 3.13 Source-session disposition

After successful target-session verification:

```text
source session -> migration archive/backup
new target session -> active canonical session
```

The old source session is removed from the ordinary resumable-session search surface so it is not repeatedly encountered as a bank mismatch.

Explicit approved migration occurs before ordinary mismatch/quarantine handling for that exact admitted revision.

## 3.14 Idempotence

Migration must be idempotent.

A deterministic migration identity is derived from exact revision authority, conceptually:

```text
migration_id = sha256(
    source_bank_content_fingerprint
    + target_bank_content_fingerprint
    + manifest_sha256
)
```

If the exact migration has already been applied:

```text
MIGRATION_ALREADY_APPLIED
    -> verified no-op
```

The system must not duplicate attempts, history, lineage receipts, sessions, or analytics evidence.

## 3.15 Crash recovery

Crash behavior is fail closed.

### Crash before verified target installation

Source remains authoritative.

### Verified target exists but source archival was interrupted

On restart:

```text
verified target
+ identical migration_id
    -> finish source archival/cleanup
```

### Conflicting target exists

```text
target exists
+ migration identity/content conflict
    -> FAIL CLOSED
    -> preserve both artifacts
    -> no automatic overwrite
```

## 3.16 Runtime does not perform semantic review

Runtime only verifies deterministic authority:

```text
manifest admitted?
exact bank identities?
exact question fingerprints?
exact edge/lineage present?
```

All semantic review occurs before runtime admission.

## 3.17 Section 3 terminal behavior

For an admitted revision:

```text
PROGRESS =
FULL CONTINUITY
+ TARGET ACTIVE FINGERPRINT
+ IMMUTABLE MIGRATION LINEAGE

HISTORY =
IMMUTABLE
+ EQUIVALENCE-AWARE JOIN

SMART PRACTICE / ANALYTICS =
OLD EVENTS MAY CONTRIBUTE THROUGH APPROVED LINEAGE

COMPLETED SESSION ANSWERS =
PRESERVED

PENDING SELECTION ON CHANGED QUESTION =
LOCAL RESET

SAVED SESSION BANK IDENTITY =
REBOUND TO TARGET
+ SIGNATURES REGENERATED

FAILED / INCOMPLETE REVISION =
EXISTING FAIL-CLOSED PATH
```

---

# Current design state

Sections 1-3 are approved design authority for the remainder of the brainstorming/specification process.

They are **not** implementation authority.

```text
SECTIONS_1_3_RECORDED = YES
SECTION_4_ADVERSARIAL_TEST_MATRIX = NOT_YET_RECORDED
FINAL_SPEC_COMPLETE = NO
IMPLEMENTATION_PLAN_AUTHORIZED = NO
IMPLEMENTATION_AUTHORIZED = NO
PRODUCTION_BANK_MUTATION_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
```

The next design section will define adversarial tests and proof obligations before the full specification is considered complete.