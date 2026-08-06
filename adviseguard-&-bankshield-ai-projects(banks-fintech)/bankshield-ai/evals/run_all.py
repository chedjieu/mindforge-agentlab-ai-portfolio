"""Run all BankShield eval gates; non-zero if any ship gate fails."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("BANKSHIELD_MODEL", "fake")
os.environ.setdefault("BANKSHIELD_EMBEDDINGS", "fake")
os.environ.setdefault("BANKSHIELD_JUDGE_MODEL", "fake")

SCRIPTS = (
    ("groundedness_judge.py", "ship_groundedness"),
    ("citation_coverage.py", "ship_citation_coverage"),
    ("risk_consistency.py", "ship_risk_consistency"),
    ("e2e_eval.py", "ship_e2e"),
)


def main() -> int:
    failed = 0
    for script, gate in SCRIPTS:
        print(f"\n=== {gate} ({script}) ===")
        proc = subprocess.run([sys.executable, str(Path(__file__).parent / script)], cwd=ROOT)
        if proc.returncode != 0:
            failed += 1
    print(f"\nFailed gates: {failed}/{len(SCRIPTS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
