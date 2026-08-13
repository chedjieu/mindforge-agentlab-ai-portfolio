# PowerShell: run a Python module with the uv-managed interpreter.
# Do not use uv run / uv sync — venv python.exe is often Access denied.
# Examples:
#   .\scripts\with-python.ps1 -m pytest
#   .\scripts\with-python.ps1 -m evals.run_all
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PythonArgs
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue

if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not $env:RAIP_MODEL) { $env:RAIP_MODEL = "fake" }
if (-not $env:RAIP_HITL) { $env:RAIP_HITL = "required" }

$py = (uv python find 3.12).Trim()
$site = Join-Path $env:LOCALAPPDATA "raip-venv\Lib\site-packages"
if (-not (Test-Path (Join-Path $site "fastapi"))) {
    New-Item -ItemType Directory -Force -Path $site | Out-Null
    uv pip install --python $py --target $site -e ".[dev]"
}
$env:PYTHONPATH = $site
& $py @PythonArgs
