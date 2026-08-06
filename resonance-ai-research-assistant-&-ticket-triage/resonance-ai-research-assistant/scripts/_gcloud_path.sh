#!/usr/bin/env bash
# Ensure gcloud is on PATH for Git Bash on Windows.
# The SDK install path contains a space ("Cloud SDK"), which breaks PATH parsing.

ensure_gcloud_on_path() {
    if command -v gcloud >/dev/null 2>&1; then
        return 0
    fi

    local candidates=()
    if [ -n "${LOCALAPPDATA:-}" ]; then
        candidates+=("$LOCALAPPDATA/Google/Cloud SDK/google-cloud-sdk/bin")
    fi
    if [ -n "${ProgramFiles:-}" ]; then
        candidates+=("$ProgramFiles/Google/Cloud SDK/google-cloud-sdk/bin")
    fi
    local pf86
    pf86="$(printenv 'ProgramFiles(x86)' 2>/dev/null || true)"
    if [ -n "$pf86" ]; then
        candidates+=("$pf86/Google/Cloud SDK/google-cloud-sdk/bin")
    fi
    candidates+=("$HOME/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin")

    local dir
    for dir in "${candidates[@]}"; do
        if [ -f "$dir/gcloud" ] || [ -f "$dir/gcloud.cmd" ]; then
            export PATH="$dir:$PATH"
            return 0
        fi
    done

    return 1
}
