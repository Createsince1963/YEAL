@echo off
rem Windows build: ONE small portable file  ->  dist\Yeal.exe   (PyInstaller, see Yeal.spec)
rem   Build_Yeal_Exe.bat          slim exe; ffmpeg.exe + node.exe are copied to dist\bin\ (the exe finds them there)
rem   Build_Yeal_Exe.bat embed    ffmpeg + node packed INSIDE the exe (about 100 MB bigger, one single file)
rem   Build_Yeal_Exe.bat slim     like the default but without Qt's bundled FFmpeg (about 8 MB smaller; the video
rem                               preview of the frame extractor then uses the Windows media backend)
rem Only the Qt/Python parts the app really uses are packed (see Yeal.spec).
rem Run only dist\Yeal.exe - the folder "build\" holds intermediate files that do not start.
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
if exist "%STAGE_BUILD%" rmdir /s /q "%STAGE_BUILD%"
if exist "%STAGE_DIST%" rmdir /s /q "%STAGE_DIST%"
"%YEAL_PY%" -m PyInstaller --noconfirm --clean --workpath "%STAGE_BUILD%" --distpath "%STAGE_DIST%" "%~dp0Yeal.spec"
if errorlevel 1 ( echo Build failed. & pause & exit /b 1 )

if not defined YEAL_EMBED_TOOLS (
  if not exist "%STAGE_DIST%\bin" mkdir "%STAGE_DIST%\bin"
  if exist "%TC%\Video Tools\FFMPEG\bin\ffmpeg.exe" ( copy /y "%TC%\Video Tools\FFMPEG\bin\ffmpeg.exe" "%STAGE_DIST%\bin\" >nul & echo ffmpeg staged ) else echo WARNING: ffmpeg.exe not found - merging/MP3/images will not work.
  if exist "%TC%\Dependencies\node\bin\node.exe" ( copy /y "%TC%\Dependencies\node\bin\node.exe" "%STAGE_DIST%\bin\" >nul & echo node staged ) else echo WARNING: node.exe not found - YouTube downloads will not work.
)
if not exist "%~dp0dist" mkdir "%~dp0dist"
copy /y "%STAGE_DIST%\Yeal.exe" "%~dp0dist\Yeal.exe" >nul
if errorlevel 1 (
  echo The new build is ready in "%STAGE_DIST%", but dist\Yeal.exe is open and could not be replaced.
  echo Close Yeal and copy the staged output, or run this build again. The existing dist folder was not changed.
  pause & exit /b 1
)
if not defined YEAL_EMBED_TOOLS (
  if not exist "%~dp0dist\bin" mkdir "%~dp0dist\bin"
  if exist "%STAGE_DIST%\bin\ffmpeg.exe" copy /y "%STAGE_DIST%\bin\ffmpeg.exe" "%~dp0dist\bin\" >nul
  if exist "%STAGE_DIST%\bin\node.exe" copy /y "%STAGE_DIST%\bin\node.exe" "%~dp0dist\bin\" >nul
)
for %%F in ("%~dp0dist\Yeal.exe") do echo.& echo Done: %%~fF  (%%~zF bytes)
pause
