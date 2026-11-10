@echo off
setlocal
cd /d "%~dp0.."
echo [goodnews] Ensuring Neo4j is running...
docker compose up -d
if errorlevel 1 (
  echo [goodnews] Could not start Neo4j. Check Docker Desktop.
  pause
  exit /b 1
)
start "goodnews backend" cmd /k "%~dp0start-backend.bat"
start "goodnews frontend" cmd /k "%~dp0start-frontend.bat"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo [goodnews] Backend and frontend windows were started.
echo [goodnews] API docs: http://127.0.0.1:8000/docs
endlocal
