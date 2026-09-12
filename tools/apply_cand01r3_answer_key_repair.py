from pathlib import Path

path = Path("cand01r3_protocol.py")
text = path.read_text(encoding="utf-8")

old = '''def score_measurement_probe_answer(question: Mapping[str, Any], selected: Sequence[str] | None = None) -> bool:
    correct = question.get("correct")
    if not isinstance(correct, (list, tuple, set)) or not correct:
        raise Cand01R3AuthorityError("INVALID_MEASUREMENT_ANSWER_KEY")
    selected_ids = {str(value) for value in (selected or [])}
    correct_ids = {str(value) for value in correct}
    return selected_ids == correct_ids


def record_measurement_probe_answer(
    question: Mapping[str, Any],
    *,
    selected: Sequence[str] | None = None,
) -> MeasurementObservation:
    correct = score_measurement_probe_answer(question, selected)
    return record_measurement_event(question, selected=list(selected or []), correct=correct, kind="SCORED")
'''
new = '''def _frozen_compiled_answer_key(question_id: str) -> tuple[str, ...]:
    actual_sha256 = hashlib.sha256(
        COMPILED_PATH.read_bytes().replace(b"\\r\\n", b"\\n").replace(b"\\r", b"\\n")
    ).hexdigest()
    if actual_sha256 != EXPECTED_COMPILED_SHA256:
        raise Cand01R3AuthorityError("COMPILED_BANK_HASH_MISMATCH")
    raw = json.loads(COMPILED_PATH.read_text(encoding="utf-8"))
    questions = raw.get("questions") if isinstance(raw, Mapping) else raw
    if isinstance(raw, Mapping) and questions is None:
        questions = raw.get("items") or []
    for row in questions or []:
        if not isinstance(row, Mapping) or canonical_question_id(row) != question_id:
            continue
        correct = row.get("correct")
        if not isinstance(correct, (list, tuple, set)) or not correct:
            raise Cand01R3AuthorityError("INVALID_MEASUREMENT_ANSWER_KEY")
        return tuple(str(value) for value in correct)
    raise Cand01R3AuthorityError("MEASUREMENT_ANSWER_KEY_NOT_FOUND")


def score_measurement_probe_answer(question: Mapping[str, Any], selected: Sequence[str] | None = None) -> bool:
    question_id = canonical_question_id(question)
    if not question_id:
        raise Cand01R3AuthorityError("MEASUREMENT_QUESTION_ID_MISSING")
    correct = _frozen_compiled_answer_key(question_id)
    selected_ids = {str(value) for value in (selected or [])}
    return selected_ids == set(correct)


def record_measurement_probe_answer(
    question: Mapping[str, Any],
    *,
    selected: Sequence[str] | None = None,
    kind: str = "SCORED",
) -> MeasurementObservation:
    correct = score_measurement_probe_answer(question, selected)
    return record_measurement_event(question, selected=list(selected or []), correct=correct, kind=kind)
'''
if new not in text:
    if old not in text:
        raise SystemExit("authoritative answer-key repair anchor not found")
    text = text.replace(old, new, 1)

old = '''    return record_measurement_event(question, selected=selected, correct=correct, kind=kind)
'''
new = '''    return record_measurement_probe_answer(question, selected=selected, kind=kind)
'''
if new not in text:
    if old not in text:
        raise SystemExit("notify_scored_attempt repair anchor not found")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("authoritative CAND-01R3 answer-key repair applied")
