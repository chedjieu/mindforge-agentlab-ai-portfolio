"""Run all Project 1 evals."""

from __future__ import annotations

import subprocess
import sys


def _run(module: str) -> int:
    print(f"\n{'=' * 60}\n  {module}\n{'=' * 60}\n")
    return subprocess.call([sys.executable, "-m", module])


def main() -> int:
    modules = [
        "evals.planner_eval",
        "evals.citation_eval",
        "evals.e2e_eval",
    ]
    codes = [_run(m) for m in modules]
    failed = sum(1 for c in codes if c != 0)
    print(f"\n{'=' * 60}")
    if failed:
        print(f"  {failed}/{len(modules)} eval suite(s) failed")
        return 1
    print("  All eval suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
