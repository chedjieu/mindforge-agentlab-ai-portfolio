#!/usr/bin/env bash
# Deploy panasonic-egkp to AWS Bedrock AgentCore.
# AgentCore managed memory is disabled by default (DISABLE_AGENTCORE_MEMORY=1);
# Postgres checkpointer/store via POSTGRES_DSN is the source of truth.

set -euo pipefail

export AGENTCORE_SUPPRESS_RECOMMENDATION="${AGENTCORE_SUPPRESS_RECOMMENDATION:-1}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
fi

# Agent names: letters, numbers, underscores only (no hyphens).
NAME="${AGENT_NAME:-panasonic_egkp}"
# Root entrypoint avoids Windows backslash paths that break Linux ARM64 runtime.
ENTRYPOINT="${ENTRYPOINT:-agentcore_entrypoint.py}"
REGION="${AWS_REGION:-us-east-1}"
IDLE_TIMEOUT="${IDLE_TIMEOUT:-600}"
PYTHON_RUNTIME="${PYTHON_RUNTIME:-PYTHON_3_11}"
DISABLE_MEMORY="${DISABLE_AGENTCORE_MEMORY:-1}"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-direct_code_deploy}"

agentcore_cmd() {
    if [[ -x "$ROOT/.venv/Scripts/agentcore.exe" ]] || [[ -x "$ROOT/.venv/bin/agentcore" ]]; then
        PATH="$ROOT/.venv/Scripts:$ROOT/.venv/bin:$PATH" uv run agentcore "$@"
    else
        uv run agentcore "$@"
    fi
}

if ! agentcore_cmd --help >/dev/null 2>&1; then
    echo "agentcore CLI not found — installing bedrock-agentcore-starter-toolkit..."
    uv pip install bedrock-agentcore-starter-toolkit
fi

echo "Deploying $NAME from $ROOT"
echo "  region=$REGION  entrypoint=$ENTRYPOINT  deployment=$DEPLOYMENT_TYPE"
echo "  DISABLE_AGENTCORE_MEMORY=$DISABLE_MEMORY"
echo

# Force reconfigure if entrypoint still points at nested deploy/ path.
if [[ -f .bedrock_agentcore.yaml ]] && grep -Eq 'deploy[/\\]+agentcore_entrypoint\.py' .bedrock_agentcore.yaml; then
    echo "Entrypoint is nested under deploy/ — moving to project-root agentcore_entrypoint.py"
    agentcore_cmd destroy --agent "$NAME" --force || true
    rm -f .bedrock_agentcore.yaml
fi

configure_args=(
    --name "$NAME"
    --entrypoint "$ENTRYPOINT"
    --deployment-type "$DEPLOYMENT_TYPE"
    --idle-timeout "$IDLE_TIMEOUT"
    --region "$REGION"
    --non-interactive
    --language python
)

if [[ "$DISABLE_MEMORY" == "1" ]]; then
    configure_args+=(--disable-memory)
fi

if [[ "$DEPLOYMENT_TYPE" == "direct_code_deploy" ]]; then
    configure_args+=(--runtime "$PYTHON_RUNTIME")
fi

echo "1. Configure"
agentcore_cmd configure "${configure_args[@]}"

deploy_args=(--agent "$NAME")
if [[ -n "${POSTGRES_DSN:-}" ]]; then
    deploy_args+=(--env "POSTGRES_DSN=$POSTGRES_DSN")
fi
if [[ -n "${EGKP_MODEL:-}" ]]; then
    deploy_args+=(--env "EGKP_MODEL=$EGKP_MODEL")
fi
if [[ -n "${EGKP_EMBEDDINGS:-}" ]]; then
    deploy_args+=(--env "EGKP_EMBEDDINGS=$EGKP_EMBEDDINGS")
fi
if [[ -n "${EGKP_VECTORS:-}" ]]; then
    deploy_args+=(--env "EGKP_VECTORS=$EGKP_VECTORS")
fi
if [[ -n "${AWS_REGION:-}" ]]; then
    deploy_args+=(--env "AWS_REGION=$AWS_REGION")
fi
deploy_args+=(--env "DISABLE_AGENTCORE_MEMORY=$DISABLE_MEMORY")

echo "2. Deploy"
agentcore_cmd deploy "${deploy_args[@]}"

echo "Done. Check status with: uv run agentcore status --agent $NAME"
echo "Logs: uv run agentcore logs --agent $NAME --follow"
