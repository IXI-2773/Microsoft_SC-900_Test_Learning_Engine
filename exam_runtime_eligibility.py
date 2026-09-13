from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

T = TypeVar("T", bound=Mapping[str, Any])


def exam_runtime_eligible(question: Mapping[str, Any]) -> bool:
    return question.get("exam_simulation_eligible", True) is not False


def filter_new_exam_pool(pool: Iterable[T]) -> list[T]:
    return [question for question in pool if exam_runtime_eligible(question)]
