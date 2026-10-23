@echo off
setlocal
rem ============================================================================
rem  Yeal - Windows EXE build (PyInstaller --onefile) + versioned release copy
rem  Uses the central Python of Tools_Central (never modified). Runs only on
rem  explicit invocation.
rem ============================================================================
cd /d "%~dp0"
set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
set /p VER=<"%PROJECT%\VERSION"

echo [1/3] Building single-file EXE for Yeal v%VER% ...
call "%PROJECT%\Build_Yeal_Exe.bat"
if not exist "%PROJECT%\dist\Yeal.exe" ( echo dist\Yeal.exe missing & pause & exit /b 1 )

echo [2/3] Archiving ...
set "ARCH=%PROJECT%\BIN\releases"
if not exist "%ARCH%" mkdir "%ARCH%"
copy /y "%PROJECT%\dist\Yeal.exe" "%ARCH%\Yeal-v%VER%.exe" >nul
powershell -NoProfile -Command "(Get-FileHash '%ARCH%\Yeal-v%VER%.exe' -Algorithm SHA256).Hash.ToLower() + '  Yeal-v%VER%.exe' | Set-Content -Encoding ascii '%ARCH%\Yeal-v%VER%.exe.sha256'"

if exist "%PROJECT%\dist\bin" (
  set "ZIP=%ARCH%\Yeal-v%VER%-portable.zip"
  if exist "%ZIP%" del "%ZIP%"
  powershell -NoProfile -Command "Compress-Archive -Path '%PROJECT%\dist\Yeal.exe','%PROJECT%\dist\bin' -DestinationPath '%ZIP%'"
  echo   Portable ZIP: %ZIP%
)
echo [3/3] Done.
echo   EXE : %PROJECT%\dist\Yeal.exe
echo   Copy: %ARCH%\Yeal-v%VER%.exe
pause
exit /b 0
