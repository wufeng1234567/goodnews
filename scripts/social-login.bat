@echo off
setlocal EnableExtensions
cd /d "%~dp0..\backend"

set "PLATFORM=%~1"
if "%PLATFORM%"=="" (
  echo Usage: social-login.bat xiaohongshu^|douyin^|bilibili
  set /p PLATFORM=Platform:
)

if /I not "%PLATFORM%"=="xiaohongshu" if /I not "%PLATFORM%"=="douyin" if /I not "%PLATFORM%"=="bilibili" (
  echo [ERROR] Unsupported platform: %PLATFORM%
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Backend virtual environment not found.
  pause
  exit /b 1
)

echo [goodnews] Login helper will open Edge. Scan the QR code, then return here.
set "SOCIAL_BROWSER_HEADLESS=false"
.venv\Scripts\python.exe scripts\social_login.py %PLATFORM%
if errorlevel 1 (
  echo [ERROR] Login state was not saved.
) else (
  echo [OK] Login state saved. You can retry the social fetch.
)
pause
endlocal
