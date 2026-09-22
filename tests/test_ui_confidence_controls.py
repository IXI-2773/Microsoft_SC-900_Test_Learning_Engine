from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app as app_module
from app_question_flow_mixin import QuestionFlowMixin
from config_store import DEFAULT_CONFIG, load_config, save_config


class _FixedVar:
    def __init__(self, value: bool):
        self.value = value

    def get(self) -> bool:
        return self.value

    def set(self, value: bool):
        self.value = value


class _GeometryWidget:
    def __init__(self, *, x=0, y=0, width=1, height=1, requested_width=None, requested_height=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.requested_width = width if requested_width is None else requested_width
        self.requested_height = height if requested_height is None else requested_height

    def update_idletasks(self):
        return None

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_reqwidth(self):
        return self.requested_width

    def winfo_reqheight(self):
        return self.requested_height

    def winfo_rootx(self):
        return self.x

    def winfo_rooty(self):
        return self.y

    def winfo_exists(self):
        return True


class _CanvasGeometry(_GeometryWidget):
    def __init__(self, *, visible_top, **kwargs):
        super().__init__(**kwargs)
        self.visible_top = visible_top

    def canvasy(self, value):
        return self.visible_top + value


class _Root:
    def __init__(self, *, pointer_x=0, pointer_y=0):
        self.saved_geometry = None
        self.pointer_x = pointer_x
        self.pointer_y = pointer_y

    def geometry(self, value):
        self.saved_geometry = value

    def winfo_pointerx(self):
        return self.pointer_x

    def winfo_pointery(self):
        return self.pointer_y


class _FlowHarness(QuestionFlowMixin):
    def __init__(self, show_confidence_controls: bool):
        self.show_confidence_controls_var = _FixedVar(show_confidence_controls)
        self.events = []
        self.recorded = None

    def _should_suppress_confidence_capture(self, q):
        return False

    def render_question(self):
        self.events.append("render")

    def _show_feedback_popover(self, q, selected, anchor_widget=None):
        self.events.append("prompt")

    def _destroy_feedback_popover(self):
        self.events.append("destroy")

    def save_app_config(self):
        self.events.append("save")

    def _record_answer(self, q, selected, anchor_widget=None, feedback_override=None):
        self.events.append("record")
        self.recorded = {"selected": list(selected), "feedback": dict(feedback_override or {})}


class ConfidenceControlRegressionTests(unittest.TestCase):
    def _app_with_short_visible_canvas(self, *, pointer_x=0, pointer_y=0):
        app = object.__new__(QuestionFlowMixin)
        app.root = _Root(pointer_x=pointer_x, pointer_y=pointer_y)
        app.content_frame = _GeometryWidget(x=100, y=100, width=700, height=900)
        app.content_canvas = _CanvasGeometry(x=100, y=100, width=700, height=260, visible_top=400)
        return app

    def test_confidence_prompt_centers_at_pointer_inside_clicked_answer(self):
        app = self._app_with_short_visible_canvas(pointer_x=360, pointer_y=520)
        answer_row = _GeometryWidget(x=120, y=500, width=650, height=50)
        prompt = _GeometryWidget(width=1, height=1, requested_width=240, requested_height=90)

        x, y = app._position_feedback_popover(prompt, answer_row)

        self.assertEqual(260, x + prompt.requested_width // 2)
        self.assertGreaterEqual(y, 410)
        self.assertLessEqual(y + prompt.requested_height, 648)

    def test_d_anchored_confidence_prompt_stays_in_visible_scrolled_canvas(self):
        app = self._app_with_short_visible_canvas()
        d_row = _GeometryWidget(x=120, y=720, width=650, height=50)
        prompt = _GeometryWidget(width=1, height=1, requested_width=240, requested_height=90)

        _x, y = app._position_feedback_popover(prompt, d_row)

        self.assertGreaterEqual(y, 412)
        self.assertLessEqual(y + prompt.requested_height, 648)

    def test_confidence_prompt_clamps_centered_pointer_at_left_viewport_edge(self):
        app = self._app_with_short_visible_canvas(pointer_x=125, pointer_y=520)
        answer_row = _GeometryWidget(x=120, y=500, width=650, height=50)
        prompt = _GeometryWidget(width=1, height=1, requested_width=240, requested_height=90)

        x, y = app._position_feedback_popover(prompt, answer_row)

        self.assertEqual(12, x)
        self.assertGreaterEqual(y, 410)
        self.assertLessEqual(y + prompt.requested_height, 648)

    def test_each_answer_selection_repaints_pending_before_confidence_prompt(self):
        for letter in "ABCD":
            with self.subTest(letter=letter):
                app = _FlowHarness(show_confidence_controls=True)
                question = {"choices": {item: item for item in "ABCD"}, "correct": ["A"]}

                app._begin_confidence_capture(question, [letter])

                self.assertEqual([letter], question["pending"])
                self.assertEqual(["render", "prompt"], app.events)
                self.assertIsNone(app.recorded)

    def test_confidence_control_preference_defaults_on_and_persists_off(self):
        self.assertIs(DEFAULT_CONFIG["show_confidence_controls"], True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            save_config(path, {"show_confidence_controls": False})
            self.assertIs(load_config(path)["show_confidence_controls"], False)

    def test_disabled_confidence_records_unknown_without_fabricated_judgment(self):
        app = _FlowHarness(show_confidence_controls=False)
        question = {"choices": {item: item for item in "ABCD"}, "correct": ["A"]}

        app._begin_confidence_capture(question, ["D"])

        self.assertEqual(["render", "record"], app.events)
        self.assertEqual(["D"], app.recorded["selected"])
        self.assertEqual("Unknown", app.recorded["feedback"]["confidence"])
        self.assertEqual("", app.recorded["feedback"]["miss_reason"])

    def test_disabling_controls_during_prompt_records_pending_answer_as_unknown(self):
        app = _FlowHarness(show_confidence_controls=True)
        question = {"id": "q-1", "question_number": 1, "choices": {item: item for item in "ABCD"}, "correct": ["A"]}
        app.questions = [question]
        app.pending_feedback_request = {"question_id": "q-1", "question_number": 1, "selected": ["D"]}
        app.show_confidence_controls_var.set(False)

        app.on_confidence_controls_change()

        self.assertIsNone(app.pending_feedback_request)
        self.assertEqual(["D"], app.recorded["selected"])
        self.assertEqual("Unknown", app.recorded["feedback"]["confidence"])
        self.assertEqual(["destroy", "record", "save", "render"], app.events)

    def test_hidden_preference_hides_post_answer_confidence_controls(self):
        hidden = _FlowHarness(show_confidence_controls=False)
        shown = _FlowHarness(show_confidence_controls=True)

        self.assertFalse(hidden._confidence_review_controls_visible(show_exam_feedback=True))
        self.assertTrue(shown._confidence_review_controls_visible(show_exam_feedback=True))
        self.assertFalse(shown._confidence_review_controls_visible(show_exam_feedback=False))

    def test_reenabling_confidence_controls_restores_their_visibility_without_answer_mutation(self):
        app = _FlowHarness(show_confidence_controls=False)
        question = {"selected": ["D"], "answered": True, "last_confidence": "Unknown"}

        self.assertFalse(app._confidence_review_controls_visible(show_exam_feedback=True))
        app.show_confidence_controls_var.set(True)

        self.assertTrue(app._confidence_review_controls_visible(show_exam_feedback=True))
        self.assertEqual(["D"], question["selected"])
        self.assertEqual("Unknown", question["last_confidence"])

    def test_reset_preferences_restores_confidence_controls_and_invalidates_snapshot(self):
        app = object.__new__(app_module.TestingEngineApp)
        for name in (
            "session_count_var",
            "session_source_var",
            "session_random_var",
            "auto_next_correct_var",
            "explanation_recall_var",
            "compact_review_var",
            "dense_answers_var",
            "show_confidence_controls_var",
            "gamification_enabled_var",
            "reward_intensity_var",
            "celebration_popups_var",
            "reward_sounds_var",
            "micro_feedback_var",
            "boss_rounds_enabled_var",
            "quest_count_var",
            "domain_filter_var",
            "topic_filter_var",
            "status_filter_var",
        ):
            setattr(app, name, _FixedVar(None))
        app.root = _Root()
        app.last_render_snapshot = object()
        app.set_sidebar_width_mode = lambda value, save=False: None
        app.refresh_question_list = lambda: None
        snapshots_seen = []
        app.render_question = lambda: snapshots_seen.append(app.last_render_snapshot)

        with (
            mock.patch.object(app_module.messagebox, "askyesno", return_value=True),
            mock.patch.object(app_module.messagebox, "showinfo"),
            mock.patch.object(app_module, "save_config"),
        ):
            app.reset_preferences()

        self.assertIs(app.show_confidence_controls_var.get(), True)
        self.assertEqual([None], snapshots_seen)


if __name__ == "__main__":
    unittest.main()
