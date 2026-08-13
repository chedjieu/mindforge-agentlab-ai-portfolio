#!/usr/bin/env bash
# Shared env for Git Bash. Never query venv Scripts\python.exe (os error 5).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"
unset VIRTUAL_ENV
unset UV_PROJECT_ENVIRONMENT

export RAIP_MODEL="${RAIP_MODEL:-fake}"
export RAIP_HITL="${RAIP_HITL:-required}"
if [[ ! -f .env ]]; then
  cp .env.example .env
fi

RAIP_PYTHON="$(uv python find 3.12)"
SITE="${LOCALAPPDATA:-$HOME/AppData/Local}/raip-venv/Lib/site-packages"
if [[ ! -d "$SITE/fastapi" ]]; then
  mkdir -p "$SITE"
  uv pip install --python "$RAIP_PYTHON" --target "$SITE" -e ".[dev]"
fi

export PYTHONPATH="$SITE${PYTHONPATH:+:$PYTHONPATH}"
export RAIP_PYTHON
