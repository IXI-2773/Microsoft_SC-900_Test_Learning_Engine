from copy import deepcopy

import pytest

import progress_store
from progress_store import question_key
from runtime_persistence import RuntimePersistence


def question(qid, number):
    return {"question_id": qid, "question_number": number, "prompt": "p", "choices": {"A": "a"}, "correct": ["A"]}


def legacy_payload(records):
    return {
        "version": 3,
        "questions": deepcopy(records),
        "history": [],
        "created_at": "2026-09-12T00:00:00",
        "updated_at": "2026-09-12T00:00:00",
    }


def test_b1_01_same_number_different_id_does_not_share_key():
    assert question_key(question("sc900-a", 27)) != question_key(question("sc900-b", 27))


def test_b1_02_stable_id_survives_renumbering():
    assert question_key(question("sc900-a", 27)) == question_key(question("sc900-a", 93)) == "sc900-a"


def test_b1_03_missing_canonical_id_does_not_fall_back_to_number():
    with pytest.raises(ValueError, match="MISSING_CANONICAL_QUESTION_ID"):
        question_key({"question_number": 27})


def test_b1_04_migration_api_exists_and_preserves_record_contents():
    assert hasattr(progress_store, "migrate_legacy_progress_keys")
    record = {"attempts": 3, "wrong_count": 1, "custom": {"keep": True}}
    migrated = progress_store.migrate_legacy_progress_keys(legacy_payload({"27": record}), [question("sc900-a", 27)])
    assert migrated["questions"] == {"sc900-a": record}


def test_b1_05_runtime_persistence_exposes_atomic_progress_migration(tmp_path):
    persistence = RuntimePersistence(checkpoint_dir=tmp_path / "checkpoints", backup_dir=tmp_path / "backups")
    assert hasattr(persistence, "load_progress_with_identity_migration")
