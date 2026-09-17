# SC-900 Answer-Length Leakage Repair — Learner-History Compatibility Gate

**Work ID:** `SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / TRANCHE1`  
**Authoritative main base:** `23d440b6976b9f6bbb3b77285bf0d11effc2513f`  
**Compatibility verification SHA:** `959b5d11bc61a739be58413fd518218f172d0b0a`  
**GitHub Actions run:** `35219697551`  
**Job:** `105196517489`  
**Result:** PASS — the tests prove the existing architecture fails closed on wording-only durable-content changes.

## Disposition

```text
LEARNER_HISTORY_COMPATIBILITY = BLOCKED_BY_CHANGED_CONTENT_QUARANTINE
TRANCHE1_CONTENT_REWRITE_AUTHORIZED = NO
NEW_IDENTITY_OR_MIGRATION_ARCHITECTURE_AUTHORIZED = NO
CONTENT_REWRITE_EXECUTED = NO
PRODUCTION_BANK_CHANGED = NO
```

This is an intentional safety stop, not a test failure.

## What was tested

`tests/test_answer_length_history_compatibility.py` characterizes the exact current identity contract without modifying `question_identity.py`, `session_store.py`, `runtime_persistence.py`, or production bank content.

### 1. Unchanged durable content preserves bound progress

A canonical progress payload bound to a question and its content fingerprint was migrated against an unchanged copy of that question.

Observed:

```text
MIGRATION_CHANGED = NO
PRIOR_PROGRESS_PRESERVED = YES
QUESTION_QUARANTINED = NO
```

### 2. Wording-only answer-choice edit changes durable content identity

The test preserves:

- canonical question ID;
- correct-answer key;
- objective code;
- calibration tier;
- exam eligibility;
- prompt and other metadata.

It changes only one distractor from `four` to `a more realistic distractor`.

Observed:

```text
QUESTION_ID_CHANGED = NO
MECHANICAL_BANK_INVARIANTS = PASS
QUESTION_CONTENT_FINGERPRINT_CHANGED = YES
PROGRESS_EPOCH_MIGRATION_CHANGED = YES
PRIOR_PROGRESS_PRESERVED_ON_ACTIVE_RECORD = NO
QUARANTINE_REASON = CHANGED_CONTENT
```

The previous learner record is removed from the active `questions` mapping and placed under `quarantined_questions[question_id]` with reason `CHANGED_CONTENT`.

### 3. Wording-only edit invalidates canonical saved-session bank identity

A canonical saved session was created against the original bank fingerprint. The same canonical question ID was then evaluated against the revised wording.

Observed:

```text
OLD_BANK_FINGERPRINT_EQUALS_NEW_BANK_FINGERPRINT = NO
SAVED_SESSION_MATCHES_REVISED_BANK = NO
LEGACY_BYPASS_USED = NO
```

The current saved-session contract requires bank fingerprint agreement; the content revision therefore does not silently resume an old canonical session against changed durable content.

### 4. Mechanical invariant safety is insufficient by itself

The new `compare_bank_invariants` guard reports no ID/key/objective/tier/eligibility drift for the wording-only revision, while the learner-history epoch correctly quarantines the prior learner state.

Therefore both statements are simultaneously true:

```text
BANK_MECHANICAL_INVARIANTS = PASS
LEARNER_HISTORY_COMPATIBILITY_FOR_WORDING_REVISION = FAIL_CLOSED
```

This proves why Tranche 1 cannot safely proceed merely because canonical IDs remain stable.

## Verification evidence

At exact verification SHA `959b5d11bc61a739be58413fd518218f172d0b0a`:

| Gate | Result |
| --- | --- |
| Answer-length audit tests | 7 PASS |
| Bank revision guard tests | 18 PASS |
| Learner-history compatibility tests | 4 PASS |
| Existing BACKLOG-1 progress + Segment-3 + final-bank activation regressions | 55 run / 54 PASS / 1 display-dependent Tk skip |
| Production bank lint | PASS — 454 questions, 1 governed frozen warning, 0 unexpected warnings |
| Installation verification | PASS |
| Production bank SHA-256 | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |

The one skip is `test_application_starts_with_final_bank_and_leaves_baseline_progress_untouched`, skipped because the Linux runner has no Tk display. The non-GUI activation/session identity tests passed.

Existing identity regressions independently continue to prove that changed durable content must not inherit prior progress/history.

## Safety conclusion

The existing architecture does **not** contain an approved mechanism for treating a deliberate wording revision as history-compatible while retaining the current content-fingerprint safety boundary.

Proceeding to the planned 40-60-question content rewrite would knowingly cause the edited questions' prior learner progress/history to be quarantined and existing canonical sessions to fail bank-fingerprint matching. The approved Tranche 1 plan explicitly prohibits weakening or inventing identity/migration semantics inside this package.

Therefore Tasks 5-7 of the conditional content-rewrite portion are not executed.

## Required separate operator decision before content rewriting

A later package must choose and explicitly govern one of these approaches:

1. **Accept deliberate learner-state reset/quarantine for reworded questions.** The current safety architecture remains unchanged; affected question history is intentionally not inherited across the content revision.
2. **Design a separate content-revision migration contract.** Such a design would need an explicit reviewed equivalence/admission mechanism capable of distinguishing authorized meaning-preserving wording changes from substantive content changes without weakening fail-closed identity behavior.

No choice is made by this package.

## Terminal state

```text
AUDIT_TOOLING = PASS
BASELINE_AUDIT = PASS / REPRODUCIBLE
BASELINE_ANALYZABLE = 449
BASELINE_STRICT_LONGEST = 291/449 = 64.8106904232%
BASELINE_UNIQUE_LONGEST_HEURISTIC = 291/431 = 67.5174013921%
HISTORY_COMPATIBILITY = BLOCKED_BY_CHANGED_CONTENT_QUARANTINE
CONTENT_REWRITE_EXECUTED = NO
TRANCHE1_EDITED_QUESTIONS = 0
CANDIDATE_BANK_SHA256 = N/A
PRODUCTION_BANK_SHA256 = 177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c
PR13_MODIFIED = NO
RECOVERY_REFS_MODIFIED = NO
PRODUCTION_EXE_CHANGED = NO
MERGE_AUTHORIZED = NO
```
