# SC-900 Ingestion Baseline Design

## Purpose

Prepare the SC-900 Test Learning Engine to accept structured exports from an external book extractor without coupling the engine to that extractor's wire format. The existing runtime question-bank format remains compatible; imported content is staged separately and becomes runtime content only through an explicit compilation step.

## Boundaries

`extractor export -> adapter -> canonical record -> validation/normalization -> duplicate classification -> persistent store -> runtime-bank compiler`

The adapter accepts a versioned JSONL envelope and maps extractor-specific field names to canonical records. Canonical records preserve provenance, whether they are question or source-material records, and their origin (`extracted`, `generated`, or `manual`). The importer never fetches content or accesses third-party systems.

## Canonical Question Model

Question records carry a deterministic ID, exam, taxonomy version, domain/objective/subobjective, type, difficulty, stem, choices, correct-answer IDs, explanation, references, tags, metadata, and provenance. Source-material records use the same provenance envelope but have no answer key and are persisted independently. Source fields are optional individually, but a supplied field must have the expected type.

## Validation and Deduplication

The importer quarantines malformed records with stable reason codes and diagnostics. It normalizes text and choice IDs before validation, creates deterministic IDs from normalized question content plus source fingerprint, and classifies duplicates as exact, probable, or conceptually related. Exact duplicates are skipped; probable duplicates are accepted with a review flag; related records are accepted unchanged.

## Persistence and Runtime Integration

The JSON store is append-safe and idempotent by canonical ID. Import reports include accepted, rejected, skipped, and review counts, reason codes, source statistics, and a resumable batch fingerprint. A compiler creates the existing runtime JSON bank from accepted question records; it never mixes source-material records into the question bank. The current eight-question SC-900 placeholder remains the default runtime bank until the compiler output is deliberately selected.

## Configuration

The SC-900 objective taxonomy lives in a versioned JSON configuration. The current four domains retain their published ranges (10–15%, 25–30%, 35–40%, 20–25%); future blueprints can be added without editing application logic.

## Verification

Tests cover schema validation, normalization, deterministic identity, exact/probable/related duplicate classification, malformed-record quarantine, idempotent and 1,000-record imports, source-material separation, taxonomy mapping, compiler output compatibility, seeded selection, and choice shuffling.
