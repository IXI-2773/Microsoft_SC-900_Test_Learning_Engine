from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from extraction.pages import PageText

QUESTION_HEADER = re.compile(
    r"^(?:question\s+(?P<n1>\d+)|q\.?\s*(?P<n2>\d+)|(?P<n3>\d+)[.)])(?:\s+|$)(?P<rest>.*)$",
    re.IGNORECASE,
)
CHOICE_LINE = re.compile(r"^(?:\((?P<p>[A-Da-d])\)|(?P<b>[A-Da-d])[.):])\s+(?P<text>.+)$")
ANSWER_LINE = re.compile(r"^(?:correct(?:\s+answer)?|answer(?:\s+key)?)\s*[:\-]\s*(?P<value>.+)$", re.IGNORECASE)
EXPLANATION_LINE = re.compile(r"^(?:explanation|rationale)\s*[:\-]\s*(?P<value>.*)$", re.IGNORECASE)
OBJECTIVE_LINE = re.compile(r"^objective\s*[:\-]\s*(?P<value>\S+)", re.IGNORECASE)
DOMAIN_LINE = re.compile(r"^domain\s*[:\-]\s*(?P<value>\S+)", re.IGNORECASE)
ANSWER_TOKEN = re.compile(r"[A-D]", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedQuestion:
    question_text: str
    choices: tuple[dict[str, str], ...]
    source_answer: tuple[str, ...]
    source_explanation: str | None
    source_page: int
    source_page_end: int
    source_locator: str
    raw_source_fragment: str
    warnings: tuple[str, ...]
    domain: str | None
    objective: str | None
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "question_text": self.question_text,
            "choices": [dict(choice) for choice in self.choices],
            "source_answer": list(self.source_answer),
            "source_explanation": self.source_explanation,
            "source_page": self.source_page,
            "source_page_end": self.source_page_end,
            "source_locator": self.source_locator,
            "raw_source_fragment": self.raw_source_fragment,
            "warnings": list(self.warnings),
            "domain": self.domain,
            "objective": self.objective,
            "confidence": self.confidence,
        }


def _lines(pages: tuple[PageText, ...]) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for page in pages:
        for line in page.text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            stripped = line.strip()
            if stripped:
                rows.append((page.page_number, stripped))
    return rows


def _parse_answers(value: str) -> tuple[str, ...]:
    tokens = tuple(dict.fromkeys(token.upper() for token in ANSWER_TOKEN.findall(value)))
    return tokens


def _flush(buffer: dict[str, Any]) -> ParsedQuestion:
    warnings: list[str] = list(buffer.get("warnings") or [])
    choices: list[dict[str, str]] = buffer["choices"]
    labels = [choice["id"] for choice in choices]
    if not choices:
        warnings.append("NO_CHOICES")
    if len(labels) != len(set(labels)):
        warnings.append("DUPLICATE_CHOICE_LABELS")
    answers: tuple[str, ...] = tuple(buffer.get("answers") or ())
    valid_ids = set(labels)
    if not answers:
        warnings.append("UNRESOLVED_ANSWER")
    elif any(answer not in valid_ids for answer in answers):
        warnings.append("ANSWER_NOT_IN_CHOICES")
        answers = ()
    if len(buffer.get("answer_lines") or []) > 1 and len(set(buffer.get("answer_lines") or [])) > 1:
        warnings.append("CONTRADICTORY_KEYS")
        answers = ()
    stem = " ".join(part for part in buffer["stem_parts"] if part).strip()
    explanation = buffer.get("explanation")
    if not explanation:
        warnings.append("UNRESOLVED_EXPLANATION")
    if not buffer.get("objective"):
        warnings.append("TAXONOMY_UNMAPPED")
    confidence = 1.0
    if warnings:
        confidence = 0.4 if "NO_CHOICES" in warnings else 0.6
    fragment = str(buffer.get("raw") or "")[:800]
    start = int(buffer["start_page"])
    end = int(buffer["end_page"])
    return ParsedQuestion(
        question_text=stem,
        choices=tuple(choices),
        source_answer=answers,
        source_explanation=explanation,
        source_page=start,
        source_page_end=end,
        source_locator=f"page:{start}-{end}#q{buffer['number']}",
        raw_source_fragment=fragment,
        warnings=tuple(dict.fromkeys(warnings)),
        domain=buffer.get("domain"),
        objective=buffer.get("objective"),
        confidence=confidence,
    )


def parse_question_blocks(
    pages: tuple[PageText, ...],
    *,
    default_domain: str | None = None,
    default_objective: str | None = None,
) -> list[ParsedQuestion]:
    records: list[ParsedQuestion] = []
    current: dict[str, Any] | None = None

    def start_question(page: int, number: str, rest: str, raw: str) -> dict[str, Any]:
        return {
            "number": number,
            "start_page": page,
            "end_page": page,
            "stem_parts": [rest] if rest else [],
            "choices": [],
            "answers": [],
            "answer_lines": [],
            "explanation": None,
            "domain": default_domain,
            "objective": default_objective,
            "warnings": [],
            "raw": raw,
            "in_choices": False,
            "in_explanation": False,
        }

    for page, line in _lines(pages):
        header = QUESTION_HEADER.match(line)
        if header:
            if current:
                records.append(_flush(current))
            number = header.group("n1") or header.group("n2") or header.group("n3")
            current = start_question(page, number, (header.group("rest") or "").strip(), line)
            continue
        if current is None:
            continue
        current["end_page"] = page
        current["raw"] = f"{current['raw']}\n{line}"
        choice = CHOICE_LINE.match(line)
        if choice:
            label = (choice.group("p") or choice.group("b") or "").upper()
            current["choices"].append({"id": label, "text": choice.group("text").strip()})
            current["in_choices"] = True
            current["in_explanation"] = False
            continue
        answer = ANSWER_LINE.match(line)
        if answer:
            parsed = _parse_answers(answer.group("value"))
            current["answers"] = list(parsed)
            current["answer_lines"].append(tuple(parsed))
            current["in_explanation"] = False
            continue
        explanation = EXPLANATION_LINE.match(line)
        if explanation:
            current["explanation"] = explanation.group("value").strip()
            current["in_explanation"] = True
            continue
        objective = OBJECTIVE_LINE.match(line)
        if objective:
            current["objective"] = objective.group("value").strip()
            continue
        domain = DOMAIN_LINE.match(line)
        if domain:
            current["domain"] = domain.group("value").strip()
            continue
        if current["in_explanation"] and current["explanation"] is not None:
            current["explanation"] = f"{current['explanation']} {line}".strip()
            continue
        if not current["in_choices"]:
            current["stem_parts"].append(line)
    if current:
        records.append(_flush(current))
    return records
