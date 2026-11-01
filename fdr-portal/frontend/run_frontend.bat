@echo off
title FDR Portal Frontend - Port 5173
cd /d "%~dp0"
echo Starting FDR Portal Frontend on http://localhost:5173 ...
call npm run dev
pause

