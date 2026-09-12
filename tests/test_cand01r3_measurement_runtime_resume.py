from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

from _cand01r3_measurement_runtime_resume_cases import (
    Cand01R3MeasurementRuntimeResumeTests as _RuntimeResumeTests,
)

_BASE_LOCAL_DATE = date(2026, 9, 12)
_original_set_up = _RuntimeResumeTests.setUp
_original_tear_down = _RuntimeResumeTests.tearDown


def _set_up_with_controlled_calendar(self) -> None:
    _original_set_up(self)
    self._r1_test_local_date = _BASE_LOCAL_DATE
    self._r1_calendar_patch = mock.patch(
        "cand01r3_protocol._current_experiment_local_date",
        side_effect=lambda: self._r1_test_local_date.isoformat(),
        create=True,
    )
    self._r1_calendar_patch.start()


def _tear_down_with_controlled_calendar(self) -> None:
    try:
        self._r1_calendar_patch.stop()
    finally:
        _original_tear_down(self)


def _finish_days_with_calendar_progression(self, last_day: int) -> None:
    for scheduled_day in range(1, last_day + 1):
        self._r1_test_local_date = _BASE_LOCAL_DATE + timedelta(days=scheduled_day - 1)
        self._finish_day(scheduled_day)
    self._r1_test_local_date = _BASE_LOCAL_DATE + timedelta(days=last_day)


_RuntimeResumeTests.setUp = _set_up_with_controlled_calendar
_RuntimeResumeTests.tearDown = _tear_down_with_controlled_calendar
_RuntimeResumeTests._finish_days = _finish_days_with_calendar_progression

Cand01R3MeasurementRuntimeResumeTests = _RuntimeResumeTests


if __name__ == "__main__":
    import unittest

    unittest.main()
