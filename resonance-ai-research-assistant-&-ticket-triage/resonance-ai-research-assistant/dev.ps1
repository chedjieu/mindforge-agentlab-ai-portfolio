# Start the research assistant (PowerShell)
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error 'Run "uv sync" first to create the virtual environment.'
    exit 1
}
& .\.venv\Scripts\python.exe -m app.main
