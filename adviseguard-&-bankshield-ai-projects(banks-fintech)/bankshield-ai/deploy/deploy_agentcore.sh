#!/usr/bin/env bash
# Deploy BankShield graph to Amazon Bedrock AgentCore (stub).
# Requires: AWS creds, POSTGRES_DSN, bedrock-agentcore toolkit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DISABLE_AGENTCORE_MEMORY="${DISABLE_AGENTCORE_MEMORY:-1}"
echo "BankShield AgentCore deploy stub"
echo "Entrypoint: ${ROOT}/agentcore_entrypoint.py"
echo "Set BANKSHIELD_MODEL / POSTGRES_DSN, then run agentcore launch with your account config."
echo "Local smoke: BANKSHIELD_MODEL=fake uv run python -m app.graph"
