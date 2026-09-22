"""Pure deterministic metrics for auditing answer-length leakage."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

LETTERS = ("A", "B", "C", "D")


def _question_id(question: Mapping[str, Any]) -> str:
    value = question.get("id", "")
    return value if isinstance(value, str) else ""


def _domain(question: Mapping[str, Any]) -> str:
    value = question.get("domain", "")
    return value if isinstance(value, str) else ""


def _single_correct_letter(value: Any) -> str | None:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        candidates = list(value)
    else:
        return None

    if len(candidates) != 1 or candidates[0] not in LETTERS:
        return None
    return candidates[0]


def _analyze(question: Mapping[str, Any]) -> dict[str, Any] | None:
    choices = question.get("choices")
    if not isinstance(choices, Mapping) or set(choices) != set(LETTERS) or len(choices) != len(LETTERS):
        return None
    if any(not isinstance(choices[letter], str) for letter in LETTERS):
        return None

    correct_letter = _single_correct_letter(question.get("correct"))
    if correct_letter is None:
        return None

    char_lengths = {letter: len(choices[letter].strip()) for letter in LETTERS}
    word_lengths = {letter: len(choices[letter].strip().split()) for letter in LETTERS}
    distractor_lengths = [char_lengths[letter] for letter in LETTERS if letter != correct_letter]
    correct_chars = char_lengths[correct_letter]
    max_distractor_chars = max(distractor_lengths)

    return {
        "question_id": _question_id(question),
        "domain": _domain(question),
        "correct_letter": correct_letter,
        "char_lengths": char_lengths,
        "word_lengths": word_lengths,
        "correct_chars": correct_chars,
        "max_distractor_chars": max_distractor_chars,
        "strict_longest_correct": correct_chars > max_distractor_chars,
        "correct_among_longest": correct_chars == max(char_lengths.values()),
        "strict_shortest_correct": correct_chars < min(distractor_lengths),
    }


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _count_metric(count: int, denominator: int) -> dict[str, int | float]:
    return {"count": count, "denominator": denominator, "rate": _rate(count, denominator)}


def _heuristic_metric(successes: int, denominator: int) -> dict[str, int | float]:
    return {"successes": successes, "denominator": denominator, "rate": _rate(successes, denominator)}


def _audit_core(questions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    analyzed: list[dict[str, Any]] = []
    skipped_question_ids: list[str] = []

    for question in questions:
        if not isinstance(question, Mapping):
            skipped_question_ids.append("")
            continue
        row = _analyze(question)
        if row is None:
            skipped_question_ids.append(_question_id(question))
        else:
            analyzed.append(row)

    analyzable = len(analyzed)
    strict_longest_count = sum(row["strict_longest_correct"] for row in analyzed)
    correct_among_longest_count = sum(row["correct_among_longest"] for row in analyzed)
    strict_shortest_count = sum(row["strict_shortest_correct"] for row in analyzed)

    unique_longest_denominator = 0
    unique_longest_successes = 0
    unique_shortest_denominator = 0
    unique_shortest_successes = 0
    correct_letter_counts = {letter: 0 for letter in LETTERS}

    for row in analyzed:
        correct_letter_counts[row["correct_letter"]] += 1
        char_lengths = row["char_lengths"]
        longest = max(char_lengths.values())
        longest_letters = [letter for letter in LETTERS if char_lengths[letter] == longest]
        if len(longest_letters) == 1:
            unique_longest_denominator += 1
            unique_longest_successes += longest_letters[0] == row["correct_letter"]

        shortest = min(char_lengths.values())
        shortest_letters = [letter for letter in LETTERS if char_lengths[letter] == shortest]
        if len(shortest_letters) == 1:
            unique_shortest_denominator += 1
            unique_shortest_successes += shortest_letters[0] == row["correct_letter"]

    ranked_outliers = []
    for row in analyzed:
        if not row["strict_longest_correct"]:
            continue
        absolute_gap = row["correct_chars"] - row["max_distractor_chars"]
        relative_gap = absolute_gap / max(1, row["max_distractor_chars"])
        ranked_outliers.append(
            {
                "question_id": row["question_id"],
                "domain": row["domain"],
                "correct_letter": row["correct_letter"],
                "char_lengths": row["char_lengths"],
                "word_lengths": row["word_lengths"],
                "absolute_gap": absolute_gap,
                "relative_gap": relative_gap,
            }
        )
    ranked_outliers.sort(key=lambda row: (-row["relative_gap"], -row["absolute_gap"], row["question_id"]))

    total_correct_chars = sum(row["correct_chars"] for row in analyzed)
    total_longest_distractor_chars = sum(row["max_distractor_chars"] for row in analyzed)

    return {
        "question_count": len(questions),
        "analyzable_single_answer": analyzable,
        "skipped_question_ids": sorted(skipped_question_ids),
        "strict_longest_correct": _count_metric(strict_longest_count, analyzable),
        "correct_among_longest": _count_metric(correct_among_longest_count, analyzable),
        "strict_shortest_correct": _count_metric(strict_shortest_count, analyzable),
        "unique_longest_heuristic": _heuristic_metric(unique_longest_successes, unique_longest_denominator),
        "unique_shortest_heuristic": _heuristic_metric(unique_shortest_successes, unique_shortest_denominator),
        "correct_letter_counts": correct_letter_counts,
        "mean_correct_chars": _rate(total_correct_chars, analyzable),
        "mean_longest_distractor_chars": _rate(total_longest_distractor_chars, analyzable),
        "ranked_outliers": ranked_outliers,
    }


def audit_questions(questions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return deterministic JSON-compatible answer-length leakage metrics."""

    result = _audit_core(questions)
    domain_questions: dict[str, list[Mapping[str, Any]]] = {}
    for question in questions:
        domain = _domain(question) if isinstance(question, Mapping) else ""
        domain_questions.setdefault(domain, []).append(question)
    result["domains"] = {domain: _audit_core(domain_questions[domain]) for domain in sorted(domain_questions)}
    return result


def ranked_strict_longest_outliers(questions: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return strict-longest-correct questions ordered by deterministic severity."""

    return _audit_core(questions)["ranked_outliers"]
