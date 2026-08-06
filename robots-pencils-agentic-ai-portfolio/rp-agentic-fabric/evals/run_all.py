"""Run all evals (LangSmith-ready local suite)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SCRIPTS = [
    "router_eval.py",
    "compliance_judge.py",
    "leakage_judge.py",
    "e2e_eval.py",
]


def main() -> int:
    failed = 0
    for name in SCRIPTS:
        print(f"\n=== {name} ===")
        proc = subprocess.run([sys.executable, str(ROOT / name)], cwd=str(ROOT.parent))
        if proc.returncode != 0:
            failed += 1
    print(f"\n{len(SCRIPTS) - failed}/{len(SCRIPTS)} eval suites passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
