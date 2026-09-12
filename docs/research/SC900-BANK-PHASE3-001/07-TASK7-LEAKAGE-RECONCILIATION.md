# SC900-BANK-PHASE3-001 — Task 7 All-Path Leakage Reconciliation

```text
TASK_7_LEAKAGE_RECONCILIATION = FROZEN
ALL_KNOWN_QUESTION_PATHS_RECONCILED = YES
NEWLY_DISCOVERED_PATHS_DOCUMENTED = YES
IMPLEMENTATION_READY_EXCLUSION_CONTRACT = FROZEN
FAIL_CLOSED_SEMANTICS = FROZEN
FUTURE_PATH_TEST_MATRIX = COMPLETE
RUNTIME_GUARDS_IMPLEMENTED = NO
RUNTIME_CONSUMER_COUNT = 0
RUNTIME_CONSUMER_AUTHORIZED = NO
GATE2_REOPENED = NO
```

WORK_BRANCH = `implementation/sc900-reviewed-bank-phase3`
TASK_6_ACCEPTED_HEAD = `f2c9a04d109de1d5d91e3fd32d9e39568f3828c1`
SUPERSEDES_FOR_PHASE3 = `docs/research/SC900-ENGINE-RDAF-CAND01-GATE2-001/05-probe-leakage-audit.md`
DOES_NOT_OVERWRITE = original Gate-2 file `05-probe-leakage-audit.md`

This receipt carries Gate-2 leakage design forward against the now-real Phase-3 bank and Task-6 TRAIN/PROBE partition. It does **not** implement runtime guards, consume the manifest from runtime, reopen Gate 2, or authorize implementation.

Gate 2 evaluates whether the all-path guard design, fail-closed semantics, and future verification matrix are implementation-ready. Runtime enforcement belongs to Gate 3 or later. Absence of implemented TRAIN/PROBE guards is not itself a Gate-2 failure.

## Motto applied

«Доверяй, но проверяй.» Trust, but verify.

The original Gate-2 inventory was treated as a hypothesis, not as a complete map. Current source was re-inspected. Historical line numbers were re-verified; several remain valid, several have shifted, and additional paths were found. Documented design is not an implemented guard. Absence of observed leakage is not proof of no leakage, because the 200-question candidate bank is not the launch bank and no runtime consumer exists.

## Frozen Phase-3 evidence this contract protects

```text
APPROVED_QUESTIONS = 200
COMPILED_QUESTIONS = 200
SEMANTIC_FAMILIES = 27
UNRESOLVED_SEMANTIC_FAMILIES = 0
TRAIN_QUESTIONS = 171
PROBE_QUESTIONS = 29
UNASSIGNED_QUESTIONS = 0
TRAIN_FAMILIES = 20
PROBE_FAMILIES = 7
EFFECTIVE_INDEPENDENT_PROBE_UNITS = 7
FAMILY_SPLITS = 0
TRANSFER_EDGE_CROSSINGS = 0
```

PROBE families: `shared_responsibility_model`, `zero_trust_and_identity_perimeter`, `multifactor_authentication`, `privileged_identity_management`, `entra_roles_rbac`, `azure_key_vault`, `purview_portal`.

29 PROBE questions belong to 7 independent semantic families. They are not 29 independent measurements.

Manifest SHA-256: `67c8f0e83d7c7c52af323fde6a30ef35e2642045b0fbc04d5ba510a2c912ca90`  
Semantic-audit SHA-256: `e23fec15f148e50640d6851d192f4d17dca5d4f1b8c85b32f0e81eeb00059701`

This is a design-time partition only.

## Method

Current-repository search covered selectors, injectors, caches, renderers, persistence, analytics, import/export, compilers, debug editors, and tests/fixtures. Original Gate-2 files `04`–`14` and Task-4/5/6 receipts were loaded first. Runtime files were not assumed partition-aware because Task 6 recorded `RUNTIME_CONSUMER_COUNT = 0`.

Search confirmed that `content/sc900/phase3/train_probe_manifest.json` is referenced only by design-time builder/validator, Task-6 tests, and research/plan documents. No Smart Practice, session builder, question flow, renderer, history, analytics, importer, exporter, or restore path consumes it.

## Central exclusion contract

Future implementation must provide one shared eligibility boundary. Every path in this inventory must call it before constructing a candidate, ranking a pool, caching a payload, injecting a follow-up, rendering protected material, persisting answer/stem text, restoring a session, or exporting derived content. Guarding only the final displayed question is insufficient.

Conceptual contract:

```text
partition_eligibility(item_id, intended_use, manifest, audit) ->
    TRAIN | PROBE | NOT_ELIGIBLE
```

Authority sources, in order:

1. Task-6 TRAIN/PROBE manifest, hash-bound to the Task-5 store and Task-4 semantic audit;
2. Task-4 family identity (whole family, one role);
3. approval/review status from the reviewed store;
4. probe-eligibility flags already frozen in the store.

Intended use:

| Intended use | May consume | Must reject |
| --- | --- | --- |
| `TRAINING` | `TRAIN` only | `PROBE`, `UNASSIGNED`, `UNKNOWN`, `MISSING_ROLE`, `MALFORMED_ROLE`, `MISSING_MANIFEST`, `HASH_MISMATCH`, `UNRESOLVED_FAMILY`, `UNAPPROVED_ITEM` |
| `MEASUREMENT` | `PROBE` only, and only under clean first-attempt measurement conditions | prior exposure, prior answer reveal, prior explanation reveal, contamination, duplicate scored attempt, invalid timing, invalid persistence identity, missing role, manifest mismatch, family mismatch, unapproved item, `train_only` |

`RESTORE` / `IMPORT` / `CACHE` paths must not bypass role authority. Restored eligibility is recomputed from current manifest + current item identity, not copied from the saved session’s implied pool.

`ANALYTICS` / `EXPORT` / `HISTORY` paths must not reveal protected PROBE stem, answer, explanation, or semantically equivalent proposition in a way that contaminates later measurement. Derived recommendations that name or paraphrase a PROBE answer are contamination.

Family and transfer rules:

```text
ONE_FAMILY_ONE_ROLE = REQUIRED
NO_TRAIN_PROBE_FAMILY_SPLIT = REQUIRED
NO_TRAIN_PROBE_TRANSFER_EDGE_CROSSING = REQUIRED
PROBE_REQUIRES_APPROVED_RESOLVED_ELIGIBLE = REQUIRED
TRAIN_REQUIRES_APPROVED_RESOLVED = REQUIRED
```

TRAINING paths must reject an entire family if any member is PROBE. MEASUREMENT paths must reject an entire family if any member is TRAIN. Semantic-family-equivalent items and Task-4 transfer-edge-connected items are the same contamination unit.

## Fail-closed rule

Missing or malformed partition authority must never default to TRAIN eligibility.

```text
missing role            -> NOT_ELIGIBLE
unknown role            -> NOT_ELIGIBLE
malformed role          -> NOT_ELIGIBLE
manifest hash mismatch  -> NOT_ELIGIBLE
question absent         -> NOT_ELIGIBLE
unresolved family       -> NOT_ELIGIBLE
unknown family          -> NOT_ELIGIBLE
nonapproved item        -> NOT_ELIGIBLE
probe-ineligible item   -> NOT_ELIGIBLE FOR PROBE
UNASSIGNED              -> NOT_ELIGIBLE
```

Do not design permissive fallback such as “treat unknown as TRAIN,” “use the launch bank if the manifest is missing,” or “include PROBE when the TRAIN pool is empty.” Empty TRAIN pool is a valid fail-closed outcome.

## Cache / prewarm rule

A future runtime guard cannot merely filter the last displayed question if caches, recommendations, rankings, signal payloads, related-item candidates, or prewarmed pools were already computed using PROBE information.

Required contract:

1. Role-safe candidate construction happens **before** derived training state is created.
2. Smart Practice signal payloads, value rankings, concept-graph neighborhoods, interference maps, and prewarmed pools may be built only from TRAIN-eligible items.
3. Follow-up candidate indexes may index only TRAIN-eligible items for training sessions.
4. If derived state already incorporates protected PROBE information, that state is `CONTAMINATED` unless a later implementation proves that no protected stem, answer, explanation, or answer-signal escaped.
5. Cache invalidation after role-authority load is mandatory; stale prewarm is not a bypass.

## Answer / stem custody

Exposure is broader than rendering the exact question ID.

Contamination-relevant exposure includes, where materially revealing:

- exact stem / prompt;
- correct answer letter or text;
- explanation or answer rationale;
- choice-specific explanations;
- semantic-family-equivalent item;
- Task-4 transfer-edge-connected content;
- analytics or recommendation text that reveals the answer or proposition;
- history rows storing `selected_texts` / `correct_texts`;
- screenshot-review or issue-review editors that display or mutate stem/answer/explanation.

Hiding a question ID does not preserve holdout if the proposition is taught or revealed by a co-family item, a related follow-up, or derived text.

## Path-class legend

| PATH_CLASS | Meaning |
| --- | --- |
| `TRAINING_SELECTION` | Builds or starts a practice/review/smart pool |
| `TRAINING_INJECTION` | Inserts additional items into an active session |
| `DERIVED_STATE` | Ranks, caches, indexes, or recommends using question material |
| `RENDER` | Shows stem, choices, answers, or explanations |
| `PERSISTENCE` | Stores or restores progress/session/history |
| `ANALYTICS_EXPORT` | Dashboard, derived rows, or file export |
| `IMPORT_COMPILE` | Ingestion, compile, rebuild, or bank load |
| `DEBUG_EDITOR` | Human review/debug surfaces that can reveal or mutate content |
| `FIXTURE_TEST` | Tests/fixtures that load full question material |
| `DESIGN_TIME` | Phase-3 partition/build tools; not a runtime consumer |

`CURRENT_PARTITION_AWARENESS` is `NONE` unless noted. Design-time tools are `DESIGN_TIME_ONLY`. Two paths are conceptually misnamed “probe” and are training paths unless later reclassified.

`TASK7_DISPOSITION` for every runtime path:

`CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

## Summary inventory

Original Gate-2 paths were re-verified. Newly discovered paths are marked `NEW`.

| PATH_ID | Path | PATH_CLASS | Current location | NEW |
| --- | --- | --- | --- | --- |
| P01 | Normal practice builder | `TRAINING_SELECTION` | `app_session_builder_mixin.py` `start_custom_session` / `get_session_builder_pool` | |
| P02 | Smart Practice initial selection | `TRAINING_SELECTION` | `build_smart_practice_pool`; `smart_practice_core.build_smart_practice_selection` | |
| P03 | Smart Practice signal payload | `DERIVED_STATE` | `_build_smart_practice_signal_payload` | NEW |
| P04 | Smart Practice prewarm/cache | `DERIVED_STATE` | `schedule_smart_practice_prewarm`; `smart_practice_cache.SmartPracticePrewarmService`; `app.py` `invalidate_learning_state` | |
| P05 | Smart Practice detached worker | `DERIVED_STATE` | `smart_practice_worker.build_detached_signal_payload` / `build_detached_pool` | NEW |
| P06 | Due-review path | `TRAINING_SELECTION` | `build_due_review_pool`; `progress_store.select_due_review_questions` | |
| P07 | Weak/retest path | `TRAINING_SELECTION` | `build_weak_retest_pool` | |
| P08 | Full-bank restore | `TRAINING_SELECTION` | `restore_full_bank`; `app.py` `restore_progress_manual` | |
| P09 | Session start from pool | `TRAINING_SELECTION` | `app_session_persistence_mixin.start_session_from_pool` | NEW |
| P10 | Twins | `TRAINING_INJECTION` | `find_question_twins` / `maybe_queue_question_twins` | |
| P11 | Delayed-recall follow-up | `TRAINING_INJECTION` | `maybe_queue_delayed_recall_probe` | |
| P12 | Memory ramp | `TRAINING_INJECTION` | `find_memory_ramp_candidates` / `maybe_queue_memory_ramp` | |
| P13 | Wrong-answer memory | `TRAINING_INJECTION` | `find_wrong_answer_memory_candidates` / `maybe_queue_wrong_answer_memory` | |
| P14 | Confusion-pair drill | `TRAINING_INJECTION` | `find_confusion_pair_candidates` / `maybe_queue_confusion_pair_drill` | |
| P15 | Streak rescue | `TRAINING_INJECTION` | `maybe_trigger_streak_rescue` | |
| P16 | Misconception repair | `TRAINING_INJECTION` | `plan_misconception_repair` | |
| P17 | Follow-up candidate index | `DERIVED_STATE` | `_rebuild_followup_candidate_index` | NEW |
| P18 | Boss rounds | `TRAINING_INJECTION` | `app_game_mixin.maybe_trigger_boss_round` | |
| P19 | Stealth checkpoints | `TRAINING_INJECTION` | `maybe_trigger_stealth_checkpoint` | |
| P20 | Question list / jump | `RENDER` | `refresh_question_list`; `jump_to_question`; `on_listbox_select` | NEW |
| P21 | Normal answer rendering | `RENDER` | `app_question_render_mixin.render_question` / `_render_choice_rows` | |
| P22 | Explanation reveal | `RENDER` | `_inline_explanation_for_question`; `complete_explanation_recall`; `app.py` `render_general_explanation` | |
| P23 | Choice-explanation formatter | `RENDER` | `format_choice_explanations` | NEW |
| P24 | Adaptive explanation text | `RENDER` | `app.py` `adaptive_explanation_text` | NEW |
| P25 | History persistence | `PERSISTENCE` | `app.py` `append_answer_history`; `progress_store.append_progress_history` | |
| P26 | Progress save/backup | `PERSISTENCE` | `save_progress`; `backup_progress_manual`; `auto_backup_progress` | NEW |
| P27 | Progress restore/import | `PERSISTENCE` | `restore_progress_manual`; `load_progress_if_present` | |
| P28 | Session snapshot restore | `PERSISTENCE` | `load_session_if_present`; `session_store.build_session_snapshot` | NEW |
| P29 | Analytics dashboard | `ANALYTICS_EXPORT` | `compute_analytics`; `open_analytics_window`; `_build_analytics_payload` | |
| P30 | Analytics “delayed probe” rows | `DERIVED_STATE` | `_build_delayed_probe_rows` | NEW |
| P31 | Analytics export | `ANALYTICS_EXPORT` | `export_analytics_json` | |
| P32 | Smart Practice measurement report | `ANALYTICS_EXPORT` | `generate_smart_practice_measurement_report`; `smart_practice_measurement.build_measurement_report` | NEW |
| P33 | Analytics recommendations | `ANALYTICS_EXPORT` | `analytics_recommendations.build_analytics_recommendations` | NEW |
| P34 | Bank open/reload | `IMPORT_COMPILE` | `app.py` `open_bank` / `reload_bank` / `load_from_path`; `question_bank.load_bank` | NEW |
| P35 | Question-bank import | `IMPORT_COMPILE` | `ingestion/importer.import_jsonl`; `tools/import_sc900_content.py` | |
| P36 | Question-bank compile | `IMPORT_COMPILE` | `ingestion/importer.compile_question_bank` | |
| P37 | Candidate-bank rebuild | `DESIGN_TIME` | `tools/build_sc900_phase3.py` | NEW |
| P38 | Extraction pipeline | `IMPORT_COMPILE` | `extraction/pipeline.py`; `extraction/parse.py` | NEW |
| P39 | Screenshot-review editor | `DEBUG_EDITOR` | `open_screenshot_review_window`; `_update_bank_question_fields` | NEW |
| P40 | Issue review | `DEBUG_EDITOR` | `open_issue_review_window`; `_render_issue_review_detail` | NEW |
| P41 | Redo / retry | `PERSISTENCE` | `redo_question` | NEW |
| P42 | Tests / fixtures | `FIXTURE_TEST` | `tests/test_sc900_engine_regression.py` and related fixtures | |
| P43 | Design-time TRAIN/PROBE manifest | `DESIGN_TIME` | `content/sc900/phase3/train_probe_manifest.json` | NEW |
| P44 | Exam-mode rendering | `RENDER` | `render_question` with `exam_reveal` | NEW |
| P45 | Progress directory recovery | `PERSISTENCE` | `app.py` progress-file strength recovery | NEW |
| P46 | Bank lint/clean/validate tools | `IMPORT_COMPILE` | `tools/clean_bank.py`; `tools/validate_bank.py`; `tools/lint_bank.py` | NEW |
| P47 | Concept-graph prerequisite path | `DERIVED_STATE` | `smart_practice_concept_graph.select_prerequisite_path` | NEW |
| P48 | Question-material export surfaces | `ANALYTICS_EXPORT` | No dedicated learner-facing question exporter; compile/analytics/progress JSON are the write surfaces | NEW |

No dedicated UI “question export” command exists in `app.py`. Question material can still leave the process through compiled banks, analytics JSON, progress/history JSON, screenshot-review saves, and test fixtures.

## Detailed path records

Common future tests for every path are listed once in [Future verification matrix](#future-verification-matrix). Each record names the additional obligation unique to that path.

### P01 — Normal practice builder

- CURRENT_SOURCE_LOCATION: `app_session_builder_mixin.start_custom_session` (non-Smart-Practice branch), `get_session_builder_pool`, `get_filtered_master_pool`, `filter_pool_by_session_source`
- QUESTION_MATERIAL_TOUCHED: full runtime questions from `master_questions`
- CAN_SELECT_QUESTION = YES
- CAN_REVEAL_STEM = YES (once `start_session_from_pool` renders)
- CAN_REVEAL_ANSWER = YES (after submit)
- CAN_REVEAL_EXPLANATION = YES
- CAN_PERSIST_CONTENT = YES (via history after answers)
- CAN_RESTORE_CONTENT = NO (selection only)
- CURRENT_PARTITION_AWARENESS = NONE
- REQUIRED_FUTURE_GUARD: filter builder pool to TRAIN before count/sample/interleave
- FAIL_CLOSED_BEHAVIOR: empty TRAIN pool blocks session start; do not refill from PROBE
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P02 — Smart Practice initial selection

- CURRENT_SOURCE_LOCATION: `build_smart_practice_pool`; nested `build_candidate` / `final_selection`; `smart_practice_core.build_smart_practice_selection`
- QUESTION_MATERIAL_TOUCHED: candidate utility, source-risk, concept keys, stems used in scoring
- CAN_SELECT_QUESTION = YES
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = YES after session start
- CAN_PERSIST_CONTENT = YES
- CAN_RESTORE_CONTENT = NO
- CURRENT_PARTITION_AWARENESS = NONE. Existing “protected role” helpers inside `build_smart_practice_pool` are Smart Practice scoring roles, not TRAIN/PROBE roles.
- REQUIRED_FUTURE_GUARD: TRAIN-only candidate construction before utility ranking
- FAIL_CLOSED_BEHAVIOR: missing manifest or PROBE member in input pool → no Smart Practice session
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P03 — Smart Practice signal payload

- CURRENT_SOURCE_LOCATION: `_build_smart_practice_signal_payload`
- PATH_CLASS = `DERIVED_STATE`
- QUESTION_MATERIAL_TOUCHED: history-derived maps, near-miss pressure, wrong-answer recycling over `master_questions`
- CAN_SELECT_QUESTION = NO (but feeds P02)
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = NO directly; derived signals can encode answer-adjacent structure
- CAN_PERSIST_CONTENT = YES if snapshot published into progress meta
- REQUIRED_FUTURE_GUARD: compute signals only over TRAIN-eligible items
- FAIL_CLOSED_BEHAVIOR: contaminated signal snapshot must be discarded, not filtered after ranking
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P04 — Smart Practice prewarm/cache

- CURRENT_SOURCE_LOCATION: `schedule_smart_practice_prewarm`; `SmartPracticePrewarmService`; `app.invalidate_learning_state`
- QUESTION_MATERIAL_TOUCHED: same as P02/P03, computed off the UI thread
- CAN_SELECT_QUESTION = YES (precomputed pool)
- REQUIRED_FUTURE_GUARD: prewarm builder receives a TRAIN-only snapshot; invalidate on manifest/hash change
- FAIL_CLOSED_BEHAVIOR: stale cache is not usable; empty TRAIN snapshot yields no prewarm
- CACHE TEST obligation is primary
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P05 — Smart Practice detached worker

- CURRENT_SOURCE_LOCATION: `smart_practice_worker.py`
- QUESTION_MATERIAL_TOUCHED: deep-copied `master_questions` plus progress/history
- REQUIRED_FUTURE_GUARD: snapshot copied into the worker must already be role-filtered
- FAIL_CLOSED_BEHAVIOR: worker must not rank a mixed TRAIN+PROBE `master_questions` list
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P06 — Due review

- CURRENT_SOURCE_LOCATION: `build_due_review_pool`; `progress_store.is_review_due`; `select_due_review_questions`
- CAN_SELECT_QUESTION = YES
- CURRENT_PARTITION_AWARENESS = NONE
- REQUIRED_FUTURE_GUARD: due predicate may run only on TRAIN-eligible records; PROBE due-ness must not enqueue training
- FAIL_CLOSED_BEHAVIOR: PROBE item with a due date remains NOT ELIGIBLE for training
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P07 — Weak/retest

- CURRENT_SOURCE_LOCATION: `build_weak_retest_pool` using `is_active_weak`, flagged, due, then analytics-domain fallback over `master_questions`
- CAN_SELECT_QUESTION = YES
- REQUIRED_FUTURE_GUARD: all four current predicates (flagged, due, active-weak, weak-domain fallback) must be TRAIN-bounded
- FAIL_CLOSED_BEHAVIOR: analytics fallback must not fill from PROBE domains/families
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P08 — Full-bank restore

- CURRENT_SOURCE_LOCATION: `restore_full_bank`; `restore_progress_manual` then `start_session_from_pool(self.master_questions, ...)`
- CAN_SELECT_QUESTION = YES (entire `master_questions`)
- CAN_RESTORE_CONTENT = YES
- REQUIRED_FUTURE_GUARD: “full bank” for training means full TRAIN set, never PROBE
- FAIL_CLOSED_BEHAVIOR: restore cannot start a session that includes PROBE items even if saved progress names them
- RESTORE TEST obligation is primary
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P09 — Session start from pool

- CURRENT_SOURCE_LOCATION: `start_session_from_pool`
- QUESTION_MATERIAL_TOUCHED: clones pool, adaptive answer-order shuffle, may resume saved qnums from `master_questions`
- REQUIRED_FUTURE_GUARD: reject mixed-role pools; resumed qnum lists must be re-authorized
- FAIL_CLOSED_BEHAVIOR: saved qnum that is now PROBE is dropped and the session is marked contaminated if any dropped item was previously shown
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P10 — Twins

- CURRENT_SOURCE_LOCATION: `find_question_twins` iterates `master_questions` by topic/domain
- CAN_SELECT_QUESTION = YES
- REQUIRED_FUTURE_GUARD: twin search corpus = TRAIN only; co-family PROBE siblings are excluded by family role
- FAIL_CLOSED_BEHAVIOR: no twin rather than a PROBE twin
- FAMILY TEST / TRANSFER TEST apply
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P11 — Delayed-recall follow-up

- CURRENT_SOURCE_LOCATION: `maybe_queue_delayed_recall_probe`
- CURRENT_PARTITION_AWARENESS = `NONE_AND_CONCEPTUALLY_MISNAMED`
- NOTE: despite the “probe” tag (`QUESTION_TAG_DELAYED_RECALL_PROBE`), this is a **training follow-up injector**, not the Task-6 held-out PROBE measurement path.
- CAN_SELECT_QUESTION = YES from related follow-up candidates
- REQUIRED_FUTURE_GUARD: treat as TRAINING; never inject Task-6 PROBE items; do not count these events as clean held-out measurements
- FAIL_CLOSED_BEHAVIOR: misnamed tag does not confer MEASUREMENT eligibility
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P12 — Memory ramp

- CURRENT_SOURCE_LOCATION: `find_memory_ramp_candidates` / `maybe_queue_memory_ramp`
- CAN_SELECT_QUESTION = YES (same-unit/topic/objective)
- REQUIRED_FUTURE_GUARD: unit index is TRAIN-only
- FAMILY TEST applies because same-unit often equals same semantic family
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P13 — Wrong-answer memory

- CURRENT_SOURCE_LOCATION: `find_wrong_answer_memory_candidates` uses selected and correct labels
- CAN_SELECT_QUESTION = YES
- CAN_REVEAL_ANSWER = YES (uses correct labels to find relatives)
- REQUIRED_FUTURE_GUARD: candidate search TRAIN-only; do not use PROBE answer text as a retrieval key
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P14 — Confusion-pair drill

- CURRENT_SOURCE_LOCATION: `find_confusion_pair_candidates`
- CAN_SELECT_QUESTION = YES
- REQUIRED_FUTURE_GUARD: TRAIN-only; co-family PROBE items are the exact leakage this drill would cause
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P15 — Streak rescue

- CURRENT_SOURCE_LOCATION: `maybe_trigger_streak_rescue`
- CAN_SELECT_QUESTION = YES (same-domain inject)
- REQUIRED_FUTURE_GUARD: domain rescue pool = TRAIN-only
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P16 — Misconception repair

- CURRENT_SOURCE_LOCATION: `plan_misconception_repair` (prerequisite, transfer, twin, wrong-answer, confusion inserts)
- CAN_SELECT_QUESTION = YES
- REQUIRED_FUTURE_GUARD: every repair branch uses the shared eligibility boundary; concept-graph neighbors are TRAIN-only
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P17 — Follow-up candidate index

- CURRENT_SOURCE_LOCATION: `_rebuild_followup_candidate_index`
- QUESTION_MATERIAL_TOUCHED: stores prompt + choice text in `search_text` for every `master_questions` item
- CAN_REVEAL_STEM = YES to later injectors; CAN_REVEAL_ANSWER = YES if choices include the keyed answer
- REQUIRED_FUTURE_GUARD: index TRAIN items only before any search_text is built
- CACHE TEST / FAMILY TEST apply
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P18 — Boss rounds

- CURRENT_SOURCE_LOCATION: `maybe_trigger_boss_round`
- CAN_SELECT_QUESTION = YES from `master_questions` ranked by weak/due/domain/volatility
- REQUIRED_FUTURE_GUARD: gamification injectors are training paths
- FAIL_CLOSED_BEHAVIOR: optional game setting does not exempt partition rules
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P19 — Stealth checkpoints

- CURRENT_SOURCE_LOCATION: `maybe_trigger_stealth_checkpoint`
- QUESTION_MATERIAL_TOUCHED: analytics over `master_questions` then injects same-unit/topic candidates
- CAN_SELECT_QUESTION = YES
- REQUIRED_FUTURE_GUARD: latent-weakness/transfer maps used for injection must be TRAIN-only
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P20 — Question list / jump

- CURRENT_SOURCE_LOCATION: `refresh_question_list` shows status, question number, source page, truncated domain; `jump_to_question` / `on_listbox_select` render the selected item
- CAN_SELECT_QUESTION = YES
- CAN_REVEAL_STEM = YES on jump; list itself does not print the stem
- REQUIRED_FUTURE_GUARD: session list may contain only authorized items; IDs of held-out PROBE items must not appear in a training session list
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P21 — Normal answer rendering

- CURRENT_SOURCE_LOCATION: `render_question`; `_render_choice_rows` marks correct/wrong after answer
- CAN_REVEAL_STEM = YES; CAN_REVEAL_ANSWER = YES when `show_exam_feedback`
- REQUIRED_FUTURE_GUARD: MEASUREMENT rendering may show stem/choices but must not reveal keyed answer or explanation until after a clean first scored attempt, and must not persist reveal into training history as if it were practice
- RENDER TEST applies
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P22 — Explanation reveal

- CURRENT_SOURCE_LOCATION: `_inline_explanation_for_question`; `complete_explanation_recall`; `render_general_explanation`
- CAN_REVEAL_EXPLANATION = YES
- REQUIRED_FUTURE_GUARD: explanation reveal on a PROBE item is contamination for later primary-endpoint use of that exact item
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P23 — Choice-explanation formatter

- CURRENT_SOURCE_LOCATION: `format_choice_explanations` emits selected letters, keyed answer, and per-choice explanations
- CAN_REVEAL_ANSWER = YES; CAN_REVEAL_EXPLANATION = YES
- REQUIRED_FUTURE_GUARD: formatter is a reveal path even if not currently packed into the default review panel
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P24 — Adaptive explanation text

- CURRENT_SOURCE_LOCATION: `app.py` `adaptive_explanation_text`
- CAN_REVEAL_EXPLANATION = YES (derived coaching from the keyed explanation)
- REQUIRED_FUTURE_GUARD: derived paraphrase of a PROBE explanation is still contamination
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P25 — History persistence

- CURRENT_SOURCE_LOCATION: `append_answer_history` stores `selected`, `correct_letters`, `selected_texts`, `correct_texts`, domain/topics, session tags
- CAN_PERSIST_CONTENT = YES
- CAN_REVEAL_ANSWER = YES to any later history consumer
- REQUIRED_FUTURE_GUARD: PROBE measurement events persist identity and correctness for the endpoint, but training analytics must not replay PROBE answer text into recommendations; duplicate restored events are not first attempts
- HISTORY TEST applies
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P26 — Progress save/backup

- CURRENT_SOURCE_LOCATION: `save_progress`; `backup_progress_manual`; `auto_backup_progress`; `runtime_persistence`
- CAN_PERSIST_CONTENT = YES
- REQUIRED_FUTURE_GUARD: backups inherit contamination flags; restoring a backup cannot wash contamination
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P27 — Progress restore/import

- CURRENT_SOURCE_LOCATION: `restore_progress_manual`; `load_progress_if_present`
- CAN_RESTORE_CONTENT = YES, then starts a full-bank practice session
- REQUIRED_FUTURE_GUARD: restored records are re-authorized; PROBE items in restored history are contamination evidence, not training eligibility
- FAIL_CLOSED_BEHAVIOR: restore never implies TRAIN
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P28 — Session snapshot restore

- CURRENT_SOURCE_LOCATION: `load_session_if_present`; `session_store.build_session_snapshot` / `migrate_session_snapshot`
- CAN_RESTORE_CONTENT = YES including answered state, selected letters, builder context, qnum lists
- REQUIRED_FUTURE_GUARD: qnum reconstitution from `master_questions` must re-run eligibility; answered PROBE items in a training snapshot contaminate those items
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P29 — Analytics dashboard

- CURRENT_SOURCE_LOCATION: `compute_analytics`; `open_analytics_window`; `_build_analytics_payload` plus dozens of row builders
- QUESTION_MATERIAL_TOUCHED: prompts, explanations (phrasing-normalization), choice labels, history texts, concept units
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = YES where row builders emit question-adjacent notes (for example phrasing rows use `general_explanation`)
- REQUIRED_FUTURE_GUARD: training analytics exclude PROBE item content; aggregate PROBE measurement stats may exist only on a sealed measurement surface
- ANALYTICS/EXPORT TEST applies
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P30 — Analytics “delayed probe” rows

- CURRENT_SOURCE_LOCATION: `_build_delayed_probe_rows`
- CURRENT_PARTITION_AWARENESS = `NONE_AND_CONCEPTUALLY_MISNAMED`
- NOTE: these rows recommend a “surprise delayed probe” on previously seen items. That is a **training spacing heuristic**, not Task-6 held-out PROBE measurement.
- CAN_SELECT_QUESTION = YES indirectly (feeds stealth/recommendation)
- REQUIRED_FUTURE_GUARD: must not target Task-6 PROBE families; must not be counted as clean held-out outcomes
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P31 — Analytics export

- CURRENT_SOURCE_LOCATION: `export_analytics_json` writes the full analytics payload
- CAN_PERSIST_CONTENT = YES to an operator-chosen JSON file
- REQUIRED_FUTURE_GUARD: exported training analytics omit protected PROBE stems/answers/explanations; measurement exports are separately sealed
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P32 — Smart Practice measurement report

- CURRENT_SOURCE_LOCATION: `generate_smart_practice_measurement_report`; `smart_practice_measurement.build_measurement_report`
- QUESTION_MATERIAL_TOUCHED: history events, repair state, concept graph, calibration
- REQUIRED_FUTURE_GUARD: this report is champion-policy instrumentation, not the SC-900 7-day held-out endpoint. It must not consume Task-6 PROBE items as training calibration.
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P33 — Analytics recommendations

- CURRENT_SOURCE_LOCATION: `analytics_recommendations.build_analytics_recommendations`
- CAN_REVEAL_STEM = possible via recommendation text that names units/questions
- REQUIRED_FUTURE_GUARD: recommendations are TRAINING derived state; PROBE families excluded
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P34 — Bank open / reload / load_from_path

- CURRENT_SOURCE_LOCATION: `open_bank`; `reload_bank`; `load_from_path`; `question_bank.load_bank`
- CAN_SELECT_QUESTION = YES (replaces `master_questions`)
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = YES after load
- REQUIRED_FUTURE_GUARD: loading a bank that is not hash-bound to the frozen partition is NOT_ELIGIBLE for CAND-01 measurement; default launch bank remains the 8-question placeholder and is not the Phase-3 candidate bank
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

Default launch bank SHA-256 remains `60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426`. Task 7 does not change that.

### P35 — Question-bank import

- CURRENT_SOURCE_LOCATION: `ingestion.importer.import_jsonl`; `tools/import_sc900_content.py`
- CAN_PERSIST_CONTENT = YES into the store as pending-by-default
- REQUIRED_FUTURE_GUARD: import does not assign TRAIN/PROBE; new items are UNASSIGNED until a later authorized partition revision. UNASSIGNED is NOT ELIGIBLE.
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P36 — Question-bank compile

- CURRENT_SOURCE_LOCATION: `compile_question_bank`
- CAN_PERSIST_CONTENT = YES (answers and explanations into a runtime JSON)
- REQUIRED_FUTURE_GUARD: compiling PROBE items into a launch/runtime bank used for training is a contamination/authorization event; Phase-3 compiled candidate bank is not the launch bank
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P37 — Candidate-bank rebuild

- CURRENT_SOURCE_LOCATION: `tools.build_sc900_phase3`
- CURRENT_PARTITION_AWARENESS = `DESIGN_TIME_ONLY`
- CAN_PERSIST_CONTENT = YES (store + compiled candidate bank + manifest)
- REQUIRED_FUTURE_GUARD: remains design-time until a later package authorizes runtime consumption
- TASK7_DISPOSITION = `DESIGN_TIME_AUTHORITY_NOT_RUNTIME_CONSUMER`

### P38 — Extraction pipeline

- CURRENT_SOURCE_LOCATION: `extraction/pipeline.py`; `extraction/parse.py`; `ingestion/adapter.py`
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = YES in exchange JSONL
- REQUIRED_FUTURE_GUARD: extracted rows stay pending; they have no partition role
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P39 — Screenshot-review editor

- CURRENT_SOURCE_LOCATION: `open_screenshot_review_window`; `_render_screenshot_review_detail`; `_update_bank_question_fields`
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = YES
- CAN_PERSIST_CONTENT = YES (mutates bank fields)
- REQUIRED_FUTURE_GUARD: editor access to a PROBE item is contamination of that exact item unless the protocol classifies screenshot review as pre-training authoring (not learner exposure). Learner-facing screenshot review during a study epoch contaminates.
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P40 — Issue review

- CURRENT_SOURCE_LOCATION: `open_issue_review_window`
- CAN_REVEAL_STEM = YES for the reported item
- REQUIRED_FUTURE_GUARD: same custody as P39 for PROBE items
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P41 — Redo / retry

- CURRENT_SOURCE_LOCATION: `redo_question` clears runtime answer state; history already contains the prior event
- CAN_SELECT_QUESTION = YES (same item)
- REQUIRED_FUTURE_GUARD: redo is never a clean first scored attempt; PROBE redo cannot enter the primary endpoint
- HISTORY TEST / MEASUREMENT duplicate-attempt test apply
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P42 — Tests / fixtures

- CURRENT_SOURCE_LOCATION: `tests/test_sc900_engine_regression.py`, ingestion/extraction fixtures, Phase-3 tests, `tests/pdf_fixtures.py`
- QUESTION_MATERIAL_TOUCHED: full synthetic or cloned questions including answers/explanations
- REQUIRED_FUTURE_GUARD: tests may construct ineligible items to prove fail-closed behavior; they must not silently become a runtime eligibility bypass. Future guard tests should not load the live PROBE stems into a training-selector helper without asserting rejection.
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P43 — Design-time TRAIN/PROBE manifest

- CURRENT_SOURCE_LOCATION: `content/sc900/phase3/train_probe_manifest.json` plus schema/validator/builder
- CURRENT_PARTITION_AWARENESS = `DESIGN_TIME_ONLY`
- RUNTIME_CONSUMER_COUNT = 0
- REQUIRED_FUTURE_GUARD: runtime consumption remains unauthorized in Task 7
- TASK7_DISPOSITION = `DESIGN_TIME_AUTHORITY_NOT_RUNTIME_CONSUMER`

### P44 — Exam-mode rendering

- CURRENT_SOURCE_LOCATION: `render_question` with `exam_reveal`; list status shows `R` instead of OK/X
- CAN_REVEAL_ANSWER = NO until exam finish; CAN_REVEAL_STEM = YES
- REQUIRED_FUTURE_GUARD: exam mode is not automatically MEASUREMENT. Stem exposure still contaminates a held-out PROBE item if the item was not in a clean measurement protocol.
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P45 — Progress directory recovery

- CURRENT_SOURCE_LOCATION: `app.py` progress-file strength recovery across directories
- CAN_RESTORE_CONTENT = YES
- REQUIRED_FUTURE_GUARD: recovered history cannot create duplicate first-attempt PROBE observations or restore TRAIN eligibility for PROBE items
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P46 — Bank lint / clean / validate tools

- CURRENT_SOURCE_LOCATION: `tools/clean_bank.py`; `tools/validate_bank.py`; `tools/lint_bank.py`
- CAN_REVEAL_STEM / ANSWER / EXPLANATION = YES to operators/reports
- REQUIRED_FUTURE_GUARD: operator QA of the candidate bank is authoring/review, not learner training exposure; outputs must not be copied over the launch bank without authorization
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P47 — Concept-graph prerequisite path

- CURRENT_SOURCE_LOCATION: `smart_practice_concept_graph.select_prerequisite_path`
- CAN_SELECT_QUESTION = YES indirectly via concept keys mapped to questions
- REQUIRED_FUTURE_GUARD: graph neighborhoods used for training cannot include PROBE family concept keys
- TRANSFER TEST applies
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

### P48 — Question-material export surfaces

- CURRENT_SOURCE_LOCATION: no `export_questions` UI; write surfaces are compile output, analytics JSON, progress JSON, screenshot-review saves
- REQUIRED_FUTURE_GUARD: any new exporter inherits this contract
- TASK7_DISPOSITION = `CONTRACT_FROZEN_RUNTIME_UNIMPLEMENTED`

## Future verification matrix

Do not implement these tests in Task 7 if they require runtime guards. They are implementation-ready obligations for a later authorized package.

For **every** inventory path, specify at least:

| Test class | Required assertion |
| --- | --- |
| POSITIVE | Valid TRAIN item may enter a TRAINING path; valid clean PROBE item may enter a MEASUREMENT path |
| NEGATIVE | PROBE item must not enter a TRAINING exposure path; TRAIN item must not be scored as a clean held-out probe |
| FAIL-CLOSED | Missing/malformed partition metadata blocks eligibility; never defaults to TRAIN |
| FAMILY | Whole-family role is preserved; no family split |
| TRANSFER | A Task-4 transfer edge cannot connect TRAIN and PROBE; co-family injection is rejected |
| RESTORE | Restored session/progress/backup cannot bypass role restrictions or duplicate first attempts |
| CACHE | Prewarm/cache/index/signal payload cannot reintroduce protected material |
| RENDER | Protected content cannot leak through answer/explanation/adaptive-text rendering |
| HISTORY | History cannot expose PROBE answer text into training analytics or duplicate future first-attempt measurement |
| ANALYTICS/EXPORT | Derived/output paths do not contaminate PROBE |

Path-specific additions:

- P04/P05/P17: CACHE test must fail if filtering occurs only after payload construction.
- P08/P09/P27/P28/P45: RESTORE test must use a snapshot that names PROBE qnums.
- P11/P30: explicitly assert that a “probe” label does not confer MEASUREMENT eligibility.
- P25/P41: HISTORY test must treat redo, restore, and import as non-first attempts.
- P35/P36/P37: IMPORT/COMPILE test must leave new items UNASSIGNED / NOT_ELIGIBLE until an authorized partition revision.
- P42: fixture test must prove fail-closed on synthetic missing roles rather than bypassing the boundary.

## What Task 7 does not claim

```text
RUNTIME_GUARDS_IMPLEMENTED = NO
every runtime path currently enforces the contract = NOT CLAIMED
PHASE_3_STRUCTURALLY_ACCEPTED = NO
Gate 2 reopened = NO
learning effectiveness = NOT CLAIMED
29 independent probe measurements = NO
```

The map in this file is the design-assurance inventory. It is not runtime isolation.
