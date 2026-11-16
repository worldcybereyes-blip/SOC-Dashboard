@echo off
taskkill /FI "WINDOWTITLE eq SOC n8n*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SOC Mock*" /T /F >nul 2>&1
echo Stopped n8n and the mock lab windows.
pause
