from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASE1_STORE = ROOT / "content" / "sc900" / "phase1" / "store"
PHASE2_ROOT = ROOT / "content" / "sc900" / "phase2"
PHASE2_BATCHES = PHASE2_ROOT / "batches"
PHASE2_REVIEWS = PHASE2_ROOT / "reviews"
PHASE2_STORE = PHASE2_ROOT / "store"
PHASE2_COMPILED = PHASE2_ROOT / "compiled" / "sc900_phase2_reviewed_bank.json"
SEMANTIC_AUDIT_PATH = PHASE2_ROOT / "semantic_family_audit.json"
BUILD_RECEIPT_PATH = PHASE2_ROOT / "phase2_build_receipt.json"
DEFAULT_BANK = ROOT / "sc900_bank_v8_baseline.json"

WORK_ID = "SC900-BANK-PHASE2-001"
DETERMINISTIC_IMPORT_AT = "2026-09-11T12:00:00+00:00"
SEMANTIC_AUDIT_REVIEWER = "openai-gpt5.6-sol-deep-review-correction"
SEMANTIC_AUDIT_REVIEWED_AT = "2026-09-11T13:10:00Z"
EXPLICIT_TRANSFER_EDGES = {
    frozenset({"sc900_p1_q037", "sc900_p2_q033"}): "SOAR automation/playbook exposure materially transfers across the SIEM/SOAR and Sentinel mitigation leaves."
}
STORE_FILES = (
    "questions.json",
    "source_material.json",
    "quarantine.json",
    "review.json",
    "review_decisions.json",
)

from ingestion.importer import apply_review_decision, compile_question_bank, import_jsonl, promotion_counts
from ingestion.models import load_taxonomy, normalize_text


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_answer_ids(record: Mapping[str, Any]) -> list[str]:
    value = record.get("correct_answer")
    raw = value if isinstance(value, list) else [value]
    return [normalize_text(item) for item in raw if normalize_text(item)]


def _as_choices(record: Mapping[str, Any]) -> list[dict[str, str]]:
    value = record.get("choices")
    if isinstance(value, Mapping):
        return [{"id": normalize_text(key), "text": normalize_text(text)} for key, text in value.items()]
    if not isinstance(value, list):
        return []
    return [
        {"id": normalize_text(item.get("id")), "text": normalize_text(item.get("text"))}
        for item in value
        if isinstance(item, Mapping)
    ]


def review_content_material(record: Mapping[str, Any]) -> dict[str, Any]:
    """Content custody material. Semantic-family identity is audited separately."""
    raw_metadata = record.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    metadata.pop("semantic_family_id", None)
    provenance = record.get("provenance") if isinstance(record.get("provenance"), Mapping) else {}
    source = record.get("source") if isinstance(record.get("source"), Mapping) else provenance.get("source", {})
    return {
        "id": normalize_text(record.get("id")),
        "exam": normalize_text(record.get("exam")),
        "domain": normalize_text(record.get("domain")),
        "objective": normalize_text(record.get("objective")),
        "subobjective": normalize_text(record.get("subobjective")),
        "difficulty": normalize_text(record.get("difficulty")),
        "type": normalize_text(record.get("type")),
        "stem": normalize_text(record.get("stem")),
        "choices": _as_choices(record),
        "correct_answer": _as_answer_ids(record),
        "explanation": normalize_text(record.get("explanation")),
        "references": [normalize_text(value) for value in record.get("references", []) if normalize_text(value)],
        "tags": [normalize_text(value) for value in record.get("tags", []) if normalize_text(value)],
        "source": source,
        "metadata": metadata,
    }


def review_content_sha256(record: Mapping[str, Any]) -> str:
    return _sha256_bytes(_json_bytes(review_content_material(record)))


def load_phase2_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(PHASE2_BATCHES.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"non-object row in {path}")
                rows.append(payload)
    return rows


def load_phase2_reviews() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(PHASE2_REVIEWS.glob("*.json")):
        payload = _read_json(path, {})
        rows = payload.get("reviews", []) if isinstance(payload, Mapping) else []
        for row in rows:
            if isinstance(row, dict) and normalize_text(row.get("question_id")):
                qid = normalize_text(row["question_id"])
                if qid in result:
                    raise ValueError(f"duplicate Phase-2 review receipt for {qid}")
                result[qid] = row
    return result


def review_custody_errors(records: Sequence[Mapping[str, Any]], reviews: Mapping[str, Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for record in records:
        qid = normalize_text(record.get("id"))
        receipt = reviews.get(qid)
        if receipt is None:
            errors.append(f"{qid}: missing Phase-2 review receipt")
            continue
        expected = review_content_sha256(record)
        actual = normalize_text(receipt.get("reviewed_content_sha256")).lower()
        if actual != expected:
            errors.append(f"{qid}: review custody hash mismatch expected={expected} actual={actual or '<missing>'}")
    extra = sorted(set(reviews) - {normalize_text(row.get("id")) for row in records})
    if extra:
        errors.append(f"review receipts without authored rows: {', '.join(extra)}")
    return errors


def _correct_answer_text(record: Mapping[str, Any]) -> str:
    ids = set(_as_answer_ids(record))
    texts = [choice["text"] for choice in _as_choices(record) if choice["id"] in ids]
    return " | ".join(texts)


def _answer_key(record: Mapping[str, Any]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _correct_answer_text(record).casefold()).strip()


class _UnionFind:
    def __init__(self, values: Sequence[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            if left_root < right_root:
                self.parent[right_root] = left_root
            else:
                self.parent[left_root] = right_root


def compute_semantic_family_audit(questions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    qids = [normalize_text(row.get("id")) for row in questions]
    if len(qids) != len(set(qids)) or any(not qid for qid in qids):
        raise ValueError("semantic audit requires unique non-empty question IDs")
    by_id = {normalize_text(row["id"]): row for row in questions}
    uf = _UnionFind(qids)
    reasons: dict[frozenset[str], str] = {}

    by_leaf: dict[str, list[str]] = defaultdict(list)
    by_answer: dict[str, list[str]] = defaultdict(list)
    for row in questions:
        qid = normalize_text(row["id"])
        metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
        leaf = normalize_text(metadata.get("blueprint_leaf_id"))
        answer = _answer_key(row)
        if leaf:
            by_leaf[leaf].append(qid)
        if answer:
            by_answer[answer].append(qid)

    for leaf, members in sorted(by_leaf.items()):
        for qid in members[1:]:
            uf.union(members[0], qid)
            reasons[frozenset({members[0], qid})] = f"same blueprint leaf: {leaf}"
    for answer, members in sorted(by_answer.items()):
        if len(members) < 2:
            continue
        for qid in members[1:]:
            uf.union(members[0], qid)
            reasons[frozenset({members[0], qid})] = f"shared correct-answer cue: {answer}"
    for edge, rationale in EXPLICIT_TRANSFER_EDGES.items():
        members = sorted(edge)
        if all(member in by_id for member in members):
            uf.union(members[0], members[1])
            reasons[edge] = rationale

    components: dict[str, list[str]] = defaultdict(list)
    for qid in qids:
        components[uf.find(qid)].append(qid)

    decisions: list[dict[str, Any]] = []
    for members in sorted((sorted(values) for values in components.values()), key=lambda values: values[0]):
        rows = [by_id[qid] for qid in members]
        leaves = sorted(
            {
                normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id"))
                for row in rows
                if isinstance(row.get("metadata"), Mapping)
                and normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id"))
            }
        )
        prior_families = sorted(
            {
                normalize_text((row.get("metadata") or {}).get("semantic_family_id"))
                for row in rows
                if isinstance(row.get("metadata"), Mapping)
                and normalize_text((row.get("metadata") or {}).get("semantic_family_id"))
            }
        )
        if len(leaves) == 1:
            canonical = leaves[0]
            basis = ["same_blueprint_leaf_floor"]
        elif {"sc900_p1_q037", "sc900_p2_q033"}.issubset(set(members)):
            canonical = "sentinel_siem_soar_automation"
            basis = ["explicit_cross_leaf_transfer_review", "shared_answer_or_leaf_edges"]
        else:
            canonical = prior_families[0] if prior_families else (leaves[0] if leaves else "semantic_family_unresolved")
            basis = ["shared_answer_cross_leaf_transfer"]
        for row in rows:
            qid = normalize_text(row["id"])
            prior = normalize_text((row.get("metadata") or {}).get("semantic_family_id"))
            decisions.append(
                {
                    "question_id": qid,
                    "blueprint_leaf_id": normalize_text((row.get("metadata") or {}).get("blueprint_leaf_id")),
                    "correct_answer_text": _correct_answer_text(row),
                    "prior_semantic_family_id": prior,
                    "semantic_family_id": canonical,
                    "override_type": "none" if prior == canonical else "family_merge",
                    "basis": basis,
                    "component_members": members,
                    "rationale": "Conservative Phase-2 transfer audit: same-leaf, shared-answer, and explicit cross-leaf transfer edges are not allowed to masquerade as independent held-out families.",
                }
            )

    decisions.sort(key=lambda row: row["question_id"])
    return {
        "work_id": WORK_ID,
        "audit_version": "sc900-semantic-family-audit/v1",
        "reviewer": SEMANTIC_AUDIT_REVIEWER,
        "reviewed_at": SEMANTIC_AUDIT_REVIEWED_AT,
        "rule": {
            "same_blueprint_leaf": "merge",
            "same_normalized_correct_answer": "merge",
            "explicit_cross_leaf_transfer_edges": [sorted(edge) for edge in EXPLICIT_TRANSFER_EDGES],
            "unknown_or_disputed": "fail_closed",
        },
        "question_count": len(decisions),
        "family_count": len({row["semantic_family_id"] for row in decisions}),
        "override_count": sum(row["override_type"] != "none" for row in decisions),
        "decisions": decisions,
    }


def apply_semantic_audit(questions: list[dict[str, Any]], audit: Mapping[str, Any]) -> None:
    decisions = {
        normalize_text(row.get("question_id")): row
        for row in audit.get("decisions", [])
        if isinstance(row, Mapping)
    }
    if set(decisions) != {normalize_text(row.get("id")) for row in questions}:
        raise ValueError("semantic audit does not cover exactly the cumulative question set")
    for record in questions:
        qid = normalize_text(record["id"])
        metadata = dict(record.get("metadata") or {})
        metadata["semantic_family_id"] = normalize_text(decisions[qid].get("semantic_family_id"))
        record["metadata"] = metadata


def _normalize_generated_custody(store_dir: Path, phase2_ids: set[str], reviews: Mapping[str, Mapping[str, Any]]) -> None:
    questions = _read_json(store_dir / "questions.json", [])
    for row in questions:
        if normalize_text(row.get("id")) in phase2_ids:
            provenance = dict(row.get("provenance") or {})
            provenance["imported_at"] = DETERMINISTIC_IMPORT_AT
            row["provenance"] = provenance
    _write_json(store_dir / "questions.json", questions)

    decisions = _read_json(store_dir / "review_decisions.json", [])
    for row in decisions:
        qid = normalize_text(row.get("id"))
        if qid not in phase2_ids:
            continue
        decision = normalize_text(row.get("decision")).lower()
        if decision == "pending":
            row["actor"] = "import"
            row["decided_at"] = DETERMINISTIC_IMPORT_AT
        elif decision == "approved":
            receipt = reviews[qid]
            row["actor"] = normalize_text(receipt.get("reviewer")) or "phase2-reviewer"
            row["decided_at"] = normalize_text(receipt.get("reviewed_at")) or DETERMINISTIC_IMPORT_AT
    _write_json(store_dir / "review_decisions.json", decisions)


def _copy_phase1_store(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in STORE_FILES:
        source = PHASE1_STORE / name
        if source.exists():
            shutil.copy2(source, destination / name)
        else:
            _write_json(destination / name, [])


def _hash_map(paths: Sequence[Path]) -> dict[str, str]:
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def build_phase2(work_dir: Path) -> dict[str, Any]:
    taxonomy = load_taxonomy()
    phase2_records = load_phase2_records()
    phase2_ids = [normalize_text(row.get("id")) for row in phase2_records]
    if len(phase2_ids) != 50 or len(set(phase2_ids)) != 50:
        raise ValueError("Phase 2 requires exactly 50 unique authored IDs")

    phase1_questions = _read_json(PHASE1_STORE / "questions.json", [])
    phase1_ids = {normalize_text(row.get("id")) for row in phase1_questions}
    if set(phase2_ids) & phase1_ids:
        raise ValueError("Phase-2 IDs must be disjoint from Phase-1 IDs")

    reviews = load_phase2_reviews()
    custody_errors = review_custody_errors(phase2_records, reviews)
    if custody_errors:
        raise ValueError("; ".join(custody_errors))

    store_dir = work_dir / "store"
    compiled_path = work_dir / "compiled.json"
    audit_path = work_dir / "semantic_family_audit.json"
    _copy_phase1_store(store_dir)

    import_reports: list[dict[str, Any]] = []
    for batch in sorted(PHASE2_BATCHES.glob("*.jsonl")):
        report = import_jsonl(batch, store_dir, taxonomy)
        import_reports.append(report)
        if report["accepted"] != 10 or report["rejected"] or report["skipped"] or report["review"]:
            raise ValueError(f"Phase-2 import failed closed for {batch.name}: {report}")

    preapproval_questions = _read_json(store_dir / "questions.json", [])
    counts_before = promotion_counts(preapproval_questions)
    new_before = [row for row in preapproval_questions if normalize_text(row.get("id")) in set(phase2_ids)]
    if counts_before != {"approved": 50, "pending": 50, "withheld": 0}:
        raise ValueError(f"import-before-approval invariant failed: {counts_before}")
    if any(normalize_text(row.get("promotion_status")).lower() != "pending" for row in new_before):
        raise ValueError("every Phase-2 imported item must be pending before review promotion")

    pending_ledger = _read_json(store_dir / "review_decisions.json", [])
    pending_ids = {
        normalize_text(row.get("id"))
        for row in pending_ledger
        if normalize_text(row.get("decision")).lower() == "pending"
    }
    if not set(phase2_ids).issubset(pending_ids):
        raise ValueError("import-pending ledger is missing one or more Phase-2 IDs")

    for qid in phase2_ids:
        receipt = reviews[qid]
        if normalize_text(receipt.get("disposition")).lower() != "approved":
            raise ValueError(f"{qid}: Phase-2 build only promotes explicit approved receipts")
        apply_review_decision(store_dir, qid, "approved", actor=normalize_text(receipt.get("reviewer")))

    _normalize_generated_custody(store_dir, set(phase2_ids), reviews)
    questions = _read_json(store_dir / "questions.json", [])
    counts_after = promotion_counts(questions)
    if counts_after != {"approved": 100, "pending": 0, "withheld": 0}:
        raise ValueError(f"post-review promotion counts invalid: {counts_after}")

    audit = compute_semantic_family_audit(questions)
    apply_semantic_audit(questions, audit)
    _write_json(store_dir / "questions.json", questions)
    _write_json(audit_path, audit)

    compile_result = compile_question_bank(store_dir, compiled_path)
    if compile_result["compiled"] != 100:
        raise ValueError(f"compiled count invalid: {compile_result}")

    batch_paths = sorted(PHASE2_BATCHES.glob("*.jsonl"))
    review_paths = sorted(PHASE2_REVIEWS.glob("*.json"))
    receipt = {
        "work_id": WORK_ID,
        "status": "REPRODUCIBLE",
        "phase1_approved_base_count": 50,
        "phase2_authored_count": 50,
        "pending_before_approval_count": counts_before["pending"],
        "approved_after_review_count": counts_after["approved"],
        "withheld_after_review_count": counts_after["withheld"],
        "phase2_ids": phase2_ids,
        "semantic_family_count": audit["family_count"],
        "semantic_family_override_count": audit["override_count"],
        "inputs": {
            "phase1_questions_sha256": sha256_file(PHASE1_STORE / "questions.json"),
            "batches": _hash_map(batch_paths),
            "reviews": _hash_map(review_paths),
        },
        "outputs": {
            "store": {name: sha256_file(store_dir / name) for name in STORE_FILES},
            "compiled_sha256": sha256_file(compiled_path),
            "semantic_family_audit_sha256": sha256_file(audit_path),
            "default_launch_bank_sha256": sha256_file(DEFAULT_BANK),
        },
        "import_reports": import_reports,
        "custody": {
            "review_hash_algorithm": "sha256(canonical reviewed question content excluding semantic_family_id)",
            "reviewed_phase2_items": len(reviews),
            "import_pending_ledger_complete": True,
            "semantic_family_audit_reviewed_by": SEMANTIC_AUDIT_REVIEWER,
            "semantic_family_audit_reviewed_at": SEMANTIC_AUDIT_REVIEWED_AT,
        },
    }
    return {"store_dir": store_dir, "compiled_path": compiled_path, "audit_path": audit_path, "receipt": receipt}


def _write_committed(build: Mapping[str, Any]) -> None:
    PHASE2_STORE.mkdir(parents=True, exist_ok=True)
    for name in STORE_FILES:
        shutil.copy2(Path(build["store_dir"]) / name, PHASE2_STORE / name)
    PHASE2_COMPILED.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(build["compiled_path"]), PHASE2_COMPILED)
    shutil.copy2(Path(build["audit_path"]), SEMANTIC_AUDIT_PATH)
    _write_json(BUILD_RECEIPT_PATH, build["receipt"])


def _verify_committed(build: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in STORE_FILES:
        expected = Path(build["store_dir"]) / name
        actual = PHASE2_STORE / name
        if not actual.exists() or actual.read_bytes() != expected.read_bytes():
            errors.append(f"store artifact drift: {name}")
    if not PHASE2_COMPILED.exists() or PHASE2_COMPILED.read_bytes() != Path(build["compiled_path"]).read_bytes():
        errors.append("compiled bank drift")
    if not SEMANTIC_AUDIT_PATH.exists() or SEMANTIC_AUDIT_PATH.read_bytes() != Path(build["audit_path"]).read_bytes():
        errors.append("semantic-family audit drift")
    committed_receipt = _read_json(BUILD_RECEIPT_PATH, {})
    if committed_receipt != build["receipt"]:
        errors.append("build receipt drift")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild and verify the SC-900 reviewed-bank Phase-2 evidence chain.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write deterministic cumulative artifacts to content/sc900/phase2.")
    mode.add_argument("--verify-committed", action="store_true", help="Rebuild independently and compare with committed artifacts.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="sc900-phase2-build-") as temp_dir:
        build = build_phase2(Path(temp_dir))
        if args.write:
            _write_committed(build)
            print(json.dumps(build["receipt"], indent=2, sort_keys=True))
            return 0
        errors = _verify_committed(build)
        if errors:
            print(json.dumps({"status": "DRIFT", "errors": errors}, indent=2, sort_keys=True))
            return 1
        print(json.dumps({"status": "REPRODUCIBLE", "receipt": build["receipt"]}, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
