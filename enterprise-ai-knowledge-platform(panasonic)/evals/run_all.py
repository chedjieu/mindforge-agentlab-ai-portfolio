"""Run all EGKP judge + e2e gates; non-zero if any ship/deploy gate fails."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ship / deploy gates first; report-only last (still fails process if crash).
SCRIPTS = (
    ("retrieval_judge.py", "ship_retrieval"),
    ("groundedness_judge.py", "ship_groundedness"),
    ("pairwise_regression.py", "gate_deploy"),
    ("e2e_eval.py", "ship_e2e"),
    ("answer_quality_judge.py", "report_only"),
)


def main() -> None:
    os.environ.setdefault("EGKP_MODEL", "fake")
    os.environ.setdefault("EGKP_EMBEDDINGS", "fake")
    os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")

    root = Path(__file__).resolve().parent
    # Ensure goldens exist
    gen = root / "generate_goldens.py"
    if gen.exists():
        subprocess.run([sys.executable, str(gen)], cwd=str(root.parent), check=False)

    failed = 0
    for name, kind in SCRIPTS:
        print(f"\n{'=' * 60}\nRunning {name} [{kind}]\n{'=' * 60}")
        env = os.environ.copy()
        # Keep e2e bounded in CI unless overridden
        if name == "e2e_eval.py" and "EGKP_E2E_LIMIT" not in env:
            env["EGKP_E2E_LIMIT"] = env.get("EGKP_E2E_LIMIT", "8")
        proc = subprocess.run(
            [sys.executable, str(root / name)],
            cwd=str(root.parent),
            env=env,
        )
        if proc.returncode != 0:
            failed += 1
            print(f"{name} exited {proc.returncode}")
    if failed:
        print(f"\n{failed} gate(s) failed.")
        sys.exit(1)
    print("\nAll evals finished.")


if __name__ == "__main__":
    main()
