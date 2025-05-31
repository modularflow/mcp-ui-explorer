@echo off
REM Windows batch file for easy macro playback
REM Usage: play_macro.bat "macro_file.json" [speed]

if "%~1"=="" (
    echo Usage: play_macro.bat "macro_file.json" [speed]
    echo Example: play_macro.bat "macros/Login Workflow.json"
    echo Example: play_macro.bat "macros/Login Workflow.json" 2.0
    echo.
    echo Available macros:
    python play_macro.py --list
    pause
    exit /b 1
)

if "%~2"=="" (
    python play_macro.py --file "%~1"
) else (
    python play_macro.py --file "%~1" --speed %~2
)

pause 