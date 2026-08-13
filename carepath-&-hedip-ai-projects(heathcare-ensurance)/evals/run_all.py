"""Forward `python -m evals.run_all` from the suite root into sister packages."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from suite_runner import run_all

if __name__ == "__main__":
    raise SystemExit(run_all(["python", "-m", "evals.run_all"]))
