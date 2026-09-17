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
  - `choice_length(value: object) -> tuple[int, int]`
  - `analyze_question(question: dict) -> dict | None`
  - `analyze_bank(questions: list[dict]) -> dict`
  - `rank_longest_outliers(question_rows: list[dict]) -> list[dict]`
  - `write_json_report(report: dict, path: Path) -> None`
  - `write_markdown_report(report: dict, path: Path) -> None`
  - CLI: `python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out <path> --markdown-out <path>`.

- [ ] **Step 1: Write the failing synthetic tests and local fixture helper.**

At the top of `tests/test_answer_length_audit.py`, define the helper used by every test in this task:

```python
def make_question(
    question_id: str,
    correct_letter: str,
    choices: dict[str, str],
    *,
    domain: str = "Domain A",
) -> dict:
    return {
        "id": question_id,
        "question_number": 1,
        "question_type": "single",
        "domain": domain,
        "choices": dict(choices),
        "correct": [correct_letter],
    }
```

Then add:

```python
class AnswerLengthAuditTests(unittest.TestCase):
    def test_single_answer_question_reports_length_metrics(self):
        question = make_question(
            "q1",
            "B",
            {"A": "short", "B": "the clearly much longer correct choice", "C": "medium text", "D": "other"},
        )
        row = analyze_question(question)
        self.assertIsNotNone(row)
        self.assertTrue(row["correct_is_strict_longest"])
        self.assertEqual("B", row["correct_letter"])
        self.assertGreater(row["correct_characters"], row["max_distractor_characters"])

    def test_non_single_question_is_not_analyzable(self):
        question = {
            "id": "q2",
            "question_type": "multiple",
            "choices": {"A": "x", "B": "y"},
            "correct": ["A", "B"],
        }
        self.assertIsNone(analyze_question(question))
```

- [ ] **Step 2: Run the focused tests and verify RED.**

```bash
python -m unittest tests.test_answer_length_audit -v
```

Expected: import/function failures because `tools.answer_length_audit` does not exist yet.

- [ ] **Step 3: Implement normalization and per-question analysis minimally.**

```python
def normalize_choice_text(value: object) -> str:
    return " ".join(str(value or "").split())


def choice_length(value: object) -> tuple[int, int]:
    text = normalize_choice_text(value)
    return len(text), len(text.split())
```

`analyze_question()` must require `question_type == "single"`, exactly one correct letter, the correct letter present in non-empty `choices`, and at least two non-empty choices. Its returned row must include canonical ID, question number, domain, correct letter, per-choice character/word counts, strict/tied longest, strict/tied shortest, absolute correct-vs-strongest-distractor gap, relative gap, and answer-letter metadata.

- [ ] **Step 4: Add RED tests for bank-level longest, shortest, letter, and domain metrics.**

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
    self.assertEqual(0.5, report["most_common_answer_letter_rate"])
```

- [ ] **Step 5: Implement bank aggregation and deterministic outlier ranking.**

`rank_longest_outliers()` must include only rows with positive `absolute_gap` and sort by:

```python
key=lambda row: (
    -row["relative_gap"],
    -row["absolute_gap"],
    str(row["question_id"]),
)
```

`analyze_bank()` must expose these exact keys:

```text
question_count
analyzable_count
strict_longest_correct_count
strict_longest_correct_rate
correct_among_longest_count
correct_among_longest_rate
unique_longest_question_count
unique_longest_heuristic_success_count
unique_longest_heuristic_success_rate
strict_shortest_correct_count
strict_shortest_correct_rate
unique_shortest_question_count
unique_shortest_heuristic_success_count
unique_shortest_heuristic_success_rate
correct_letter_distribution
correct_letter_rates
most_common_answer_letter_rate
mean_correct_characters
mean_max_distractor_characters
per_domain
longest_outliers
```

Each `per_domain` row uses the same rate-key names where applicable.

- [ ] **Step 6: Add JSON and Markdown report rendering and CLI parsing.**

The Markdown report shows overall metrics, a per-domain table, correct-letter distribution, and the top 60 outliers with question ID/number, correct letter, lengths, absolute gap, and relative gap. Do not print answer text into CI logs by default.

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
  - `compare_bank_invariants(baseline: list[dict], candidate: list[dict], *, expected_count: int | None = None) -> list[str]`
  - `compare_bias_metrics(baseline_report: dict, candidate_report: dict, *, final_gate: bool = False) -> list[str]`
  - CLI returning exit code 1 on any invariant/bias failure.

- [ ] **Step 1: Write RED tests with a local fixture helper.**

At the top of `tests/test_bank_revision_guard.py`:

```python
def question(
    question_id: str,
    *,
    correct: list[str] | None = None,
    objective_code: str = "1.1",
    tier: str = "CORE",
    eligible: bool = True,
) -> dict:
    return {
        "id": question_id,
        "question_number": 1,
        "question_type": "single",
        "choices": {"A": "a", "B": "bb", "C": "ccc", "D": "dddd"},
        "correct": list(correct or ["A"]),
        "objective_code": objective_code,
        "exam_calibration_tier": tier,
        "exam_simulation_eligible": eligible,
    }
```

Add independent tests for question removed, question added, canonical ID changed, correct key changed, `objective_code` changed, `exam_calibration_tier` changed, `exam_simulation_eligible` changed, and `expected_count` mismatch.

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

`question_invariants()` projects exactly:

```python
{
    "question_id": canonical_question_id(question),
    "correct": tuple(question.get("correct") or []),
    "objective_code": str(question.get("objective_code") or ""),
    "exam_calibration_tier": str(question.get("exam_calibration_tier") or ""),
    "exam_simulation_eligible": question.get("exam_simulation_eligible", True),
}
```

Compare by canonical ID, never by question number. Stable failure strings begin with `QUESTION_IDS_ADDED`, `QUESTION_IDS_REMOVED`, `CORRECT_KEYS_CHANGED`, `OBJECTIVE_CODES_CHANGED`, `TIERS_CHANGED`, `EXAM_ELIGIBILITY_CHANGED`, or `QUESTION_COUNT_CHANGED`.

- [ ] **Step 4: Add RED tests for bias-substitution gates.**

For this implementation, “material” means:
- more than `0.02` bank-wide increase in `strict_shortest_correct_rate`;
- more than `0.02` increase in `unique_shortest_heuristic_success_rate`;
- more than `0.02` increase in `most_common_answer_letter_rate`;
- for domains with at least 20 analyzable questions, more than `0.05` worsening in `strict_longest_correct_rate`.

Final gate additionally requires bank-wide strict-longest `< 0.40`, unique-longest heuristic `< 0.40`, and sufficiently populated domain strict-longest `<= 0.45`.

- [ ] **Step 5: Implement `compare_bias_metrics`.**

Tranche mode requires improvement in at least one of `strict_longest_correct_rate` or `unique_longest_heuristic_success_rate`, allows no more than `0.005` worsening in the other, and enforces the substitution limits above.

- [ ] **Step 6: Add CLI.**

```bash
python -m tools.bank_revision_guard \
  --baseline sc900_bank_v8_final.json \
  --candidate path/to/candidate.json \
  --expected-count 454 \
  --mode tranche
```

`--mode final` enables the strong final thresholds.

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
- Ephemeral: `/tmp/sc900-answer-length-audit-1.json`, `/tmp/sc900-answer-length-audit-2.json`

**Interfaces:**
- Consumes: current `sc900_bank_v8_final.json`.
- Produces: reproducible metrics and top-outlier list used to select Tranche 1.

- [ ] **Step 1: Verify source authority before measurement.**

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

Record exact source SHA-256, question count, lint disposition, and current `main` SHA.

- [ ] **Step 2: Run the audit twice and prove deterministic byte-identical JSON output.**

```bash
python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out /tmp/sc900-answer-length-audit-1.json --markdown-out /tmp/sc900-answer-length-audit-1.md
python -m tools.answer_length_audit --bank sc900_bank_v8_final.json --json-out /tmp/sc900-answer-length-audit-2.json --markdown-out /tmp/sc900-answer-length-audit-2.md
cmp /tmp/sc900-answer-length-audit-1.json /tmp/sc900-answer-length-audit-2.json
```

Expected: `cmp` exits 0.

- [ ] **Step 3: Check continuity against the prior read-only audit.**

Investigate rather than silently accept if the authoritative new tool differs by more than 1.0 percentage point or more than 5 analyzable questions from the previously observed `449`, `64.81%` strict-longest, and `67.52%` unique-longest heuristic figures.

- [ ] **Step 4: Write the baseline receipt.**

Include exact main SHA, bank SHA-256, audit command, overall/per-domain metrics, A/B/C/D distribution, shortest-answer metrics, top 60 outlier IDs/severity values, and `BANK_CONTENT_CHANGED = NO`.

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
- Consumes: `question_content_fingerprint`, `bank_content_fingerprint`, `migrate_progress_content_epoch`, `saved_session_matches_current`.
- Produces exactly one disposition:
  - `LEARNER_HISTORY_COMPATIBILITY = PASS_WITH_EXISTING_ARCHITECTURE`
  - `LEARNER_HISTORY_COMPATIBILITY = BLOCKED_BY_CHANGED_CONTENT_QUARANTINE`

- [ ] **Step 1: Add exact local helpers to the new test module.**

```python
from copy import deepcopy

from question_identity import (
    PROGRESS_CONTENT_EPOCH_VERSION,
    PROGRESS_IDENTITY_KIND,
    PROGRESS_IDENTITY_VERSION,
    bank_content_fingerprint,
    canonical_question_id,
    migrate_progress_content_epoch,
    question_content_fingerprint,
)


def make_question(question_id: str, *, choices: dict[str, str], correct: list[str]) -> dict:
    return {
        "id": question_id,
        "question_number": 1,
        "question_type": "single",
        "prompt": "Which option is correct?",
        "domain": "Describe the concepts of security, compliance, and identity",
        "topics": ["test"],
        "objective_code": "1.1",
        "exam_calibration_tier": "CORE",
        "exam_simulation_eligible": True,
        "choices": dict(choices),
        "correct": list(correct),
        "general_explanation": "Test explanation.",
        "choice_explanations": {letter: f"Explanation {letter}" for letter in choices},
    }


def canonical_progress_for(questions: list[dict], records: dict) -> dict:
    fingerprints = {
        canonical_question_id(question): question_content_fingerprint(question) for question in questions
    }
    return {
        "version": 3,
        "progress_identity_version": PROGRESS_IDENTITY_VERSION,
        "question_identity": PROGRESS_IDENTITY_KIND,
        "progress_content_epoch_version": PROGRESS_CONTENT_EPOCH_VERSION,
        "bank_fingerprint": bank_content_fingerprint(questions),
        "question_content_fingerprints": fingerprints,
        "questions": deepcopy(records),
        "history": [],
    }
```

- [ ] **Step 2: Add the wording-change characterization test.**

```python
def test_wording_only_choice_edit_changes_content_fingerprint_and_quarantines_prior_state(self):
    original = make_question(
        "sc900-x",
        choices={"A": "one", "B": "two", "C": "three", "D": "four"},
        correct=["A"],
    )
    revised = deepcopy(original)
    revised["choices"]["D"] = "a more realistic distractor"

    payload = canonical_progress_for([original], {"sc900-x": {"attempts": 7}})
    migrated, changed = migrate_progress_content_epoch(payload, [revised])

    self.assertTrue(changed)
    self.assertNotEqual(question_content_fingerprint(original), question_content_fingerprint(revised))
    self.assertNotIn("sc900-x", migrated["questions"])
    self.assertEqual("CHANGED_CONTENT", migrated["quarantined_questions"]["sc900-x"]["reason"])
```

This characterizes the intended current safety behavior; do not change production identity code to make it pass differently.

- [ ] **Step 3: Add saved-session fingerprint mismatch coverage without inventing a migration path.**

Use a minimal saved-session mapping because `saved_session_matches_current` only needs the persisted identity fields for this assertion:

```python
def test_wording_only_edit_changes_bank_fingerprint_and_old_session_no_longer_matches(self):
    original = make_question(
        "sc900-x",
        choices={"A": "one", "B": "two", "C": "three", "D": "four"},
        correct=["A"],
    )
    revised = deepcopy(original)
    revised["choices"]["D"] = "a more realistic distractor"

    old_bank_fp = bank_content_fingerprint([original])
    new_bank_fp = bank_content_fingerprint([revised])
    self.assertNotEqual(old_bank_fp, new_bank_fp)

    saved = {
        "mode": "practice",
        "question_numbers": [1],
        "restore_question_numbers": [1],
        "question_ids": ["sc900-x"],
        "restore_question_ids": ["sc900-x"],
        "bank_fingerprint": old_bank_fp,
    }
    self.assertFalse(
        saved_session_matches_current(
            saved,
            "practice",
            [1],
            [1],
            bank_fingerprint=new_bank_fp,
            current_question_ids=["sc900-x"],
            restore_question_ids=["sc900-x"],
        )
    )
```

If the exact current `saved_session_matches_current` signature requires an additional explicit argument, use the signature from `session_store.py` without changing its semantics; do not pass a legacy-bypass flag.

- [ ] **Step 4: Run the compatibility tests.**

```bash
python -m unittest tests.test_answer_length_history_compatibility -v
```

Expected under current authority: tests PASS while proving wording changes trigger fail-closed content/session mismatch behavior.

- [ ] **Step 5: Make the package-level safety decision.**

If the result is `CHANGED_CONTENT` quarantine, record:

```text
LEARNER_HISTORY_COMPATIBILITY = BLOCKED_BY_CHANGED_CONTENT_QUARANTINE
TRANCHE1_CONTENT_REWRITE_AUTHORIZED = NO
NEW_IDENTITY_OR_MIGRATION_ARCHITECTURE_AUTHORIZED = NO
```

Then **STOP before Task 5**. This is the design’s mandatory fail-closed condition. Return evidence for a separate operator decision: either explicitly accept/reset learner state for deliberately reworded questions, or authorize a separately designed content-revision migration contract.

Only if the existing architecture already provides a reviewed mechanism that preserves learner state across semantically equivalent wording changes without weakening fingerprint safety may execution continue to Task 5. Do not invent such a mechanism here.

- [ ] **Step 6: Write and commit the compatibility receipt.**

```bash
git add tests/test_answer_length_history_compatibility.py docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/01-HISTORY-COMPATIBILITY-GATE.md
git commit -m "test: characterize answer-length revision history safety"
```

---

## Conditional continuation — execute only if Task 4 returns PASS_WITH_EXISTING_ARCHITECTURE

Tasks 5-7 are not authorization to alter identity/migration semantics. If Task 4 returns `BLOCKED_BY_CHANGED_CONTENT_QUARANTINE`, do not execute them.

### Task 5: Create deterministic Tranche 1 patch manifest and candidate builder

**Files:**
- Create: `tools/build_answer_length_tranche.py`
- Create: `tests/test_answer_length_tranche1_candidate.py`
- Create: `content/sc900/answer-length-repair/tranche1/patches.json`
- Generate: `content/sc900/answer-length-repair/tranche1/candidate_bank.json`

**Interfaces:**
- Patch entry:

```json
{
  "question_id": "sc900-example",
  "classification": "mechanical",
  "choice_updates": {"D": "Revised distractor text"},
  "choice_explanation_updates": {},
  "authority_refs": []
}
```

- Builder: `build_candidate(source_path: Path, patch_path: Path) -> dict`.
- Allowed Tranche 1 mutation fields: `choices`, `choice_explanations` only.
- Explicitly reject patch fields that target `correct`, ID, prompt, domain, objective, tier, eligibility, question number, or question count.

- [ ] **Step 1: Write RED tests that reject unknown IDs, duplicate patch IDs, and unauthorized fields.**

```python
def test_builder_rejects_correct_key_change(self):
    patch = {"question_id": "q1", "classification": "mechanical", "correct": ["B"]}
    with self.assertRaises(ValueError):
        validate_patch_entry(patch)
```

- [ ] **Step 2: Implement the deterministic builder and validate patch classifications.**
- [ ] **Step 3: Select the top 40-60 current outliers from the Task 3 ranking; reduce scope when semantic review is difficult.**
- [ ] **Step 4: Author the smallest safe wording repair per selected question: tighten verbose correct answer first, strengthen implausibly terse distractors second, rebalance both only when needed.**
- [ ] **Step 5: For every semantic edit, record current Microsoft Learn URLs/authority in `authority_refs`; if official support is insufficient, leave the item unchanged.**
- [ ] **Step 6: Generate candidate twice and prove byte-identical output.**

```bash
python -m tools.build_answer_length_tranche --source sc900_bank_v8_final.json --patches content/sc900/answer-length-repair/tranche1/patches.json --out /tmp/candidate1.json
python -m tools.build_answer_length_tranche --source sc900_bank_v8_final.json --patches content/sc900/answer-length-repair/tranche1/patches.json --out /tmp/candidate2.json
cmp /tmp/candidate1.json /tmp/candidate2.json
```

- [ ] **Step 7: Commit manifest, builder, tests, and governed candidate.**

---

### Task 6: Run mechanical, semantic, and statistical Tranche 1 admission gates

**Files:**
- Create: `docs/research/SC900-ANSWER-LENGTH-LEAKAGE-REPAIR-001/02-TRANCHE1-REVIEW.md`
- Test: `tests/test_answer_length_tranche1_candidate.py`

- [ ] **Step 1: Run invariant and substitution guard.**

```bash
python -m tools.bank_revision_guard \
  --baseline sc900_bank_v8_final.json \
  --candidate content/sc900/answer-length-repair/tranche1/candidate_bank.json \
  --expected-count 454 \
  --mode tranche
```

- [ ] **Step 2: Run generic candidate validation.**

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

Any new warning fails closed until explained. Do not use `--allow-warnings` as an acceptance override.

- [ ] **Step 3: Audit candidate and compare bank/domain/shortest/letter metrics to baseline.**
- [ ] **Step 4: Perform line-by-line semantic review for every edited question.** Record before/after text, classification, official authority for semantic edits, key unchanged, distractors clearly incorrect, explanation consistency, and absence of filler/new cues. Remove uncertain items and regenerate before continuing.
- [ ] **Step 5: Run focused, identity, and full regression.**

```bash
python -m unittest tests.test_answer_length_audit tests.test_bank_revision_guard tests.test_answer_length_history_compatibility tests.test_answer_length_tranche1_candidate -v
python -m unittest tests.test_backlog1_progress_identity_migration tests.test_backlog1_segment3_adversarial_closure tests.test_sc900_final_bank_activation_migration -v
python -m unittest discover -s tests -v
python -m tools.run_quality_checks
python -m tools.verify_installation
```

If `tools.run_quality_checks` reports a baseline-identical pre-existing issue, prove exact baseline-vs-candidate equivalence; do not suppress it inside this package.

- [ ] **Step 6: Write the Tranche 1 review artifact with source/candidate SHA-256, edited IDs, invariants, baseline/candidate metrics, per-domain metrics, shortest/letter checks, authority table, tests, and remaining outliers.**

---

### Task 7: External-review handoff only — no production activation

**Files:**
- No production-bank replacement.
- No EXE replacement.

- [ ] **Step 1: Verify final branch diff contains only approved audit/gating/tranche artifacts.**
- [ ] **Step 2: Re-verify PR #13 and both recovery refs at their protected SHAs.**
- [ ] **Step 3: Open a draft PR only if all executed gates pass.**
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
- Fail-closed stop rather than inventing identity architecture: Task 4.
- Bounded 40-60-question Tranche 1, Microsoft Learn semantic review, deterministic candidate: Task 5, conditional.
- Mechanical/semantic/statistical admission gates: Task 6, conditional.
- No merge/EXE/PR13/recovery mutation: Global Constraints and Task 7.

### Placeholder scan

No `TBD`, `TODO`, “implement later”, or undefined cross-task helper is intentionally left in the plan. Each example helper used by a test is defined in the same task.

### Type/interface consistency

The metric key names used by `analyze_bank` are the same keys consumed by `compare_bias_metrics`: `strict_longest_correct_rate`, `unique_longest_heuristic_success_rate`, `strict_shortest_correct_rate`, `unique_shortest_heuristic_success_rate`, and `most_common_answer_letter_rate`.

### Important planning discovery

The existing repository intentionally defines **same canonical ID + different durable content** as `CHANGED_CONTENT`, quarantining learner state rather than silently inheriting it. Choice text is part of `question_content_fingerprint`; saved sessions also bind to the bank fingerprint. Therefore the design’s learner-history requirement cannot be assumed to pass merely because canonical IDs stay stable. Task 4 is an explicit hard gate and is expected to expose this conflict on the current architecture. The plan does not authorize weakening that safety behavior.
