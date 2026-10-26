@echo off
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
rem Audio performance and stability calibration of Yeal.
rem   Calibrate_Yeal.bat                 quick test (about 1 minute): smallest stable sound card buffer
rem   Calibrate_Yeal.bat --stress        plus song change / pause / seek stress and leak test (about 4 minutes)
rem   Calibrate_Yeal.bat --stress --minutes 10 --apply     long run, then save the values in the settings
rem   Calibrate_Yeal.bat --list          only the audio outputs and their formats
rem   Calibrate_Yeal.bat --device Kopf   test the output whose name contains "Kopf" (e.g. the Bluetooth headphones)
rem Close Yeal before using --apply. Results: %APPDATA%\Yeal\audio_profile.json and audio_report.json
set "PYTHONPATH=%~dp0BIN\versions\v0.1\PyModul"
set "ARGS=%*"
if "%ARGS%"=="" set "ARGS=--quick"
"%YEAL_PY%" -m yeal.ui.calibration %ARGS%
echo.
pause
