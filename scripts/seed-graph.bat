@echo off
setlocal
cd /d "%~dp0..\backend"
if not exist ".venv\Scripts\python.exe" (
  echo [goodnews] Backend virtual environment not found.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m scripts.seed_graph
if errorlevel 1 (
  echo [goodnews] Graph seed failed. Is Neo4j running?
  pause
  exit /b 1
)
endlocal
