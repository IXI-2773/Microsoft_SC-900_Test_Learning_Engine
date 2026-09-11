from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from tools.build_sc900_phase2 import load_phase2_records, review_content_sha256

ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "content" / "sc900" / "phase2"
REVIEWER = "openai-gpt5.6-sol-deep-review-correction"
REVIEWED_AT = "2026-09-11T13:10:00Z"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


def bind_review_custody_and_sources() -> None:
    records = load_phase2_records()
    by_id = {row["id"]: row for row in records}
    seen: set[str] = set()
    for review_path in sorted((PHASE2 / "reviews").glob("*.json")):
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        payload["custody_hash_algorithm"] = "sha256(canonical reviewed question content excluding semantic_family_id)"
        payload["custody_reverified_by"] = REVIEWER
        payload["custody_reverified_at"] = REVIEWED_AT
        for receipt in payload.get("reviews", []):
            qid = receipt["question_id"]
            if qid not in by_id:
                raise RuntimeError(f"review without Phase-2 authored row: {qid}")
            receipt["reviewed_content_sha256"] = review_content_sha256(by_id[qid])
            receipt["custody_reverified_by"] = REVIEWER
            receipt["custody_reverified_at"] = REVIEWED_AT
            seen.add(qid)
        review_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if seen != set(by_id):
        raise RuntimeError(f"review custody coverage mismatch: {len(seen)} vs {len(by_id)}")

    inventory_path = PHASE2 / "source_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    sources = inventory["sources"]
    by_url = {source["url"]: source for source in sources}
    all_questions = json.loads((ROOT / "content/sc900/phase1/store/questions.json").read_text(encoding="utf-8")) + records
    claims: dict[str, dict[str, set[str]]] = {}
    for row in all_questions:
        metadata = row.get("metadata") or {}
        urls = set(row.get("references") or []) | set(metadata.get("source_urls") or [])
        for url in urls:
            claim = claims.setdefault(url, {"objectives": set(), "leaves": set()})
            claim["objectives"].add(row["objective"])
            claim["leaves"].add(metadata["blueprint_leaf_id"])
    for url, claim in sorted(claims.items()):
        if url in by_url:
            entry = by_url[url]
            entry["objective_ids"] = sorted(set(entry.get("objective_ids", [])) | claim["objectives"])
            entry["leaf_ids"] = sorted(set(entry.get("leaf_ids", [])) | claim["leaves"])
            continue
        parsed = urlparse(url)
        slug = parsed.path.rstrip("/").split("/")[-1] or "microsoft-source"
        entry = {
            "source_id": "question-source-" + hashlib.sha256(url.encode()).hexdigest()[:12],
            "url": url,
            "title": "Official Microsoft source: " + slug.replace("-", " ").title(),
            "source_type": "module" if "/training/modules/" in parsed.path else "product_documentation",
            "objective_ids": sorted(claim["objectives"]),
            "leaf_ids": sorted(claim["leaves"]),
            "retrieved_at": "2026-09-11",
            "assessment_content_used": False,
        }
        sources.append(entry)
        by_url[url] = entry
    inventory["sources"] = sorted(sources, key=lambda row: row["source_id"])
    inventory["per_question_source_join_required"] = True
    inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_validator() -> None:
    path = ROOT / "tools/validate_sc900_phase2.py"
    text = path.read_text(encoding="utf-8")
    import_anchor = "from tools.validate_sc900_phase1 import REVIEW_CHECK_FIELDS, validate_source_inventory\n"
    extra_import = "from tools.build_sc900_phase2 import BUILD_RECEIPT_PATH, DEFAULT_BANK, SEMANTIC_AUDIT_PATH, review_content_sha256, sha256_file\n"
    if extra_import not in text:
        text = replace_once(text, import_anchor, import_anchor + extra_import, "builder import")

    load_anchor = "def _load_phase2_ids(path: Path) -> list[str]:\n"
    if "def _load_phase2_records(" not in text:
        block = '''def _load_phase2_records(path: Path) -> list[dict[str, Any]]:\n    rows: list[dict[str, Any]] = []\n    if not path.exists():\n        return rows\n    for batch_path in sorted(path.glob("*.jsonl")):\n        for line in batch_path.read_text(encoding="utf-8").splitlines():\n            if not line.strip():\n                continue\n            payload = json.loads(line)\n            if isinstance(payload, dict):\n                rows.append(payload)\n    return rows\n\n\ndef validate_phase2_review_custody(\n    records: Sequence[Mapping[str, Any]], review_receipts: Sequence[Mapping[str, Any]]\n) -> list[dict[str, Any]]:\n    errors: list[dict[str, Any]] = []\n    reviews = _review_index(review_receipts)\n    ids = [normalize_text(row.get("id")) for row in records]\n    if len(ids) != 50 or len(set(ids)) != 50:\n        errors.append(_error("REVIEW_CUSTODY_INPUT_SET_INVALID", "custody verification requires exactly 50 unique Phase-2 authored records"))\n    for record in records:\n        qid = normalize_text(record.get("id"))\n        receipt = reviews.get(qid)\n        if receipt is None:\n            errors.append(_error("MISSING_PHASE2_REVIEW_CUSTODY", "Phase-2 authored record lacks a review receipt", question_id=qid))\n            continue\n        expected = review_content_sha256(record)\n        actual = normalize_text(receipt.get("reviewed_content_sha256")).lower()\n        if actual != expected:\n            errors.append(_error("REVIEW_CONTENT_HASH_MISMATCH", "review receipt is not bound to the authored question content", question_id=qid, expected=expected, actual=actual))\n    return errors\n\n\ndef validate_question_source_links(questions: Sequence[Mapping[str, Any]], inventory: Mapping[str, Any]) -> list[dict[str, Any]]:\n    errors: list[dict[str, Any]] = []\n    by_url: dict[str, list[Mapping[str, Any]]] = defaultdict(list)\n    for source in inventory.get("sources", []):\n        if isinstance(source, Mapping) and normalize_text(source.get("url")):\n            by_url[normalize_text(source.get("url"))].append(source)\n    for record in questions:\n        if phase1_review_status(record) != "approved":\n            continue\n        qid = normalize_text(record.get("id"))\n        objective = normalize_text(record.get("objective"))\n        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}\n        leaf = normalize_text(metadata.get("blueprint_leaf_id"))\n        urls = {normalize_text(value) for value in record.get("references", []) if normalize_text(value)}\n        urls.update(normalize_text(value) for value in metadata.get("source_urls", []) if normalize_text(value))\n        if not urls:\n            errors.append(_error("QUESTION_SOURCE_LINK_MISSING", "approved question has no source URL to join to inventory", question_id=qid))\n            continue\n        for url in sorted(urls):\n            candidates = by_url.get(url, [])\n            if not candidates:\n                errors.append(_error("QUESTION_SOURCE_NOT_IN_INVENTORY", "approved question source URL is absent from source inventory", question_id=qid, url=url))\n                continue\n            if not any(objective in set(source.get("objective_ids", [])) and leaf in set(source.get("leaf_ids", [])) for source in candidates):\n                errors.append(_error("QUESTION_SOURCE_SCOPE_MISMATCH", "source inventory entry does not claim the question objective and blueprint leaf", question_id=qid, url=url, objective=objective, leaf=leaf))\n    return errors\n\n\ndef validate_semantic_audit(questions: Sequence[Mapping[str, Any]], audit: Mapping[str, Any]) -> list[dict[str, Any]]:\n    errors: list[dict[str, Any]] = []\n    approved = [row for row in questions if phase1_review_status(row) == "approved"]\n    decisions = {normalize_text(row.get("question_id")): row for row in audit.get("decisions", []) if isinstance(row, Mapping)}\n    approved_ids = {normalize_text(row.get("id")) for row in approved}\n    if set(decisions) != approved_ids:\n        errors.append(_error("SEMANTIC_AUDIT_COVERAGE_MISMATCH", "semantic-family audit must cover exactly every approved cumulative question", expected=len(approved_ids), actual=len(decisions)))\n        return errors\n    for record in approved:\n        qid = normalize_text(record.get("id"))\n        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}\n        actual_family = normalize_text(metadata.get("semantic_family_id"))\n        expected_family = normalize_text(decisions[qid].get("semantic_family_id"))\n        if not expected_family or actual_family != expected_family:\n            errors.append(_error("SEMANTIC_AUDIT_STORE_MISMATCH", "canonical store family does not match audited family assignment", question_id=qid, expected=expected_family, actual=actual_family))\n    reported_count = audit.get("family_count")\n    actual_count = len({normalize_text(row.get("semantic_family_id")) for row in decisions.values()})\n    if reported_count != actual_count:\n        errors.append(_error("SEMANTIC_AUDIT_COUNT_MISMATCH", "semantic audit family_count is inconsistent", expected=actual_count, actual=reported_count))\n    return errors\n\n\ndef validate_build_receipt(store_dir: Path, compiled_path: Path, receipt: Mapping[str, Any]) -> list[dict[str, Any]]:\n    errors: list[dict[str, Any]] = []\n    if normalize_text(receipt.get("status")) != "REPRODUCIBLE":\n        errors.append(_error("BUILD_RECEIPT_NOT_REPRODUCIBLE", "Phase-2 build receipt must declare REPRODUCIBLE"))\n        return errors\n    outputs = receipt.get("outputs") if isinstance(receipt.get("outputs"), Mapping) else {}\n    store_hashes = outputs.get("store") if isinstance(outputs.get("store"), Mapping) else {}\n    for name in ("questions.json", "source_material.json", "quarantine.json", "review.json", "review_decisions.json"):\n        file_path = store_dir / name\n        expected = normalize_text(store_hashes.get(name)).lower()\n        actual = sha256_file(file_path) if file_path.exists() else ""\n        if expected != actual:\n            errors.append(_error("BUILD_STORE_HASH_MISMATCH", "committed store artifact differs from build receipt", file=name, expected=expected, actual=actual))\n    expected_compiled = normalize_text(outputs.get("compiled_sha256")).lower()\n    actual_compiled = sha256_file(compiled_path) if compiled_path.exists() else ""\n    if expected_compiled != actual_compiled:\n        errors.append(_error("BUILD_COMPILED_HASH_MISMATCH", "compiled candidate differs from build receipt", expected=expected_compiled, actual=actual_compiled))\n    expected_default = normalize_text(outputs.get("default_launch_bank_sha256")).lower()\n    actual_default = sha256_file(DEFAULT_BANK) if DEFAULT_BANK.exists() else ""\n    if expected_default != actual_default:\n        errors.append(_error("DEFAULT_BANK_HASH_MISMATCH", "default launch bank changed relative to Phase-2 build receipt", expected=expected_default, actual=actual_default))\n    if receipt.get("pending_before_approval_count") != 50 or receipt.get("approved_after_review_count") != 100:\n        errors.append(_error("BUILD_CUSTODY_COUNTS_INVALID", "build receipt does not prove 50 pending imports followed by 100 cumulative approvals"))\n    return errors\n\n\n'''
        text = replace_once(text, load_anchor, block + load_anchor, "evidence helper insertion")

    old = '''    reviews = _load_review_receipts(args.phase1_reviews, args.phase2_reviews)\n    phase2_ids = _load_phase2_ids(args.phase2_batches)\n    inventory = _load_json(args.source_inventory, {})\n    if not isinstance(inventory, Mapping):\n        inventory = {}\n\n    source_errors = validate_source_inventory(inventory, taxonomy)\n    result = validate_phase2_set(questions, taxonomy, reviews, phase2_ids)\n    compiled_count, bank_issues = _bank_validation_issues(args.compiled)\n    result["source_inventory_errors"] = source_errors\n    result["bank_validation_issues"] = bank_issues\n    result["compiled_count"] = compiled_count\n'''
    new = '''    reviews = _load_review_receipts(args.phase1_reviews, args.phase2_reviews)\n    phase2_records = _load_phase2_records(args.phase2_batches)\n    phase2_ids = [normalize_text(row.get("id")) for row in phase2_records]\n    inventory = _load_json(args.source_inventory, {})\n    if not isinstance(inventory, Mapping):\n        inventory = {}\n\n    source_errors = validate_source_inventory(inventory, taxonomy)\n    source_errors.extend(validate_question_source_links(questions, inventory))\n    result = validate_phase2_set(questions, taxonomy, reviews, phase2_ids)\n    review_custody_errors = validate_phase2_review_custody(phase2_records, reviews)\n    semantic_audit = _load_json(SEMANTIC_AUDIT_PATH, {})\n    if not isinstance(semantic_audit, Mapping):\n        semantic_audit = {}\n    semantic_audit_errors = validate_semantic_audit(questions, semantic_audit)\n    build_receipt = _load_json(BUILD_RECEIPT_PATH, {})\n    if not isinstance(build_receipt, Mapping):\n        build_receipt = {}\n    build_receipt_errors = validate_build_receipt(args.store, args.compiled, build_receipt)\n    compiled_count, bank_issues = _bank_validation_issues(args.compiled)\n    result["source_inventory_errors"] = source_errors\n    result["review_custody_errors"] = review_custody_errors\n    result["semantic_audit_errors"] = semantic_audit_errors\n    result["build_receipt_errors"] = build_receipt_errors\n    result["bank_validation_issues"] = bank_issues\n    result["compiled_count"] = compiled_count\n    result["compiled_sha256"] = sha256_file(args.compiled) if args.compiled.exists() else ""\n    result["default_launch_bank_sha256"] = sha256_file(DEFAULT_BANK) if DEFAULT_BANK.exists() else ""\n'''
    if old in text:
        text = text.replace(old, new, 1)
    elif "review_custody_errors = validate_phase2_review_custody" not in text:
        raise RuntimeError("missing main integration anchor")

    old_status = '    if source_errors or bank_issues or result["quality_errors"]:\n'
    new_status = '    if source_errors or review_custody_errors or semantic_audit_errors or build_receipt_errors or bank_issues or result["quality_errors"]:\n'
    if old_status in text:
        text = text.replace(old_status, new_status, 1)
    elif new_status not in text:
        raise RuntimeError("missing terminal status anchor")
    path.write_text(text, encoding="utf-8")


def extend_tests() -> None:
    path = ROOT / "tests/test_sc900_phase2_deep_review.py"
    text = path.read_text(encoding="utf-8")
    if "class Phase2EvidenceChainTests" in text:
        return
    text = text.replace(
        "from tests.test_sc900_phase2 import _complete_phase2_set, _load_phase2_module\n",
        "from tests.test_sc900_phase2 import _approved_question, _complete_phase2_set, _load_phase2_module\n",
        1,
    )
    marker = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    block = '''\n\nclass Phase2EvidenceChainTests(unittest.TestCase):\n    def setUp(self):\n        self.taxonomy = load_taxonomy()\n        self.module = _load_phase2_module(self)\n\n    def test_review_content_hash_detects_substantive_mutation(self):\n        from tools.build_sc900_phase2 import review_content_sha256\n        question = _approved_question(1, "security_compliance_concepts", "security_compliance_identity", "shared_responsibility_model", phase2=True)\n        original = review_content_sha256(question)\n        question["stem"] += " changed"\n        self.assertNotEqual(original, review_content_sha256(question))\n\n    def test_semantic_audit_merges_same_leaf_even_when_prior_family_differs(self):\n        from tools.build_sc900_phase2 import compute_semantic_family_audit\n        left = _approved_question(1, "entra_authentication", "microsoft_entra", "multifactor_authentication", phase2=False)\n        right = _approved_question(2, "entra_authentication", "microsoft_entra", "multifactor_authentication", phase2=True)\n        left["metadata"]["semantic_family_id"] = "old-a"\n        right["metadata"]["semantic_family_id"] = "old-b"\n        audit = compute_semantic_family_audit([left, right])\n        families = {row["semantic_family_id"] for row in audit["decisions"]}\n        self.assertEqual({"multifactor_authentication"}, families)\n\n    def test_source_link_validation_requires_exact_inventory_join(self):\n        question = _approved_question(1, "security_compliance_concepts", "security_compliance_identity", "shared_responsibility_model", phase2=True)\n        errors = self.module.validate_question_source_links([question], {"sources": []})\n        self.assertIn("QUESTION_SOURCE_NOT_IN_INVENTORY", {row["code"] for row in errors})\n'''
    if marker not in text:
        raise RuntimeError("test file terminal marker missing")
    path.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")


def main() -> int:
    bind_review_custody_and_sources()
    patch_validator()
    extend_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
