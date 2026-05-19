param(
    [string]$OutputDir = "reports\attachments"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$pytestText = Join-Path $OutputDir "pytest-attachments.txt"
$summary = Join-Path $OutputDir "summary.md"

Write-Host "Running attachment upload/download security tests..."

& $python -m pytest tests\test_attachment_security.py -vv | Tee-Object -FilePath $pytestText
$pytestExit = $LASTEXITCODE

@"
# Attachment Security Test Summary

Command: python -m pytest tests\test_attachment_security.py -vv

Exit code: $pytestExit

Text report: $pytestText

These tests cover:

- forbidden file extensions;
- double-extension bypass;
- upload path traversal;
- file overwrite with identical names;
- missing file size limit;
- Content-Type spoofing;
- download path traversal;
- attachment IDOR across users.
"@ | Out-File -FilePath $summary -Encoding utf8

if ($pytestExit -ne 0) {
    throw "Attachment security tests failed with exit code $pytestExit"
}

Write-Host "Attachment reports saved to $OutputDir"
