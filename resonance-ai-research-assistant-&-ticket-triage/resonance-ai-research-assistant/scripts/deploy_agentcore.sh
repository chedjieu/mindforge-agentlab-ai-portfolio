#!/usr/bin/env bash
# Resonance Technologies - deploy Project 2 (Ticket Triage) to AWS Bedrock AgentCore.
# Delegates to RTTA-AI-Multi-Agent-Ticket-Triage/deploy/deploy_agentcore.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../RTTA-AI-Multi-Agent-Ticket-Triage" && pwd)"

exec "$PROJECT_ROOT/deploy/deploy_agentcore.sh"
