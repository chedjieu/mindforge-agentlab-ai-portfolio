# PowerShell launcher. Never query venv Scripts\python.exe (Access denied).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
& "$PSScriptRoot\with-python.ps1" -m app.main
