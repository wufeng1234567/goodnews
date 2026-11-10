@echo off
setlocal
cd /d "%~dp0.."
if not exist "backend\.venv\Scripts\python.exe" (
  echo [goodnews] Backend virtual environment not found.
  pause
  exit /b 1
)
backend\.venv\Scripts\python.exe scripts\ui-smoke.py
endlocal
