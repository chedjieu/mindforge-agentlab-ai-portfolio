@echo off
REM Start RAIP on http://127.0.0.1:8011
REM Avoids Desktop .venv Access denied. Do not use uv run here.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\run.ps1"
