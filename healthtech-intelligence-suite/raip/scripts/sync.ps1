# Install deps without querying a Windows-locked venv python.exe.
# Do not run: uv sync / uv run / .\.venv\Scripts\Activate.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

$py = (uv python find 3.12).Trim()
$site = Join-Path $env:LOCALAPPDATA "raip-venv\Lib\site-packages"
New-Item -ItemType Directory -Force -Path $site | Out-Null
uv pip install --python $py --target $site -e ".[dev]"
Write-Host "OK: packages in $site"
Write-Host "Run: .\scripts\run.ps1"
