@echo off
setlocal EnableExtensions
title goodnews - launcher
cd /d "%~dp0.."

set "OPEN_BROWSER=1"
if /I "%~1"=="--no-browser" set "OPEN_BROWSER=0"
set "HEALTH_URL=http://127.0.0.1:8000/api/v1/health"
set "WEB_URL=http://127.0.0.1:5173"

echo ==================================================
echo   goodnews - local development launcher
echo ==================================================
echo.

where docker >nul 2>&1
if errorlevel 1 goto no_docker

docker info >nul 2>&1
if errorlevel 1 (
  echo [1/4] Docker is not running. Starting Docker Desktop...
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    call :wait_for_docker
    if errorlevel 1 goto docker_failed
  ) else (
    goto docker_failed
  )
)

echo [1/4] Starting Neo4j...
docker compose up -d
if errorlevel 1 goto docker_failed
call :wait_for_neo4j
if errorlevel 1 (
  echo [WARN] Neo4j is not healthy yet. Backend may start in degraded mode.
) else (
  echo [OK] Neo4j is healthy.
)
echo.

echo [2/4] Checking backend...
call :http_code "%HEALTH_URL%"
if "%HTTP_CODE%"=="200" (
  echo [OK] Backend is already running.
  goto backend_ready
)
echo [..] Starting backend window...
start "goodnews backend" cmd /k "%~dp0start-backend.bat"
call :wait_for_http "%HEALTH_URL%" 90
if errorlevel 1 (
  echo [WARN] Backend did not answer within 90 seconds.
  echo        Check the "goodnews backend" window for details.
) else (
  echo [OK] Backend is ready.
)
:backend_ready
echo.

echo [3/4] Checking frontend...
call :http_code "%WEB_URL%"
if "%HTTP_CODE%"=="200" (
  echo [OK] Frontend is already running.
  goto frontend_ready
)
echo [..] Starting frontend window...
start "goodnews frontend" cmd /k "%~dp0start-frontend.bat"
call :wait_for_http "%WEB_URL%" 120
if errorlevel 1 (
  echo [WARN] Frontend did not answer within 120 seconds.
  echo        Check the "goodnews frontend" window for details.
) else (
  echo [OK] Frontend is ready.
)
:frontend_ready
echo.

echo [4/4] Opening goodnews...
if "%OPEN_BROWSER%"=="1" start "" "%WEB_URL%"
echo [DONE] goodnews is ready.
echo        Web UI:   %WEB_URL%
echo        API docs: http://127.0.0.1:8000/docs
echo.
echo You can close this launcher. Backend/frontend windows keep running.
ping 127.0.0.1 -n 6 >nul
endlocal
exit /b 0

:no_docker
echo [ERROR] Docker was not found. Install Docker Desktop or add docker to PATH.
pause
exit /b 1

:docker_failed
echo [ERROR] Docker Desktop could not be started or Docker is unavailable.
echo         Start Docker Desktop manually, then run this launcher again.
pause
exit /b 1

:wait_for_docker
set /a DOCKER_TRIES=0
:wait_for_docker_loop
docker info >nul 2>&1
if not errorlevel 1 exit /b 0
set /a DOCKER_TRIES+=1
if %DOCKER_TRIES% GEQ 60 exit /b 1
ping 127.0.0.1 -n 3 >nul
goto wait_for_docker_loop

:wait_for_neo4j
set /a NEO_TRIES=0
:wait_for_neo4j_loop
set "NEO_STATUS=unknown"
for /f "delims=" %%S in ('docker inspect -f "{{.State.Health.Status}}" goodnews-neo4j 2^>nul') do set "NEO_STATUS=%%S"
if /I "%NEO_STATUS%"=="healthy" exit /b 0
set /a NEO_TRIES+=1
if %NEO_TRIES% GEQ 45 exit /b 1
ping 127.0.0.1 -n 3 >nul
goto wait_for_neo4j_loop

:wait_for_http
set /a HTTP_TRIES=0
:wait_for_http_loop
call :http_code "%~1"
if "%HTTP_CODE%"=="200" exit /b 0
set /a HTTP_TRIES+=1
if %HTTP_TRIES% GEQ %~2 exit /b 1
ping 127.0.0.1 -n 2 >nul
goto wait_for_http_loop

:http_code
set "HTTP_CODE=000"
for /f "delims=" %%C in ('curl.exe -s -o NUL -w "%%{http_code}" "%~1" 2^>nul') do set "HTTP_CODE=%%C"
exit /b 0
