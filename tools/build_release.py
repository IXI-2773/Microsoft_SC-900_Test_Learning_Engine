from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_info import APP_NAME, APP_VERSION  # noqa: E402
from cert_config import QUESTION_BANK_FILENAME, RUNTIME_BANK_QUESTION_COUNT  # noqa: E402
from pe_validation import pe_file_metadata, validate_pe_file  # noqa: E402

DIST_EXE = ROOT / "dist" / "SC900TestLearningEngine.exe"
RELEASE_DIR = ROOT / "release" / "SC900TestLearningEngine"
RELEASE_EXE = RELEASE_DIR / "SC900TestLearningEngine.exe"
RELEASE_README = RELEASE_DIR / "README - Start Here.txt"
RELEASE_MANIFEST = RELEASE_DIR / "release_manifest.json"
BANK_FILE = ROOT / QUESTION_BANK_FILENAME
EXPECTED_QUESTION_COUNT = RUNTIME_BANK_QUESTION_COUNT


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release(_bank_path=None) -> Path:
    if not DIST_EXE.exists():
        raise FileNotFoundError(f"Missing built executable: {DIST_EXE}")
    if not BANK_FILE.exists():
        raise FileNotFoundError(f"Missing SC-900 bank: {BANK_FILE}")
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DIST_EXE, RELEASE_EXE)
    failure = validate_pe_file(RELEASE_EXE)
    if failure is not None:
        raise ValueError(f"Release EXE failed PE validation: {failure}")
    RELEASE_README.write_text(
        f"{APP_NAME} v{APP_VERSION}\n\nDouble-click SC900TestLearningEngine.exe to study.\n",
        encoding="utf-8",
    )
    pe = pe_file_metadata(RELEASE_EXE)
    manifest = {
        "application_name": APP_NAME,
        "application_version": APP_VERSION,
        "build_timestamp_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "executable_filename": RELEASE_EXE.name,
        "executable_sha256": _sha256(RELEASE_EXE),
        "executable_size": RELEASE_EXE.stat().st_size,
        "question_bank_filename": BANK_FILE.name,
        "question_bank_sha256": _sha256(BANK_FILE),
        "expected_bank_count": EXPECTED_QUESTION_COUNT,
        "pe_format": pe["format"],
        "pe_machine_type": pe["machine_type"],
    }
    RELEASE_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return RELEASE_DIR


if __name__ == "__main__":
    print(f"Release folder ready: {build_release()}")
