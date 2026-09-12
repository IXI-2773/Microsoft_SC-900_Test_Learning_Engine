from __future__ import annotations

from pathlib import Path

PATH = Path("tests/test_cand01r3_measurement_integrity.py")
text = PATH.read_text(encoding="utf-8")

old = '''        correct = MeasurementFlowHarness(question(qid, role_hint="PROBE", answered=True, selected=["A"]))
        wrong = MeasurementFlowHarness(question(qid, role_hint="PROBE", answered=True, selected=["B"]))
        QuestionFlowMixin.maybe_auto_next_after_answer(correct, correct.current_question())
'''
new = '''        correct = MeasurementFlowHarness(question(qid, role_hint="PROBE", answered=True, selected=["A"]))
        wrong = MeasurementFlowHarness(question(qid, role_hint="PROBE", answered=True, selected=["B"]))
        correct.questions.append(question(self._train_ids(1)[0], role_hint="TRAIN"))
        wrong.questions.append(question(self._train_ids(1)[0], role_hint="TRAIN"))
        QuestionFlowMixin.maybe_auto_next_after_answer(correct, correct.current_question())
'''
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("R2-012 navigation anchor not found")

old = '''    def cancel_auto_next_after_answer(self):
        self.auto_next_after_id = None


class Cand01R3MeasurementIntegrityTests(unittest.TestCase):
'''
new = '''    def cancel_auto_next_after_answer(self):
        self.auto_next_after_id = None

    def _auto_next_after_answer(self):
        self.auto_next_calls += 1


class Cand01R3MeasurementIntegrityTests(unittest.TestCase):
'''
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("R2-012 callback anchor not found")

old = '''    def _auto_next_after_answer(self):
        self.auto_next_calls += 1


class Cand01R3MeasurementIntegrityTests(unittest.TestCase):
'''
new = '''    def _auto_next_after_answer(self):
        self.auto_next_calls += 1

    def _record_measurement_probe_answer(self, q, selected):
        from app_question_flow_mixin import QuestionFlowMixin

        return QuestionFlowMixin._record_measurement_probe_answer(self, q, selected)


class Cand01R3MeasurementIntegrityTests(unittest.TestCase):
'''
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("measurement boundary harness anchor not found")

old = '        self.assertEqual("2026-09-15", result.payload["calendar_local_date"])\n'
new = '        self.assertEqual("2026-09-15", result.payload.get("calendar_local_date"))\n'
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("R2-026 anchor not found")

old = '''    def test_r2_040_no_empirical_winner_is_declared(self):
        from cand01r3_protocol import load_committed_protocol

        protocol = load_committed_protocol()
        self.assertEqual("NOT_YET_AVAILABLE", protocol.get("empirical_result"))
        self.assertEqual("NO", protocol.get("deployment_authorized"))


if __name__ == "__main__":
'''
new = '''    def test_r2_040_no_empirical_winner_is_declared(self):
        from cand01r3_protocol import load_committed_protocol

        protocol = load_committed_protocol()
        self.assertEqual("NOT_YET_AVAILABLE", protocol.get("empirical_result"))
        self.assertEqual("NO", protocol.get("deployment_authorized"))

    def test_r2_041_measurement_score_uses_frozen_compiled_answer_key(self):
        from cand01r3_partition import COMPILED_PATH, canonical_question_id
        from cand01r3_protocol import score_measurement_probe_answer

        self._begin()
        self._enter_measurement(1)
        qid = self._probe_ids(1)[0]
        raw = json.loads(COMPILED_PATH.read_text(encoding="utf-8"))
        row = next(item for item in raw.get("questions", []) if canonical_question_id(item) == qid)
        authoritative = list(row.get("correct") or [])
        self.assertTrue(authoritative)
        q = question(qid, role_hint="PROBE")
        q["correct"] = ["__TAMPERED_RUNTIME_KEY__"]
        self.assertTrue(score_measurement_probe_answer(q, authoritative))


if __name__ == "__main__":
'''
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("R2-041 anchor not found")

PATH.write_text(text, encoding="utf-8")
