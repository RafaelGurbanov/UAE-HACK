# Start backend and frontend in two windows and open the website.
. "$PSScriptRoot\_common.ps1"
Assert-Venv
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-backend.ps1`""
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSScriptRoot\start-frontend.ps1`""
Start-Sleep -Seconds 6
Start-Process "http://localhost:5173"
