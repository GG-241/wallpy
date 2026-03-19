@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: wallpy screensaver launcher  (Windows)
::
:: Usage:
::   screensaver.bat [options]
::
:: Options are passed through to screensaver.py:
::   -i, --idle-time SECONDS   Idle time before activating  (default: 300)
::   -m, --mode MODE           Art mode: matrix|stars|shapes|lissajous|life|web
::   -f, --fps  FPS            Frames per second            (default: 30)
::   -p, --preview             Launch immediately (no idle wait)
::       --list-modes          Show available art modes
::
:: Examples:
::   screensaver.bat                        :: random art after 5 min
::   screensaver.bat -i 60 -m matrix        :: matrix rain after 60 s
::   screensaver.bat --preview -m stars     :: preview starfield now
:: ─────────────────────────────────────────────────────────────────────────────

setlocal

set "SCRIPT_DIR=%~dp0"
set "PY_SCRIPT=%SCRIPT_DIR%screensaver.py"

:: ── Locate Python ─────────────────────────────────────────────────────────────
set "PYTHON="
for %%P in (python python3 py) do (
    if not defined PYTHON (
        where %%P >nul 2>&1 && set "PYTHON=%%P"
    )
)

if not defined PYTHON (
    echo [wallpy] ERROR: Python 3.7+ not found.
    echo.
    echo   Download from https://www.python.org/downloads/
    echo   Make sure to tick "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: ── Check Python version ──────────────────────────────────────────────────────
%PYTHON% -c "import sys; sys.exit(0 if sys.version_info>=(3,7) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [wallpy] ERROR: Python 3.7 or newer is required.
    pause
    exit /b 1
)

:: ── Check tkinter ─────────────────────────────────────────────────────────────
%PYTHON% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [wallpy] ERROR: tkinter is not available.
    echo.
    echo   Reinstall Python from https://www.python.org/downloads/
    echo   During installation choose "Modify" and ensure "tcl/tk and IDLE" is checked.
    pause
    exit /b 1
)

:: ── Run ───────────────────────────────────────────────────────────────────────
echo [wallpy] Using %PYTHON%
%PYTHON% "%PY_SCRIPT%" %*
