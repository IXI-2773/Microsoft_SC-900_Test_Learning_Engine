from __future__ import annotations

from pathlib import Path

from cert_config import QUESTION_BANK_FILENAME

ROOT = Path(__file__).resolve().parent
REQUIRED_RUNTIME_RESOURCES = (
    Path("cert_profile_sc900.json"),
    Path(QUESTION_BANK_FILENAME),
    Path("sc900_bank_v8_baseline.json"),
    Path("config/certifications/sc900-2026.json"),
)


def pyinstaller_resource_args(separator: str) -> list[str]:
    args: list[str] = []
    for resource in REQUIRED_RUNTIME_RESOURCES:
        source = ROOT / resource
        if not source.is_file():
            raise FileNotFoundError(f"Required runtime resource is missing: {source}")
        destination = resource.parent.as_posix() if resource.parent != Path(".") else "."
        args.extend(["--add-data", f"{source}{separator}{destination}"])
    return args
