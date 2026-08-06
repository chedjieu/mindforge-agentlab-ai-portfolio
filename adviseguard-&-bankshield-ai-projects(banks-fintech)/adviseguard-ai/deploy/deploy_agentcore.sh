#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DISABLE_AGENTCORE_MEMORY="${DISABLE_AGENTCORE_MEMORY:-1}"
echo "AdviseGuard AgentCore deploy stub"
echo "Entrypoint: ${ROOT}/agentcore_entrypoint.py"
echo "Local smoke: ADVISEGUARD_MODEL=fake python -m app.graph"
