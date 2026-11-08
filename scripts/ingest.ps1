# Index every PDF/HTML/TXT in kb\raw. Use -Reset to rebuild from scratch.
# Usage:  .\scripts\ingest.ps1   |   .\scripts\ingest.ps1 -Reset
param([switch]$Reset, [switch]$Force)
. "$PSScriptRoot\_common.ps1"
Assert-Venv
Set-Location (Join-Path $Root "backend")
$a = @(); if ($Reset) { $a += "--reset" }; if ($Force) { $a += "--force" }
& $VenvPy -m app.kb.ingest @a
exit $LASTEXITCODE
