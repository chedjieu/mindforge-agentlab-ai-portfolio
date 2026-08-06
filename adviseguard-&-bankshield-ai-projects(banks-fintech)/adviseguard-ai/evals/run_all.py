"""Run all AdviseGuard eval gates."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("ADVISEGUARD_MODEL", "fake")
os.environ.setdefault("ADVISEGUARD_EMBEDDINGS", "fake")

SCRIPTS = (
    "groundedness_judge.py",
    "advice_suitability.py",
    "fraud_gold.py",
    "e2e_eval.py",
)


def main() -> int:
    failed = 0
    for script in SCRIPTS:
        print(f"\n=== {script} ===")
        proc = subprocess.run([sys.executable, str(Path(__file__).parent / script)], cwd=ROOT)
        failed += int(proc.returncode != 0)
    print(f"\nFailed gates: {failed}/{len(SCRIPTS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
