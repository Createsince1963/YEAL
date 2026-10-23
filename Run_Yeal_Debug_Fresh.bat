@echo off
rem Self test with a FRESH browser profile (YouTube starts light -> exercises the light-to-dark switch).
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
if not exist "%APPDATA%\Yeal" mkdir "%APPDATA%\Yeal"
set "WEBVIEW2_USER_DATA_FOLDER=%TEMP%\yeal_wv2_selftest"
if exist "%WEBVIEW2_USER_DATA_FOLDER%" rmdir /s /q "%WEBVIEW2_USER_DATA_FOLDER%"
set "LOG=%APPDATA%\Yeal\debug_fresh.log"
set "QT_LOGGING_RULES=qt.webview*=true"
set "PYTHONUNBUFFERED=1"
"%YEAL_PY%" -u "%~dp0_debug_run.py" > "%LOG%" 2>&1
echo exit code %errorlevel% >> "%LOG%"
