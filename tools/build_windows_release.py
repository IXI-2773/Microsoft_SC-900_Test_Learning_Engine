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
    # Invoke PyInstaller in-process. The governed closure is explicit per file, and
    # that many --add-data arguments exceed the Windows process command-line limit.
    from PyInstaller.__main__ import run as pyinstaller_run

    pyinstaller_run(
        [
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            "SC900TestLearningEngine",
            "--distpath",
            str(ROOT / "dist"),
            "--workpath",
            str(ROOT / "build"),
            "--specpath",
            str(ROOT / "build"),
            *pyinstaller_resource_args(os.pathsep),
            str(ROOT / "app.py"),
        ]
    )
    run([sys.executable, "tools/verify_packaged_resources.py"])
    run([sys.executable, "tools/build_release.py"])
    run([sys.executable, "tools/smoke_test.py"])


if __name__ == "__main__":
    main()
