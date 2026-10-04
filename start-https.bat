@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-https.ps1"
set "SCRIPT_EXIT=%ERRORLEVEL%"
echo.
if not "%SCRIPT_EXIT%"=="0" echo HTTPS startup failed. Check the PowerShell messages above.
pause
exit /b %SCRIPT_EXIT%
