# 09 — Final bank activation plan

This section is a decision package. **Do not activate here.**

```text
FINAL_BANK_ACTIVATED = NO
DEFAULT_BANK_CHANGED = NO
ACTIVATION_TECHNICALLY_READY = YES
```

Technical readiness means the frozen 454-question bank is loadable, isolated from the launch bank, identity-safe, and covered by passing runtime tests. It is **not** authorization to change the default.

## Current launch bank

| Field | Value |
| --- | --- |
| Config authority | `cert_profile_sc900.json` → `runtime_bank` |
| Filename | `sc900_bank_v8_baseline.json` |
| Resolver | `cert_config.QUESTION_BANK_FILENAME` → `app.DEFAULT_BANK` |
| Path | repository root `sc900_bank_v8_baseline.json` (then resource dir fallback) |
| Question count | 8 |
| File SHA-256 | `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426` |
| Identity fingerprint | `a59a0c07132b8f31fea453d8d331f1bbc6415ddca5d2854365591928e69cda3a` |
| Release expected count | `tools/build_release.py` `EXPECTED_QUESTION_COUNT = 8` |
| Contract tests | `tests/test_sc900_contract.py` asserts filename + 8 questions |

## Frozen candidate (already in tree, not launched)

| Field | Value |
| --- | --- |
| Path | `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json` |
| File SHA-256 | `8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254` |
| Count | 454 |
| Identity fingerprint | `058053324cbf1928759b6e97147dd0e47000ec34ff93dcc25477f3c7909b4793` |

The engine already loads this file through explicit tests (`tests/test_sc900_final_bank_runtime.py`). Launch still uses the 8-question baseline.

## Required change to make 454 the normal launch bank

Preferred bounded switch (do **not** overwrite the baseline file in place):

1. Set `cert_profile_sc900.json` `runtime_bank` to `content/sc900/microsoft-learn-corpus/compiled/sc900_microsoft_learn_corpus_bank.json` **or** copy/publish that file to a dedicated launch filename and point `runtime_bank` at the copy.
2. Set `placeholder_bank_question_count` from `8` to `454`.
3. Set `tools/build_release.py` `EXPECTED_QUESTION_COUNT` from `8` to `454`.
4. Update `tests/test_sc900_contract.py` (filename, count, domain-balance assertions currently hardcoded to 8/2+2+2+2).
5. Update any bootstrap/release scripts that still assert `sc900_bank_v8_baseline.json` and count 8 (`.github/scripts/bootstrap_sc900_v8_current.py` and related).
6. Keep the 8-question baseline file in-tree as a historical fixture unless a later package explicitly retires it.
7. Do **not** bump engine feature work. Decide separately whether `engine_version` / app version should change; content epoch is not a field in `cert_profile_sc900.json`.

Do not copy 454 questions over `sc900_bank_v8_baseline.json` as the activation mechanism. That would change the historical baseline SHA and collapse two identities into one filename.

## Activation diff summary

| Surface | Before | After activation |
| --- | --- | --- |
| `DEFAULT_BANK` name | `sc900_bank_v8_baseline.json` | compiled corpus filename (or chosen launch copy) |
| Default file SHA | `60842eb…18a426` | `8fe229a…ec1a254` |
| `DEFAULT_BANK_CHANGED` | NO | YES |
| `FINAL_BANK_ACTIVATED` | NO | YES |
| Launch question count | 8 | 454 |
| Identity fingerprint | `a59a0c07…9cda3a` | `05805332…9b4793` |
| Session/progress file stem | `sc900_bank_v8_baseline` | `sc900_microsoft_learn_corpus_bank` (if using compiled path) |

## Migration impact

Learner state is namespaced by `runtime_bank_stem(bank_path)` in `session_store.py`:

- progress: `{stem}_progress.json`
- sessions: `{stem}_{mode}_session_{count}_{signature}.json`
- checkpoints: `{stem}_{mode}_checkpoint_{n}.json`

Changing the launch filename stem **isolates** old 8-question progress/sessions. They are not silently replayed onto the 454-question bank.

Canonical sessions also bind `bank_fingerprint`. Restore fails closed if the fingerprint does not match (`session_store` raises on missing/mismatched `bank_fingerprint`).

`question_identity.migrate_progress_content_epoch` rebinds canonical progress when the **same** progress document is loaded against a bank whose per-question content fingerprints changed. Switching launch files uses a new stem, so the 8-question progress file is not auto-migrated into the 454-question namespace. That is the desired isolation.

If an operator previously loaded the candidate bank explicitly, those sessions already use the corpus stem and the 454 fingerprint. Activation would start using that same namespace as the default.

## Content epoch

There is no `content_epoch` key in `cert_profile_sc900.json`. Epoch handling is per progress document (`progress_content_epoch_version` inside canonical progress). Activation of a different file stem does **not** by itself increment a global content epoch. It starts a new progress namespace. Explicit epoch migration applies only if the same progress file is rebound to mutated question content.

## Learner-state and session restore

| Scenario | Expected behavior after activation |
| --- | --- |
| Fresh install | Loads 454-question default bank |
| Fresh learner | New progress file under the new stem |
| Existing 8-question progress | Remains under `sc900_bank_v8_baseline_progress.json`; not the new default |
| Resume 8-question session | Only if that bank file is opened explicitly; default launch will not see it |
| Resume 454-question explicit-load session | Eligible if fingerprint and IDs match |
| Builder isolation | Unchanged (BACKLOG-3); builder fingerprint still suffixes canonical session names |

## Tests required before activation (future package)

- Update and pass `tests/test_sc900_contract.py`
- Re-run `tests/test_sc900_final_bank_runtime.py`
- BACKLOG-1/2/3, Gate-3 CAND, Microsoft corpus
- Full `python -m unittest discover -s tests`
- `python -m tools.lint_bank` against the new default (expect 454; decide whether the Q394–Q399 C-streak warning is allowed at launch)
- `python -m tools.run_quality_checks`
- `python -m tools.verify_installation`
- Fresh-install / fresh-learner / resume smoke as in `docs/research/SC900-FINAL-STABILIZATION-001/`

## Rollback

1. Restore `cert_profile_sc900.json` `runtime_bank` to `sc900_bank_v8_baseline.json`.
2. Restore `placeholder_bank_question_count` and `EXPECTED_QUESTION_COUNT` to 8.
3. Restore contract tests.
4. Default SHA returns to `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`.
5. 8-question learner files are still on disk if they existed; 454-question files remain as a separate stem.

Do not delete the compiled 454 bank during rollback.

## Authorization boundary

```text
ACTIVATION_TECHNICALLY_READY = YES
FINAL_BANK_ACTIVATED = NO
```

A later operator package must perform the config/contract switch. Publication of PRs #10–#24 can complete with the default bank still the 8-question baseline.
