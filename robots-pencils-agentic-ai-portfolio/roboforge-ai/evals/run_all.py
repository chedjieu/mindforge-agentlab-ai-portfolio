"""Run RoboForge evals."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    failed = 0
    for name in ("e2e_eval.py",):
        print(f"=== {name} ===")
        rc = subprocess.run([sys.executable, str(ROOT / name)], cwd=str(ROOT.parent)).returncode
        failed += int(rc != 0)
    print(f"{1 - failed}/1 eval suites passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
