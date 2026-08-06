# Run evals from RAIRA-AI-Research-Assistant (PowerShell)
param(
    [ValidateSet("planner", "citation", "e2e", "all")]
    [string]$Eval = "planner"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$module = switch ($Eval) {
    "planner"  { "evals.planner_eval" }
    "citation" { "evals.citation_eval" }
    "e2e"      { "evals.e2e_eval" }
    "all"      { "evals.run_all" }
}

uv run python -m $module @args
