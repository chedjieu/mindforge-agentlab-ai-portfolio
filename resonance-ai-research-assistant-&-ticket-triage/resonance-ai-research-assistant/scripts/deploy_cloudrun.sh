#!/usr/bin/env bash
# Resonance Technologies - deploy Project 1 (Research Assistant) to Google Cloud Run.
# Day 4 H4b. Idempotent — safe to re-run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# shellcheck source=_gcloud_path.sh
source "$SCRIPT_DIR/_gcloud_path.sh"
ensure_gcloud_on_path || true

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
skip() { printf "  \033[33m⊘\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m!!\033[0m %s\n" "$*"; }
err()  { printf "  \033[31mERR\033[0m %s\n" "$*"; }

# Load .env line-by-line (DSNs contain ? and = that break `source`)
if [[ -f .env ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" || ! "$line" == *=* ]] && continue
        key="${line%%=*}"
        value="${line#*=}"
        export "$key=$value"
    done < .env
fi

PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "$PROJECT" || "$PROJECT" == "(unset)" ]]; then
    PROJECT="${GCP_PROJECT:-}"
fi
if [[ -z "$PROJECT" ]]; then
    err "No gcloud project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

SERVICE="${SERVICE:-raira-research-assistant}"
REGION="${REGION:-asia-south1}"
CLOUDSQL_INSTANCE="${CLOUDSQL_INSTANCE:-raira-postgres}"
CONNECTION_NAME="${PROJECT}:${REGION}:${CLOUDSQL_INSTANCE}"
VERTEX_LOCATION="us-central1"

bold "Resonance Technologies - deploy $SERVICE to Cloud Run"
echo "  project=$PROJECT  region=$REGION  cloudsql=$CONNECTION_NAME"
echo

bold "Step 1 — Enable APIs"
NEEDED=(
    run.googleapis.com
    cloudbuild.googleapis.com
    artifactregistry.googleapis.com
    secretmanager.googleapis.com
    sqladmin.googleapis.com
    aiplatform.googleapis.com
)
MISSING=()
for api in "${NEEDED[@]}"; do
    if gcloud services list --enabled --project="$PROJECT" --format='value(name)' | grep -qx "$api"; then
        skip "$api"
    else
        MISSING+=("$api")
    fi
done
if ((${#MISSING[@]} > 0)); then
    if gcloud services enable "${MISSING[@]}" --project="$PROJECT" 2>/tmp/gcloud-api-err.txt; then
        for api in "${MISSING[@]}"; do
            ok "$api (enabled)"
        done
    elif grep -qiE 'billing|403' /tmp/gcloud-api-err.txt 2>/dev/null; then
        warn "API enable skipped — enable billing at https://console.cloud.google.com/billing"
    else
        cat /tmp/gcloud-api-err.txt >&2
        exit 1
    fi
fi
echo

push_secret() {
    local name="$1" value="$2"
    if [[ -z "$value" ]]; then
        err "Empty value for secret $name — set it in .env"
        exit 1
    fi
    if gcloud secrets describe "$name" --project="$PROJECT" >/dev/null 2>&1; then
        skip "secret $name (exists)"
    else
        printf "%s" "$value" | gcloud secrets create "$name" \
            --replication-policy=automatic \
            --data-file=- \
            --project="$PROJECT" \
            --quiet
        ok "secret $name (created)"
    fi
}

bold "Step 2 — Secrets"
push_secret raira-postgres-dsn "${POSTGRES_DSN:-}"
push_secret raira-tavily       "${TAVILY_API_KEY:-}"
push_secret raira-langsmith    "${LANGSMITH_API_KEY:-}"
echo

bold "Step 3 — IAM for Compute Engine default service account"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "  service account: $SA_EMAIL"

for secret in raira-postgres-dsn raira-tavily raira-langsmith; do
    gcloud secrets add-iam-policy-binding "$secret" \
        --project="$PROJECT" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        &>/dev/null || true
done
ok "secretAccessor on raira-* secrets"

for role in roles/storage.objectViewer roles/cloudbuild.builds.builder roles/artifactregistry.writer roles/aiplatform.user; do
    gcloud projects add-iam-policy-binding "$PROJECT" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        &>/dev/null || true
done
ok "project roles for Cloud Build + Vertex"
echo

bold "Step 4 — Deploy to Cloud Run"
gcloud run deploy "$SERVICE" \
    --source . \
    --project "$PROJECT" \
    --region "$REGION" \
    --allow-unauthenticated \
    --add-cloudsql-instances "$CONNECTION_NAME" \
    --set-env-vars "RAIRA_MODEL=google_vertexai:gemini-2.5-pro,RAIRA_EMBEDDINGS=google_vertexai:text-embedding-005,LANGSMITH_PROJECT=${SERVICE},LANGSMITH_TRACING=true,GCP_PROJECT=${PROJECT},GCP_LOCATION=${VERTEX_LOCATION}" \
    --set-secrets "POSTGRES_DSN=raira-postgres-dsn:latest,TAVILY_API_KEY=raira-tavily:latest,LANGSMITH_API_KEY=raira-langsmith:latest" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 600 \
    --concurrency 4
echo

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
bold "Deployed."
echo "  $URL"
