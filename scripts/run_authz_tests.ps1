param(
    [string]$OutputDir = "reports\authz"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$pytestText = Join-Path $OutputDir "pytest-authz.txt"
$summary = Join-Path $OutputDir "summary.md"

Write-Host "Running authentication and authorization security tests..."

& $python -m pytest tests\test_authz_security.py -vv | Tee-Object -FilePath $pytestText
$pytestExit = $LASTEXITCODE

@"
# Authentication and Authorization Test Summary

Command: `python -m pytest tests\test_authz_security.py -vv`

Exit code: $pytestExit

Text report: $pytestText

These tests cover:

- unauthenticated access to `/dashboard`;
- role checks for `/admin/users` and `/admin/sql`;
- logout and session termination;
- session cookie flags;
- IDOR behavior for `/mail/<id>`;
- unauthenticated API access to `/api/v1/mail/<id>`;
- brute-force lockout behavior;
- login SQL injection behavior.
"@ | Out-File -FilePath $summary -Encoding utf8

if ($pytestExit -ne 0) {
    throw "Authentication and authorization tests failed with exit code $pytestExit"
}

Write-Host "AuthZ reports saved to $OutputDir"
