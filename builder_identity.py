from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, TypedDict

from app_constants import SESSION_SOURCE_OPTIONS, STATUS_FILTER_ALIASES, STATUS_FILTER_OPTIONS
from progress_store import SESSION_SOURCE_ALIASES
from session_models import BuilderContext

BUILDER_IDENTITY_KIND = "canonical_builder_request"
BUILDER_IDENTITY_VERSION = 1
BUILDER_IDENTITY_CANONICAL = "canonical"
BUILDER_IDENTITY_MIGRATED = "migrated"
BUILDER_IDENTITY_LEGACY_DEFAULTED = "legacy_defaulted"
BUILDER_IDENTITY_AMBIGUOUS = "ambiguous"
BUILDER_IDENTITY_INVALID = "invalid"

BUILDER_CONTEXT_FIELDS = (
    "mode",
    "count",
    "source_label",
    "session_source",
    "randomize",
    "domain_filter",
    "topic_filter",
    "status_filter",
)

ALL_DOMAINS = "All domains"
ALL_TOPICS = "All topics"
ALL_QUESTIONS = "All questions"
ALL_VISIBLE = "All visible"
DEFAULT_SESSION_SOURCE = "All"

__all__ = [
    "BUILDER_CONTEXT_FIELDS",
    "BUILDER_IDENTITY_AMBIGUOUS",
    "BUILDER_IDENTITY_CANONICAL",
    "BUILDER_IDENTITY_INVALID",
    "BUILDER_IDENTITY_KIND",
    "BUILDER_IDENTITY_LEGACY_DEFAULTED",
    "BUILDER_IDENTITY_MIGRATED",
    "BUILDER_IDENTITY_VERSION",
    "builder_context_fingerprint",
    "builder_identities_match",
    "builder_ui_state_from_context",
    "canonical_builder_identity",
    "normalize_builder_context",
    "resolve_builder_identity_from_snapshot",
]


class BuilderIdentity(TypedDict):
    builder_context: BuilderContext
    builder_identity: str
    builder_identity_version: int
    builder_context_fingerprint: str
    builder_identity_status: str


def _collapse_ws(value: Any) -> str:
    return " ".join(str(value or "").split())


def _normalize_count(value: Any) -> str:
    text = _collapse_ws(value)
    if not text:
        return ""
    if text.casefold() == ALL_VISIBLE.casefold():
        return ALL_VISIBLE
    if text.isdigit() or (text[0] in "+-" and text[1:].isdigit()):
        return str(int(text))
    return text


def _normalize_named(
    value: Any,
    *,
    default: str,
    aliases: Mapping[str, str] | None = None,
    options: list[str] | None = None,
) -> str:
    text = _collapse_ws(value)
    lookup = {default.casefold(): default}
    for source_key, source_value in (aliases or {}).items():
        lookup[str(source_key).casefold()] = source_value
    for option in options or []:
        lookup[str(option).casefold()] = option
    if not text:
        return default
    return lookup.get(text.casefold(), text)


def _coerce_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().casefold()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no", ""}:
            return False
    if value is None:
        return False
    raise ValueError(f"Invalid boolean for {field}: {value!r}")


def _raw_has(payload: Mapping[str, Any], key: str) -> bool:
    return key in payload and payload.get(key) not in (None, "")


def normalize_builder_context(
    raw: Mapping[str, Any] | None = None,
    *,
    mode: str | None = None,
    count: Any = None,
    source_label: str | None = None,
    session_source: str | None = None,
    randomize: bool | None = None,
    domain_filter: str | None = None,
    topic_filter: str | None = None,
    status_filter: str | None = None,
    question_count: Any = None,
) -> BuilderContext:
    payload = dict(raw or {})
    mode_value: Any
    count_value: Any
    source_value: Any
    session_source_value: Any
    randomize_value: Any
    domain_value: Any
    topic_value: Any
    status_value: Any

    if mode is not None:
        mode_value = mode
    elif _raw_has(payload, "mode"):
        mode_value = payload.get("mode")
    else:
        mode_value = payload.get("mode") or ""

    if count is not None:
        count_value = count
    elif _raw_has(payload, "count"):
        count_value = payload.get("count")
    elif question_count not in (None, ""):
        count_value = question_count
    else:
        count_value = payload.get("count") or ""

    if source_label is not None:
        source_value = source_label
    elif _raw_has(payload, "source_label"):
        source_value = payload.get("source_label")
    else:
        source_value = payload.get("source_label") or ""

    if session_source is not None:
        session_source_value = session_source
    elif _raw_has(payload, "session_source"):
        session_source_value = payload.get("session_source")
    else:
        session_source_value = payload.get("session_source") or DEFAULT_SESSION_SOURCE

    if randomize is not None:
        randomize_value = randomize
    elif "randomize" in payload:
        randomize_value = payload.get("randomize")
    else:
        randomize_value = False

    if domain_filter is not None:
        domain_value = domain_filter
    elif _raw_has(payload, "domain_filter"):
        domain_value = payload.get("domain_filter")
    else:
        domain_value = payload.get("domain_filter") or ALL_DOMAINS

    if topic_filter is not None:
        topic_value = topic_filter
    elif _raw_has(payload, "topic_filter"):
        topic_value = payload.get("topic_filter")
    else:
        topic_value = payload.get("topic_filter") or ALL_TOPICS

    if status_filter is not None:
        status_value = status_filter
    elif _raw_has(payload, "status_filter"):
        status_value = payload.get("status_filter")
    else:
        status_value = payload.get("status_filter") or ALL_QUESTIONS

    return {
        "mode": _collapse_ws(mode_value),
        "count": _normalize_count(count_value),
        "source_label": _collapse_ws(source_value),
        "session_source": _normalize_named(
            session_source_value,
            default=DEFAULT_SESSION_SOURCE,
            aliases=SESSION_SOURCE_ALIASES,
            options=list(SESSION_SOURCE_OPTIONS),
        ),
        "randomize": _coerce_bool(randomize_value, field="randomize"),
        "domain_filter": _normalize_named(domain_value, default=ALL_DOMAINS),
        "topic_filter": _normalize_named(topic_value, default=ALL_TOPICS),
        "status_filter": _normalize_named(
            status_value,
            default=ALL_QUESTIONS,
            aliases=STATUS_FILTER_ALIASES,
            options=list(STATUS_FILTER_OPTIONS),
        ),
    }


def builder_context_fingerprint(context: Mapping[str, Any]) -> str:
    canonical = dict(normalize_builder_context(context))
    payload = {
        "builder_identity": BUILDER_IDENTITY_KIND,
        "builder_identity_version": BUILDER_IDENTITY_VERSION,
        "builder_context": {key: canonical[key] for key in BUILDER_CONTEXT_FIELDS},
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_builder_identity(
    raw: Mapping[str, Any] | None = None,
    *,
    status: str = BUILDER_IDENTITY_CANONICAL,
    **kwargs: Any,
) -> BuilderIdentity:
    context = normalize_builder_context(raw, **kwargs)
    return {
        "builder_context": context,
        "builder_identity": BUILDER_IDENTITY_KIND,
        "builder_identity_version": BUILDER_IDENTITY_VERSION,
        "builder_context_fingerprint": builder_context_fingerprint(context),
        "builder_identity_status": str(status or BUILDER_IDENTITY_CANONICAL),
    }


def resolve_builder_identity_from_snapshot(
    payload: Mapping[str, Any] | None,
    *,
    saved_mode: str = "",
    source_label: str = "",
    question_count: Any = 0,
) -> BuilderIdentity:
    saved = dict(payload or {})
    claimed = any(
        key in saved and saved.get(key) not in (None, "")
        for key in ("builder_identity", "builder_identity_version", "builder_context_fingerprint")
    )
    raw_context = saved.get("builder_context", None)
    if "builder_context" not in saved or raw_context in (None, ""):
        if claimed:
            raise ValueError("Canonical builder identity is missing builder_context.")
        identity = canonical_builder_identity(
            None,
            mode=saved_mode,
            source_label=source_label,
            count=question_count,
            randomize=False,
            status=BUILDER_IDENTITY_AMBIGUOUS,
        )
        identity["builder_context_fingerprint"] = ""
        identity["builder_identity_status"] = BUILDER_IDENTITY_AMBIGUOUS
        return identity
    if not isinstance(raw_context, Mapping):
        raise ValueError("Session builder_context must be a mapping.")

    randomize_missing = "randomize" not in raw_context
    identity = canonical_builder_identity(
        raw_context,
        mode=None if _raw_has(raw_context, "mode") else saved_mode or None,
        source_label=None if _raw_has(raw_context, "source_label") else source_label or None,
        count=None if _raw_has(raw_context, "count") else question_count,
        status=BUILDER_IDENTITY_LEGACY_DEFAULTED if randomize_missing else BUILDER_IDENTITY_MIGRATED,
    )
    if not claimed:
        return identity

    stored_kind = str(saved.get("builder_identity") or "").strip()
    if stored_kind and stored_kind != BUILDER_IDENTITY_KIND:
        raise ValueError("Unsupported builder identity kind.")
    stored_version = saved.get("builder_identity_version")
    if stored_version not in (None, ""):
        try:
            version = int(stored_version)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid builder identity version.") from exc
        if version != BUILDER_IDENTITY_VERSION:
            raise ValueError("Unsupported future builder identity version.")
    stored_fp = str(saved.get("builder_context_fingerprint") or "").strip()
    if not stored_fp:
        raise ValueError("Canonical snapshot is missing builder_context_fingerprint.")
    if stored_fp != identity["builder_context_fingerprint"]:
        raise ValueError("Builder context fingerprint does not match stored builder context.")
    stored_status = str(saved.get("builder_identity_status") or BUILDER_IDENTITY_CANONICAL).strip()
    if stored_status == BUILDER_IDENTITY_INVALID:
        raise ValueError("Stored builder identity is invalid.")
    identity["builder_identity_status"] = stored_status or BUILDER_IDENTITY_CANONICAL
    return identity


def builder_identities_match(saved: Mapping[str, Any] | None, desired: Mapping[str, Any] | None) -> bool:
    if not isinstance(saved, Mapping) or not isinstance(desired, Mapping):
        return False
    saved_status = str(saved.get("builder_identity_status") or "").strip()
    if saved_status in {BUILDER_IDENTITY_AMBIGUOUS, BUILDER_IDENTITY_INVALID}:
        return False
    saved_kind = str(saved.get("builder_identity") or BUILDER_IDENTITY_KIND).strip()
    desired_kind = str(desired.get("builder_identity") or BUILDER_IDENTITY_KIND).strip()
    if saved_kind != BUILDER_IDENTITY_KIND or desired_kind != BUILDER_IDENTITY_KIND:
        return False
    saved_version = saved.get("builder_identity_version", BUILDER_IDENTITY_VERSION)
    desired_version = desired.get("builder_identity_version", BUILDER_IDENTITY_VERSION)
    try:
        if int(saved_version) != BUILDER_IDENTITY_VERSION or int(desired_version) != BUILDER_IDENTITY_VERSION:
            return False
    except (TypeError, ValueError):
        return False
    saved_fp = str(saved.get("builder_context_fingerprint") or "").strip()
    desired_fp = str(desired.get("builder_context_fingerprint") or "").strip()
    return bool(saved_fp) and saved_fp == desired_fp


def builder_ui_state_from_context(context: Mapping[str, Any] | None) -> dict[str, Any]:
    canonical = dict(normalize_builder_context(context))
    return {key: canonical[key] for key in BUILDER_CONTEXT_FIELDS}
