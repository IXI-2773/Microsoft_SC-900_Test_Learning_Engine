from pathlib import Path
import unittest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class SessionCountControlTests(unittest.TestCase):
    def test_question_amount_control_is_editable_without_changing_presets(self):
        source = " ".join(APP_PATH.read_text(encoding="utf-8").split())
        self.assertIn(
            'sess, textvariable=self.session_count_var, state="normal", values=["25", "50", "90", "All visible"]',
            source,
        )

    def test_saved_count_load_and_persistence_wiring_remains_intact(self):
        source = " ".join(APP_PATH.read_text(encoding="utf-8").split())
        self.assertIn(
            'self.session_count_var = tk.StringVar(value=str(self.config.get("session_count") or "25"))',
            source,
        )
        self.assertIn('"session_count": self.session_count_var.get(),', source)


if __name__ == "__main__":
    unittest.main()
