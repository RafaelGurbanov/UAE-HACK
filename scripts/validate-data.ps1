# Check kb\data\*.json (schema, duplicate ids, missing citations, verified=false) and print a summary.
. "$PSScriptRoot\_common.ps1"
Assert-Venv
Set-Location (Join-Path $Root "backend")
& $VenvPy -m app.kb.validate_data @args
exit $LASTEXITCODE
