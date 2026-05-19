param(
    [string]$OutputDir = "reports\sast"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$localSemgrep = Join-Path (Get-Location) ".venv\Scripts\semgrep.exe"
if (Test-Path $localSemgrep) {
    $semgrep = $localSemgrep
} else {
    $semgrep = "semgrep"
}

$semgrepJson = Join-Path $OutputDir "semgrep.json"
$semgrepSarif = Join-Path $OutputDir "semgrep.sarif"
$banditJson = Join-Path $OutputDir "bandit.json"
$banditText = Join-Path $OutputDir "bandit.txt"

Write-Host "Running Semgrep..."
& $semgrep `
    --config p/python `
    --config .semgrep.yml `
    --json `
    --output $semgrepJson `
    app.py webmail templates

& $semgrep `
    --config p/python `
    --config .semgrep.yml `
    --sarif `
    --output $semgrepSarif `
    app.py webmail templates

Write-Host "Running Bandit..."
& $python -m bandit `
    -c bandit.yml `
    -r app.py webmail `
    -f json `
    -o $banditJson

& $python -m bandit `
    -c bandit.yml `
    -r app.py webmail `
    -f txt `
    -o $banditText

& $python scripts\sast_summary.py

Write-Host ""
Write-Host "SAST reports saved to $OutputDir"
Write-Host "Semgrep JSON: $semgrepJson"
Write-Host "Semgrep SARIF: $semgrepSarif"
Write-Host "Bandit JSON: $banditJson"
Write-Host "Bandit TXT: $banditText"
Write-Host "Summary: $(Join-Path $OutputDir 'summary.md')"
