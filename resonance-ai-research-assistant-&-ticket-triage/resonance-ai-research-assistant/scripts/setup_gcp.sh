#!/usr/bin/env bash
# Resonance Technologies - guided GCP setup for the lab.
# Run once before Day 1. Re-running is safe.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_gcloud_path.sh
source "$SCRIPT_DIR/_gcloud_path.sh"
ensure_gcloud_on_path || true

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
ok()   { printf "  \033[32mok\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m!!\033[0m %s\n" "$*"; }
err()  { printf "  \033[31mERR\033[0m %s\n" "$*"; }

bold "Resonance Technologies - GCP setup check"
echo

# 1. gcloud installed?
bold "1. gcloud CLI"
if ! command -v gcloud >/dev/null 2>&1; then
    err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
ok "$(gcloud --version | head -1)"
echo

# 2. logged in?
bold "2. gcloud auth"
ACCOUNT=$(gcloud auth list --format='value(account)' 2>/dev/null | head -1 || true)
if [[ -z "$ACCOUNT" ]]; then
    err "No active gcloud account. Run: gcloud auth login"
    err "  (Git Bash: source ~/.bashrc  OR  ./bin/gcloud auth login)"
    exit 1
fi
ok "logged in as $ACCOUNT"
echo

# 3. project set?
bold "3. GCP project"
PROJECT=$(gcloud config get-value project 2>/dev/null || true)
if [[ -z "$PROJECT" || "$PROJECT" == "(unset)" ]]; then
    err "No default project. Run: gcloud config set project YOUR_PROJECT_ID"
    err "If you have not created a project, do so at: https://console.cloud.google.com/projectcreate"
    exit 1
fi
ok "project=$PROJECT"
echo

# 4. APIs enabled?
bold "4. APIs"
NEEDED=(aiplatform.googleapis.com run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com)
for api in "${NEEDED[@]}"; do
    if gcloud services list --enabled --format='value(name)' | grep -q "^$api$"; then
        ok "$api"
    else
        warn "$api not enabled. Enabling..."
        if ! gcloud services enable "$api" 2>/tmp/gcloud-enable-err.txt; then
            if grep -q billing-enabled /tmp/gcloud-enable-err.txt 2>/dev/null; then
                warn "$api skipped — enable billing at https://console.cloud.google.com/billing"
            else
                cat /tmp/gcloud-enable-err.txt >&2
                exit 1
            fi
        else
            ok "$api (enabled now)"
        fi
    fi
done
echo

# 5. Application Default Credentials
bold "5. Application Default Credentials"
HAS_ADC=false
if gcloud auth application-default print-access-token >/dev/null 2>&1; then
    HAS_ADC=true
    ok "ADC available"
else
    warn "ADC not set. Run: gcloud auth application-default login"
fi
echo

# 6. Vertex AI smoke test
bold "6. Vertex AI smoke test"
LOCATION="${GCP_LOCATION:-us-central1}"
if [[ "$HAS_ADC" == true ]]; then
python3 - <<PY
import os, sys
os.environ.setdefault("GCP_LOCATION", "$LOCATION")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    vertexai.init(project="$PROJECT", location="$LOCATION")
    m = GenerativeModel("gemini-2.5-pro")
    resp = m.generate_content("Reply with the four letters: PING")
    if "PING" in (resp.text or "").upper():
        print("  ok Gemini 2.5 Pro responded.")
    else:
        print("  ok Gemini responded:", resp.text[:80])
except Exception as e:
    print("  WARN Vertex AI test failed:", e)
    sys.exit(0)
PY
else
    warn "skipped (ADC required)"
fi
echo

# 7. Staging bucket for Agent Engine
bold "7. Agent Engine staging bucket"
BUCKET="${GCP_BUCKET:-$PROJECT-raira-staging}"
if gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
    ok "bucket gs://$BUCKET exists"
else
    warn "bucket gs://$BUCKET not found. Creating..."
    if gcloud storage buckets create "gs://$BUCKET" --location="$LOCATION" --uniform-bucket-level-access 2>/tmp/gcloud-bucket-err.txt; then
        ok "created gs://$BUCKET"
    elif grep -qiE 'billing|403' /tmp/gcloud-bucket-err.txt 2>/dev/null; then
        warn "bucket skipped — enable billing at https://console.cloud.google.com/billing"
    else
        cat /tmp/gcloud-bucket-err.txt >&2
        exit 1
    fi
fi
echo

bold "Done."
echo "Make sure your .env contains:"
echo "  GCP_PROJECT=$PROJECT"
echo "  GCP_LOCATION=$LOCATION"
echo "  GCP_BUCKET=$BUCKET"
