# Shared helpers for the Qalam scripts. Dot-sourced by the other scripts.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPy = Join-Path $Root "backend\.venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"            # Arabic text in console output
$env:PYTHONIOENCODING = "utf-8"

function Assert-Venv {
    if (-not (Test-Path $VenvPy)) {
        throw "Backend environment not found. Run first:  .\scripts\setup.ps1"
    }
}

function Test-ApiKey {
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) { Write-Warning ".env not found. Copy .env.example to .env and set ANTHROPIC_API_KEY."; return }
    $line = Select-String -Path $envFile -Pattern '^\s*ANTHROPIC_API_KEY\s*=\s*(\S+)' -ErrorAction SilentlyContinue
    if (-not $line) { Write-Host "No ANTHROPIC_API_KEY: running in FREE offline mode (answers from kb\data, no AI generation)." -ForegroundColor Cyan }
}
