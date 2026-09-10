from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from release_resources import pyinstaller_resource_args

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> None:
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> None:
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "SC900TestLearningEngine",
            *pyinstaller_resource_args(os.pathsep),
            "app.py",
        ]
    )
    run([sys.executable, "tools/build_release.py"])
    run([sys.executable, "tools/smoke_test.py"])


if __name__ == "__main__":
    main()
