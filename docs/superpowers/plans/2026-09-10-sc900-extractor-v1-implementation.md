# SC-900 Extractor v1 Implementation Plan

> **For agentic workers:** Implement task-by-task with RED → smallest GREEN → focused regression. Do not mutate `sc900-v8.0.0-baseline`.

**Goal:** Authorized PDF text read → question extraction → versioned JSONL → existing SC-900 importer → pending review → explicit approval → approved-only runtime compilation.

**Architecture:** Thin page-text adapter around `pdf_extractor_engine` when present, else `pypdf`. SC-900 question parsing and exchange JSONL live in `extraction/`. A small `ingestion/adapter.py` maps the exchange contract onto canonical records consumed by the frozen importer.

**Tech Stack:** Python 3.11, pypdf, unittest, existing ingestion store/review/compiler.

**Spec:** `docs/superpowers/specs/2026-09-10-sc900-extractor-v1-design.md`

## Global Constraints

- Frozen tag `sc900-v8.0.0-baseline` → `fed4d4a44591ca93fe8428bc3ca02ec66a12f715` must remain unchanged.
- IMPORT != APPROVAL.
- Do not fabricate questions, choices, keys, explanations, pages, or taxonomy codes.
- Do not copy `PDF_Extractor_Engine` into this repository.
- Do not change Smart Practice or the default eight-question bank.
- Synthetic original PDFs only in tests; no copyrighted book pages.

### Task 1: Page extraction adapter

**Files:** `extraction/pages.py`, `tests/pdf_fixtures.py`, `tests/test_extraction_pages.py`, `requirements-extract.txt`

- [ ] Tests: text PDF page text + 1-based page numbers; multi-page provenance; insufficient-text diagnostic; encrypted PDF fail-closed.
- [ ] Implement `extract_pdf_pages(path)` using `pdf_extractor_engine` if importable, else `pypdf`.
- [ ] Run `python -m unittest tests.test_extraction_pages -v`

### Task 2: Question parsing and exchange contract

**Files:** `extraction/parse.py`, `extraction/contract.py`, `tests/test_extraction_parse.py`

- [ ] Tests: Question/Q/numbered headers; A/B/C/D choices; answer + explanation association; missing answer stays unresolved; malformed duplicate labels warned; deterministic output.
- [ ] Implement isolated stages: normalize → segment → choices → key/explanation → exchange record.

### Task 3: Adapter, CLI, pending/approval path

**Files:** `extraction/pipeline.py`, `ingestion/adapter.py`, `tools/extract_sc900_pdf.py`, `tools/import_sc900_pdf.py`, `tests/test_extraction_pipeline.py`

- [ ] Tests: JSONL maps into canonical import; pending-by-default; explicit approval required; approved-only compile; provenance page survives compile; duplicate import idempotent; unknown taxonomy quarantined; extraction warnings preserved.
- [ ] CLI extract then import; do not auto-approve or auto-compile unless `--compile` after review.

### Task 4: Scale, original-PDF pilot, baseline gate

**Files:** `tests/test_extraction_scale.py`, `tests/test_extraction_pilot.py`

- [ ] 1,000-record synthetic JSONL through adapter+import: deterministic, no duplicate explosion, compiler approved-only.
- [ ] Generate an original 24-question text PDF, extract → import twice, approve a small subset, compile, report counts.
- [ ] Run full unittest, bank lint, installation verification, Ruff, Black, mypy.
- [ ] Prove frozen tag still dereferences `fed4d4a44591ca93fe8428bc3ca02ec66a12f715`.
