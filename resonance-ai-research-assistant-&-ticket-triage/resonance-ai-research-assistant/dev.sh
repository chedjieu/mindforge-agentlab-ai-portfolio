#!/usr/bin/env bash
# Start the research assistant (Git Bash).
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
exec uv run python -m app.main "$@"
