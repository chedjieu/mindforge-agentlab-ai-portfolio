#!/usr/bin/env bash
# Resonance Technologies - provision Cloud SQL PostgreSQL + pgvector for Project 1.
# Idempotent: safe to re-run. Run from the repo root or scripts/ directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INIT_SQL="$SCRIPT_DIR/postgres-init.sql"
# shellcheck source=_gcloud_path.sh
source "$SCRIPT_DIR/_gcloud_path.sh"
ensure_gcloud_on_path || true

# Cloud SQL Proxy for `gcloud sql connect` fallback (Windows / no psql).
BIN_DIR="$ROOT_DIR/bin"
if [[ -f "$BIN_DIR/cloud-sql-proxy.exe" && ! -f "$BIN_DIR/cloud-sql-proxy" ]]; then
    cp -f "$BIN_DIR/cloud-sql-proxy.exe" "$BIN_DIR/cloud-sql-proxy" 2>/dev/null \
        || ln -sf cloud-sql-proxy.exe "$BIN_DIR/cloud-sql-proxy" 2>/dev/null || true
fi
if [[ -d "$BIN_DIR" ]]; then
    export PATH="$BIN_DIR:$PATH"
fi

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
skip() { printf "  \033[33m⊘\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m!!\033[0m %s\n" "$*"; }
err()  { printf "  \033[31mERR\033[0m %s\n" "$*"; }

DELETE=false
for arg in "$@"; do
    case "$arg" in
        --delete) DELETE=true ;;
        -h|--help)
            echo "Usage: $0 [--delete]"
            echo "  Provisions Cloud SQL Postgres 15 + pgvector (default)."
            echo "  --delete  Tear down the instance."
            exit 0
            ;;
        *)
            err "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

if ! command -v gcloud >/dev/null 2>&1; then
    err "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "$PROJECT" || "$PROJECT" == "(unset)" ]]; then
    err "No gcloud project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

CLOUDSQL_INSTANCE="${CLOUDSQL_INSTANCE:-raira-postgres}"
REGION="${REGION:-asia-south1}"
DB_NAME="${DB_NAME:-resonance}"
DB_PASS="${DB_PASS:-$(openssl rand -base64 24 2>/dev/null | tr -d '/+=' | head -c 24)}"
CONNECTION_NAME="${PROJECT}:${REGION}:${CLOUDSQL_INSTANCE}"

bold "Resonance Technologies - Cloud SQL setup"
echo "  project=$PROJECT  instance=$CLOUDSQL_INSTANCE  region=$REGION  database=$DB_NAME"
echo

if [[ "$DELETE" == true ]]; then
    bold "Deleting Cloud SQL instance"
    if gcloud sql instances describe "$CLOUDSQL_INSTANCE" --project="$PROJECT" >/dev/null 2>&1; then
        gcloud sql instances delete "$CLOUDSQL_INSTANCE" --project="$PROJECT" --quiet
        ok "deleted $CLOUDSQL_INSTANCE"
    else
        skip "instance $CLOUDSQL_INSTANCE does not exist"
    fi
    exit 0
fi

bold "Step 0 — Enable Cloud SQL Admin API"
if gcloud services list --enabled --project="$PROJECT" --format='value(name)' \
    | grep -qx 'sqladmin.googleapis.com'; then
    skip "sqladmin.googleapis.com already enabled"
else
    gcloud services enable sqladmin.googleapis.com --project="$PROJECT"
    ok "sqladmin.googleapis.com enabled (waiting 30s for propagation)"
    sleep 30
fi
echo

bold "Step 1 — Cloud SQL instance (db-f1-micro, Postgres 15)"
if gcloud sql instances describe "$CLOUDSQL_INSTANCE" --project="$PROJECT" >/dev/null 2>&1; then
    skip "instance $CLOUDSQL_INSTANCE already exists — resetting postgres password"
    gcloud sql users set-password postgres \
        --instance="$CLOUDSQL_INSTANCE" \
        --project="$PROJECT" \
        --password="$DB_PASS" \
        --quiet
    ok "postgres password reset"
else
    gcloud sql instances create "$CLOUDSQL_INSTANCE" \
        --project="$PROJECT" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --root-password="$DB_PASS" \
        --storage-auto-increase \
        --quiet
    ok "created $CLOUDSQL_INSTANCE"
fi
echo

bold "Step 2 — Database"
if gcloud sql databases describe "$DB_NAME" \
    --instance="$CLOUDSQL_INSTANCE" \
    --project="$PROJECT" >/dev/null 2>&1; then
    skip "database $DB_NAME already exists"
else
    gcloud sql databases create "$DB_NAME" \
        --instance="$CLOUDSQL_INSTANCE" \
        --project="$PROJECT" \
        --quiet
    ok "created database $DB_NAME"
fi
echo

bold "Step 3 — Schema (pgvector + tables)"
if [[ ! -f "$INIT_SQL" ]]; then
    err "Missing $INIT_SQL"
    exit 1
fi

MY_IP="$(curl -4 -fsS ifconfig.me 2>/dev/null || curl -4 -fsS icanhazip.com 2>/dev/null || true)"
if [[ -z "$MY_IP" ]]; then
    err "Could not detect public IPv4 (curl -4 ifconfig.me). Cannot authorise temporary access."
    exit 1
fi

warn "Temporarily authorising $MY_IP/32"
gcloud sql instances patch "$CLOUDSQL_INSTANCE" \
    --project="$PROJECT" \
    --authorized-networks="$MY_IP/32" \
    --quiet

cleanup_ip() {
    gcloud sql instances patch "$CLOUDSQL_INSTANCE" \
        --project="$PROJECT" \
        --clear-authorized-networks \
        --quiet >/dev/null 2>&1 || true
}
trap cleanup_ip EXIT

# Public IP can take a moment after instance creation.
for _ in $(seq 1 12); do
    PUBLIC_IP="$(gcloud sql instances describe "$CLOUDSQL_INSTANCE" \
        --project="$PROJECT" \
        --format='value(ipAddresses[0].ipAddress)' 2>/dev/null || true)"
    [[ -n "$PUBLIC_IP" ]] && break
    sleep 5
done

if [[ -z "$PUBLIC_IP" ]]; then
    err "Could not resolve Cloud SQL public IP"
    exit 1
fi

run_init() {
    if command -v psql >/dev/null 2>&1; then
        PGPASSWORD="$DB_PASS" psql \
            "host=${PUBLIC_IP} port=5432 user=postgres dbname=${DB_NAME} sslmode=require" \
            -v ON_ERROR_STOP=1 \
            -f "$INIT_SQL"
    elif [[ -f "$ROOT_DIR/pyproject.toml" ]]; then
        warn "psql not found — using uv + psycopg"
        PGPASSWORD="$DB_PASS" INIT_SQL="$INIT_SQL" PUBLIC_IP="$PUBLIC_IP" DB_NAME="$DB_NAME" \
            uv run --directory "$ROOT_DIR" python - <<'PY'
import os, pathlib
import psycopg

init_sql = pathlib.Path(os.environ["INIT_SQL"]).read_text()
conninfo = (
    f"host={os.environ['PUBLIC_IP']} port=5432 user=postgres "
    f"password={os.environ['PGPASSWORD']} dbname={os.environ['DB_NAME']} sslmode=require"
)
with psycopg.connect(conninfo, autocommit=True) as conn:
    conn.execute(init_sql)
PY
    else
        warn "psql not found — falling back to gcloud sql connect"
        # shellcheck disable=SC2090
        gcloud sql connect "$CLOUDSQL_INSTANCE" \
            --user=postgres \
            --database="$DB_NAME" \
            --project="$PROJECT" \
            --quiet < "$INIT_SQL"
    fi
}

if run_init; then
    ok "ran $INIT_SQL"
else
    err "schema init failed"
    exit 1
fi

trap - EXIT
cleanup_ip
skip "removed temporary IP authorisation ($MY_IP/32)"
echo

bold "Done — add to .env"
ENCODED_PASS="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$DB_PASS")"
CLOUD_RUN_DSN="postgresql://postgres:${ENCODED_PASS}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"
LOCAL_DSN="postgresql://postgres:${ENCODED_PASS}@${PUBLIC_IP}:5432/${DB_NAME}?sslmode=require"

echo
echo "  # Cloud Run (Unix socket via Cloud SQL Auth proxy sidecar)"
echo "  POSTGRES_DSN=${CLOUD_RUN_DSN}"
echo
echo "  # gcloud run deploy --add-cloudsql-instances"
echo "  CONNECTION_NAME=${CONNECTION_NAME}"
echo
echo "  # Local debugging (requires authorised IP or Cloud SQL Auth Proxy)"
echo "  POSTGRES_DSN_LOCAL=${LOCAL_DSN}"
echo
echo "  DB_PASS=${DB_PASS}  # save this — shown once when auto-generated"
