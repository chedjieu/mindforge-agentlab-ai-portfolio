#!/usr/bin/env bash
# Run from starter-repo-main root — forwards to RAIRA-AI-Research-Assistant/scripts/create_cloudsql.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$ROOT/RAIRA-AI-Research-Assistant/scripts/create_cloudsql.sh" "$@"
