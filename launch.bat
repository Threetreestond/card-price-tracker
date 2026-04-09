@echo off
title Sorcery Tracker
cd /d C:\Users\three\Projects\ml-roadmap\card-price-tracker

:: Open the browser after a short delay (runs in background so it doesn't block)
start "" /B cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Start the server in the foreground — Ctrl+C here will properly shut it down
.venv\Scripts\uvicorn.exe api:app --host 127.0.0.1 --port 8000
