# SC-900 Ingestion Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned, provenance-aware, deduplicating ingestion boundary for structured SC-900 content exports.

**Architecture:** Keep the runtime bank loader unchanged. New ingestion modules map a JSONL envelope to canonical records, validate and normalize them, persist accepted questions and source material separately, and compile accepted questions into the loader's existing JSON-bank contract.

**Tech Stack:** Python 3.11, standard-library JSON/JSONL, unittest.

**Spec:** `docs/superpowers/specs/2026-09-10-sc900-ingestion-baseline-design.md`

## Global Constraints

- Never fetch, scrape, or bypass access controls for content.
- Preserve extractor provenance when supplied and distinguish extracted, generated, and manual records.
- Keep source material separate from runnable questions.
- Do not change the default eight-question baseline bank.
- Unknown SC-900 mappings must quarantine with diagnostics; current domains use the declared four published ranges.

### Task 1: Taxonomy and canonical contracts

**Files:** Create `config/certifications/sc900-2026.json`, `ingestion/models.py`, `tests/test_ingestion_models.py`.

**Interfaces:** `load_taxonomy(path)`, `canonicalize_record(raw, taxonomy)`, and `ValidationIssue` establish the canonical data boundary.

- [ ] Write tests that accept a valid canonical question, reject a missing stem, missing choices, duplicated normalized choices, unsupported type, invalid answer, and invalid taxonomy mapping.
- [ ] Run `python -m unittest tests.test_ingestion_models -v` and observe failures before implementation.
- [ ] Implement immutable canonical/provenance structures and validation reason codes.
- [ ] Rerun the focused tests and commit the contract.

### Task 2: Adapter, normalization, and duplicate classification

**Files:** Create `ingestion/adapter.py`, `ingestion/dedup.py`, `tests/test_ingestion_adapter.py`.

**Interfaces:** `adapt_record(raw)`, `normalize_record(record)`, `deterministic_id(record)`, and `classify_duplicate(candidate, accepted)` return `exact`, `probable`, `related`, or `unique`.

- [ ] Write tests for legacy/extractor aliases, formatting normalization, stable IDs, reordered-choice exact duplicates, near stem duplicates, and concept relations.
- [ ] Run the focused test module and observe expected failures.
- [ ] Implement the mappings and comparison fingerprints without deleting near-duplicates.
- [ ] Rerun the focused tests and commit the adapter layer.

### Task 3: Persistent idempotent importer and runtime compiler

**Files:** Create `ingestion/store.py`, `ingestion/importer.py`, `tools/import_sc900_content.py`, `tests/test_ingestion_importer.py`.

**Interfaces:** `import_jsonl(input_path, store_dir, taxonomy_path) -> ImportReport` and `compile_question_bank(store_dir, output_path)`.

- [ ] Write tests for accepted/rejected/skipped counts, actionable quarantine diagnostics, preserved source metadata, separate source-material storage, idempotency, and a 1,000-record synthetic import.
- [ ] Run the importer tests and observe expected failures.
- [ ] Implement JSONL streaming, JSON persistent stores, batch reports, and compilation to the current `question_bank.load_bank` contract.
- [ ] Rerun focused tests and commit the importer.

### Task 4: Generation compatibility and verification

**Files:** Modify `question_bank.py`; create `tests/test_question_bank_selection.py`, `docs/SC900_INGESTION_CONTRACT.md`.

**Interfaces:** `select_questions(questions, count, *, seed=None, domain=None, objective=None, difficulty=None, unseen_ids=None, missed_ids=None)` returns deterministic, non-repeating selections; existing shuffle functions keep correct-answer alignment.

- [ ] Write tests for domain weighting, seeded determinism, filters, unseen/missed modes, and choice shuffling.
- [ ] Run focused tests and observe expected failures.
- [ ] Implement a pure selection helper only; do not rewrite the GUI session builder.
- [ ] Run full tests, lint, formatting, type checks, a compilation smoke test, and commit the documented baseline.
