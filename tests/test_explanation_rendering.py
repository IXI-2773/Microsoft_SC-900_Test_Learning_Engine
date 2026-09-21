from __future__ import annotations

import unittest

from app_question_render_mixin import QuestionRenderMixin


class FakeVar:
    def __init__(self, value=False):
        self.value = value

    def get(self):
        return self.value


class FakeWidget:
    def __init__(self, bg="#ffffff"):
        self.visible = False
        self.config = {}
        self._bg = bg

    def pack(self, *args, **kwargs):
        self.visible = True

    def pack_forget(self):
        self.visible = False

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def cget(self, key):
        if key == "bg":
            return self._bg
        return self.config.get(key)


class FakeChoiceRow:
    def __init__(self):
        self.inner = FakeWidget()
        self.detail = ""
        self.detail_calls = []
        self.interactive = True
        self.state = "default"
        self.visible = False

    def set_text(self, text):
        self.text = text

    def set_density(self, dense):
        self.dense = dense

    def reset(self):
        self.detail = ""
        self.detail_calls.clear()
        self.state = "default"

    def pack(self, *args, **kwargs):
        self.visible = True

    def pack_forget(self):
        self.visible = False

    def set_interactive(self, value):
        self.interactive = value

    def mark_selected_correct(self):
        self.state = "selected_correct"

    def mark_selected_wrong(self):
        self.state = "selected_wrong"

    def mark_correct_unselected(self):
        self.state = "correct_unselected"

    def mark_pending(self, multi=False):
        self.state = "pending"

    def set_detail(self, text, **kwargs):
        self.detail = text
        self.detail_calls.append((text, kwargs))


class RenderingHarness(QuestionRenderMixin):
    def __init__(self):
        self.explanation_recall_var = FakeVar(False)
        self.explanation_wrap = FakeWidget()
        self.recall_prompt_wrap = FakeWidget()
        self.general_card = FakeWidget()
        self.dense_answers_var = FakeVar(False)
        self.choice_rows = {letter: FakeChoiceRow() for letter in "ABCD"}

    def _question_correct(self, q):
        return set(q.get("selected", [])) == set(q.get("correct", []))


def _question(*, selected=("B",), answered=True, sparse=True):
    general = "General explanation of why A is correct."
    feedback = (
        {
            "B": "B confuses a neighboring product with the required capability.",
            "C": "C operates at a different control plane.",
        }
        if sparse
        else {letter: general for letter in "ABCD"}
    )
    return {
        "question_number": 1,
        "prompt": "Prompt?",
        "choices": {"A": "Correct", "B": "Near miss", "C": "Other miss", "D": "Irrelevant"},
        "correct": ["A"],
        "selected": list(selected),
        "pending": list(selected),
        "answered": answered,
        "question_type": "single",
        "general_explanation": general,
        "choice_explanations": feedback,
        "recall_ready": False,
    }


class ExplanationRenderingTests(unittest.TestCase):
    def setUp(self):
        self.engine = RenderingHarness()

    def test_expl_025_practice_rendering_distinct_general_and_selected_wrong(self):
        q = _question()
        self.engine._render_choice_rows(q, True)
        self.engine._render_general_explanation_block(q, True)
        self.assertTrue(self.engine.explanation_wrap.visible)
        self.assertTrue(self.engine.general_card.visible)
        self.assertEqual(q["general_explanation"], self.engine.general_card.config["text"])
        self.assertEqual(q["choice_explanations"]["B"], self.engine.choice_rows["B"].detail)
        self.assertEqual("", self.engine.choice_rows["C"].detail)
        self.assertEqual("", self.engine.choice_rows["A"].detail)

    def test_expl_026_smart_practice_uses_same_feedback_contract(self):
        q = _question()
        self.engine._render_choice_rows(q, True)
        self.assertEqual("selected_wrong", self.engine.choice_rows["B"].state)
        self.assertEqual(q["choice_explanations"]["B"], self.engine.choice_rows["B"].detail)
        self.assertEqual("", self.engine.choice_rows["C"].detail)

    def test_expl_027_exam_before_reveal_suppresses_feedback(self):
        q = _question()
        self.engine._render_choice_rows(q, False)
        self.engine._render_general_explanation_block(q, False)
        self.assertFalse(self.engine.explanation_wrap.visible)
        self.assertFalse(self.engine.general_card.visible)
        self.assertEqual("", self.engine.choice_rows["B"].detail)

    def test_expl_028_exam_after_reveal_uses_practice_contract(self):
        q = _question()
        self.engine._render_choice_rows(q, True)
        self.engine._render_general_explanation_block(q, True)
        self.assertTrue(self.engine.general_card.visible)
        self.assertEqual(q["choice_explanations"]["B"], self.engine.choice_rows["B"].detail)

    def test_expl_029_general_and_selected_wrong_feedback_remain_distinct(self):
        q = _question()
        general = self.engine._general_explanation_for_question(q, True)
        wrong = self.engine._selected_wrong_feedback_for_letter(q, "B", True)
        self.assertEqual(q["general_explanation"], general)
        self.assertEqual(q["choice_explanations"]["B"], wrong)
        self.assertNotEqual(general, wrong)

    def test_legacy_blanket_duplicate_is_not_rendered_as_selected_wrong_feedback(self):
        q = _question(sparse=False)
        self.assertTrue(self.engine._choice_feedback_is_legacy_blanket_duplicate(q))
        self.engine._render_choice_rows(q, True)
        self.engine._render_general_explanation_block(q, True)
        self.assertEqual("", self.engine.choice_rows["B"].detail)
        self.assertTrue(self.engine.general_card.visible)
        self.assertEqual(q["general_explanation"], self.engine.general_card.config["text"])

    def test_correct_answer_never_receives_selected_wrong_feedback(self):
        q = _question(selected=("A",))
        q["choice_explanations"] = {"A": "should never display"}
        self.engine._render_choice_rows(q, True)
        self.assertEqual("", self.engine.choice_rows["A"].detail)

    def test_recall_mode_hides_general_until_recall_ready(self):
        q = _question(selected=("A",))
        self.engine.explanation_recall_var.value = True
        self.engine._render_general_explanation_block(q, True)
        self.assertTrue(self.engine.explanation_wrap.visible)
        self.assertFalse(self.engine.general_card.visible)
        self.assertTrue(self.engine.recall_prompt_wrap.visible)
        q["recall_ready"] = True
        self.engine._render_general_explanation_block(q, True)
        self.assertTrue(self.engine.general_card.visible)
        self.assertFalse(self.engine.recall_prompt_wrap.visible)


if __name__ == "__main__":
    unittest.main()
