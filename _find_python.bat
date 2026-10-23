@echo off
rem Sets YEAL_PY to the central WinPython of Tools_Central. Override with CENTRAL_PYTHON.
set "YEAL_PY="
if defined CENTRAL_PYTHON if exist "%CENTRAL_PYTHON%" set "YEAL_PY=%CENTRAL_PYTHON%"
if not defined YEAL_PY if exist "%~dp0..\Tools_Central\Python\python\python.exe" set "YEAL_PY=%~dp0..\Tools_Central\Python\python\python.exe"
if not defined YEAL_PY if exist "C:\Users\mail\AI_Coworker_Claude\Tools_Central\Python\python\python.exe" set "YEAL_PY=C:\Users\mail\AI_Coworker_Claude\Tools_Central\Python\python\python.exe"
if not defined YEAL_PY (
  echo Central Python not found. Set CENTRAL_PYTHON to Tools_Central\Python\python\python.exe
  exit /b 1
)
exit /b 0
