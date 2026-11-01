@echo off
title FDR SmartTrack MVP Launcher
echo ========================================================
echo   FDR SmartTrack Portal - SIH 26265 MVP Launcher
echo ========================================================
echo.
echo Starting Backend (FastAPI on http://127.0.0.1:8000)...
start "FDR Backend" cmd /k "call "%~dp0backend\run_backend.bat""

echo Starting Frontend (Vite React on http://localhost:5173)...
start "FDR Frontend" cmd /k "call "%~dp0frontend\run_frontend.bat""

echo.
echo Launching browser to http://localhost:5173 ...
ping 127.0.0.1 -n 4 >nul
start http://localhost:5173

echo.
echo Demo Accounts (Password for all: Demo@123):
echo   - Super Admin:          superadmin@demo.in
echo   - Finance Officer:      finance@inst001.demo.in
echo   - Institution Reviewer: reviewer@inst001.demo.in
echo   - AICTE Officer:        aicte@demo.in
echo   - Auditor:              auditor@demo.in
echo.
pause

