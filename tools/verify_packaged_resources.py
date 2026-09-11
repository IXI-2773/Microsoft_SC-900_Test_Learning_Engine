from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from release_resources import REQUIRED_RUNTIME_RESOURCES  # noqa: E402


def canonical_archive_member(name: str) -> str:
    return name.replace("\\", "/")


def archive_listing_members(listing: str) -> set[str]:
    _prefix, marker, member_listing = listing.partition("Contents of ")
    if not marker:
        return set()
    _header, _separator, paths = member_listing.partition(":\n")
    return {
        canonical_archive_member(line.strip())
        for line in paths.splitlines()
        if line.startswith(" ")
    }


def missing_runtime_resources(members: set[str]) -> list[str]:
    canonical_members = {canonical_archive_member(member) for member in members}
    return [
        resource.as_posix()
        for resource in REQUIRED_RUNTIME_RESOURCES
        if resource.as_posix() not in canonical_members
    ]


def verify_packaged_resources(executable: Path) -> list[str]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller.utils.cliutils.archive_viewer",
            str(executable),
            "--list",
            "--brief",
        ],
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
    try:
        missing = verify_packaged_resources(executable)
    except RuntimeError as error:
        print(f"Packaged resource verification failed: {error}", file=sys.stderr)
        return 1
    if missing:
        print(f"Packaged resource verification failed: missing {', '.join(missing)}", file=sys.stderr)
        return 1
    print("Packaged resource verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
