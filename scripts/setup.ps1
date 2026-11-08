# One-time setup: Python venv + backend packages, frontend packages, .env file.
# Usage (from the project folder):  .\scripts\setup.ps1
. "$PSScriptRoot\_common.ps1"
Set-Location $Root

# ---- Python 3.11+ (prefers 3.12, which has wheels for every package)
function Test-Python([string]$exe, [string[]]$pre) {
    # Native tools write warnings to stderr; never let that stop the script.
    $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try {
        $out = & $exe @pre -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        return ($LASTEXITCODE -eq 0 -and "$out" -match '^3\.(1[1-4])$')
    } catch { return $false } finally { $ErrorActionPreference = $old }
}
$pyExe = $null; $pyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in "3.12", "3.11", "3.13", "3.14") {
        if (Test-Python "py" @("-$v")) { $pyExe = "py"; $pyArgs = @("-$v"); break }
    }
}
if (-not $pyExe) {
    foreach ($cand in "python", "python3") {
        if ((Get-Command $cand -ErrorAction SilentlyContinue) -and (Test-Python $cand @())) { $pyExe = $cand; break }
    }
}
if (-not $pyExe) {
    Write-Host ""
    Write-Host "Python 3.11 or newer was not found on this computer." -ForegroundColor Red
    Write-Host "Install Python 3.12 from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')," -ForegroundColor Yellow
    Write-Host "or run:  winget install -e --id Python.Python.3.12" -ForegroundColor Yellow
    Write-Host "Then double-click run-website.cmd again." -ForegroundColor Yellow
    exit 1
}
Write-Host ("Using Python: " + $pyExe + " " + ($pyArgs -join " ")) -ForegroundColor Cyan
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js was not found. Install Node.js 22 LTS from https://nodejs.org/ or run:  winget install -e --id OpenJS.NodeJS.LTS" -ForegroundColor Red
    Write-Host "Then double-click run-website.cmd again." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "Creating Python environment in backend\.venv ..." -ForegroundColor Cyan
    & $pyExe @pyArgs -m venv (Join-Path $Root "backend\.venv")
}
Write-Host "Installing backend packages (PyTorch, Chroma, ...: several minutes the first time) ..." -ForegroundColor Cyan
& $VenvPy -m pip install --upgrade pip --quiet
& $VenvPy -m pip install -r (Join-Path $Root "backend\requirements-ml.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install failed (see the messages above)." }

Write-Host "Installing frontend packages ..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
npm install --no-fund --no-audit
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm install failed." }
Pop-Location

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    Write-Host "Created .env. Open it and set ANTHROPIC_API_KEY." -ForegroundColor Yellow
}
Write-Host "`nSetup done. Next: put documents in kb\raw\<layer>\, then run .\scripts\ingest.ps1" -ForegroundColor Green
