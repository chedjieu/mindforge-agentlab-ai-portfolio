#!/usr/bin/env bash
# Install deps without querying a Windows-locked venv python.exe.
# Do not run: uv sync / uv run / source .venv/Scripts/activate
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"
unset VIRTUAL_ENV
unset UV_PROJECT_ENVIRONMENT

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

RAIP_PYTHON="$(uv python find 3.12)"
SITE="${LOCALAPPDATA:-$HOME/AppData/Local}/raip-venv/Lib/site-packages"
mkdir -p "$SITE"

# Install into site-packages using the uv-managed interpreter (not venv Scripts\python.exe).
uv pip install --python "$RAIP_PYTHON" --target "$SITE" -e ".[dev]"

export RAIP_PYTHON
export PYTHONPATH="$SITE${PYTHONPATH:+:$PYTHONPATH}"
echo "OK: packages in $SITE"
echo "Run: bash scripts/run.sh"
