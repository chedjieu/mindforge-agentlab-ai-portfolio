# Run a Python module with the uv-managed interpreter (avoids locked venv python.exe).
# Examples:
#   .\scripts\with-python.ps1 -m pytest
#   .\scripts\with-python.ps1 -m evals.run_all
#   .\scripts\with-python.ps1 -m security.injection_eval
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PythonArgs
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue

if (-not $env:RAIP_MODEL -and -not $env:CAREPATH_MODEL -and -not $env:HEDIP_MODEL) {
    $env:RAIP_MODEL = "fake"
}

$py = (uv python find 3.12).Trim()
$site = Join-Path $env:LOCALAPPDATA "healthtech-suite-venv\Lib\site-packages"
if (-not (Test-Path (Join-Path $site "pytest"))) {
    New-Item -ItemType Directory -Force -Path $site | Out-Null
    uv pip install --python $py --target $site pytest
}
$env:PYTHONPATH = "$((Get-Location).Path);$site"
& $py @PythonArgs
exit $LASTEXITCODE
