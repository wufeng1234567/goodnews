@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "TARGET=%~dp0start-all.bat"
set "ICON=%ROOT%\assets\goodnews.ico"

if not exist "%TARGET%" (
  echo [ERROR] start-all.bat was not found.
  pause
  exit /b 1
)
if not exist "%ICON%" (
  echo [WARN] Icon not found. The shortcut will use the default icon.
  set "ICON=%SystemRoot%\System32\shell32.dll"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop=[Environment]::GetFolderPath('Desktop'); $shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut((Join-Path $desktop 'goodnews - Start.lnk')); $shortcut.TargetPath='%TARGET%'; $shortcut.WorkingDirectory='%ROOT%'; $shortcut.IconLocation='%ICON%,0'; $shortcut.Description='Start goodnews local services (Neo4j + API + Web UI)'; $shortcut.WindowStyle=1; $shortcut.Save()"
if errorlevel 1 (
  echo [ERROR] Could not create the desktop shortcut.
  pause
  exit /b 1
)
echo [OK] Desktop shortcut created: goodnews - Start
echo      Target: %TARGET%
endlocal
