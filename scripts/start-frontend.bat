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

cd /d "frontend"
if not exist "node_modules" (
  echo [goodnews] Installing frontend dependencies...
  call npm install
  if errorlevel 1 (
    echo [goodnews] npm install failed.
    pause
    exit /b 1
  )
)
set "GOODNEWS_API_TARGET=http://%BACKEND_HOST%:%BACKEND_PORT%"
echo [goodnews] Starting frontend at http://127.0.0.1:5173
echo [goodnews] Vite API proxy -> %GOODNEWS_API_TARGET%
call npm run dev -- --host 127.0.0.1
endlocal
