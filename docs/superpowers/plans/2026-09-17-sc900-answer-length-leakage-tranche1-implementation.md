# SC-900 Answer-Length Leakage Tranche 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build reusable answer-length leakage audit and bank-integrity gates, prove the learner-history safety boundary, and prepare Tranche 1 for the highest-severity leakage cases without mutating production content until compatibility is proven.

**Architecture:** Add a read-only deterministic audit module and a baseline-vs-candidate invariant guard. Before any bank wording edit, execute an explicit content-epoch compatibility gate against the repository’s existing canonical-ID/fingerprint migration semantics. If wording changes still quarantine existing learner state as `CHANGED_CONTENT`, stop this package after the audit/gating foundation and return that blocker; do not weaken identity semantics or invent a new migration system inside this tranche.

**Tech Stack:** Python 3.11, stdlib `json`/`argparse`/`hashlib`/`collections`, repository `unittest`, existing `question_bank`, `question_identity`, `tools.validate_bank`, `tools.lint_bank`, and GitHub Actions/repository CI.

**Spec:** `docs/superpowers/specs/2026-09-17-sc900-answer-length-leakage-repair-design.md`

## Global Constraints

- Start implementation from the then-current `main`; the design baseline is `23d440b6976b9f6bbb3b77285bf0d11effc2513f`, but refresh `main` before branching and reconcile only if intervening changes touch the final bank, identity/migration code, bank validation, or the new audit surface.
- Production runtime bank remains `sc900_bank_v8_final.json` with exactly `454` questions.
- Final strong target remains `STRICT_LONGEST_CORRECT_RATE < 40%` and `UNIQUE_LONGEST_HEURISTIC_SUCCESS < 40%`, with no domain above `45%` strict-longest-correct.
- Do not create shortest-answer or answer-letter shortcuts while reducing longest-answer leakage.
- Do not change canonical question IDs, correct-answer keys, objective codes, `exam_calibration_tier`, or exam eligibility.
- Do not modify scoring, Smart Practice selection, readiness, analytics semantics, confidence controls, or UI behavior.
- Do not merge or modify PR #13. Keep `research/sc900-cand01r3-measurement-001` at `fc7d32f976c0b4c75658ff67d8d47ebe53d854bb`.
- Do not modify recovery refs `b567d4b74a2f99e50022dd0dafd81ffa75dff0a2` and `bbc3bd900b73bde89151dc51706ad62fc69e8196`.
- Do not refresh the repository-root EXE in this package.
- Microsoft Learn is the factual authority for semantic wording changes. No Practice Assessment or third-party question wording may be copied.
- TDD is mandatory for reusable audit/gating code: RED first, then the smallest GREEN implementation, then focused and full regression.
- The existing identity authority is fail-closed: same canonical ID plus different durable content is currently classified as `CHANGED_CONTENT` and quarantined rather than silently inheriting learner state. Do not weaken this behavior without a separately approved design.

---

## File structure for this plan

### Create

- `tools/answer_length_audit.py` — deterministic read-only leakage metrics, outlier ranking, JSON/Markdown rendering, and CLI.
- `tools/bank_revision_guard.py` — baseline-vs-candidate invariant comparison for IDs, keys, objectives, tiers, eligibility, count, and bias substitution checks.
- `tests/test_answer_length_audit.py` — synthetic TDD coverage for longest/shortest/letter/domain/outlier behavior.
- `tests/test_bank_revision_guard.py` — synthetic and production-bank invariant-gate coverage.
- `tests/test_answer_length_history_compatibility.py` — explicit characterization of current fingerprint/migration behavior for wording-only revisions.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/00-TRANCHE1-BASELINE.md` — reproducible baseline and top-outlier receipt.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/01-HISTORY-COMPATIBILITY-GATE.md` — result of the required content-epoch safety gate.

### Conditionally create only if the history-compatibility gate passes without changing identity architecture

- `content/sc900/answer-length-repair/tranche1/patches.json` — reviewed, explicit question-by-question wording patch manifest for 40-60 highest-severity safe cases.
- `content/sc900/answer-length-repair/tranche1/candidate_bank.json` — deterministic candidate generated from the active bank plus `patches.json`.
- `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/02-TRANCHE1-REVIEW.md` — before/after semantic and statistical review artifact.
- `tests/test_answer_length_tranche1_candidate.py` — candidate-specific invariant and reproducibility coverage.

### Do not modify in the initial safety foundation

- `sc900_bank_v8_final.json`
- `question_identity.py`
- `session_store.py`
- `runtime_persistence.py`
- any CAND-01R3 files
- `SC900TestLearningEngine.exe`

---

### Task 1: Build the deterministic answer-length audit

**Files:**
- Create: `tools/answer_length_audit.py`
- Create: `tests/test_answer_length_audit.py`

**Interfaces:**
- Consumes: question dictionaries from `question_bank.load_bank(path)["questions"]`.
- Produces:
  - `normalize_choice_text(value: object) -> str`
  - `choice_length(value: object) -> tuple[int, int]` returning `(character_count, word_count)` after whitespace normalization.
  - `analyze_question(question: dict) -> dict | None`
  - `analyze_bank(questions: list[dict]) -> dict`
  - `rank_longest_outliers(question_rows: list[dict]) -> list[dict]`
  - `write_json_report(report: dict, path: Path) -> None`
  - `write_markdown_report(report: dict, path: Path) -> None`
  - CLI: `python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out <path> --markdown-out <path>`.

- [ ] **Step 1: Write synthetic RED tests for analyzability and length normalization.**

```python
class AnswerLengthAuditTests(unittest.TestCase):
    def test_single_answer_question_reports_length_metrics(self):
        question = {
            "id": "q1",
            "question_type": "single",
            "domain": "Domain A",
            "choices": {"A": "short", "B": "the clearly much longer correct choice", "C": "medium text", "D": "other"},
            "correct": ["B"],
        }
        row = analyze_question(question)
        self.assertIsNotNone(row)
        self.assertTrue(row["correct_is_strict_longest"])
        self.assertEqual("B", row["correct_letter"])
        self.assertGreater(row["correct_characters"], row["max_distractor_characters"])

    def test_non_single_question_is_not_analyzable(self):
        question = {"id": "q2", "question_type": "multiple", "choices": {"A": "x", "B": "y"}, "correct": ["A", "B"]}
        self.assertIsNone(analyze_question(question))
```

- [ ] **Step 2: Run the focused tests and verify RED.**

Run:

```bash
python -m unittest tests.test_answer_length_audit -v
```

Expected: import/function failures because `tools.answer_length_audit` does not exist yet.

- [ ] **Step 3: Implement normalization and per-question analysis minimally.**

Use whitespace normalization only; do not strip meaningful punctuation or alter the bank:

```python
def normalize_choice_text(value: object) -> str:
    return " ".join(str(value or "").split())


def choice_length(value: object) -> tuple[int, int]:
    text = normalize_choice_text(value)
    return len(text), len(text.split())
```

`analyze_question()` must require:
- `question_type == "single"`;
- exactly one correct letter;
- correct letter present in non-empty `choices`;
- at least two non-empty choices.

Its returned row must include canonical ID, question number, domain, correct letter, per-choice character/word counts, strict/tied longest, strict/tied shortest, absolute correct-vs-strongest-distractor gap, relative gap, and answer-letter metadata.

- [ ] **Step 4: Write RED tests for bank-level longest, shortest, letter, and domain metrics.**

```python
def test_bank_metrics_detect_longest_and_shortest_heuristics(self):
    questions = [
        make_question("q1", "A", {"A": "123456789", "B": "12", "C": "123", "D": "1234"}, domain="D1"),
        make_question("q2", "D", {"A": "123456", "B": "12345", "C": "1234", "D": "1"}, domain="D1"),
    ]
    report = analyze_bank(questions)
    self.assertEqual(2, report["analyzable_count"])
    self.assertEqual(0.5, report["strict_longest_correct_rate"])
    self.assertEqual(0.5, report["strict_shortest_correct_rate"])
    self.assertEqual({"A": 1, "D": 1}, report["correct_letter_distribution"])
```

- [ ] **Step 5: Implement bank aggregation and deterministic outlier ranking.**

`rank_longest_outliers()` must include only rows with a positive correct-vs-max-distractor character gap and sort by:

```python
key=lambda row: (
    -row["relative_gap"],
    -row["absolute_gap"],
    str(row["question_id"]),
)
```

This makes severity deterministic and prioritizes proportionally extreme cues before raw gap ties.

`analyze_bank()` must expose at least:
- `question_count`;
- `analyzable_count`;
- `strict_longest_correct_count/rate`;
- `correct_among_longest_count/rate`;
- `unique_longest_question_count`;
- `unique_longest_heuristic_success_count/rate`;
- `strict_shortest_correct_count/rate`;
- `unique_shortest_question_count`;
- `unique_shortest_heuristic_success_count/rate`;
- `correct_letter_distribution` and rates;
- per-domain versions of the above;
- `mean_correct_characters`;
- `mean_max_distractor_characters`;
- ordered `longest_outliers`.

- [ ] **Step 6: Add JSON and Markdown report rendering and CLI parsing.**

The Markdown report must show the overall metrics, per-domain table, correct-letter distribution, and top 60 outliers with question ID/number, correct letter, lengths, absolute gap, and relative gap. It must not print answer text into CI logs by default.

- [ ] **Step 7: Run focused tests GREEN.**

```bash
python -m unittest tests.test_answer_length_audit -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit Task 1.**

```bash
git add tools/answer_length_audit.py tests/test_answer_length_audit.py
git commit -m "feat: add deterministic answer-length leakage audit"
```

---

### Task 2: Add a baseline-vs-candidate bank revision guard

**Files:**
- Create: `tools/bank_revision_guard.py`
- Create: `tests/test_bank_revision_guard.py`

**Interfaces:**
- Consumes: baseline and candidate question lists plus reports from `tools.answer_length_audit.analyze_bank`.
- Produces:
  - `question_invariants(question: dict) -> dict`
  - `compare_bank_invariants(baseline: list[dict], candidate: list[dict]) -> list[str]`
  - `compare_bias_metrics(baseline_report: dict, candidate_report: dict, *, final_gate: bool = False) -> list[str]`
  - CLI returning exit code 1 on any invariant/bias failure.

- [ ] **Step 1: Write RED tests proving invariant drift fails closed.**

Create independent tests for:
- question removed;
- question added;
- canonical ID changed;
- correct key changed;
- `objective_code` changed;
- `exam_calibration_tier` changed;
- `exam_simulation_eligible` changed;
- count not equal to 454 for production-bank mode.

Example:

```python
def test_correct_key_change_fails(self):
    baseline = [question("q1", correct=["A"])]
    candidate = [question("q1", correct=["B"])]
    failures = compare_bank_invariants(baseline, candidate)
    self.assertTrue(any("CORRECT_KEYS_CHANGED" in item for item in failures))
```

- [ ] **Step 2: Run focused tests RED.**

```bash
python -m unittest tests.test_bank_revision_guard -v
```

Expected: import/function failure.

- [ ] **Step 3: Implement exact-ID invariant comparison.**

`question_invariants()` must project only:

```python
{
    "question_id": canonical_question_id(question),
    "correct": tuple(question.get("correct") or []),
    "objective_code": str(question.get("objective_code") or ""),
    "exam_calibration_tier": str(question.get("exam_calibration_tier") or ""),
    "exam_simulation_eligible": question.get("exam_simulation_eligible", True),
}
```

Compare by canonical ID, not question number. Return stable machine-readable failure strings beginning with the design names: `QUESTION_IDS_ADDED`, `QUESTION_IDS_REMOVED`, `CORRECT_KEYS_CHANGED`, `OBJECTIVE_CODES_CHANGED`, `TIERS_CHANGED`, `EXAM_ELIGIBILITY_CHANGED`, `QUESTION_COUNT_CHANGED`.

- [ ] **Step 4: Write RED tests for bias-substitution gates.**

Define “material” for this implementation as a **greater than 2.0 percentage-point bank-wide increase** in either strict-shortest or unique-shortest heuristic success, or a **greater than 2.0 percentage-point increase** in the most-common-answer-letter heuristic. For domains with at least 20 analyzable questions, a greater than 5.0 percentage-point worsening in strict-longest rate also fails a tranche candidate.

Final-gate requirements additionally enforce:
- strict-longest correct `< 0.40`;
- unique-longest heuristic success `< 0.40`;
- every sufficiently populated domain strict-longest `<= 0.45`.

- [ ] **Step 5: Implement `compare_bias_metrics`.**

Tranche mode must require the candidate to improve at least one of `strict_longest_correct_rate` or `unique_longest_heuristic_success_rate` and not worsen either by more than 0.005. It must enforce the 0.02 shortest/position substitution limits above.

- [ ] **Step 6: Add CLI.**

Required command shape:

```bash
python -m tools.bank_revision_guard \
  --baseline sc900_bank_v8_final.json \
  --candidate path/to/candidate.json \
  --mode tranche
```

`--mode final` turns on the strong `<40%`/domain `<=45%` final thresholds.

- [ ] **Step 7: Run focused tests GREEN and commit.**

```bash
python -m unittest tests.test_bank_revision_guard -v
git add tools/bank_revision_guard.py tests/test_bank_revision_guard.py
git commit -m "feat: add bank revision leakage guard"
```

---

### Task 3: Reproduce the production baseline and lock the audit authority

**Files:**
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/00-TRANCHE1-BASELINE.md`
- Generated during verification but do not commit unless intentionally governed: `reports/answer_length_baseline.json`

**Interfaces:**
- Consumes: current `sc900_bank_v8_final.json`.
- Produces: reproducible metrics and top-outlier list used to select Tranche 1.

- [ ] **Step 1: Verify source authority before measurement.**

Run:

```bash
python - <<'PY'
from pathlib import Path
import hashlib
p = Path('sc900_bank_v8_final.json')
print(hashlib.sha256(p.read_bytes()).hexdigest())
PY
python -m tools.lint_bank
python -m tools.verify_installation
```

Record the exact source SHA-256, question count, lint disposition, and current `main` SHA.

- [ ] **Step 2: Run the new audit twice and prove deterministic byte-identical JSON output.**

```bash
python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out /tmp/audit1.json --markdown-out /tmp/audit1.md
python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out /tmp/audit2.json --markdown-out /tmp/audit2.md
cmp /tmp/audit1.json /tmp/audit2.json
```

Expected: `cmp` exits 0.

- [ ] **Step 3: Assert the measured baseline matches the previously observed pattern closely enough to establish continuity.**

The authoritative new tool output becomes the baseline, but investigate rather than silently accept if any of these differ materially from the prior read-only audit:
- analyzable count near `449`;
- strict-longest correct near `64.81%`;
- unique-longest heuristic success near `67.52%`.

A difference greater than 1.0 percentage point or more than 5 analyzable questions requires root-cause explanation before continuing.

- [ ] **Step 4: Write the baseline receipt.**

Include:
- exact main SHA;
- source bank SHA-256;
- exact audit command;
- overall/per-domain metrics;
- A/B/C/D distribution;
- shortest-answer metrics;
- top 60 outlier IDs and severity values;
- statement that no bank content changed.

- [ ] **Step 5: Commit the receipt.**

```bash
git add docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/00-TRANCHE1-BASELINE.md
git commit -m "docs: record answer-length leakage baseline"
```

---

### Task 4: Execute the learner-history compatibility gate before any wording edit

**Files:**
- Create: `tests/test_answer_length_history_compatibility.py`
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/01-HISTORY-COMPATIBILITY-GATE.md`
- Read only: `question_identity.py`, `session_store.py`, `runtime_persistence.py`, `tests/test_backlog1_segment3_adversarial_closure.py`, `tests/test_sc900_final_bank_activation_migration.py`

**Interfaces:**
- Consumes: `question_content_fingerprint`, `bank_content_fingerprint`, `migrate_progress_content_epoch`, session bank fingerprint checks.
- Produces: one of exactly two dispositions:
  - `LEARNER_HISTORY_COMPATIBILITY = PASS_WITH_EXISTING_ARCHITECTURE`
  - `LEARNER_HISTORY_COMPATIBILITY = BLOCKED_BY_CHANGED_CONTENT_QUARANTINE`

- [ ] **Step 1: Write a characterization test for choice-wording change.**

Construct one canonical question and canonical progress payload using the existing epoch fields, then change only one distractor’s text while preserving ID, key, objective, tier, and eligibility:

```python
def test_wording_only_choice_edit_changes_content_fingerprint_and_quarantines_prior_state(self):
    original = make_question("sc900-x", choices={"A": "one", "B": "two", "C": "three", "D": "four"}, correct=["A"])
    revised = deepcopy(original)
    revised["choices"]["D"] = "a more realistic distractor"

    payload = canonical_progress_for([original], {"sc900-x": {"attempts": 7}})
    migrated, changed = migrate_progress_content_epoch(payload, [revised])

    self.assertTrue(changed)
    self.assertNotEqual(question_content_fingerprint(original), question_content_fingerprint(revised))
    self.assertNotIn("sc900-x", migrated["questions"])
    self.assertEqual("CHANGED_CONTENT", migrated["quarantined_questions"]["sc900-x"]["reason"])
```

This is a characterization test of the intended existing safety behavior; do not alter production identity code to make it pass differently.

- [ ] **Step 2: Add a session characterization proving revised bank fingerprint invalidates old saved-session identity.**

Use `build_session_snapshot`, `saved_session_matches_current`, and `migrate_session_snapshot` in the same style as `tests/test_sc900_final_bank_activation_migration.py`. A wording change that changes bank fingerprint must not be silently treated as the same saved session.

- [ ] **Step 3: Run the compatibility tests.**

```bash
python -m unittest tests.test_answer_length_history_compatibility -v
```

Expected under the current repository design: tests PASS while proving changed wording is fail-closed as `CHANGED_CONTENT` and old session fingerprints do not match.

- [ ] **Step 4: Make the package-level safety decision.**

If the result is the expected `CHANGED_CONTENT` quarantine, set:

```text
LEARNER_HISTORY_COMPATIBILITY = BLOCKED_BY_CHANGED_CONTENT_QUARANTINE
TRANCHE1_CONTENT_REWRITE_AUTHORIZED = NO
NEW_IDENTITY_OR_MIGRATION_ARCHITECTURE_AUTHORIZED = NO
```

Then **STOP before Task 5**. This is not a failed implementation; it is the design’s mandatory fail-closed stop condition. Return the evidence for external review and request a separate decision on whether learner state for deliberately reworded questions may be explicitly reset/quarantined, or whether a new reviewed content-revision migration contract is desired.

Only if the existing architecture already provides a reviewed mechanism that preserves learner state across semantically equivalent wording changes without weakening fingerprint safety may execution continue to Task 5. Do not invent such a mechanism during this package.

- [ ] **Step 5: Write and commit the compatibility receipt.**

The receipt must state the exact behavior observed for progress history and sessions, include the focused test command/result, and explicitly say whether content rewriting is authorized to continue.

```bash
git add tests/test_answer_length_history_compatibility.py docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/01-HISTORY-COMPATIBILITY-GATE.md
git commit -m "test: characterize answer-length revision history safety"
```

---

## Conditional continuation — execute only if Task 4 returns PASS_WITH_EXISTING_ARCHITECTURE

Tasks 5-7 are deliberately conditional. They are not authorization to alter identity/migration semantics. If Task 4 returns `BLOCKED_BY_CHANGED_CONTENT_QUARANTINE`, do not execute them.

### Task 5: Create a deterministic Tranche 1 patch format and candidate builder

**Files:**
- Create: `tools/build_answer_length_tranche.py`
- Create: `tests/test_answer_length_tranche1_candidate.py`
- Create: `content/sc900/answer-length-repair/tranche1/patches.json`
- Generate: `content/sc900/answer-length-repair/tranche1/candidate_bank.json`

**Interfaces:**
- Patch manifest entry shape:

```json
{
  "question_id": "<canonical-id>",
  "classification": "mechanical|semantic",
  "choice_updates": {"A": "new text"},
  "choice_explanation_updates": {},
  "authority_refs": []
}
```

- Builder: `build_candidate(source_path: Path, patch_path: Path) -> dict`.
- Builder may modify only `choices` and corresponding `choice_explanations`; it must reject any request to change `correct`, ID, objective, tier, eligibility, prompt, domain, or question count in Tranche 1.

- [ ] **Step 1: Write RED tests that reject unauthorized patch fields and unknown IDs.**
- [ ] **Step 2: Implement the minimal deterministic patch builder.**
- [ ] **Step 3: Select the top 40-60 baseline outliers by the Task 3 deterministic ranking, reducing scope when factual review is difficult.**
- [ ] **Step 4: For each selected question, author the smallest safe wording repair using the approved order: tighten verbose correct answer first, strengthen implausibly terse distractors second, rebalance both only when needed.**
- [ ] **Step 5: For every semantic edit, record current Microsoft Learn authority in `authority_refs`; if official support is insufficient, leave the question unchanged.**
- [ ] **Step 6: Generate candidate twice and `cmp` outputs to prove reproducibility.**
- [ ] **Step 7: Commit manifest, builder, tests, and candidate.**

---

### Task 6: Run mechanical, semantic, and statistical admission gates on Tranche 1

**Files:**
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/02-TRANCHE1-REVIEW.md`
- Test: `tests/test_answer_length_tranche1_candidate.py`

- [ ] **Step 1: Run bank invariant guard.**

```bash
python -m tools.bank_revision_guard \
  --baseline sc900_bank_v8_final.json \
  --candidate content/sc900/answer-length-repair/tranche1/candidate_bank.json \
  --mode tranche
```

Expected: zero invariant failures; leakage improves without >2pp shortest/position substitution.

- [ ] **Step 2: Run generic bank validation on candidate.**

```bash
python - <<'PY'
from pathlib import Path
from tools.validate_bank import validate_bank
r = validate_bank(Path('content/sc900/answer-length-repair/tranche1/candidate_bank.json'))
assert r['question_count'] == 454, r['question_count']
assert not r['issues'], r['issues']
print('candidate validation PASS', len(r.get('warnings', [])), 'warnings')
PY
```

Existing governed production warnings must be distinguished from new warnings; a new warning fails closed until reviewed.

- [ ] **Step 3: Audit candidate and compare against baseline.**

Produce overall/per-domain metrics and top remaining outliers. Do not claim the final `<40%` target after Tranche 1 unless it is actually reached; the tranche only needs safe directional improvement.

- [ ] **Step 4: Perform line-by-line semantic review of every edited question.**

For each question record:
- before and after choice text;
- mechanical vs semantic classification;
- official authority for semantic edits;
- correct key unchanged;
- all distractors remain clearly incorrect;
- explanation remains consistent;
- no padding/filler;
- no new style cue.

Any uncertain item is removed from `patches.json`, candidate regenerated, and all gates rerun.

- [ ] **Step 5: Run focused tests, identity tests, and full suite.**

```bash
python -m unittest tests.test_answer_length_audit tests.test_bank_revision_guard tests.test_answer_length_history_compatibility tests.test_answer_length_tranche1_candidate -v
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment3_adversarial_closure tests.test_sc900_final_bank_activation_migration -v
python -m unittest discover -s tests -v
python -m tools.run_quality_checks
python -m tools.verify_installation
```

If `tools.run_quality_checks` still reports the known baseline-identical `builder_identity.py` mypy issue on the then-current base, document exact baseline-vs-candidate equivalence; do not suppress or broaden type checking inside this package.

- [ ] **Step 6: Write and commit the Tranche 1 review artifact.**

The artifact must include source/candidate SHA-256, edited IDs, exact invariant attestations, baseline/candidate leakage metrics, per-domain metrics, shortest/letter checks, semantic authority table, tests, and remaining worst outliers.

---

### Task 7: External-review handoff only — no production activation

**Files:**
- No production bank replacement.
- No EXE replacement.

- [ ] **Step 1: Verify final branch diff contains only approved audit/gating/tranche artifacts.**
- [ ] **Step 2: Re-verify PR #13 and both recovery refs at their protected SHAs.**
- [ ] **Step 3: Open a draft PR for external review if and only if all executed gates pass.**
- [ ] **Step 4: Report exact head SHA and STOP.**

Required terminal report:

```text
WORK_ID = SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001 / TRANCHE1
START_MAIN_SHA = <exact>
SOURCE_BANK_SHA256 = <exact>
AUDIT_TOOLING = PASS/FAIL
BASELINE_ANALYZABLE = <count>
BASELINE_STRICT_LONGEST = <count/rate>
BASELINE_UNIQUE_LONGEST_HEURISTIC = <count/rate>
HISTORY_COMPATIBILITY = PASS_WITH_EXISTING_ARCHITECTURE/BLOCKED_BY_CHANGED_CONTENT_QUARANTINE
CONTENT_REWRITE_EXECUTED = YES/NO
TRANCHE1_EDITED_QUESTIONS = <count or 0>
CANDIDATE_BANK_SHA256 = <sha or N/A>
CANDIDATE_STRICT_LONGEST = <count/rate or N/A>
CANDIDATE_UNIQUE_LONGEST_HEURISTIC = <count/rate or N/A>
SHORTEST_SUBSTITUTION_GATE = PASS/FAIL/N/A
POSITIONAL_SUBSTITUTION_GATE = PASS/FAIL/N/A
QUESTION_COUNT = 454
QUESTION_IDS_CHANGED = 0
CORRECT_KEYS_CHANGED = 0
OBJECTIVE_CODES_CHANGED = 0
TIERS_CHANGED = 0
EXAM_ELIGIBILITY_CHANGED = 0
SEMANTIC_REVIEW = PASS/BLOCKED/N/A
FULL_REGRESSION = PASS/FAIL/N/A
PR13_MODIFIED = NO
RECOVERY_REFS_MODIFIED = NO
PRODUCTION_BANK_CHANGED = NO
PRODUCTION_EXE_CHANGED = NO
MERGED = NO
NEXT_ACTION = <history-policy decision or external tranche review>
```

---

## Plan self-review notes

### Spec coverage

- Deterministic read-only audit: Task 1.
- Longest/shortest/letter/domain metrics and severity ranking: Task 1.
- Stable IDs/keys/objective/tier/eligibility gates: Task 2.
- Strong final thresholds and substitution protection: Task 2.
- Reproducible production baseline: Task 3.
- Learner-history/session safety: Task 4.
- Fail-closed stop rather than inventing an identity architecture: Task 4.
- Bounded 40-60-question Tranche 1, Microsoft Learn semantic review, deterministic candidate: Task 5, conditional.
- Mechanical/semantic/statistical admission gates: Task 6, conditional.
- No merge/EXE/PR13/recovery mutation: Global Constraints and Task 7.

### Important planning discovery

The existing repository intentionally defines **same canonical ID + different durable content** as `CHANGED_CONTENT`, quarantining learner state rather than silently inheriting it. Choice text is part of `question_content_fingerprint`; saved sessions also bind to the bank fingerprint. Therefore the design’s learner-history requirement cannot be assumed to pass merely because canonical IDs stay stable. Task 4 is an explicit hard gate and is expected to expose this conflict on the current architecture. The plan does not authorize weakening that safety behavior.
