@echo off
REM Start the research assistant (Windows). Double-click or run from cmd/PowerShell.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Run "uv sync" first to create the virtual environment.
    exit /b 1
)
.venv\Scripts\python.exe -m app.main
