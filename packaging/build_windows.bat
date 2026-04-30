@echo off
setlocal enabledelayedexpansion
echo === wallpy Windows EXE + installer builder ===

cd /d "%~dp0.."

REM Install PyInstaller
pip install --quiet pyinstaller
if %ERRORLEVEL% neq 0 (
    echo ERROR: pip install pyinstaller failed
    exit /b 1
)

REM Build standalone .exe
echo Building wallpy.exe...
pyinstaller --clean packaging\windows\wallpy.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller failed
    exit /b 1
)
echo Built: dist\wallpy.exe

REM Compile Inno Setup installer if ISCC is available
where ISCC >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Compiling installer...
    ISCC packaging\windows\installer.iss
    if %ERRORLEVEL% equ 0 (
        echo Built: dist\wallpy-setup-1.0.0.exe
    ) else (
        echo WARNING: Inno Setup compilation failed
    )
) else (
    echo.
    echo Inno Setup not found. To create the installer:
    echo   1. Download Inno Setup from https://jrsoftware.org/isdl.php
    echo   2. Run: ISCC packaging\windows\installer.iss
    echo   3. Installer will be at dist\wallpy-setup-1.0.0.exe
)

echo.
echo === Done! ===
