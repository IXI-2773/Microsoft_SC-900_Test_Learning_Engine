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
    raise SystemExit("R2-012 anchor not found")

old = '        self.assertEqual("2026-09-15", result.payload["calendar_local_date"])\n'
new = '        self.assertEqual("2026-09-15", result.payload.get("calendar_local_date"))\n'
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("R2-026 anchor not found")

PATH.write_text(text, encoding="utf-8")
