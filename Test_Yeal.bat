@echo off
setlocal
cd /d "%~dp0tests"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
set QT_QPA_PLATFORM=offscreen
set QT_QUICK_BACKEND=software
"%YEAL_PY%" -m unittest discover -v
echo.
pause
