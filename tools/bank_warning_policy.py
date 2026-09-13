from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

GOVERNED_ACTIVE_BANK_FILENAME = "sc900_bank_v8_final.json"
GOVERNED_ACTIVE_BANK_SHA256 = "177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c"
GOVERNED_ACTIVE_BANK_WARNINGS: tuple[tuple[str, str], ...] = (
    (
        "Repeated answer-pattern bias",
        "C streak on Q394-Q399 (6 in a row)",
    ),
)


def hash_bank_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def normalize_warnings(warnings: object) -> tuple[tuple[str, str], ...]:
    return tuple((str(title), str(body)) for title, body in list(warnings or []))


@dataclass(frozen=True)
class WarningPolicyDecision:
    passed: bool
    failures: tuple[str, ...]
    known_frozen_warning_count: int
    unexpected_warning_count: int
    governed: bool
    bank_sha256: str


def evaluate_production_warnings(
    bank_path: Path,
    warnings: object,
    *,
    bank_sha256: str | None = None,
) -> WarningPolicyDecision:
    actual = normalize_warnings(warnings)
    sha = bank_sha256 if bank_sha256 is not None else hash_bank_file(bank_path)
    if bank_path.name != GOVERNED_ACTIVE_BANK_FILENAME:
        if actual:
            return WarningPolicyDecision(
                passed=False,
                failures=tuple(f"warning {title}: {body}" for title, body in actual),
                known_frozen_warning_count=0,
                unexpected_warning_count=len(actual),
                governed=False,
                bank_sha256=sha,
            )
        return WarningPolicyDecision(
            passed=True,
            failures=(),
            known_frozen_warning_count=0,
            unexpected_warning_count=0,
            governed=False,
            bank_sha256=sha,
        )

    if sha != GOVERNED_ACTIVE_BANK_SHA256:
        return WarningPolicyDecision(
            passed=False,
            failures=(
                "active-bank SHA mismatch: expected "
                f"{GOVERNED_ACTIVE_BANK_SHA256}, got {sha}",
            ),
            known_frozen_warning_count=0,
            unexpected_warning_count=len(actual),
            governed=True,
            bank_sha256=sha,
        )

    expected = GOVERNED_ACTIVE_BANK_WARNINGS
    missing = [item for item in expected if item not in actual]
    extra = [item for item in actual if item not in expected]
    failures: list[str] = []
    if missing:
        failures.append(
            "missing expected frozen warning(s): "
            + "; ".join(f"{title}: {body}" for title, body in missing)
        )
    if extra:
        failures.append(
            "unexpected warning(s): "
            + "; ".join(f"{title}: {body}" for title, body in extra)
        )
    known = len([item for item in actual if item in expected])
    return WarningPolicyDecision(
        passed=not failures,
        failures=tuple(failures),
        known_frozen_warning_count=known,
        unexpected_warning_count=len(extra),
        governed=True,
        bank_sha256=sha,
    )
