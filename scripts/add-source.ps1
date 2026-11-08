# Download a document into kb\raw and register it in kb\sources.csv.
# Usage:  .\scripts\add-source.ps1 <url> --title "..." --layer uae_federal --language ar
. "$PSScriptRoot\_common.ps1"
Assert-Venv
Set-Location (Join-Path $Root "backend")
& $VenvPy -m app.kb.add_source @args
exit $LASTEXITCODE
