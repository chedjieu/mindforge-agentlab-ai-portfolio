#!/usr/bin/env bash
# Create raira-research-guardrail (Project 1). Works in Git Bash on Windows.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# AWS CLI: add to PATH if installed but not linked (common on Windows Git Bash)
if ! command -v aws >/dev/null 2>&1; then
  for candidate in \
    "/c/Program Files/Amazon/AWSCLIV2/aws.exe" \
    "/c/Program Files (x86)/Amazon/AWSCLIV2/aws.exe" \
    "$PROGRAMFILES/Amazon/AWSCLIV2/aws.exe"; do
    if [[ -x "$candidate" ]]; then
      export PATH="$(dirname "$candidate"):$PATH"
      break
    fi
  done
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: AWS CLI not found. Install: winget install Amazon.AWSCLI" >&2
  echo "Then restart your terminal or add AWSCLIV2 to PATH." >&2
  exit 1
fi

aws bedrock create-guardrail \
  --region us-east-1 \
  --name "raira-research-guardrail" \
  --description "RAIRA lab standard guardrail for Project 1" \
  --blocked-input-messaging "Sorry — the RAIRA Research Assistant only handles business and technology research, not cooking questions." \
  --blocked-outputs-messaging "Sorry — the RAIRA Research Assistant only handles business and technology research, not cooking questions." \
  --topic-policy-config "file://${SCRIPT_DIR}/guardrail-topic-policy.json" \
  --content-policy-config "file://${SCRIPT_DIR}/guardrail-content-policy.json" \
  --sensitive-information-policy-config "file://${SCRIPT_DIR}/guardrail-pii-policy.json"
