# 09 — Pre-Day-1 measurement-integrity repair

## Disposition

```text
REPOSITORY_MEASUREMENT_INTEGRITY_REPAIR = VERIFIED
PROTOCOL_VERSION = cand01r3-measurement-001-v2
PROTOCOL_SHA256 = 51dbee61e2a7d0c23ad48e7f37799812bd67918e37aacd1b60e3600787365c72
SCIENTIFIC_PROTOCOL_CHANGED = NO
FROZEN_COMPILED_ANSWER_KEY_AUTHORITY = VERIFIED
MUTABLE_RUNTIME_ANSWER_KEY_AUTHORITY = PROHIBITED
DUPLICATE_SCORER_DEFINITIONS = 0
TEMPORARY_SELF_MUTATING_CI = REMOVED
TEMPORARY_REPAIR_INFRASTRUCTURE = REMOVED
FINAL_MEASUREMENT_ADVERSARIAL_SWEEP = CLEAR
PRODUCTION_LEDGER = UNVERIFIED_AUTHORIZED_MACHINE_OFFLINE
READY_FOR_DAY1 = NO
DAY1_STARTED = NO
EMPIRICAL_RESULT = NOT_YET_AVAILABLE
EMPIRICAL_WINNER_DECLARED = NO
DEPLOYMENT_AUTHORIZED = NO
```

`READY_FOR_DAY1` remains `NO` solely because the required check of the authorized application's production empirical ledger could not be performed: the authorized desktop was offline during terminal verification. Committed pre-run artifacts still declare zero real observations, but committed JSON is not substituted for production-ledger evidence.

## Repair history

The second-pass adversarial review originally produced 40 RED integrity regressions. Commit `708dd89a5e3124e1e3d592c1d7ab47d2ef29152b` implemented the first measurement-integrity repair and produced the initial 40/40 GREEN result.

A subsequent canonical regression, R2-041 `measurement_score_uses_frozen_compiled_answer_key`, deliberately tampered with the runtime question's `correct` field and demonstrated that measurement scoring must remain bound to the frozen compiled candidate bank. R2-041 was RED when mutable runtime answer authority was used.

Commit `3eb06a95a8b530d4ff5be78ac203e2e67896e898` established the known-good frozen answer-key repair. The authoritative scorer verifies the normalized compiled-bank SHA-256, requires `72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b`, resolves the canonical `question_id` in that artifact, obtains `correct` from the frozen row, and fails closed on authority/hash defects.

The temporary workflow `.github/workflows/verify-cand01r3-measurement-integrity.yml` later became self-mutating: it had write permission and executed repair helpers that modified, committed, and pushed implementation/test files. Source-inventory checkpoint `2a3f7f06c0cfafc58807b0fa22a8b47c5c986d43` only added inventory intent, but bot commit `2b17991830d87a31be5539c123f9343c625d2341` reintroduced a later duplicate scorer that trusted `question.get("correct")`. Because the later definition overrode the earlier frozen-authority scorer, R2-041 failed while R2-001 through R2-040 still passed.

The continuation repaired forward from `2b179918...`; it did not reset away valid later work. The canonical scorer semantics were restored, a structural regression was added to require exactly one effective scorer and recorder definition, the self-mutating workflow was removed, and permanent CI was replaced with `.github/workflows/verify-cand01r3-pre-day1-readonly.yml`, which checks the exact pushed SHA with `contents: read` and no commit/push path.

The temporary patch/bootstrap helpers were classified as repair infrastructure and removed:

- `tools/prepare_cand01r3_integrity_repair.py`
- `tools/apply_cand01r3_measurement_integrity_repair.py`
- `tools/apply_cand01r3_answer_key_repair.py`
- `tools/strengthen_cand01r3_r2_tests.py`

A temporary one-shot formatting workflow was used only after a repository-standard quality gate exposed formatting/type defects. It ran the complete pre-write test/quality gate, failed closed if the branch moved, committed only the two proven source changes, and deleted itself in the same commit. It does not remain in the terminal tree.

## Calendar-aware R1 fixture correction

The production calendar guard correctly forbids starting Day N before `Day1 + (N-1)` calendar days. Four R1 tests had historically simulated Days 1–6 within one wall-clock date, so the newly enforced calendar contract made those fixtures invalid. The production guard was not weakened. The original 30 R1 cases were preserved and executed through a controlled test clock that advances one local date per scheduled day.

## Final source verification results

The final repaired source content was exercised before commit and again through the read-only verification chain. Observed source-verification results are:

| Gate | Result |
| --- | --- |
| structural scorer uniqueness | 1/1 PASS |
| R2 measurement integrity | 41/41 PASS |
| R2-041 | PASS |
| R1 runtime/resume | 30/30 PASS |
| protocol-v2 regression | 20/20 PASS |
| all CAND-01R3 tests | 187/187 PASS |
| Phase-3 regression | 79/79 PASS |
| full unittest suite | 783 run / 0 failures / 0 errors / 230 skipped |
| Ruff | PASS |
| Black `--check` | PASS |
| MyPy | PASS |

The permanent read-only verifier additionally runs `lint_bank`, `verify_installation`, all three deterministic Phase-3 verifiers, frozen hash/protocol proofs, protected-ref proofs, the adversarial source inventory, and clean-tree checks before and after testing. These are terminal acceptance gates and must remain green on the documentation head.

## All-path adversarial sweep

A fresh source-assisted sweep covered the measurement scoring/recording path, application answer path, render path, persistence/restore, export/analytics custody, navigation/redo/retry/flag/suspend behavior, day transition, ledger replay, contamination replay, and UNOBSERVED handling.

The sweep found no alternate path that can legitimately:

- score a PROBE from mutable runtime answer authority;
- reveal a PROBE answer, correctness signal, keyed option, or explanation;
- route a PROBE through ordinary learner/training-state mutation;
- create a second PRIMARY observation by retry/redo;
- reverse UNOBSERVED terminality or bypass contamination;
- silently accept malformed empirical evidence;
- admit future-day or past-day PROBEs or reorder the frozen day's schedule;
- bypass TRAIN completion or calendar timing;
- restore stale measurement state as valid current state; or
- export selected options/correctness to the learner.

The application answer path uses the dedicated measurement recorder instead of ordinary progress recording. Measurement rendering suppresses correctness and explanations. Correctness-dependent auto-next is suppressed. REDO is prohibited; retry cannot mint another PRIMARY; FLAG and SUSPEND are non-terminal. Measurement persistence/export sanitizes or redacts answer state. Ledger replay preserves mutually exclusive PRIMARY / UNOBSERVED / CONTAMINATED terminal states and fails closed on malformed evidence. The today-only scheduled PROBE pool and frozen within-day order remain enforced.

Therefore:

```text
MEASUREMENT_SPECIFIC_ANSWER_PATH = VERIFIED
NORMAL_LEARNING_STATE_MUTATION_FROM_PROBE = PROHIBITED
PROBE_CORRECTNESS_FEEDBACK = SUPPRESSED
PROBE_EXPLANATION_REVEAL = SUPPRESSED
PROBE_REDO = PROHIBITED
PROBE_RETRY_PRIMARY = PROHIBITED
UNOBSERVED_TERMINALITY = VERIFIED
MUTUALLY_EXCLUSIVE_TERMINAL_STATES = VERIFIED
LEDGER_CORRUPTION = FAIL_CLOSED
STRICT_BOOLEAN_SCORE = VERIFIED
CALENDAR_DAY_ENFORCEMENT = VERIFIED
PROBE_ANALYTICS_CUSTODY = VERIFIED
POST_HOC_CONTAMINATION_REPLAY = VERIFIED
MEASUREMENT_POOL_TODAY_ONLY = VERIFIED
RESTART_RESUME = VERIFIED
TRAIN_EXPOSURE_PERSISTENCE = VERIFIED
DAY7_HANDOFF = VERIFIED
FINAL_MEASUREMENT_ADVERSARIAL_SWEEP = CLEAR
```

## Frozen scientific authority

Unchanged authority:

```text
PRIMARY_ENDPOINT = 7-day first-attempt correctness on CLEAN HELD-OUT SC-900 PROBE items
TRAIN = 171
PROBE = 29
INDEPENDENT_PROBE_FAMILIES = 7
PRIMARY_DAILY_TRAIN_BUDGET = 20
SMART_PRACTICE_PRIMARY_TOTAL = 60
RRC1_PRIMARY_TOTAL = 60
PRIMARY_EXPOSURE_DIFFERENCE = 0
DAY7 = 10 SMART_PRACTICE + 10 RRC_1 + 5 PROBE
EMPIRICAL_RESULT = NOT_YET_AVAILABLE
DEPLOYMENT_AUTHORIZED = NO
```

Frozen artifact hashes:

```text
TASK4_SEMANTIC_AUDIT_SHA256 = e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701
TASK5_REVIEWED_STORE_SHA256 = 2cc71208fe16b057b88cd06f841b94cb10b57176668af9adf838917795fe7f3c
TASK5_COMPILED_SHA256 = 72051418687f76d67087ff8d3a37ee626b23c8d58ee98d33dfab132f19057f2b
TASK6_MANIFEST_SHA256 = 67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90
DEFAULT_LAUNCH_BANK_SHA256 = 60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426
```

Protected authority remains:

```text
recovery/publish-exact-history/sc900-v8-20260910 = b567d4b74a2f99e50022dd0dafd81ffa75dff0a2
recovery/publish-sc900-v8-exact-history = bbc3bd900b73bde89151dc51706ad62fc69e8196
sc900-v8.0.0-baseline tag object = 9c80be5b20e652dc2eb86621dfdf7c32baa06528
```

No protected ref was intentionally mutated by this continuation.

## Production empirical ledger

The required production evidence is the actual authorized application's runtime user-data ledger for `cand01r3-measurement-001.jsonl`. The authorized desktop was offline when this receipt was finalized. The committed protocol artifact still reports `REAL_OBSERVATIONS = 0`, `EMPIRICAL_RESULT = NOT_YET_AVAILABLE`, and `DEPLOYMENT_AUTHORIZED = NO`, and this continuation did not start Day 1 or create an empirical observation.

However, committed repository state is not accepted as a substitute for the required runtime ledger proof. Therefore:

```text
PRODUCTION_LEDGER_STATUS = UNVERIFIED_AUTHORIZED_MACHINE_OFFLINE
REAL_OBSERVATIONS_PRODUCTION_PROOF = UNAVAILABLE
DAY1_START_ACTION_PERFORMED = NO
EMPIRICAL_WINNER_DECLARED = NO
READY_FOR_DAY1 = NO
```

When the authorized machine is available, the production ledger must be checked directly before `READY_FOR_DAY1` can be reconsidered. No protocol change is authorized by that check.
