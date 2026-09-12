from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "content" / "sc900" / "microsoft-learn-corpus"
CALIBRATION_ROOT = CORPUS_ROOT / "calibration"
COMPILED_BANK_PATH = CORPUS_ROOT / "compiled" / "sc900_microsoft_learn_corpus_bank.json"
STORE_PATH = CORPUS_ROOT / "store" / "questions.json"
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"

CALIBRATION_VERSION = "sc900-exam-calibration-2026-09-12-v1"
PRECALIBRATION_BANK_SHA256 = "8fe229a51d850d6656a1dcd54bb6b10f556116f0ef992a18f5145fcf6ec1a254"
CALIBRATED_BANK_SHA256 = "177a4fb5f8a874ffe4dda6b69e3d1c03dbdad1f5db5a174a990eb8b5a0e5927c"
EXPECTED_DEFAULT_BANK_SHA256 = "60842eb28810d328fe56a427b7d72baedd6b31179ca4f1c98744392aa318a426"
VALID_TIERS = ("FUNDAMENTALS_CORE", "FUNDAMENTALS_APPLIED", "STRETCH")
CORE, APPLIED, STRETCH = VALID_TIERS

SUPER_FAMILY = {
    "identity_auth": "entra",
    "entra_governance": "entra",
    "entra_directory": "entra",
    "network": "azure_infra",
    "secrets_crypto": "azure_infra",
    "defender_cloud": "azure_security_mgmt",
    "defender_xdr": "xdr",
    "sentinel": "xdr",
    "purview_protection": "purview",
    "purview_risk_ediscovery": "purview",
    "compliance_trust": "purview",
    "zero_trust_concepts": "concepts",
}

PRODUCT_FAMILIES: dict[str, tuple[str, ...]] = {
    "identity_auth": (
        "authentication",
        "authorization",
        "multifactor",
        "mfa",
        "password",
        "federation",
        "sso",
        "sspr",
        "self-service password",
        "passkey",
        "windows hello",
        "authenticator",
        "phishing-resistant",
    ),
    "entra_governance": (
        "privileged identity management",
        "pim",
        "access review",
        "entitlement management",
        "identity protection",
        "conditional access",
        "lifecycle workflow",
        "privileged access",
        "just-in-time",
        "standing access",
    ),
    "entra_directory": (
        "microsoft entra id",
        "entra id",
        "hybrid identity",
        "cloud sync",
        "connect",
        "external id",
        "b2b",
        "b2c",
        "agent id",
        "workload identity",
        "managed identity",
        "service principal",
        "tenant",
    ),
    "network": (
        "network security group",
        "nsg",
        "azure firewall",
        "web application firewall",
        "waf",
        "ddos",
        "bastion",
        "virtual network",
        "vnet",
        "application gateway",
    ),
    "secrets_crypto": (
        "key vault",
        "encryption",
        "hashing",
        "certificate",
        "customer-managed key",
        "bring your own key",
    ),
    "defender_xdr": (
        "defender xdr",
        "defender for endpoint",
        "defender for office",
        "defender for identity",
        "defender for cloud apps",
        "defender vulnerability",
        "threat intelligence",
        "unified security operations",
        "defender portal",
    ),
    "defender_cloud": (
        "defender for cloud",
        "cloud security posture",
        "cspm",
        "cloud workload protection",
        "cwpp",
        "secure score",
    ),
    "sentinel": (
        "microsoft sentinel",
        "sentinel",
        "siem",
        "soar",
        "analytics rule",
        "playbook",
        "incident",
    ),
    "purview_protection": (
        "sensitivity label",
        "data loss prevention",
        "dlp",
        "retention",
        "records management",
        "data classification",
        "content explorer",
        "activity explorer",
        "trainable classifier",
    ),
    "purview_risk_ediscovery": (
        "insider risk",
        "ediscovery",
        "audit",
        "communication compliance",
        "privileged access management",
    ),
    "compliance_trust": (
        "compliance manager",
        "compliance score",
        "service trust",
        "privacy",
        "purview portal",
        "microsoft purview",
    ),
    "zero_trust_concepts": (
        "zero trust",
        "assume breach",
        "least privilege",
        "verify explicitly",
        "defense in depth",
        "shared responsibility",
    ),
}

MULTI_STEP_MARKERS = (
    " yet ",
    "however",
    "already ",
    "still hold",
    "still has",
    "still uses",
    "administrator claims",
    "security team claims",
    "mistakenly",
    "incorrectly",
    "missing",
    "does not currently",
    "does not use",
    "does not have",
    "best explains why",
    "which statement best",
    "despite ",
    "even though",
    "instead of",
    "but the ",
    "but an ",
    "but a ",
)
DIRECT_STEM_MARKERS = (
    "what is ",
    "which microsoft",
    "which service",
    "which capability",
    "which feature",
    "which principle",
    "which statement describes",
    "which azure",
    "which entra",
    "which defender",
    "which purview",
    "what does ",
    "what capability",
)
NEGATIVE_MARKERS = (" not ", " n't", "except", "false", "never ", "cannot ")
ABSOLUTE_MARKERS = (" always ", " never ", " only ", " all ", " none ", " must ")
CLUE_SPLIT = re.compile(r"(?<=[.!?])\s+|(?:\byet\b|\bhowever\b|\balready\b|\bbut\b|;)", re.I)
WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _error(code: str, message: str, **context: Any) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    payload.update(context)
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"[.!?]+", text or "") if part.strip()]
    return max(1, len(parts)) if str(text or "").strip() else 0


def _families_in(text: str) -> set[str]:
    lowered = f" {text.casefold()} "
    found: set[str] = set()
    for family, markers in PRODUCT_FAMILIES.items():
        if any(marker in lowered for marker in markers):
            found.add(family)
    return found


def _super_families(text: str) -> set[str]:
    return {SUPER_FAMILY[family] for family in _families_in(text) if family in SUPER_FAMILY}


def _choice_map(question: Mapping[str, Any]) -> dict[str, str]:
    choices = question.get("choices")
    if isinstance(choices, Mapping):
        return {str(key): str(value) for key, value in choices.items()}
    if isinstance(choices, list):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return {letters[index]: str(item.get("text") or "") for index, item in enumerate(choices)}
    return {}


def _correct_letters(question: Mapping[str, Any], choice_map: Mapping[str, str]) -> list[str]:
    correct = question.get("correct")
    if isinstance(correct, list) and correct:
        return [str(item).upper() for item in correct]
    answers = question.get("correct_answer")
    choices = question.get("choices")
    if isinstance(choices, list):
        id_to_letter = {str(item.get("id")): "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[index] for index, item in enumerate(choices)}
        values = answers if isinstance(answers, list) else [answers]
        return [id_to_letter.get(str(value), str(value).upper()) for value in values if value]
    return []


def _prompt(question: Mapping[str, Any]) -> str:
    return str(question.get("prompt") or question.get("stem") or "")


def classify_distractor(stem: str, option: str, is_correct: bool, correct_text: str) -> str:
    if is_correct:
        return "CORRECT"
    lowered = option.casefold()
    if not option.strip():
        return "AMBIGUOUS"
    if lowered in {"none of the above", "all of the above", "both a and b"}:
        return "ABSURD"
    if any(marker in lowered for marker in ("badge printer", "only a printer", "physical badge")):
        return "ABSURD"
    option_super = _super_families(option)
    correct_super = _super_families(correct_text) | _super_families(stem)
    if option_super and correct_super and option_super.isdisjoint(correct_super):
        return "CROSS_PRODUCT_GIVEAWAY"
    if option_super & correct_super:
        return "PLAUSIBLE_NEIGHBOR"
    if any(marker in lowered for marker in ("legacy", "on-premises only")):
        return "COMMON_MISCONCEPTION"
    if option_super:
        return "TECHNICALLY_RELATED_BUT_WRONG"
    return "PLAUSIBLE_NEIGHBOR"


def measure_question(question: Mapping[str, Any], *, difficulty: str = "") -> dict[str, Any]:
    prompt = _prompt(question)
    choice_map = _choice_map(question)
    correct_letters = _correct_letters(question, choice_map)
    correct_text = " ".join(choice_map.get(letter, "") for letter in correct_letters)
    words = word_count(prompt)
    sentences = sentence_count(prompt)
    lowered = f" {prompt.casefold()} "
    independent_clues = max(1, len([part for part in CLUE_SPLIT.split(prompt) if part.strip()]))
    if sentences >= 3:
        independent_clues = max(independent_clues, sentences)
    multi_step_hits = [marker.strip() for marker in MULTI_STEP_MARKERS if marker in lowered]
    direct_hits = [marker.strip() for marker in DIRECT_STEM_MARKERS if marker in lowered]
    reasoning_steps = 0
    if independent_clues >= 3 or len(multi_step_hits) >= 2:
        reasoning_steps = 2
    elif multi_step_hits or independent_clues >= 2 and words >= 40:
        reasoning_steps = 1
    if "missing" in lowered or "best explains" in lowered:
        reasoning_steps = max(reasoning_steps, 2)
    stem_style = str(question.get("stem_style") or (question.get("metadata") or {}).get("stem_style") or "")
    if stem_style == "misconception_correction":
        reasoning_steps = max(reasoning_steps, 1)
        if words >= 45 or len(multi_step_hits) >= 1:
            reasoning_steps = max(reasoning_steps, 2)
    if stem_style in {"direct_concept", "capability_selection", "service_selection"} and not multi_step_hits:
        reasoning_steps = min(reasoning_steps, 1)
        if words < 40 and sentences <= 2:
            reasoning_steps = 0
    concepts = max(1, len(_families_in(prompt)) or (2 if independent_clues >= 2 else 1))
    option_lengths = {letter: word_count(text) for letter, text in choice_map.items()}
    correct_len = sum(option_lengths.get(letter, 0) for letter in correct_letters)
    distractor_lens = [length for letter, length in option_lengths.items() if letter not in correct_letters]
    mean_d = sum(distractor_lens) / len(distractor_lens) if distractor_lens else 0.0
    distractors = []
    giveaways = 0
    ambiguous = 0
    absurd = 0
    for letter, text in choice_map.items():
        label = classify_distractor(prompt, text, letter in correct_letters, correct_text)
        distractors.append({"letter": letter, "class": label})
        if label == "CROSS_PRODUCT_GIVEAWAY":
            giveaways += 1
        elif label == "AMBIGUOUS":
            ambiguous += 1
        elif label == "ABSURD":
            absurd += 1
    product_detail = min(
        3, prompt.casefold().count("portal") + prompt.casefold().count("blade") + prompt.casefold().count("powershell")
    )
    admin_detail = min(
        3, sum(token in lowered for token in (" administrator", " configure", " tenant-wide", " json", " cmdlet"))
    )
    proposed = propose_tier(
        {
            "stem_style": stem_style,
            "difficulty": difficulty or str(question.get("difficulty") or ""),
            "word_count": words,
            "sentence_count": sentences,
            "independent_clues": independent_clues,
            "reasoning_steps": reasoning_steps,
            "multi_step_hits": multi_step_hits,
            "direct_hits": direct_hits,
            "giveaways": giveaways,
        }
    )
    rewrite_required = bool(
        proposed["tier"] == STRETCH
        or giveaways >= 2
        or words >= 70
        or reasoning_steps >= 2
        or any(
            token in prompt.casefold()
            for token in (
                "which pairing",
                "pairing is accurate",
                "pairing is appropriate",
                "what is wrong",
                "colleague says",
                "learner says",
                "helpdesk agent says",
                "principle is missing",
                "control is missing",
            )
        )
    )
    return {
        "question_id": str(question.get("id") or ""),
        "current_difficulty": difficulty or str(question.get("difficulty") or ""),
        "stem_style": stem_style,
        "word_count": words,
        "sentence_count": sentences,
        "scenario_length": words if "scenario" in stem_style or sentences >= 2 else 0,
        "number_of_independent_clues": independent_clues,
        "estimated_reasoning_steps": reasoning_steps,
        "number_of_concepts_required": concepts,
        "product_detail_depth": product_detail,
        "administration_detail_depth": admin_detail,
        "distractor_relatedness": "mixed" if giveaways else "neighboring",
        "distractor_obviousness": (
            "giveaway" if giveaways >= 2 else ("one_weak" if giveaways == 1 else "knowledge_required")
        ),
        "negative_wording": any(marker in lowered for marker in NEGATIVE_MARKERS),
        "absolute_wording": any(marker in lowered for marker in ABSOLUTE_MARKERS),
        "correct_option_word_count": correct_len,
        "mean_distractor_word_count": round(mean_d, 2),
        "answer_length_ratio": round(correct_len / mean_d, 3) if mean_d else 1.0,
        "current_calibration_tier": proposed["tier"],
        "proposed_calibration_tier": proposed["tier"],
        "rewrite_required": rewrite_required,
        "rewrite_reason": proposed["reason"] if rewrite_required else "",
        "distractors": distractors,
        "giveaway_count": giveaways,
        "ambiguous_count": ambiguous,
        "absurd_count": absurd,
        "domain": str(question.get("domain") or ""),
        "blueprint_leaf_id": str(
            question.get("blueprint_leaf_id") or (question.get("metadata") or {}).get("blueprint_leaf_id") or ""
        ),
        "tested_decision": str(
            question.get("tested_decision") or (question.get("metadata") or {}).get("tested_decision") or ""
        ),
        "question_type": str(question.get("question_type") or question.get("type") or "single"),
        "correct": correct_letters,
        "prompt": prompt,
    }


def propose_tier(features: Mapping[str, Any]) -> dict[str, str]:
    style = str(features.get("stem_style") or "")
    words = int(features.get("word_count") or 0)
    steps = int(features.get("reasoning_steps") or 0)
    clues = int(features.get("independent_clues") or 1)
    difficulty = str(features.get("difficulty") or "")
    multi = list(features.get("multi_step_hits") or [])
    direct = list(features.get("direct_hits") or [])
    if steps >= 2 or words >= 70 or clues >= 3 or (style == "misconception_correction" and (words >= 50 or multi)):
        return {"tier": STRETCH, "reason": "multi-step or overloaded scenario"}
    if (
        style in {"direct_concept", "capability_selection", "service_selection", "current_topic"}
        and steps <= 1
        and words < 48
    ):
        return {"tier": CORE, "reason": "direct recognition"}
    if direct and steps == 0 and words < 55:
        return {"tier": CORE, "reason": "direct stem"}
    if style == "short_scenario" and steps <= 1 and words < 42 and difficulty != "intermediate":
        return {"tier": CORE, "reason": "short one-step scenario"}
    if style in {"concept_distinction", "distinction_comparison"} and steps <= 1 and words < 55:
        return {"tier": APPLIED, "reason": "neighboring distinction"}
    if style == "short_scenario" and steps <= 1:
        return {"tier": APPLIED, "reason": "short applied scenario"}
    if steps <= 1 and words < 60:
        return {"tier": APPLIED, "reason": "one inference"}
    return {"tier": STRETCH, "reason": "above fundamentals average load"}


def exam_simulation_eligible(tier: str) -> bool:
    return tier in {CORE, APPLIED}


def measure_bank(
    questions: Sequence[Mapping[str, Any]], *, difficulty_by_id: Mapping[str, str] | None = None
) -> list[dict[str, Any]]:
    difficulty_by_id = difficulty_by_id or {}
    rows = []
    for question in questions:
        qid = str(question.get("id") or "")
        rows.append(
            measure_question(question, difficulty=difficulty_by_id.get(qid, str(question.get("difficulty") or "")))
        )
    return rows


def aggregate_measurements(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tiers = Counter(str(row.get("proposed_calibration_tier")) for row in rows)
    styles = Counter(str(row.get("stem_style") or "unknown") for row in rows)
    difficulties = Counter(str(row.get("current_difficulty") or "unknown") for row in rows)
    steps = Counter(int(row.get("estimated_reasoning_steps") or 0) for row in rows)
    giveaways = sum(int(row.get("giveaway_count") or 0) for row in rows)
    rewrite = sum(1 for row in rows if row.get("rewrite_required"))
    words = [int(row.get("word_count") or 0) for row in rows]
    ratios = [float(row.get("answer_length_ratio") or 1.0) for row in rows]
    return {
        "question_count": len(rows),
        "tier_distribution": dict(sorted(tiers.items())),
        "stem_style_distribution": dict(sorted(styles.items())),
        "difficulty_distribution": dict(sorted(difficulties.items())),
        "reasoning_step_distribution": {str(key): steps[key] for key in sorted(steps)},
        "rewrite_required_count": rewrite,
        "cross_product_giveaway_options": giveaways,
        "questions_with_giveaway": sum(1 for row in rows if int(row.get("giveaway_count") or 0) > 0),
        "mean_word_count": round(sum(words) / len(words), 2) if words else 0,
        "median_word_count": sorted(words)[len(words) // 2] if words else 0,
        "p90_word_count": sorted(words)[int(0.9 * (len(words) - 1))] if words else 0,
        "mean_answer_length_ratio": round(sum(ratios) / len(ratios), 3) if ratios else 1.0,
        "length_leakage_outliers": sum(1 for ratio in ratios if ratio >= 1.8),
        "negative_wording_count": sum(1 for row in rows if row.get("negative_wording")),
        "multi_select_count": sum(1 for row in rows if "multi" in str(row.get("question_type") or "").casefold()),
    }


def answer_position_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    letters = [str((row.get("correct") or ["?"])[0]) for row in rows if len(row.get("correct") or []) == 1]
    counts = Counter(letters)
    runs = []
    current = ""
    length = 0
    max_run = 0
    for letter in letters:
        if letter == current:
            length += 1
        else:
            if length >= 4:
                runs.append({"letter": current, "length": length})
            current = letter
            length = 1
        max_run = max(max_run, length)
    if length >= 4:
        runs.append({"letter": current, "length": length})
    serial_matches = 0
    for index, letter in enumerate(letters):
        expected = "ABCD"[index % 4]
        if letter == expected:
            serial_matches += 1
    n = len(letters) or 1
    chi = sum(((counts.get(letter, 0) - n / 4) ** 2) / (n / 4) for letter in "ABCD")
    return {
        "counts": {letter: counts.get(letter, 0) for letter in "ABCD"},
        "longest_run": max_run,
        "runs_of_4_or_more": runs,
        "serial_modulo_match_rate": round(serial_matches / n, 3),
        "chi_square_vs_uniform": round(chi, 3),
        "predictable": serial_matches / n >= 0.40 or chi >= 12.0,
    }


def load_store_difficulty() -> dict[str, str]:
    if not STORE_PATH.is_file():
        return {}
    rows = load_json(STORE_PATH)
    return {str(row.get("id")): str(row.get("difficulty") or "") for row in rows if isinstance(row, Mapping)}


def _index_by_question_id(payload: Any) -> dict[str, dict[str, Any]]:
    items = payload.get("items") if isinstance(payload, Mapping) else payload
    if not isinstance(items, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for row in items:
        if isinstance(row, dict) and row.get("question_id"):
            indexed[str(row["question_id"])] = row
    return indexed


def load_classification() -> dict[str, dict[str, Any]]:
    path = CALIBRATION_ROOT / "classification.json"
    if not path.is_file():
        return {}
    return _index_by_question_id(load_json(path))


def load_overlay() -> dict[str, dict[str, Any]]:
    path = CALIBRATION_ROOT / "rewrite_overlay.json"
    if not path.is_file():
        return {}
    return _index_by_question_id(load_json(path))


def apply_overlay_to_record(record: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(record))
    if overlay.get("stem"):
        updated["stem"] = overlay["stem"]
    if overlay.get("explanation"):
        updated["explanation"] = overlay["explanation"]
    if overlay.get("choices"):
        raw_choices = overlay["choices"]
        if isinstance(raw_choices, Mapping):
            existing = list(updated.get("choices") or [])
            for index, choice in enumerate(existing):
                letter = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[index]
                if letter in raw_choices:
                    choice["text"] = raw_choices[letter]
                elif str(choice.get("id")) in raw_choices:
                    choice["text"] = raw_choices[str(choice.get("id"))]
            updated["choices"] = existing
        elif isinstance(raw_choices, list):
            updated["choices"] = json.loads(json.dumps(raw_choices))
    if overlay.get("correct_answer"):
        updated["correct_answer"] = overlay["correct_answer"]
    metadata = dict(updated.get("metadata") or {})
    if overlay.get("stem_style"):
        metadata["stem_style"] = overlay["stem_style"]
    if overlay.get("tested_decision"):
        metadata["tested_decision"] = overlay["tested_decision"]
    if overlay.get("semantic_family_id"):
        metadata["semantic_family_id"] = overlay["semantic_family_id"]
    metadata["calibration_rewrite"] = True
    metadata["calibration_rewrite_reason"] = overlay.get("reason", "")
    updated["metadata"] = metadata
    return updated


def apply_calibration(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    classification = load_classification()
    overlay = load_overlay()
    calibrated: list[dict[str, Any]] = []
    for record in records:
        updated = json.loads(json.dumps(record))
        qid = str(updated.get("id") or "")
        if qid in overlay and updated.get("promotion_status") == "approved":
            updated = apply_overlay_to_record(updated, overlay[qid])
        metadata = dict(updated.get("metadata") or {})
        row = classification.get(qid, {})
        tier = str(row.get("exam_calibration_tier") or row.get("proposed_calibration_tier") or "")
        if tier in VALID_TIERS:
            metadata["exam_calibration_tier"] = tier
            metadata["reasoning_steps"] = int(row.get("reasoning_steps", row.get("estimated_reasoning_steps", 0)))
            metadata["exam_simulation_eligible"] = bool(
                row.get("exam_simulation_eligible", exam_simulation_eligible(tier))
            )
            metadata["calibration_version"] = CALIBRATION_VERSION
        updated["metadata"] = metadata
        calibrated.append(updated)
    return calibrated


def calibration_errors(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    classification = load_classification()
    approved = [row for row in records if row.get("promotion_status") == "approved"]
    if classification and len(classification) != len(approved):
        missing = sorted({str(row.get("id")) for row in approved} - set(classification))
        extra = sorted(set(classification) - {str(row.get("id")) for row in approved})
        if missing:
            errors.append(
                _error(
                    "CALIBRATION_INCOMPLETE",
                    "approved items missing classification",
                    missing=missing[:20],
                    count=len(missing),
                )
            )
        if extra:
            errors.append(
                _error(
                    "CALIBRATION_ORPHAN",
                    "classification rows without approved items",
                    extra=extra[:20],
                    count=len(extra),
                )
            )
    for record in approved:
        qid = str(record.get("id") or "")
        raw_meta = record.get("metadata")
        metadata: dict[str, Any] = dict(raw_meta) if isinstance(raw_meta, Mapping) else {}
        tier = str(metadata.get("exam_calibration_tier") or "")
        if tier not in VALID_TIERS:
            errors.append(
                _error(
                    "MISSING_CALIBRATION_TIER",
                    "approved item lacks a valid exam_calibration_tier",
                    question_id=qid,
                    tier=tier,
                )
            )
            continue
        if "reasoning_steps" not in metadata:
            errors.append(_error("MISSING_REASONING_STEPS", "approved item lacks reasoning_steps", question_id=qid))
        if "exam_simulation_eligible" not in metadata:
            errors.append(
                _error(
                    "MISSING_EXAM_SIMULATION_ELIGIBLE", "approved item lacks exam_simulation_eligible", question_id=qid
                )
            )
        elif metadata.get("exam_simulation_eligible") not in (True, False):
            errors.append(
                _error("INVALID_EXAM_SIMULATION_ELIGIBLE", "exam_simulation_eligible must be boolean", question_id=qid)
            )
        if str(metadata.get("calibration_version") or "") != CALIBRATION_VERSION:
            errors.append(_error("CALIBRATION_VERSION_MISMATCH", "unexpected calibration_version", question_id=qid))
        if not str(metadata.get("tested_decision") or "").strip():
            errors.append(
                _error(
                    "EMPTY_TESTED_DECISION", "approved question is missing a durable tested_decision", question_id=qid
                )
            )
    default_digest = sha256_file(DEFAULT_BANK) if DEFAULT_BANK.is_file() else ""
    if default_digest != EXPECTED_DEFAULT_BANK_SHA256:
        errors.append(_error("DEFAULT_BANK_CHANGED", "default launch bank digest changed"))
    return errors


def calibration_gate(rows: Sequence[Mapping[str, Any]], *, copyrighted_imported: bool = False) -> dict[str, Any]:
    tiers = Counter(str(row.get("exam_calibration_tier") or row.get("proposed_calibration_tier")) for row in rows)
    total = len(rows) or 1
    core = tiers.get(CORE, 0)
    stretch = tiers.get(STRETCH, 0)
    giveaways = sum(int(row.get("giveaway_count") or 0) for row in rows)
    ambiguous = sum(int(row.get("ambiguous_count") or 0) for row in rows)
    flags: dict[str, Any] = {
        "ALL_APPROVED_ITEMS_CALIBRATED": all(
            str(row.get("exam_calibration_tier") or row.get("proposed_calibration_tier")) in VALID_TIERS for row in rows
        ),
        "FUNDAMENTALS_CORE_MAJORITY": core / total >= 0.60,
        "STRETCH_IS_MINORITY": stretch / total <= 0.10,
        "KNOWN_AMBIGUOUS_APPROVED": ambiguous,
        "CROSS_PRODUCT_GIVEAWAYS_REMAINING": giveaways,
        "COPYRIGHTED_REFERENCE_TEXT_IMPORTED": copyrighted_imported,
    }
    passed = (
        flags["ALL_APPROVED_ITEMS_CALIBRATED"]
        and flags["FUNDAMENTALS_CORE_MAJORITY"]
        and flags["STRETCH_IS_MINORITY"]
        and ambiguous == 0
        and not copyrighted_imported
    )
    flags["MICROSOFT_EXAM_STYLE_CALIBRATION"] = "PASS" if passed else "FAIL"
    flags["tier_distribution"] = dict(sorted(tiers.items()))
    flags["core_share"] = round(core / total, 3)
    flags["stretch_share"] = round(stretch / total, 3)
    return flags


def dump_precalibration_measurements() -> dict[str, Any]:
    bank = load_json(COMPILED_BANK_PATH)
    questions = bank["questions"]
    rows = measure_bank(questions, difficulty_by_id=load_store_difficulty())
    summary = aggregate_measurements(rows)
    positions = answer_position_audit(rows)
    compact = [{key: row[key] for key in row if key != "prompt"} for row in rows]
    payload = {
        "calibration_version": CALIBRATION_VERSION,
        "precalibration_bank_sha256": PRECALIBRATION_BANK_SHA256,
        "actual_bank_sha256": sha256_file(COMPILED_BANK_PATH),
        "summary": summary,
        "answer_position": positions,
        "items": compact,
    }
    write_json(CALIBRATION_ROOT / "precalibration_measurements.json", payload)
    rewrite_candidates = [
        {
            "question_id": row["question_id"],
            "tier": row["proposed_calibration_tier"],
            "reason": row["rewrite_reason"],
            "word_count": row["word_count"],
            "stem_style": row["stem_style"],
            "domain": row["domain"],
            "prompt": row["prompt"],
            "giveaway_count": row["giveaway_count"],
        }
        for row in rows
        if row["rewrite_required"]
    ]
    write_json(
        CALIBRATION_ROOT / "rewrite_candidates.json", {"count": len(rewrite_candidates), "items": rewrite_candidates}
    )
    return {"summary": summary, "answer_position": positions, "rewrite_required": len(rewrite_candidates)}


if __name__ == "__main__":
    print(json.dumps(dump_precalibration_measurements(), indent=2))
