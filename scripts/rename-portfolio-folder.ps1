# Run AFTER closing this folder in Cursor / VS Code.
# Renames set-of-designed-projects -> mindforge-agentlab-ai-portfolio
$ErrorActionPreference = "Stop"
$portfolioRoot = Split-Path $PSScriptRoot -Parent
$parent = Split-Path $portfolioRoot -Parent
$src = Join-Path $parent "set-of-designed-projects"
$dst = Join-Path $parent "mindforge-agentlab-ai-portfolio"

if (-not (Test-Path -LiteralPath $src)) {
  if (Test-Path -LiteralPath $dst) {
    Write-Host "Already renamed: $dst"
    exit 0
  }
  throw "Source not found: $src"
}
if (Test-Path -LiteralPath $dst) { throw "Destination already exists: $dst" }

Rename-Item -LiteralPath $src -NewName "mindforge-agentlab-ai-portfolio"
Write-Host "Renamed OK -> $dst"
Write-Host "Re-open that folder in Cursor."
