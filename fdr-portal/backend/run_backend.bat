@echo off
title FDR Portal Backend - Port 8000
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Starting FDR Portal Backend on http://127.0.0.1:8000 ...
call .venv\Scripts\activate.bat
python -m uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload
pause

