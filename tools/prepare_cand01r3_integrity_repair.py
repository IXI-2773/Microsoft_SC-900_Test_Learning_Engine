from pathlib import Path

path = Path("tools/apply_cand01r3_measurement_integrity_repair.py")
text = path.read_text(encoding="utf-8")
old = "    '''    events: list[dict[str, Any]] = []\\n    day_state: str = STATE_DAY_NOT_STARTED\\n''',"
new = "    '''    day_state: str = STATE_DAY_NOT_STARTED\\n''',"
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("repair-helper dataclass old anchor not found")
old = "    '''    events: list[dict[str, Any]] = []\\n    day_state: str = STATE_DAY_NOT_STARTED\\n    day1_local_date: str = \"\"\\n"
new = "    '''    day_state: str = STATE_DAY_NOT_STARTED\\n    day1_local_date: str = \"\"\\n"
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("repair-helper dataclass new anchor not found")
path.write_text(text, encoding="utf-8")
