@echo off
setlocal
cd /d "%~dp0..\frontend"
if not exist "node_modules" (
  echo [goodnews] Installing frontend dependencies...
  call npm install
  if errorlevel 1 (
    echo [goodnews] npm install failed.
    pause
    exit /b 1
  )
)
echo [goodnews] Starting frontend at http://127.0.0.1:5173
call npm run dev -- --host 127.0.0.1
endlocal
