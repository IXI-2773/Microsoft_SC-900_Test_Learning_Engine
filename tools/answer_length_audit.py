from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from question_bank import load_bank
from question_identity import canonical_question_id


def normalize_choice_text(value: object) -> str:
    return " ".join(str(value or "").split())


def choice_length(value: object) -> tuple[int, int]:
    text = normalize_choice_text(value)
    return len(text), len(text.split())


def analyze_question(question: dict) -> dict | None:
    if question.get("question_type") != "single":
        return None
    correct = list(question.get("correct") or [])
    if len(correct) != 1:
        return None
    choices = question.get("choices")
    if not isinstance(choices, dict):
        return None

    normalized_choices = {
        str(letter): normalize_choice_text(text)
        for letter, text in choices.items()
        if normalize_choice_text(text)
    }
    if len(normalized_choices) < 2:
        return None

    correct_letter = str(correct[0])
    if correct_letter not in normalized_choices:
        return None

    lengths = {
        letter: {
            "characters": choice_length(text)[0],
            "words": choice_length(text)[1],
        }
        for letter, text in normalized_choices.items()
    }
    char_lengths = {letter: values["characters"] for letter, values in lengths.items()}
    word_lengths = {letter: values["words"] for letter, values in lengths.items()}
    max_chars = max(char_lengths.values())
    min_chars = min(char_lengths.values())
    max_letters = sorted(letter for letter, value in char_lengths.items() if value == max_chars)
    min_letters = sorted(letter for letter, value in char_lengths.items() if value == min_chars)

    distractor_lengths = [value for letter, value in char_lengths.items() if letter != correct_letter]
    max_distractor = max(distractor_lengths)
    min_distractor = min(distractor_lengths)
    correct_chars = char_lengths[correct_letter]
    absolute_gap = correct_chars - max_distractor
    relative_gap = absolute_gap / max(correct_chars, 1)

    return {
        "question_id": canonical_question_id(question),
        "question_number": question.get("question_number"),
        "domain": str(question.get("domain") or "Unsorted"),
        "correct_letter": correct_letter,
        "choice_lengths": lengths,
        "correct_characters": correct_chars,
        "correct_words": word_lengths[correct_letter],
        "max_distractor_characters": max_distractor,
        "min_distractor_characters": min_distractor,
        "max_choice_characters": max_chars,
        "min_choice_characters": min_chars,
        "longest_letters": max_letters,
        "shortest_letters": min_letters,
        "correct_is_strict_longest": len(max_letters) == 1 and max_letters[0] == correct_letter,
        "correct_is_among_longest": correct_letter in max_letters,
        "correct_is_strict_shortest": len(min_letters) == 1 and min_letters[0] == correct_letter,
        "correct_is_among_shortest": correct_letter in min_letters,
        "unique_longest_letter": max_letters[0] if len(max_letters) == 1 else "",
        "unique_shortest_letter": min_letters[0] if len(min_letters) == 1 else "",
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
    }


def rank_longest_outliers(question_rows: list[dict]) -> list[dict]:
    rows = [dict(row) for row in question_rows if float(row.get("absolute_gap") or 0) > 0]
    rows.sort(
        key=lambda row: (
            -float(row["relative_gap"]),
            -int(row["absolute_gap"]),
            str(row.get("question_id") or ""),
        )
    )
    return rows


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _aggregate_rows(rows: list[dict]) -> dict[str, Any]:
    analyzable_count = len(rows)
    strict_longest_count = sum(bool(row["correct_is_strict_longest"]) for row in rows)
    among_longest_count = sum(bool(row["correct_is_among_longest"]) for row in rows)
    strict_shortest_count = sum(bool(row["correct_is_strict_shortest"]) for row in rows)

    unique_longest_rows = [row for row in rows if row["unique_longest_letter"]]
    unique_shortest_rows = [row for row in rows if row["unique_shortest_letter"]]
    unique_longest_success = sum(
        row["unique_longest_letter"] == row["correct_letter"] for row in unique_longest_rows
    )
    unique_shortest_success = sum(
        row["unique_shortest_letter"] == row["correct_letter"] for row in unique_shortest_rows
    )

    letters = Counter(str(row["correct_letter"]) for row in rows)
    letter_distribution = dict(sorted(letters.items()))
    letter_rates = {
        letter: _safe_rate(count, analyzable_count) for letter, count in sorted(letters.items())
    }

    return {
        "analyzable_count": analyzable_count,
        "strict_longest_correct_count": strict_longest_count,
        "strict_longest_correct_rate": _safe_rate(strict_longest_count, analyzable_count),
        "correct_among_longest_count": among_longest_count,
        "correct_among_longest_rate": _safe_rate(among_longest_count, analyzable_count),
        "unique_longest_question_count": len(unique_longest_rows),
        "unique_longest_heuristic_success_count": unique_longest_success,
        "unique_longest_heuristic_success_rate": _safe_rate(unique_longest_success, len(unique_longest_rows)),
        "strict_shortest_correct_count": strict_shortest_count,
        "strict_shortest_correct_rate": _safe_rate(strict_shortest_count, analyzable_count),
        "unique_shortest_question_count": len(unique_shortest_rows),
        "unique_shortest_heuristic_success_count": unique_shortest_success,
        "unique_shortest_heuristic_success_rate": _safe_rate(unique_shortest_success, len(unique_shortest_rows)),
        "correct_letter_distribution": letter_distribution,
        "correct_letter_rates": letter_rates,
        "most_common_answer_letter_rate": _safe_rate(max(letters.values(), default=0), analyzable_count),
        "mean_correct_characters": fmean(row["correct_characters"] for row in rows) if rows else 0.0,
        "mean_max_distractor_characters": fmean(row["max_distractor_characters"] for row in rows) if rows else 0.0,
    }


def analyze_bank(questions: list[dict]) -> dict:
    rows = [row for question in questions if (row := analyze_question(question)) is not None]
    aggregate = _aggregate_rows(rows)

    domains: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        domains[str(row["domain"])].append(row)
    per_domain = {
        domain: _aggregate_rows(domain_rows)
        for domain, domain_rows in sorted(domains.items(), key=lambda item: item[0])
    }

    return {
        "question_count": len(questions),
        **aggregate,
        "per_domain": per_domain,
        "longest_outliers": rank_longest_outliers(rows),
    }


def write_json_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _pct(value: float) -> str:
    return f"{value:.2%}"


def write_markdown_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SC-900 Answer-Length Leakage Audit",
        "",
        f"- Questions: **{report['question_count']}**",
        f"- Analyzable single-answer questions: **{report['analyzable_count']}**",
        f"- Strict-longest correct: **{report['strict_longest_correct_count']} / {report['analyzable_count']} ({_pct(report['strict_longest_correct_rate'])})**",
        f"- Correct among longest: **{report['correct_among_longest_count']} / {report['analyzable_count']} ({_pct(report['correct_among_longest_rate'])})**",
        f"- Unique-longest heuristic success: **{report['unique_longest_heuristic_success_count']} / {report['unique_longest_question_count']} ({_pct(report['unique_longest_heuristic_success_rate'])})**",
        f"- Strict-shortest correct: **{report['strict_shortest_correct_count']} / {report['analyzable_count']} ({_pct(report['strict_shortest_correct_rate'])})**",
        f"- Unique-shortest heuristic success: **{report['unique_shortest_heuristic_success_count']} / {report['unique_shortest_question_count']} ({_pct(report['unique_shortest_heuristic_success_rate'])})**",
        f"- Most-common answer-letter rate: **{_pct(report['most_common_answer_letter_rate'])}**",
        f"- Mean correct-answer length: **{report['mean_correct_characters']:.2f} characters**",
        f"- Mean longest-distractor length: **{report['mean_max_distractor_characters']:.2f} characters**",
        "",
        "## Per-domain metrics",
        "",
        "| Domain | N | Strict longest | Unique-longest heuristic | Strict shortest | Most-common letter |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for domain, metrics in report["per_domain"].items():
        lines.append(
            f"| {domain} | {metrics['analyzable_count']} | {_pct(metrics['strict_longest_correct_rate'])} | "
            f"{_pct(metrics['unique_longest_heuristic_success_rate'])} | {_pct(metrics['strict_shortest_correct_rate'])} | "
            f"{_pct(metrics['most_common_answer_letter_rate'])} |"
        )

    lines.extend(["", "## Correct-answer letter distribution", ""])
    for letter, count in report["correct_letter_distribution"].items():
        lines.append(f"- {letter}: {count} ({_pct(report['correct_letter_rates'][letter])})")

    lines.extend(
        [
            "",
            "## Top longest-answer outliers",
            "",
            "| Question | Number | Domain | Correct | Correct chars | Max distractor chars | Gap | Relative gap |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["longest_outliers"][:60]:
        lines.append(
            f"| {row['question_id']} | {row.get('question_number', '')} | {row['domain']} | {row['correct_letter']} | "
            f"{row['correct_characters']} | {row['max_distractor_characters']} | {row['absolute_gap']} | "
            f"{_pct(row['relative_gap'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit answer-length leakage in an SC-900 question bank.")
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    bank_path = args.bank.resolve()
    questions = list(load_bank(bank_path)["questions"])
    report = analyze_bank(questions)
    if args.json_out:
        write_json_report(report, args.json_out)
    if args.markdown_out:
        write_markdown_report(report, args.markdown_out)
    if not args.json_out and not args.markdown_out:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
