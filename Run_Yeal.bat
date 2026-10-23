@echo off
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
"%YEAL_PY%" "BIN\versions\v0.1\PyModul\main.py"
if errorlevel 1 pause
