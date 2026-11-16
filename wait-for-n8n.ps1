# Waits until n8n answers /healthz AND the workflow webhook is registered (max ~3 minutes).
param([string]$Url = 'http://localhost:5678')
for ($i = 0; $i -lt 90; $i++) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "$Url/healthz" -TimeoutSec 3
        if ($r.StatusCode -eq 200) { Start-Sleep -Seconds 3; exit 0 }
    } catch { Start-Sleep -Seconds 2 }
}
exit 1
