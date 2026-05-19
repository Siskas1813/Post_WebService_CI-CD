param(
    [string]$OutputDir = "reports\security-regression"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$pytestText = Join-Path $OutputDir "pytest-security-regression.txt"
$summary = Join-Path $OutputDir "summary.md"

Write-Host "Running security regression tests..."

& $python -m pytest tests\test_security_regression.py -vv | Tee-Object -FilePath $pytestText
$pytestExit = $LASTEXITCODE

$summaryContent = @"
# Security Regression Test Summary

Command: python -m pytest tests\test_security_regression.py -vv

Exit code: $pytestExit

Text report: $pytestText

These tests cover expected secure behavior:

- /dashboard without a session redirects to login;
- regular user cannot open admin area;
- SQL injection in login is rejected;
- .pkl upload is forbidden;
- path traversal download is forbidden;
- API without authorization returns 401;
- API access to another user's mail returns 403 or 404.

Current interpretation:

- PASSED means the remediated application satisfies the security regression check.
- FAILED means a previously fixed security behavior regressed.
"@

$summaryContent | Out-File -FilePath $summary -Encoding utf8

if ($pytestExit -ne 0) {
    throw "Security regression tests failed with exit code $pytestExit"
}

Write-Host "Security regression reports saved to $OutputDir"
