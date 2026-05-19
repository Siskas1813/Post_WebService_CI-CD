param(
    [int]$Port = 5000,
    [string]$TargetForDocker = "http://host.docker.internal:5000"
)

$ErrorActionPreference = "Stop"

.\scripts\start_app.ps1 -Port $Port
.\scripts\run_zap_baseline.ps1 -Target $TargetForDocker
.\scripts\run_zap_full.ps1 -Target $TargetForDocker
.\scripts\run_zap_auth.ps1 -Target $TargetForDocker
.\.venv\Scripts\python.exe scripts\dast_summary.py

Write-Host "DAST checks completed. Reports are in reports\dast"
