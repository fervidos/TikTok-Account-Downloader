@echo off
setlocal EnableExtensions EnableDelayedExpansion


:: Locate repo/app folder (supports running from inside or next to it)
set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%TikTokScanner-main"

:: If we're inside the repo already, use current folder
if exist "%SCRIPT_DIR%src\main.py" (
  set "APP_DIR=%SCRIPT_DIR%"
)

:: Verify entry point exists
if not exist "%APP_DIR%\src\main.py" (
  echo ERROR: Could not find src\main.py.
  echo Put this batch file next to the TikTokScanner-main folder, or inside the TikTokScanner-main folder.
  pause
  exit /b 1
)

:: Prefer bundled venv python if available
set "PYTHON_EXE=python"
if exist "%APP_DIR%\venv\Scripts\python.exe" (
  set "PYTHON_EXE=%APP_DIR%\venv\Scripts\python.exe"
)

:: Load optional .env file (supports MONGO_URI, etc.)
if exist "%APP_DIR%\.env" (
  for /f "usebackq tokens=1* delims== eol=#" %%A in ("%APP_DIR%\.env") do (
    if not defined %%A (
      set "%%A=%%B"
      rem strip any surrounding quotes (e.g. MONGO_URI="...")
      set "%%A=!%%A:"=!"
    )
  )
)

:: Print usage/help
goto parse_args
:usage

echo.
echo Usage: %~n0 [URL^|@username] [--concurrent N] [--headless] [--no-headless] [--force-full-scan] [--no-full-scan] [--cookies-file PATH] [--mongo-uri URI]
echo.
echo If no arguments are provided, this script will prompt for values.
echo.
echo This script will load an optional .env file from the repo root (if present).
echo You can set MONGO_URI via .env or environment variable to enable database tracking.
echo.
exit /b 0

:: Parse CLI args
if "%~1"=="-h" goto usage
if "%~1"=="--help" goto usage

set "ARG_URL="
set "ARG_CONCURRENT="
set "ARG_HEADLESS="
set "ARG_FULLSCAN="
set "ARG_COOKIES_FILE="
set "ARG_MONGO_URI="

:parse_args
if "%~1"=="" goto args_parsed

if /i "%~1"=="--headless" (
  set "ARG_HEADLESS=1"
  shift
  goto parse_args
)
if /i "%~1"=="--no-headless" (
  set "ARG_HEADLESS=0"
  shift
  goto parse_args
)
if /i "%~1"=="--force-full-scan" (
  set "ARG_FULLSCAN=1"
  shift
  goto parse_args
)
if /i "%~1"=="--no-full-scan" (
  set "ARG_FULLSCAN=0"
  shift
  goto parse_args
)
if /i "%~1"=="--concurrent" (
  shift
  if "%~1"=="" goto parse_args
  set "ARG_CONCURRENT=%~1"
  shift
  goto parse_args
)
if /i "%~1"=="--cookies-file" (
  shift
  if "%~1"=="" goto parse_args
  set "ARG_COOKIES_FILE=%~1"
  shift
  goto parse_args
)
if /i "%~1"=="--mongo-uri" (
  shift
  if "%~1"=="" goto parse_args
  set "ARG_MONGO_URI=%~1"
  shift
  goto parse_args
)
if "%ARG_URL%"=="" (
  set "ARG_URL=%~1"
) else (
  echo WARNING: Ignoring extra argument: %~1
)
shift
goto parse_args

:args_parsed

:: Prompt for missing values (only URL is required)
:prompt_for_url
if "%ARG_URL%"=="" (
  set /p "ARG_URL=Enter TikTok Profile URL (or @username): "
  if "%ARG_URL%"=="" goto prompt_for_url
)

:: Default settings (no prompting)
if "%ARG_CONCURRENT%"=="" set "ARG_CONCURRENT=3"
if "%ARG_HEADLESS%"=="" set "ARG_HEADLESS=1"
:: Always default to full scan unless explicitly disabled
if "%ARG_FULLSCAN%"=="" set "ARG_FULLSCAN=1"

:: Validate concurrent (must be positive integer)
echo %ARG_CONCURRENT%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 set "ARG_CONCURRENT=3"
if %ARG_CONCURRENT% LSS 1 set "ARG_CONCURRENT=1"

:: Default cookies path
if "%ARG_COOKIES_FILE%"=="" if exist "%APP_DIR%\src\cookies.txt" (
  set "ARG_COOKIES_FILE=%APP_DIR%\src\cookies.txt"
)

:: Default mongo uri from environment (optional)
if "%ARG_MONGO_URI%"=="" if defined MONGO_URI (
  set "ARG_MONGO_URI=%MONGO_URI%"
)

:: Build flags
set "HEADLESS_FLAG="
if "%ARG_HEADLESS%"=="1" set "HEADLESS_FLAG=--headless"

set "FULLSCAN_FLAG="
if "%ARG_FULLSCAN%"=="1" set "FULLSCAN_FLAG=--force-full-scan"

:: Run
echo Running from: "%APP_DIR%"
pushd "%APP_DIR%"

:: Run (quote paths/args to preserve spaces)
set CMD=%PYTHON_EXE% src\main.py "%ARG_URL%" %HEADLESS_FLAG% %FULLSCAN_FLAG% -c %ARG_CONCURRENT%
if not "%ARG_COOKIES_FILE%"=="" set CMD=%CMD% --cookies-file "%ARG_COOKIES_FILE%"
if not "%ARG_MONGO_URI%"=="" set CMD=%CMD% --mongo-uri "%ARG_MONGO_URI%"

REM echo %CMD%
%CMD%

popd

pause
