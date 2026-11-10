@echo off
setlocal
cd /d "%~dp0.."
if not exist "backend\.venv\Scripts\uvicorn.exe" (
  echo [goodnews] Backend virtual environment not found.
  echo [goodnews] Create it with: D:\Python3.11\python.exe -m venv backend\.venv
  echo [goodnews] Then run: backend\.venv\Scripts\python -m pip install -e "backend[dev]"
  pause
  exit /b 1
)
call "backend\.venv\Scripts\activate.bat"
cd /d "backend"
echo [goodnews] Starting backend at http://127.0.0.1:8000
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
endlocal
