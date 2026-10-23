@echo off
rem Pushes the branch and all version tags (v0.8.11, v0.8.12, ...) to GitHub.
setlocal
cd /d "%~dp0"
git push origin main --tags
echo.
git ls-remote --tags origin
pause
