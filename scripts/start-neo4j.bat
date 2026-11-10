@echo off
setlocal
cd /d "%~dp0.."
echo [goodnews] Starting Neo4j (existing PostgreSQL and Redis are left untouched)...
docker compose up -d
if errorlevel 1 (
  echo [goodnews] Neo4j failed to start. Is Docker Desktop running?
  pause
  exit /b 1
)
docker compose ps
endlocal
