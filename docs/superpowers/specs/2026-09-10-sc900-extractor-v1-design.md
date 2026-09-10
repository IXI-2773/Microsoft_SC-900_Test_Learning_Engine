# SC-900 Extractor v1 Design

## Purpose

Connect authorized PDF reading to the frozen SC-900 ingestion pipeline without coupling the learning engine to PDF libraries or silently promoting imported material into the runtime bank.

## Baseline

- Frozen tag: `sc900-v8.0.0-baseline`
- Frozen commit: `fed4d4a44591ca93fe8428bc3ca02ec66a12f715`
- This work lives only on `integration/sc900-extractor-v1`.
- PR #1 remains open/draft/unmerged. The frozen tag is not moved.

## Existing extractor evidence

`IXI-2773/PDF_Extractor_Engine` (`pdf-extractor-engine` 0.1.0) is a subject-neutral page-text library:

- Public API: `extract_pdf(ExtractionRequest) -> ExtractionResult` with 1-based `PageRecord.page_number` and `text`.
- Backend: `pypdf>=4,<5`.
- Non-scope: OCR, question parsing, CLI, persistence, SC-900 taxonomy, approval.

This package does **not** vendor that repository. It adapts the same page-text boundary: path-or-bytes PDF in, ordered page records out. If `pdf_extractor_engine` is importable it is preferred; otherwise `pypdf` is used directly. Question recognition stays in this repository.

## Data flow

```
authorized PDF
  -> PDF page extraction (pdf_extractor_engine or pypdf)
  -> text normalization / scanned-text detection
  -> question-block segmentation
  -> choice / answer / explanation association
  -> versioned JSONL exchange contract
  -> SC-900 adapter
  -> existing canonicalize / import_jsonl
  -> pending / quarantine / review
  -> explicit review decision
  -> approved-only compile_question_bank
```

Invariant: **IMPORT != APPROVAL**. Extracted records never become runtime bank questions without `apply_review_decision(..., "approved")`.

## Exchange contract

Version: `sc900.extractor.exchange/v1`  
Format: JSONL (one JSON object per line).  
`record_type`: `extracted_question` or `extraction_diagnostic`.

Question records carry: `contract_version`, `record_type`, `origin` (`SOURCE_EXTRACTED` | `GENERATED` | `MANUALLY_AUTHORED`), `source_document_id`, `source_title`, `source_path_or_reference`, `source_page`, `source_page_end`, `source_locator`, `extraction_method`, `extractor_version`, `question_text`, `choices`, `source_answer`, `source_explanation`, `raw_source_fragment`, `confidence`, `extraction_warnings`, `source_license`, `domain`, `objective` when actually present or operator-supplied.

The adapter maps those fields onto the existing canonical model (`stem`, `choices`, `correct_answer`, `explanation`, `provenance.source.page`). It does not invent missing keys, explanations, citations, page numbers, or objective codes.

## Fail-closed extraction

- Encrypted PDFs without an authorized password: document-level failure, no guessed plaintext.
- Image-only / insufficient text: diagnostic `OCR_REQUIRED`; OCR is not a hidden dependency of text extraction and is not implemented in v1.
- Question with no choices, duplicate labels, contradictory keys, or an answer that names a missing choice: emit the record with warnings; canonical import quarantines it.
- Unknown or missing SC-900 taxonomy: do not invent an objective. Operator may supply `--domain` / `--objective` for a whole authorized document. Otherwise the canonical importer quarantines with `INVALID_OBJECTIVE`.
- A bad question does not abort a valid sibling record. A corrupted PDF or unreadable exchange file may fail the batch.

## Provenance

Page identity is preserved from PDF page numbers through JSONL, canonical `provenance.source`, review storage, and compiled runtime records. Extracted record IDs, canonical question IDs, and runtime question numbers remain distinct. Canonical IDs stay deterministic from normalized stem, choices, answers, and source.

## Promotion

Reuse `ingestion.importer` only. No second approval system. Compiler still emits only `promotion_status == "approved"`.

## CLI

Two-stage, repository-native:

```
python -m tools.extract_sc900_pdf <pdf> --output <jsonl>
python -m tools.import_sc900_content <jsonl> --store <store>
python -m tools.review_sc900_content decide approved <id> --store <store>
python -m tools.review_sc900_content report --store <store> --compile <bank.json>
```

Optional convenience: `python -m tools.import_sc900_pdf <pdf>` extracts to JSONL then imports, still pending-by-default.

## Non-goals

- GUI PDF picker
- OCR implementation
- DRM / paywall / dump ingestion
- Changing Smart Practice, learner modeling, shuffling, autosave, or the frozen eight-question default bank
- Cleaning the stale `.sc900-bootstrap/sc900-source-v8` gitlink
