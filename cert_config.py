
from __future__ import annotations

import json
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().with_name("cert_profile_sc900.json")
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

VENDOR = str(PROFILE["vendor"])
EXAM_CODE = str(PROFILE["exam_code"])
EXAM_NAME = str(PROFILE["exam_name"])
APP_NAME = "Microsoft SC-900 Test Learning Engine"
APP_VERSION = str(PROFILE["engine_version"])
QUESTION_BANK_FILENAME = str(PROFILE["runtime_bank"])
USER_DATA_DIRNAME = "SC900TestLearningEngine"
OFFICIAL_SCALED_PASS_SCORE = int(PROFILE["official_scaled_pass_score"])
INTERNAL_READINESS_THRESHOLD_PCT = float(PROFILE["internal_readiness_threshold_pct"])
INTERNAL_READINESS_MIN_ATTEMPTS = int(PROFILE["internal_readiness_min_attempts"])
