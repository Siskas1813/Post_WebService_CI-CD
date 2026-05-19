param(
    [string]$OutputDir = "reports\config-headers"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$pytestText = Join-Path $OutputDir "pytest-config-headers.txt"
$summary = Join-Path $OutputDir "summary.md"

Write-Host "Running configuration and HTTP header security tests..."

& $python -m pytest tests\test_config_headers_security.py -vv | Tee-Object -FilePath $pytestText
$pytestExit = $LASTEXITCODE

$summaryContent = @"
# Configuration and HTTP Header Security Test Summary

Command: python -m pytest tests\test_config_headers_security.py -vv

Exit code: $pytestExit

Text report: $pytestText

These tests cover:

- missing Content-Security-Policy;
- missing X-Content-Type-Options;
- missing X-Frame-Options / frame-ancestors;
- missing Referrer-Policy;
- missing Permissions-Policy;
- session cookie flags;
- permissive CORS headers on API responses;
- debug mode in the application entrypoint;
- internal error detail leakage to the user.

Manual curl checks:

    curl.exe -I http://127.0.0.1:5000/
    curl.exe -I http://127.0.0.1:5000/dashboard
    curl.exe -i http://127.0.0.1:5000/api/v1/config
"@

$summaryContent | Out-File -FilePath $summary -Encoding utf8

if ($pytestExit -ne 0) {
    throw "Configuration and HTTP header security tests failed with exit code $pytestExit"
}

Write-Host "Configuration and header reports saved to $OutputDir"
