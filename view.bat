@echo off
REM TikTok Account Downloader Viewer - Start Script
REM Runs the FastAPI application on 0.0.0.0:8080

cd /d "%~dp0"

set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PY_CMD=py"

if not defined PY_CMD (
	where python >nul 2>nul
	if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
	set "PY_CMD=python"
)

REM Install dependencies if needed
echo Installing dependencies...
"%PY_CMD%" -m pip install fastapi uvicorn -q

REM Start the server
echo.
echo Starting TikTok Account Downloader Viewer...
echo Server will be available at: http://localhost:8080
echo.
"%PY_CMD%" -m uvicorn viewer:app --host 0.0.0.0 --port 8080 --reload

pause
