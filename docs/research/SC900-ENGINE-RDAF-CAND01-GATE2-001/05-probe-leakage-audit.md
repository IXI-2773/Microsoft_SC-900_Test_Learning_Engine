# Probe Leakage Audit

WORK_ID = `SC900-ENGINE-RDAF-CAND01-GATE2-001`  
RDAF_EPOCH = `SC900-RDAF-EPOCH-2026-09-11-003`

## Scope

This audit inventories repository paths that can select, insert, render, restore, cache, analyze, or reveal question material. Gate 2 occurs before runtime implementation, so the absence of already-implemented TRAIN / PROBE guards is not itself a Gate-2 failure. The Gate-2 requirement is to freeze a complete all-path leakage inventory, an implementation-ready TRAIN / PROBE exclusion contract, required fail-closed guard semantics, and a future verification matrix.

## Leakage-Path Inventory

| Path | Evidence | Leakage risk | Disposition |
| --- | --- | --- | --- |
| Smart Practice selection | `app_session_builder_mixin.py:994`, `app_session_builder_mixin.py:1363`, `app_session_builder_mixin.py:1893` | Builds candidate pools from `master_questions` / filtered pools; the future exclusion contract must cover these selectors. | `BLOCKER_FOR_IMPLEMENTATION` |
| Smart Practice prewarm/cache | `app.py:400`, `app_session_builder_mixin.py:512`, `smart_practice_worker.py:52` | Detached prewarm can build signal payloads and pools; the future exclusion contract must cover pre-computation and cache payloads. | `BLOCKER_FOR_IMPLEMENTATION` |
| Normal practice builder | `app_session_builder_mixin.py:843`, `app_session_builder_mixin.py:878` | Uses builder pools that the future exclusion contract must filter by partition membership. | `BLOCKER_FOR_IMPLEMENTATION` |
| Full-bank restore | `app_session_builder_mixin.py:891`, `app.py:2186` | Starts a full-bank practice session after restore. Future PROBE items would be exposed unless excluded. | `BLOCKER_FOR_IMPLEMENTATION` |
| Due review | `progress_store.py:542`, `app_session_builder_mixin.py:987` | Due helper will need partition-aware eligibility semantics. | `BLOCKER_FOR_IMPLEMENTATION` |
| Weak retest | `app_session_builder_mixin.py:944` | Uses due/weak/flagged predicates over filtered master pool. | `BLOCKER_FOR_IMPLEMENTATION` |
| Twins | `app_question_flow_mixin.py:411`, `app_question_flow_mixin.py:518` | Selects from `master_questions`; excludes current session duplicates and suspended items only. | `BLOCKER_FOR_IMPLEMENTATION` |
| Delayed recall probe follow-up | `app_question_flow_mixin.py:524` | Despite "probe" label, this is a training follow-up and can select related items from the bank. | `BLOCKER_FOR_IMPLEMENTATION` |
| Memory ramp | `app_question_flow_mixin.py:585`, `app_question_flow_mixin.py:639` | Selects related same-unit/topic/objective questions from the bank. | `BLOCKER_FOR_IMPLEMENTATION` |
| Wrong-answer memory | `app_question_flow_mixin.py:650`, `app_question_flow_mixin.py:699` | Uses selected and correct answer labels to locate related candidates. | `BLOCKER_FOR_IMPLEMENTATION` |
| Confusion-pair drill | `app_question_flow_mixin.py:707`, `app_question_flow_mixin.py:756` | Uses wrong/correct labels, topic, and domain to inject related questions. | `BLOCKER_FOR_IMPLEMENTATION` |
| Streak rescue | `app_question_flow_mixin.py:770` | Injects same-domain questions after wrong streaks. | `BLOCKER_FOR_IMPLEMENTATION` |
| Misconception repair | `app_question_flow_mixin.py:853` | Schedules prerequisite, transfer, twin, wrong-answer, and confusion repair inserts. | `BLOCKER_FOR_IMPLEMENTATION` |
| Boss round | `app_game_mixin.py:628` | Injects a bank question based on due/weak/domain/volatility state. | `BLOCKER_FOR_IMPLEMENTATION` |
| Stealth checkpoint | `app_game_mixin.py:661` | Injects same-unit/topic candidates based on analytics signals. | `BLOCKER_FOR_IMPLEMENTATION` |
| Answer rendering | `app_question_render_mixin.py:162`, `app_question_render_mixin.py:176`, `app_question_render_mixin.py:231` | Reveals correct choice state and explanation after normal answered items. | `ANSWER_REVEAL_GUARD_REQUIRED` |
| Progress history | `app.py:2285` | Stores selected letters/texts and correct letters/texts in history. | `ANSWER_TEXT_CUSTODY_REQUIRED` |
| Analytics dashboard/export | `app_analytics_mixin.py:4322`, `app_analytics_mixin.py:4341` | Analytics consumes history and question content, then displays/export derived recommendations. | `ANSWER_STEM_REVEAL_REVIEW_REQUIRED` |
| Import/compiler | `ingestion/importer.py:212`, `ingestion/models.py:60` | Approved imported questions are compiled into runtime bank with answers/explanations. Needs partition manifest later. | `STRUCTURE_REQUIRED` |

## Critical Finding

The current code has many legitimate question-injection paths. None can be assumed covered by guarding the obvious initial selector. Gate 2 must therefore freeze an implementation-ready shared eligibility boundary, fail-closed semantics, and tests for every path before later runtime work begins.

## Gate Consequence

Probe isolation is conceptually specified but not yet frozen as an all-path implementation contract with a verification matrix. Gate 2 cannot be earned while this inventory remains a list of future guard obligations rather than a complete design contract. Gate 3 must later implement those guards and prove every runtime path enforces them.
