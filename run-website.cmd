@echo off
rem Qalam Policy Command Centre: double-click to set up (first time only) and start the website.
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" goto setup
if not exist "frontend\node_modules" goto setup
goto start
:setup
echo First run: installing backend and frontend packages. This takes several minutes...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1"
if errorlevel 1 (
  echo.
  echo Setup failed. Read the messages above.
  pause
  exit /b 1
)
:start
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-all.ps1"
echo.
echo Backend and website are starting in two new windows. The site opens at http://localhost:5173
echo Close those two windows to stop them.
timeout /t 15
