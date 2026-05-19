param(
    [string]$OutputDir = "reports\api"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$pytestText = Join-Path $OutputDir "pytest-api.txt"
$summary = Join-Path $OutputDir "summary.md"

Write-Host "Running API security tests..."

& $python -m pytest tests\test_api_security.py -vv | Tee-Object -FilePath $pytestText
$pytestExit = $LASTEXITCODE

@"
# API Security Test Summary

Command: python -m pytest tests\test_api_security.py -vv

Exit code: $pytestExit

Text report: $pytestText

These tests cover:

- unauthenticated API access;
- access to other users' objects;
- SQL injection in API parameters;
- excessive data exposure in API responses;
- configuration disclosure;
- missing rate limiting;
- unsafe debug token format;
- permissive CORS;
- mass assignment.
"@ | Out-File -FilePath $summary -Encoding utf8

if ($pytestExit -ne 0) {
    throw "API security tests failed with exit code $pytestExit"
}

Write-Host "API reports saved to $OutputDir"
