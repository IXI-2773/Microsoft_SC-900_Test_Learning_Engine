from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from question_bank import load_bank
from question_identity import canonical_question_id
from tools.answer_length_audit import analyze_bank


def question_invariants(question: dict) -> dict:
    return {
        "question_id": canonical_question_id(question),
        "correct": tuple(question.get("correct") or []),
        "objective_code": str(question.get("objective_code") or ""),
        "exam_calibration_tier": str(question.get("exam_calibration_tier") or ""),
        "exam_simulation_eligible": question.get("exam_simulation_eligible", True),
    }


def _index_invariants(questions: list[dict]) -> tuple[dict[str, dict], list[str]]:
    indexed: dict[str, dict] = {}
    failures: list[str] = []
    for position, question in enumerate(questions, start=1):
        row = question_invariants(question)
        question_id = str(row["question_id"] or "").strip()
        if not question_id:
            failures.append(f"QUESTION_IDS_MISSING: position={position}")
            continue
        if question_id in indexed:
            failures.append(f"QUESTION_IDS_DUPLICATED: {question_id}")
            continue
        indexed[question_id] = row
    return indexed, failures


def compare_bank_invariants(
    baseline: list[dict],
    candidate: list[dict],
    *,
    expected_count: int | None = None,
) -> list[str]:
    failures: list[str] = []
    if len(baseline) != len(candidate):
        failures.append(f"QUESTION_COUNT_CHANGED: baseline={len(baseline)} candidate={len(candidate)}")
    if expected_count is not None and len(candidate) != expected_count:
        failures.append(f"QUESTION_COUNT_CHANGED: expected={expected_count} candidate={len(candidate)}")

    baseline_by_id, baseline_index_failures = _index_invariants(baseline)
    candidate_by_id, candidate_index_failures = _index_invariants(candidate)
    failures.extend(baseline_index_failures)
    failures.extend(candidate_index_failures)

    baseline_ids = set(baseline_by_id)
    candidate_ids = set(candidate_by_id)
    added = sorted(candidate_ids - baseline_ids)
    removed = sorted(baseline_ids - candidate_ids)
    if added:
        failures.append(f"QUESTION_IDS_ADDED: {','.join(added)}")
    if removed:
        failures.append(f"QUESTION_IDS_REMOVED: {','.join(removed)}")

    field_failures: dict[str, list[str]] = {
        "CORRECT_KEYS_CHANGED": [],
        "OBJECTIVE_CODES_CHANGED": [],
        "TIERS_CHANGED": [],
        "EXAM_ELIGIBILITY_CHANGED": [],
    }
    for question_id in sorted(baseline_ids & candidate_ids):
        before = baseline_by_id[question_id]
        after = candidate_by_id[question_id]
        if before["correct"] != after["correct"]:
            field_failures["CORRECT_KEYS_CHANGED"].append(question_id)
        if before["objective_code"] != after["objective_code"]:
            field_failures["OBJECTIVE_CODES_CHANGED"].append(question_id)
        if before["exam_calibration_tier"] != after["exam_calibration_tier"]:
            field_failures["TIERS_CHANGED"].append(question_id)
        if before["exam_simulation_eligible"] != after["exam_simulation_eligible"]:
            field_failures["EXAM_ELIGIBILITY_CHANGED"].append(question_id)

    for failure_name, question_ids in field_failures.items():
        if question_ids:
            failures.append(f"{failure_name}: {','.join(question_ids)}")
    return failures


def _metric(report: dict, key: str) -> float:
    return float(report.get(key) or 0.0)


def compare_bias_metrics(
    baseline_report: dict,
    candidate_report: dict,
    *,
    final_gate: bool = False,
) -> list[str]:
    failures: list[str] = []

    baseline_longest = _metric(baseline_report, "strict_longest_correct_rate")
    candidate_longest = _metric(candidate_report, "strict_longest_correct_rate")
    baseline_unique = _metric(baseline_report, "unique_longest_heuristic_success_rate")
    candidate_unique = _metric(candidate_report, "unique_longest_heuristic_success_rate")

    if not (candidate_longest < baseline_longest or candidate_unique < baseline_unique):
        failures.append(
            "NO_LONGEST_LEAKAGE_IMPROVEMENT: "
            f"strict={baseline_longest:.6f}->{candidate_longest:.6f} "
            f"unique={baseline_unique:.6f}->{candidate_unique:.6f}"
        )
    if candidate_longest - baseline_longest > 0.005:
        failures.append(
            f"STRICT_LONGEST_WORSENED: {baseline_longest:.6f}->{candidate_longest:.6f}"
        )
    if candidate_unique - baseline_unique > 0.005:
        failures.append(
            f"UNIQUE_LONGEST_WORSENED: {baseline_unique:.6f}->{candidate_unique:.6f}"
        )

    substitutions = (
        (
            "STRICT_SHORTEST_BIAS_INCREASED",
            "strict_shortest_correct_rate",
            0.02,
        ),
        (
            "UNIQUE_SHORTEST_BIAS_INCREASED",
            "unique_shortest_heuristic_success_rate",
            0.02,
        ),
        (
            "ANSWER_LETTER_BIAS_INCREASED",
            "most_common_answer_letter_rate",
            0.02,
        ),
    )
    for failure_name, key, limit in substitutions:
        before = _metric(baseline_report, key)
        after = _metric(candidate_report, key)
        if after - before > limit:
            failures.append(f"{failure_name}: {before:.6f}->{after:.6f}")

    baseline_domains = baseline_report.get("per_domain") or {}
    candidate_domains = candidate_report.get("per_domain") or {}
    for domain in sorted(set(baseline_domains) & set(candidate_domains)):
        before_row = baseline_domains[domain]
        after_row = candidate_domains[domain]
        before_n = int(before_row.get("analyzable_count") or 0)
        after_n = int(after_row.get("analyzable_count") or 0)
        if min(before_n, after_n) < 20:
            continue
        before = _metric(before_row, "strict_longest_correct_rate")
        after = _metric(after_row, "strict_longest_correct_rate")
        if after - before > 0.05:
            failures.append(f"DOMAIN_LONGEST_WORSENED: {domain} {before:.6f}->{after:.6f}")

    if final_gate:
        if candidate_longest >= 0.40:
            failures.append(f"FINAL_STRICT_LONGEST_TARGET_FAILED: {candidate_longest:.6f} >= 0.400000")
        if candidate_unique >= 0.40:
            failures.append(f"FINAL_UNIQUE_LONGEST_TARGET_FAILED: {candidate_unique:.6f} >= 0.400000")
        for domain, row in sorted(candidate_domains.items()):
            if int(row.get("analyzable_count") or 0) < 20:
                continue
            rate = _metric(row, "strict_longest_correct_rate")
            if rate > 0.45:
                failures.append(f"FINAL_DOMAIN_LONGEST_TARGET_FAILED: {domain} {rate:.6f} > 0.450000")

    return failures


def _load_questions(path: Path) -> list[dict[str, Any]]:
    return list(load_bank(path.resolve())["questions"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Guard SC-900 bank revisions against invariant and bias regressions.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--mode", choices=("tranche", "final"), default="tranche")
    args = parser.parse_args()

    baseline = _load_questions(args.baseline)
    candidate = _load_questions(args.candidate)
    failures = compare_bank_invariants(baseline, candidate, expected_count=args.expected_count)
    baseline_report = analyze_bank(baseline)
    candidate_report = analyze_bank(candidate)
    failures.extend(compare_bias_metrics(baseline_report, candidate_report, final_gate=args.mode == "final"))

    if failures:
        for failure in failures:
            print(f"bank revision guard failed: {failure}")
        return 1
    print("bank revision guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
