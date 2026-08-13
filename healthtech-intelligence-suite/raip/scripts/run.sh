#!/usr/bin/env bash
# Git Bash / MSYS2 launcher. Do not use PowerShell $env: syntax here.
set -euo pipefail
exec bash "$(dirname "$0")/with-python.sh" -m app.main
