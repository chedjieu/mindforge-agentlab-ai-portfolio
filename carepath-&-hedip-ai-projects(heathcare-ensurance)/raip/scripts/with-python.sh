#!/usr/bin/env bash
# Run a Python module with the uv-managed interpreter (avoids locked .venv).
# Examples:
#   bash scripts/with-python.sh -m app.main
#   bash scripts/with-python.sh -m pytest
set -euo pipefail
# shellcheck source=env.sh
source "$(dirname "$0")/env.sh"
exec "$RAIP_PYTHON" "$@"
