@echo off
rem Usage: test-alert.bat [true_positive ^| false_positive ^| invalid_payload]
setlocal
cd /d "%~dp0.."
set PAYLOAD=%1
if "%PAYLOAD%"=="" set PAYLOAD=true_positive
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0test-alert.ps1" -Payload %PAYLOAD%
pause
