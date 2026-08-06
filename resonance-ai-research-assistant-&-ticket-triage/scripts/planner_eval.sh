#!/usr/bin/env bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/RAIRA-AI-Research-Assistant" || exit 1
exec uv run python -m evals.planner_eval "$@"
