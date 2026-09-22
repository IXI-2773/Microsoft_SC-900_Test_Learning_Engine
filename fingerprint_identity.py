from __future__ import annotations

from collections.abc import Mapping
from typing import Any

FINGERPRINT_SCHEMA_VERSION = 2
FINGERPRINT_ALGORITHM = "sha256"
ARTIFACT_FINGERPRINT_DOMAIN = "artifact_projection_v1"
RUNTIME_FINGERPRINT_DOMAIN = "runtime_normalized_v1"
ARTIFACT_PROJECTION_VERSION = 1
RUNTIME_LOADER_CONTRACT_VERSION = 1

KNOWN_FINGERPRINT_DOMAINS = frozenset({ARTIFACT_FINGERPRINT_DOMAIN, RUNTIME_FINGERPRINT_DOMAIN})


class FingerprintIdentityError(ValueError):
    pass


def fingerprint_envelope(
    fingerprint: str,
    *,
    domain: str,
    bank_node_id: str = "",
) -> dict[str, Any]:
    value = str(fingerprint or "").strip()
    domain_value = str(domain or "").strip()
    if len(value) != 64:
        raise FingerprintIdentityError("Fingerprint must be a SHA-256 hex digest.")
    if domain_value not in KNOWN_FINGERPRINT_DOMAINS:
        raise FingerprintIdentityError(f"Unknown fingerprint domain: {domain_value!r}")
    payload: dict[str, Any] = {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "fingerprint_domain": domain_value,
        "fingerprint_algorithm": FINGERPRINT_ALGORITHM,
        "fingerprint": value,
    }
    if domain_value == ARTIFACT_FINGERPRINT_DOMAIN:
        payload["projection_version"] = ARTIFACT_PROJECTION_VERSION
    else:
        payload["loader_contract_version"] = RUNTIME_LOADER_CONTRACT_VERSION
    node = str(bank_node_id or "").strip()
    if node:
        payload["bank_node_id"] = node
    return payload


def validate_fingerprint_envelope(
    payload: Mapping[str, Any],
    *,
    expected_domain: str | None = None,
    expected_fingerprint: str | None = None,
    require_bank_node: bool = False,
) -> None:
    if int(payload.get("fingerprint_schema_version") or 0) != FINGERPRINT_SCHEMA_VERSION:
        raise FingerprintIdentityError("Unsupported fingerprint schema version.")
    domain = str(payload.get("fingerprint_domain") or "").strip()
    if domain not in KNOWN_FINGERPRINT_DOMAINS:
        raise FingerprintIdentityError("Unsupported fingerprint domain.")
    if expected_domain is not None and domain != expected_domain:
        raise FingerprintIdentityError("Fingerprint domain mismatch.")
    if str(payload.get("fingerprint_algorithm") or "").strip() != FINGERPRINT_ALGORITHM:
        raise FingerprintIdentityError("Unsupported fingerprint algorithm.")
    fingerprint = str(payload.get("fingerprint") or "").strip()
    if len(fingerprint) != 64:
        raise FingerprintIdentityError("Invalid fingerprint bytes.")
    if expected_fingerprint is not None and fingerprint != str(expected_fingerprint).strip():
        raise FingerprintIdentityError("Fingerprint value mismatch.")
    if domain == ARTIFACT_FINGERPRINT_DOMAIN:
        if int(payload.get("projection_version") or 0) != ARTIFACT_PROJECTION_VERSION:
            raise FingerprintIdentityError("Unsupported artifact projection version.")
    else:
        if int(payload.get("loader_contract_version") or 0) != RUNTIME_LOADER_CONTRACT_VERSION:
            raise FingerprintIdentityError("Unsupported runtime loader contract version.")
    if require_bank_node and not str(payload.get("bank_node_id") or "").strip():
        raise FingerprintIdentityError("Missing governed bank-node binding.")


def progress_runtime_identity_metadata(
    bank_fingerprint: str,
    *,
    bank_node_id: str = "",
) -> dict[str, Any]:
    envelope = fingerprint_envelope(
        bank_fingerprint,
        domain=RUNTIME_FINGERPRINT_DOMAIN,
        bank_node_id=bank_node_id,
    )
    return {
        "fingerprint_schema_version": envelope["fingerprint_schema_version"],
        "fingerprint_domain": envelope["fingerprint_domain"],
        "fingerprint_algorithm": envelope["fingerprint_algorithm"],
        "loader_contract_version": envelope["loader_contract_version"],
        **({"bank_node_id": envelope["bank_node_id"]} if "bank_node_id" in envelope else {}),
    }
