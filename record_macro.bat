@echo off
REM Windows batch file for easy macro recording
REM Usage: record_macro.bat "Macro Name" "Optional Description"

if "%~1"=="" (
    echo Usage: record_macro.bat "Macro Name" "Optional Description"
    echo Example: record_macro.bat "Login Workflow" "Login to the website"
    pause
    exit /b 1
)

if "%~2"=="" (
    python record_macro.py --name "%~1"
) else (
    python record_macro.py --name "%~1" --description "%~2"
)

pause 