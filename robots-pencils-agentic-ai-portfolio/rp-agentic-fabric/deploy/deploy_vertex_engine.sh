#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export RPADF_MODEL="${RPADF_MODEL:-fake}"
python deploy/vertex_engine_deploy.py
echo "Vertex Agent Engine scaffold OK"
