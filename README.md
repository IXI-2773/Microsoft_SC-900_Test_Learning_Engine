# Microsoft SC-900 Test Learning Engine v8

A Windows-first study and exam-practice engine for **Microsoft SC-900: Microsoft Security, Compliance, and Identity Fundamentals**.

The project combines a calibrated SC-900 question bank with practice, exam simulation, adaptive Smart Practice, spaced review, confidence tracking, learner analytics, persistence, session resume, and Windows packaging. The current production runtime uses the finalized **454-question** bank.

> This is an independent study project. It is not an official Microsoft product and is not affiliated with or endorsed by Microsoft.

## Current production status

| Item | Current state |
| --- | --- |
| Engine version | `8.0.0` |
| Certification | Microsoft SC-900 |
| Runtime bank | `sc900_bank_v8_final.json` |
| Total active questions | **454** |
| Fundamentals Core | **301** |
| Fundamentals Applied | **130** |
| Stretch | **23** |
| Ordinary Exam-eligible pool | **431** |
| Windows executable | `SC900TestLearningEngine.exe` |
| Active bank SHA-256 | `177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c` |
| Windows executable SHA-256 | `7155577732d488711092c9145fff93895b1ae206391112c06cc41e135cbbd399` |

The historical eight-question v8 placeholder bank is retained only as a baseline/recovery artifact. It is **not** the active production question bank.

## Quick start on Windows

1. Download `SC900TestLearningEngine.exe` from the repository root.
2. Place it in a normal writable folder.
3. Double-click the executable.
4. Choose a study mode and begin a set.

Python is not required for normal use of the packaged Windows executable.

Windows SmartScreen or antivirus software may warn about an independently built unsigned executable. Verify the SHA-256 above if you want to confirm the file matches the repository's verified build.

## What the engine does

The application is designed to be more than a static multiple-choice question viewer. It tracks what you have seen, where you are weak, when material is due again, how confident you were, what kinds of mistakes you make, and which questions are most useful to show next.

Major capabilities include:

- Practice sets with configurable question counts and filters.
- Exam-style sessions from the exam-eligible pool.
- Smart Practice that prioritizes useful review rather than simple random repetition.
- Due Review for scheduled recall work.
- Persistent progress, session state, learner history, flags, suspensions, and issue reports.
- Resume support for unfinished sessions.
- Confidence tracking and confidence-aware analytics.
- Weak-area, error-pattern, readiness, recall, transfer, and review analytics.
- Adaptive review scheduling and memory-oriented follow-up behavior.
- Optional study-game feedback such as streaks, XP, badges, milestones, quests, and session summaries.
- Question reporting and maintenance controls for problematic items.

## Study modes

### Practice

Practice mode can use the full active bank, including Stretch material. It is intended for ordinary study, topic/domain filtering, review, and broad coverage.

### Exam

A newly created ordinary Exam session draws only from questions marked `exam_simulation_eligible`.

The production bank contains:

- 301 Fundamentals Core questions
- 130 Fundamentals Applied questions
- 23 Stretch questions

The 23 Stretch questions are intentionally excluded from ordinary Exam creation, leaving **431 Exam-eligible questions**. Existing persisted historical sessions are restored from their recorded question identities rather than being retroactively rewritten.

### Smart Practice

Smart Practice can use the full bank, including Stretch material. Its purpose is to select useful questions from learner state rather than merely replaying random items.

Signals used by the wider learning engine include weak and due material, unseen coverage, recent history, recall state, confidence, repair state, concept relationships, question/source quality signals, repetition pressure, and session variety constraints.

### Due Review

Due Review surfaces material whose learner record indicates it is ready for another retrieval attempt. Review timing is persisted with the learner's progress.

## Confidence and learner state

The engine records more than correct/incorrect outcomes. Learner state supports confidence and epistemic signals such as **Sure**, **Unsure**, and **Guessed**, along with a **Super Confident** control for material the learner wants pushed farther out of ordinary review.

Confidence information is used for analysis and scheduling context; it does not alter the official answer key.

The application also preserves state such as:

- question attempts and outcomes
- wrong-answer history and recovery
- review scheduling
- flags and suspended questions
- reported-question issues
- session identity and resume information
- learner analytics and study-game state

## Analytics and readiness

The analytics layer is intended to help answer questions such as:

- Which domains and concepts are weakest?
- Which mistakes are repeating?
- Are errors associated with low confidence, overconfidence, speed, recall failure, or confusion between concepts?
- Which questions or concepts are due for review?
- Is performance improving over time?
- Are repeated correct answers transferring to related questions?

The engine exposes an internal readiness percentage as a **study heuristic**.

It is **not a conversion to Microsoft's reported scaled exam score**. Microsoft reports SC-900 on a scaled score with an official passing score of **700**; this project does not infer Microsoft's scaled score from raw practice accuracy.

The configured internal readiness threshold is `82.5%` after sufficient evidence, currently requiring at least `120` attempts. That threshold is an internal study rule only.

## SC-900 coverage

The runtime profile follows the four SC-900 skill areas recorded by the project:

| Domain | Skill area | Weight |
| --- | --- | ---: |
| 1 | Describe the concepts of security, compliance, and identity | 10-15% |
| 2 | Describe the capabilities of Microsoft Entra | 25-30% |
| 3 | Describe the capabilities of Microsoft security solutions | 35-40% |
| 4 | Describe the capabilities of Microsoft compliance solutions | 20-25% |

## Question-bank methodology

The production bank was built and reviewed as a governed content pipeline rather than as an untracked collection of questions.

Project policy treats **current Microsoft Learn / official Microsoft documentation as factual authority** for SC-900 content. External practice or reference material may be used to understand aggregate exam style and difficulty, but not as authority for Microsoft facts and not as a source to copy protected question wording.

The final bank is divided into three calibration tiers:

| Tier | Count | Purpose | Ordinary Exam mode |
| --- | ---: | --- | --- |
| Fundamentals Core | 301 | Direct fundamentals and essential recognition | Eligible |
| Fundamentals Applied | 130 | Applied/scenario-oriented fundamentals | Eligible |
| Stretch | 23 | Higher-challenge study material | Excluded |

The active bank remains available to Practice and Smart Practice even when a question is not eligible for ordinary Exam simulation.

## Progress, persistence, and session resume

The engine saves learner state between launches. Packaged Windows builds store runtime user data under:

```text
%LOCALAPPDATA%\SC900TestLearningEngine
```

The persistence layer includes defensive migration, backup/checkpoint handling, invalid-file quarantine, and session identity checks designed to prevent a saved session from silently resuming against the wrong question set.

Source execution uses the repository's source-mode user-data path rather than the packaged Windows location.

## User interface and study feedback

The desktop interface supports question navigation, answer feedback, explanations, confidence controls, filtering, analytics, reported-question review, progress controls, and resumable study sessions.

The optional game layer provides study feedback such as XP, streaks, badges, milestones, quests, combo indicators, and end-of-session summaries. These features are motivational overlays; they do not change the canonical answer key.

## Testing and release verification

The repository uses automated regression, content, installation, quality, packaging, and smoke-test gates.

Typical verification commands are:

```powershell
python -m unittest discover -s tests -v
python tools/lint_bank.py
python tools/verify_installation.py
python tools/run_quality_checks.py
```

The consolidated Windows release is built and verified by GitHub Actions. The production workflow verifies tests and quality gates, exercises supporting tooling, builds the Windows package, checks packaged resources, performs non-interactive smoke verification, and publishes a release artifact.

Automated packaging verification does not replace human interaction testing. New packaged releases should still receive a short manual sanity pass for launch, navigation, Practice, Exam, Smart Practice, Due Review, session resume, persistence, and close/relaunch behavior.

## Run from source

The project CI uses Python 3.11.

```powershell
python app.py
```

For development verification:

```powershell
python -m unittest discover -s tests -v
python tools/lint_bank.py
python tools/verify_installation.py
python tools/run_quality_checks.py
```

## Repository guide

Important production files and areas include:

| Path | Purpose |
| --- | --- |
| `SC900TestLearningEngine.exe` | Verified Windows executable for normal use |
| `app.py` | Main desktop application |
| `cert_profile_sc900.json` | SC-900 identity, domains, scoring disclaimer, runtime-bank configuration |
| `cert_config.py` | Runtime certification configuration loader |
| `sc900_bank_v8_final.json` | Active 454-question production bank |
| `exam_runtime_eligibility.py` | Ordinary Exam eligibility filter |
| `smart_practice_core.py` | Smart Practice selection logic |
| `progress_models.py` / `progress_store.py` | Learner progress model and persistence |
| `session_models.py` / `session_store.py` | Session persistence |
| `confidence_epistemics.py` | Confidence-state integrity logic |
| `analytics_*.py` | Analytics models, summaries, and recommendations |
| `tools/` | Bank, quality, release, corpus, calibration, and verification tooling |
| `tests/` | Regression, bank, runtime, persistence, calibration, and release tests |
| `docs/research/` | Research, audit, activation, calibration, and handoff evidence |
| `.github/workflows/` | CI, release verification, and bounded repository automation |

## CAND-01R3 research

The repository also contains a separate controlled research lineage for **CAND-01R3** measurement work.

That work is intentionally isolated from the ordinary production engine. The frozen measurement PR/branch must not be interpreted as automatically deployed or production-authorized, and its empirical results must not be claimed before the controlled measurement protocol is actually executed and completed.

The production executable in `main` is the normal SC-900 learning engine, not the frozen CAND-01R3 experimental runtime.

## Branch and recovery notes

`main` is the production line.

The repository also retains:

- the CAND-01R3 research branch and its required base while that controlled research remains open;
- recovery refs that preserve exact historical states needed for repository recovery and provenance.

Recovery refs are safety/history artifacts, not feature branches waiting to be merged.

## Important limitations

- This project does not contain or claim access to Microsoft's live certification exam.
- A high practice score or internal readiness score does not guarantee an SC-900 pass.
- Microsoft may change exam objectives, services, terminology, and scoring practices; current official Microsoft documentation remains the authority for those facts.
- Question quality controls reduce error risk but do not make the bank infallible. The application includes question-reporting mechanisms so questionable material can be reviewed.

## License

See `LICENSE` for the repository's license terms.
