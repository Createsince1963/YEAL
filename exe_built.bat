@echo off
setlocal
rem ============================================================================
rem  Yeal - Windows EXE build (launcher + bin runtime) + versioned portable ZIP
rem  Uses the central Python of Tools_Central (never modified). Runs only on
rem  explicit invocation.
rem ============================================================================
cd /d "%~dp0"
set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
set /p VER=<"%PROJECT%\VERSION"

echo [1/3] Building portable EXE folder for Yeal v%VER% ...
call "%PROJECT%\Build_Yeal_Exe.bat"
if not exist "%PROJECT%\dist\Yeal.exe" ( echo dist\Yeal.exe missing & pause & exit /b 1 )

echo [2/3] Archiving ...
set "ARCH=%PROJECT%\BIN\releases"
if not exist "%ARCH%" mkdir "%ARCH%"
set "ZIP=%ARCH%\Yeal-v%VER%-portable.zip"
if exist "%ZIP%" del "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path '%PROJECT%\dist\*' -DestinationPath '%ZIP%'"
powershell -NoProfile -Command "(Get-FileHash '%ZIP%' -Algorithm SHA256).Hash.ToLower() + '  Yeal-v%VER%-portable.zip' | Set-Content -Encoding ascii '%ZIP%.sha256'"
echo [3/3] Done.
echo   EXE : %PROJECT%\dist\Yeal.exe
echo   ZIP : %ZIP%
pause
exit /b 0
