@echo off
rem Windows build: ONE small portable file  ->  dist\Yeal.exe   (PyInstaller, see Yeal.spec)
rem   Build_Yeal_Exe.bat          slim exe; ffmpeg.exe + node.exe are copied to dist\bin\ (the exe finds them there)
rem   Build_Yeal_Exe.bat embed    ffmpeg + node packed INSIDE the exe (about 100 MB bigger, one single file)
rem Only the Qt/Python parts the app really uses are packed (see Yeal.spec).
rem Run only dist\Yeal.exe - the folder "build\" holds intermediate files that do not start.
setlocal
cd /d "%~dp0"
call "%~dp0_find_python.bat" || (pause & exit /b 1)
set "TC=%~dp0..\Tools_Central"
if not exist "%TC%" set "TC=C:\Users\mail\AI_Coworker_Claude\Tools_Central"
set "TOOLS_CENTRAL=%TC%"
set "YEAL_EMBED_TOOLS="
if /i "%~1"=="embed" set "YEAL_EMBED_TOOLS=1"

if exist "%~dp0build" rmdir /s /q "%~dp0build"
if exist "%~dp0dist" rmdir /s /q "%~dp0dist"
"%YEAL_PY%" -m PyInstaller --noconfirm --clean "%~dp0Yeal.spec"
if errorlevel 1 ( echo Build failed. & pause & exit /b 1 )

if not defined YEAL_EMBED_TOOLS (
  if not exist "%~dp0dist\bin" mkdir "%~dp0dist\bin"
  if exist "%TC%\Video Tools\FFMPEG\bin\ffmpeg.exe" ( copy /y "%TC%\Video Tools\FFMPEG\bin\ffmpeg.exe" "%~dp0dist\bin\" >nul & echo ffmpeg copied to dist\bin ) else echo WARNING: ffmpeg.exe not found - merging/MP3/images will not work.
  if exist "%TC%\Dependencies\node\bin\node.exe" ( copy /y "%TC%\Dependencies\node\bin\node.exe" "%~dp0dist\bin\" >nul & echo node copied to dist\bin ) else echo WARNING: node.exe not found - YouTube downloads will not work.
)
for %%F in ("%~dp0dist\Yeal.exe") do echo.& echo Done: %%~fF  (%%~zF bytes)
pause
