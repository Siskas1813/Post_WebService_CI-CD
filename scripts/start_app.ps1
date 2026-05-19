param(
    [int]$Port = 5000
)

$ErrorActionPreference = "Stop"

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$logDir = "reports\dast"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$env:FLASK_RUN_PORT = "$Port"

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Port $Port is already in use. Application may already be running."
    return
}

Write-Host "Starting Flask application on port $Port..."
Start-Process `
    -FilePath $python `
    -ArgumentList "app.py" `
    -WorkingDirectory (Get-Location) `
    -RedirectStandardOutput (Join-Path $logDir "flask.out.log") `
    -RedirectStandardError (Join-Path $logDir "flask.err.log") `
    -WindowStyle Hidden

Start-Sleep -Seconds 3

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 10
    Write-Host "Application is available: http://127.0.0.1:$Port"
    Write-Host "HTTP status: $($response.StatusCode)"
} catch {
    Write-Host "Application did not respond yet. Check reports\dast\flask.err.log"
    throw
}
