#!/usr/bin/env bash
# Deploy BankShield graph to Vertex AI Agent Engine (stub).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "BankShield Vertex Agent Engine deploy stub"
echo "Requires: GCP_PROJECT, GCP_BUCKET, gcloud ADC"
echo "Wrap build_graph() via agent_engines.LanggraphAgent as bankshield-ai"
echo "Local smoke: BANKSHIELD_MODEL=fake uv run python -m app.graph"
