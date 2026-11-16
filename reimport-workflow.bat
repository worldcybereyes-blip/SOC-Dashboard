@echo off
rem Overwrites the installed workflow with workflow\soc_playbook.json (Docker setup).
setlocal
cd /d "%~dp0.."
docker compose exec -T n8n n8n import:workflow --input=/import/soc_playbook.json
docker compose exec -T n8n n8n publish:workflow --id=socPlaybook0001
docker compose restart n8n >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wait-for-n8n.ps1"
echo Workflow re-imported and published.
pause
