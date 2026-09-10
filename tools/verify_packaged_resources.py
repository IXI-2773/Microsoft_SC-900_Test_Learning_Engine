from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from release_resources import REQUIRED_RUNTIME_RESOURCES  # noqa: E402

ARCHIVE_MEMBER_PATTERN = re.compile(
    r"^\s*\d+,\s*\d+,\s*\d+,\s*[01],\s*'[^']+',\s*'([^']+)'\s*$",
    re.MULTILINE,
)


def archive_listing_members(listing: str) -> set[str]:
    return set(ARCHIVE_MEMBER_PATTERN.findall(listing))


def missing_runtime_resources(members: set[str]) -> list[str]:
    return [resource.as_posix() for resource in REQUIRED_RUNTIME_RESOURCES if resource.as_posix() not in members]


def verify_packaged_resources(executable: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer", str(executable), "-l"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return missing_runtime_resources(archive_listing_members(result.stdout))


def main() -> int:
    executable = ROOT / "dist" / "SC900TestLearningEngine.exe"
    missing = verify_packaged_resources(executable)
    if missing:
        print(f"Packaged resource verification failed: missing {', '.join(missing)}", file=sys.stderr)
        return 1
    print("Packaged resource verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
