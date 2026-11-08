# Run the 10 test questions (kb\eval\questions.jsonl) through the live pipeline.
# Writes kb\eval\report.md and kb\eval\report.json.
. "$PSScriptRoot\_common.ps1"
Assert-Venv
Test-ApiKey
Set-Location (Join-Path $Root "backend")
& $VenvPy -m app.kb.evaluate @args
exit $LASTEXITCODE
