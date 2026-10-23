@echo off
setlocal EnableExtensions
rem ============================================================================
rem  Yeal - Android APK build (cloud track: pyside6-android-deploy on GitHub
rem  Actions). Per Tools_Central APK_BUILD_STANDARD: run ONLY on explicit user
rem  request. Steps: security gate -> commit/push -> workflow -> download ->
rem  archive as Yeal-v<ver>.apk + Yeal.apk (+ .sha256, .info.txt).
rem  Usage: apk_built.bat ["commit message"]
rem  One-time setup: see docs\ANDROID.md (git init, GitHub remote, gh auth login)
rem ============================================================================
set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
set "TOOLS=C:\Users\mail\AI_Coworker_Claude\Tools_Central"
set "SEC=%TOOLS%\SDK\Android APK\Scripts\Test-ApkSecurity.ps1"
set "ARTIFACT=yeal-apk"
set "WF=build-apk.yml"
set /p VER=<"%PROJECT%\VERSION"
set "MSG=%~1"
if "%MSG%"=="" set "MSG=Yeal v%VER% cloud APK build"
cd /d "%PROJECT%"

where gh >nul 2>&1 || ( echo [ERROR] GitHub CLI "gh" not found. & goto :fail )
where git >nul 2>&1 || ( echo [ERROR] git not found. & goto :fail )
if not exist "%SEC%" ( echo [ERROR] Security script missing: %SEC% & goto :fail )

echo [1/6] Security gate ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SEC%" -ProjectPath "%PROJECT%" -AndroidDir . -BuildType debug
if errorlevel 1 ( echo [ERROR] Security gate failed. & set "RC=3" & goto :end )

echo [2/6] Checking workflow and repository ...
if not exist "%PROJECT%\.github\workflows\%WF%" (
  if exist "%PROJECT%\ci\build-apk.yml" (
    if not exist "%PROJECT%\.github\workflows" mkdir "%PROJECT%\.github\workflows"
    copy /y "%PROJECT%\ci\build-apk.yml" "%PROJECT%\.github\workflows\%WF%" >nul
    echo   Workflow copied from ci\build-apk.yml
  ) else ( echo [ERROR] No workflow found. & goto :fail )
)
if not exist "%PROJECT%\.git" (
  echo [ERROR] Not a git repository. Run once:
  echo   powershell -File "%TOOLS%\pyside6-android-deploy\Setup-CloudBuild.ps1" -ProjectPath "%PROJECT%"
  goto :fail
)
gh auth status >nul 2>&1 || ( echo [ERROR] Run "gh auth login" first. & goto :fail )

echo [3/6] Commit and push ...
git add -A
git commit -m "%MSG%" >nul 2>&1
git push origin main || ( echo [ERROR] git push failed. & goto :fail )

echo [4/6] Starting cloud build ...
gh workflow run %WF% || ( echo [ERROR] Could not start workflow. & goto :fail )
timeout /t 10 /nobreak >nul
for /f %%i in ('gh run list --workflow %WF% --limit 1 --json databaseId --jq ".[0].databaseId"') do set "RUNID=%%i"
if not defined RUNID ( echo [ERROR] Run id not found. & goto :fail )
gh run watch %RUNID% --exit-status || ( echo [ERROR] Cloud build failed. Run: gh run view %RUNID% --log-failed & goto :fail )

echo [5/6] Downloading APK ...
set "TMP_DL=%TEMP%\yeal-apk-%RUNID%"
if exist "%TMP_DL%" rmdir /s /q "%TMP_DL%"
gh run download %RUNID% --name %ARTIFACT% --dir "%TMP_DL%" || goto :fail
set "APK="
for /r "%TMP_DL%" %%f in (*.apk) do if not defined APK set "APK=%%f"
if not defined APK ( echo [ERROR] No APK in artifact. & goto :fail )

echo [6/6] Archiving ...
set "OUT=%PROJECT%\BIN\versions\latest-cloud-build"
if not exist "%OUT%" mkdir "%OUT%"
copy /y "%APK%" "%OUT%\Yeal-v%VER%.apk" >nul
copy /y "%APK%" "%OUT%\Yeal.apk" >nul
powershell -NoProfile -Command "(Get-FileHash '%OUT%\Yeal-v%VER%.apk' -Algorithm SHA256).Hash.ToLower() + '  Yeal-v%VER%.apk' | Set-Content -Encoding ascii '%OUT%\Yeal-v%VER%.apk.sha256'"
(echo Yeal v%VER% - debug-signed test build ^(cloud, run %RUNID%^) & echo Built: %DATE% %TIME%) > "%OUT%\Yeal-v%VER%.info.txt"
echo.
echo SUCCESS: %OUT%\Yeal-v%VER%.apk
set "RC=0"
goto :end

:fail
set "RC=1"
:end
pause
exit /b %RC%
