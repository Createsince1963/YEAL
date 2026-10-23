@echo off
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
if not exist "%APPDATA%\Yeal" mkdir "%APPDATA%\Yeal"
set "LOG=%APPDATA%\Yeal\debug.log"
set "QT_LOGGING_RULES=qt.webview*=true"
set "PYTHONUNBUFFERED=1"
echo Yeal debug run - log: %LOG%
"%YEAL_PY%" -u "%~dp0_debug_run.py" > "%LOG%" 2>&1
echo exit code %errorlevel% >> "%LOG%"
