@echo off
rem Test start: embedded YouTube view without GPU acceleration (diagnoses a blank/white browser pane).
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
set "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--disable-gpu --disable-gpu-compositing"
"%YEAL_PY%" "BIN\versions\v0.1\PyModul\main.py"
if errorlevel 1 pause
