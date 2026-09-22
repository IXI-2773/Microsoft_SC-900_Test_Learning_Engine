from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY_TARGETS = [
    "analytics_models.py",
    "analytics_summary.py",
    "bank_models.py",
    "progress_models.py",
    "progress_store.py",
    "question_bank.py",
    "runtime_persistence.py",
    "content_revision_authority.py",
    "content_revision_correction_authority.py",
    "content_revision_correction_migration.py",
    "content_revision_explanation_authority.py",
    "content_revision_explanation_migration.py",
    "content_revision_migration.py",
    "content_revision_registry.py",
    "answer_length_audit.py",
    "save_queue.py",
    "render_cache.py",
    "session_models.py",
    "session_store.py",
    "builder_identity.py",
    "exam_runtime_eligibility.py",
    "smart_practice_profile.py",
    "smart_practice_cache.py",
    "cand01r3_partition.py",
    "cand01r3_runtime.py",
    "cand01r3_rrc1.py",
    "cand01r3_measurement.py",
    "cand01r3_paths.py",
    "cand01r3_protocol.py",
    "source_trust.py",
    "cert_config.py",
    "extraction/pages.py",
    "extraction/parse.py",
    "extraction/contract.py",
    "extraction/pipeline.py",
    "ingestion/adapter.py",
    "tools/extract_sc900_pdf.py",
    "tools/import_sc900_pdf.py",
    "tools/audit_answer_length.py",
    "tools/build_package_b_tranche1.py",
    "tools/build_package_b_tranche2.py",
    "tools/build_package_b_tranche3.py",
    "tools/build_package_b_tranche4.py",
    "tools/build_package_b_tranche5.py",
    "tools/build_sc900_content_correction_001.py",
    "tools/build_sc900_explanation_tranche_1.py",
    "tools/build_sc900_explanation_q118_repair.py",
    "app_question_render_mixin.py",
    "app.py",
    "tests/test_content_revision_explanation_authority.py",
    "tests/test_content_revision_explanation_migration.py",
    "tests/test_sc900_explanation_tranche_1.py",
    "tests/test_sc900_explanation_q118_repair.py",
    "tests/test_governed_production_content_activation.py",
    "tests/test_explanation_rendering.py",
]


def run_step(label: str, args: list[str]) -> None:
    print(f"[{label}] {' '.join(args)}")
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    python = sys.executable
    run_step("ruff", [python, "-m", "ruff", "check", *QUALITY_TARGETS])
    run_step("black", [python, "-m", "black", "--check", *QUALITY_TARGETS])
    run_step("mypy", [python, "-m", "mypy"])
    print("Quality checks passed.")


if __name__ == "__main__":
    main()
