@echo off
rem Windows build: small launcher + runtime DLLs -> dist\Yeal.exe + dist\bin\ (PyInstaller, see Yeal.spec)
rem   Build_Yeal_Exe.bat          default; ffmpeg.exe + node.exe are copied to dist\bin\
rem   Build_Yeal_Exe.bat embed    also places ffmpeg + node in dist\bin via PyInstaller
rem   Build_Yeal_Exe.bat slim     like the default but without Qt's bundled FFmpeg (about 8 MB smaller; the video
rem                               preview of the frame extractor then uses the Windows media backend)
rem Only the Qt/Python parts the app really uses are packed (see Yeal.spec).
rem Run only dist\Yeal.exe. Keep dist\bin beside it; the launcher does not run without that folder.
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
set "TC=%~dp0..\Tools_Central"
if not exist "%TC%" set "TC=C:\Users\mail\AI_Coworker_Claude\Tools_Central"
set "TOOLS_CENTRAL=%TC%"
set "YEAL_EMBED_TOOLS="
set "YEAL_SLIM_MEDIA="
if /i "%~1"=="embed" set "YEAL_EMBED_TOOLS=1"
if /i "%~1"=="slim" set "YEAL_SLIM_MEDIA=1"

rem Build beside the last working output. Never delete dist up front: an open Yeal.exe would leave
rem a half-deleted folder without bin\ffmpeg.exe and bin\node.exe.
set "STAGE_BUILD=%~dp0build-next"
set "STAGE_DIST=%~dp0dist-next"
set "TIDDL_PATH=%~dp0.test-tmp\tiddl-build"
if not exist "%TIDDL_PATH%" mkdir "%TIDDL_PATH%"
if exist "%STAGE_BUILD%" rmdir /s /q "%STAGE_BUILD%"
if exist "%STAGE_DIST%" rmdir /s /q "%STAGE_DIST%"
"%YEAL_PY%" -m PyInstaller --noconfirm --clean --workpath "%STAGE_BUILD%" --distpath "%STAGE_DIST%" "%~dp0Yeal.spec"
if errorlevel 1 ( echo Build failed. & pause & exit /b 1 )
set "STAGE_APP=%STAGE_DIST%\Yeal"
if not exist "%STAGE_APP%\Yeal.exe" ( echo Build failed: staged Yeal.exe missing. & pause & exit /b 1 )

if not defined YEAL_EMBED_TOOLS (
  if not exist "%STAGE_APP%\bin" mkdir "%STAGE_APP%\bin"
  if exist "%TC%\Video Tools\FFMPEG\bin\ffmpeg.exe" ( copy /y "%TC%\Video Tools\FFMPEG\bin\ffmpeg.exe" "%STAGE_APP%\bin\" >nul & echo ffmpeg staged ) else echo WARNING: ffmpeg.exe not found - merging/MP3/images will not work.
  if exist "%TC%\Dependencies\node\bin\node.exe" ( copy /y "%TC%\Dependencies\node\bin\node.exe" "%STAGE_APP%\bin\" >nul & echo node staged ) else echo WARNING: node.exe not found - YouTube downloads will not work.
)
set "OLD_DIST=%~dp0dist-old"
if exist "%OLD_DIST%" rmdir /s /q "%OLD_DIST%"
if exist "%~dp0dist" move "%~dp0dist" "%OLD_DIST%" >nul
if errorlevel 1 (
  echo The new build is ready in "%STAGE_APP%", but the existing dist folder is in use.
  echo Close Yeal and run this build again. The existing dist folder was not changed.
  pause & exit /b 1
)
move "%STAGE_APP%" "%~dp0dist" >nul
if errorlevel 1 (
  if exist "%OLD_DIST%" move "%OLD_DIST%" "%~dp0dist" >nul
  echo Could not activate the staged build. The previous dist folder was restored.
  pause & exit /b 1
)
if exist "%OLD_DIST%" rmdir /s /q "%OLD_DIST%"
for %%F in ("%~dp0dist\Yeal.exe") do echo.& echo Done: %%~fF  (%%~zF bytes)
pause
