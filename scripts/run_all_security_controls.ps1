param(
    [switch]$IncludeDAST,
    [string]$ZapUsername = "employee",
    [string]$ZapPassword = $env:ZAP_AUTH_PASSWORD
)

$ErrorActionPreference = "Stop"

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

New-Item -ItemType Directory -Path "reports\pytest" -Force | Out-Null

Write-Host "Running pytest security tests..."
& $python -m pytest tests -q | Tee-Object -FilePath "reports\pytest\security-tests.txt"

Write-Host "Running SAST..."
.\scripts\run_sast.ps1

Write-Host "Running SCA..."
.\scripts\run_sca.ps1

Write-Host "Running secrets scanning..."
.\scripts\run_secrets.ps1

Write-Host "Running AuthZ tests..."
.\scripts\run_authz_tests.ps1

Write-Host "Running API tests..."
.\scripts\run_api_tests.ps1

Write-Host "Running attachment tests..."
.\scripts\run_attachment_tests.ps1

Write-Host "Running config/header tests..."
.\scripts\run_config_headers_tests.ps1

Write-Host "Running security regression tests..."
.\scripts\run_security_regression_tests.ps1

if ($IncludeDAST) {
    if ([string]::IsNullOrWhiteSpace($ZapPassword)) {
        throw "Set ZAP_AUTH_PASSWORD or pass -ZapPassword when using -IncludeDAST."
    }
    $env:ZAP_AUTH_USERNAME = $ZapUsername
    $env:ZAP_AUTH_PASSWORD = $ZapPassword
    Write-Host "Running DAST..."
    .\scripts\run_dast_all.ps1
} else {
    Write-Host "Skipping DAST. Rerun with -IncludeDAST to include OWASP ZAP checks."
}

Write-Host "Building unified summary and dashboard..."
& $python scripts\ci_collect_summary.py
& $python scripts\ci_generate_dashboard.py

Write-Host ""
Write-Host "Security controls completed."
Write-Host "Markdown summary: reports\security-ci-summary.md"
Write-Host "HTML dashboard: reports\security-dashboard.html"
