# Start the website on http://localhost:5173 (live mode: talks to the backend).
. "$PSScriptRoot\_common.ps1"
Set-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) { throw "Frontend packages missing. Run first:  .\scripts\setup.ps1" }
npm run dev
