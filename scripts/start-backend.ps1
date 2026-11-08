# Start the API on http://localhost:8000 (docs at /docs).
. "$PSScriptRoot\_common.ps1"
Assert-Venv
Test-ApiKey
Set-Location (Join-Path $Root "backend")
Write-Host "Backend: http://localhost:8000  (API docs: http://localhost:8000/docs). Ctrl+C to stop." -ForegroundColor Green
& $VenvPy -m uvicorn app.main:app --reload --reload-dir app --port 8000
