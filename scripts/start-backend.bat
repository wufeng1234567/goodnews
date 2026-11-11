@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8010"
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /I "%%A"=="BACKEND_HOST" set "BACKEND_HOST=%%B"
    if /I "%%A"=="BACKEND_PORT" set "BACKEND_PORT=%%B"
  )
)

if not exist "backend\.venv\Scripts\uvicorn.exe" (
  echo [goodnews] Backend virtual environment not found.
  echo [goodnews] Create it with: D:\Python3.11\python.exe -m venv backend\.venv
  echo [goodnews] Then run: backend\.venv\Scripts\python -m pip install -e "backend[dev]"
  pause
  exit /b 1
)
cd /d "backend"
echo [goodnews] Starting backend at http://%BACKEND_HOST%:%BACKEND_PORT%
echo [goodnews] Reload is disabled because Playwright does not work reliably
echo [goodnews] under uvicorn --reload on Windows. Restart this window after edits.
.venv\Scripts\uvicorn.exe app.main:app --host %BACKEND_HOST% --port %BACKEND_PORT%
endlocal
