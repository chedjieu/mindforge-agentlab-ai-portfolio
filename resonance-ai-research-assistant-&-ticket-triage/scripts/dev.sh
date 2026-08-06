#!/usr/bin/env bash
# Run the research assistant from starter-repo-main/ (Git Bash).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/RAIRA-AI-Research-Assistant" || exit 1
exec uv run python -m app.main "$@"
