# SC-900 Test Learning Engine — v8 Baseline Design

Date: 2026-09-10

## Purpose

Create an SC-900-focused study application by transplanting the proven v8 architecture from `IXI-2773/Comptia-SY0-701-Test-Learning-Engine` into `IXI-2773/Microsoft_SC-900_Test_Learning_Engine`, while keeping the existing learning engine behavior stable during the certification conversion.

The SC-900 repository will become the primary experimental development repository after the conversion is stable. The existing SY0-701 repository remains the known-good reference until later engine improvements are proven and intentionally backported.

## Source Baseline

The source baseline is the current Security Testing Engine v8 architecture from the SY0-701 repository. The transplant preserves the major existing subsystems:

- Smart Practice
- Practice mode
- Exam mode
- learner progress/history
- confidence and mastery tracking
- analytics and recommendations
- autosave and resumable sessions
- backups and checkpoints
- issue reporting and question quarantine
- bank loading, cleanup, validation, and answer-order handling
- smoke testing and benchmark guards
- quality checks
- Windows packaging and release tooling

No Smart Practice algorithm redesign or analytics redesign belongs in the initial migration.

## Architectural Direction

The migration has two independent stages.

### Stage 1 — Engine Baseline Conversion

Transplant the reusable v8 application, tests, tooling, packaging, and persistence behavior into the SC-900 repository.

Convert certification-specific surfaces only:

- application identity
- exam identity
- default bank selection
- runtime namespace and storage path
- Windows executable and release names
- README and user-facing documentation
- certification-specific source labels
- SC-900 domain/objective metadata

Do not ship SY0-701 question banks in the SC-900 repository.

Use a small original placeholder SC-900 bank so the full application can be exercised before external study material is imported.

### Stage 2 — SC-900 Content Ingestion

Treat external/public/permitted study material as a separate content pipeline:

`raw source -> extraction -> staging -> normalization -> objective/domain mapping -> duplicate detection -> answer/explanation validation -> review/quarantine -> approved bank`

External source material must never be inserted directly into the production bank without passing validation and review.

## Branding and Identity

The application brand is:

`SC-900 Test Learning Engine`

The reusable engine identity and the certification identity should be separated conceptually.

Target configuration values should provide, directly or equivalently:

- `ENGINE_NAME = "Test Learning Engine"`
- `ENGINE_VERSION = "8.0.0"`
- `APP_NAME = "SC-900 Test Learning Engine"`
- `CERT_VENDOR = "Microsoft"`
- `CERT_EXAM_CODE = "SC-900"`
- `CERT_NAME = "Security, Compliance, and Identity Fundamentals"`
- `DEFAULT_BANK = "sc900_bank.json"`
- `RUNTIME_NAMESPACE = "SC900TestLearningEngine"`

Certification-specific constants should be centralized rather than duplicated throughout large application modules.

### User-facing/build artifact renames

Initial target identities:

- `Security Testing Engine` -> `SC-900 Test Learning Engine`
- `SecurityTestingEngine.exe` -> `SC900TestLearningEngine.exe`
- `%LOCALAPPDATA%\SecurityTestingEngine` -> `%LOCALAPPDATA%\SC900TestLearningEngine`
- `security_test_app_windows_v8.pyw` -> `sc900_test_learning_engine_v8.pyw`
- `run_windows_v8.bat` -> `run_sc900_v8.bat`
- `build_windows_v8.bat` -> `build_sc900_v8.bat`
- `public_sy0701_*` default-bank identity -> `sc900_bank.json`

Generic engine terminology remains unchanged where it is not certification-specific, including Smart Practice, Practice, Exam, domain, objective code, confidence, mastery, progress, question bank, source trust, and analytics.

The application should include a clear disclaimer that it is an unofficial study application and is not affiliated with or endorsed by Microsoft.

## Question Model

Retain the existing question-bank model. It already supports the required fields:

- `question_number`
- `prompt`
- `choices`
- `correct`
- `general_explanation`
- `choice_explanations`
- `domain`
- `chapter`
- `subtitle`
- `question_type`
- `topics`
- `flagged_issues`
- `source_page`
- `source_name`
- `objective_code`
- `study_focus`
- `duplicate_of`

No schema redesign is required for the initial conversion.

A representative SC-900 record should look structurally like:

```json
{
  "question_number": 1,
  "prompt": "...",
  "choices": {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "..."
  },
  "correct": ["B"],
  "general_explanation": "...",
  "choice_explanations": {},
  "domain": "Microsoft Entra",
  "objective_code": "2.x",
  "topics": ["Conditional Access"],
  "source_name": "...",
  "source_page": 42,
  "study_focus": "...",
  "flagged_issues": [],
  "duplicate_of": null
}
```

## Frozen Behavior During Migration

The following behavior is intentionally frozen during the initial SC-900 conversion:

- Smart Practice selection policy
- learner modeling
- confidence controls
- difficulty calibration
- progress semantics
- achievements/quests
- analytics calculations
- answer shuffling
- autosave behavior
- session migration
- backup/checkpoint behavior
- issue/quarantine behavior

Any functional failure after the transplant should therefore be attributable to the SC-900 adaptation rather than simultaneous algorithm changes.

## Validation and Content Safety

The SC-900 repository should preserve the v8 content-safety model:

- required bank fields must be validated
- answer keys must point to real choices
- text normalization remains active
- duplicate detection remains available
- suspicious or incomplete source records remain quarantinable
- questionable records should not silently contribute to learner scoring
- source metadata should remain traceable

The production bank is an approved output, not a raw scrape.

## Rebranding Invariant

After baseline conversion, no accidental learner-facing CompTIA or SY0-701 identity should remain in the SC-900 application.

Repository-only historical references are acceptable only where they intentionally document provenance from the v8 source baseline. They must not appear as current SC-900 application identity, release identity, default-bank identity, or user-facing certification content.

## Verification Gate

The initial SC-900 baseline is complete only when all of the following pass:

- full v8 application transplanted
- no SY0-701 question banks shipped as SC-900 content
- no accidental learner-facing Security+/CompTIA branding
- SC-900 Test Learning Engine branding applied
- SC-900-specific runtime data directory used
- `SC900TestLearningEngine.exe` release identity configured
- centralized certification/profile configuration present
- placeholder SC-900 bank loads successfully
- Practice mode works
- Smart Practice works
- Exam mode works
- progress save/resume works
- analytics opens and calculates
- issue reporting/quarantine works
- answer shuffling remains valid
- bank validator passes
- unit/regression tests pass
- smoke test passes
- benchmark guard remains usable
- Ruff passes
- Black check passes
- mypy passes
- Windows build/release tooling passes
- release manifest hashes the SC-900 bank and records the correct bank count
- README, disclaimer, and source policy are updated

## Release/Smoke-Test Adaptation

The current source application hard-codes release names, runtime paths, default bank filenames, and a fixed expected bank size. The SC-900 migration should remove those SY0-701-specific assumptions from the SC-900 release path.

The placeholder bank count may initially be small. Release and smoke-test checks must verify the configured SC-900 bank rather than assuming the historical SY0-701 count of 1231.

The smoke test should continue to verify:

- valid Windows PE output where applicable
- release and checkout executable identities
- release manifest integrity
- executable hash
- bank hash
- expected configured bank count
- bank validation
- focused release tests

## Testing Strategy

Migration work should be performed with regression protection rather than by broad search-and-replace.

Tests should cover at minimum:

1. certification/profile configuration resolves the SC-900 identity and bank path
2. runtime data is isolated from the SY0-701 application's local data
3. SC-900 placeholder bank loads and validates
4. all three study flows can build sessions from the SC-900 bank
5. progress keys and persistence remain stable inside the SC-900 application
6. release tooling produces SC-900-specific artifact names
7. the release manifest records SC-900 bank metadata
8. no forbidden learner-facing SY0-701/CompTIA strings remain on expected UI/release surfaces
9. existing adaptive-engine regression tests remain passing unless a test is explicitly certification-specific and is intentionally adapted

## Development Sequence

Implementation should proceed in this order:

1. preserve the source v8 baseline identity and record its source revision
2. transplant reusable files into the SC-900 repository
3. exclude SY0-701 bank/source-content artifacts
4. introduce centralized SC-900 profile/configuration values
5. apply application/runtime/build rebranding
6. add an original placeholder SC-900 bank
7. adapt certification-specific tests and release expectations
8. run bank validation, unit/regression tests, smoke tests, benchmarks, and quality checks
9. fix migration-only failures without redesigning Smart Practice
10. mark the passing commit as the SC-900 v8 baseline

A later content-ingestion task will import public/permitted SC-900 material through a staging and validation pipeline.

## Post-Baseline Development Policy

After the SC-900 baseline passes, the SC-900 repository becomes the primary experimental repository for improving v8.

The SY0-701 repository remains the reference implementation. Improvements proven in SC-900 may later be backported intentionally. A certification-neutral shared engine/core may be extracted in the future, but that refactor is outside this baseline migration.

## Success State

The target success state is a fully functioning SC-900-branded v8 application whose core learning behavior matches the proven SY0-701 baseline, whose runtime/build/content identity is isolated for SC-900, and whose content pipeline is ready to accept validated SC-900 source material without contaminating engine logic.
