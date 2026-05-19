param(
    [string]$OutputDir = "reports\sca"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$pipAuditJson = Join-Path $OutputDir "pip-audit.json"
$pipAuditText = Join-Path $OutputDir "pip-audit.txt"
$trivyJson = Join-Path $OutputDir "trivy.json"
$trivyText = Join-Path $OutputDir "trivy.txt"

foreach ($reportFile in @($pipAuditJson, $pipAuditText, $trivyJson, $trivyText, (Join-Path $OutputDir "summary.md"))) {
    if (Test-Path $reportFile) {
        Remove-Item -LiteralPath $reportFile -Force
    }
}

Write-Host "Running pip-audit..."
& $python -m pip_audit `
    -r requirements.txt `
    --no-deps `
    --disable-pip `
    -f json `
    -o $pipAuditJson

& $python -m pip_audit `
    -r requirements.txt `
    --no-deps `
    --disable-pip `
    -f columns `
    -o $pipAuditText

if (-not (Test-Path $pipAuditText)) {
    "No known vulnerabilities found" | Out-File -FilePath $pipAuditText -Encoding utf8
}

$trivyCommand = Get-Command trivy -ErrorAction SilentlyContinue
if ($trivyCommand) {
    Write-Host "Running Trivy..."
    & trivy fs `
        --scanners vuln `
        --format json `
        --output $trivyJson `
        .

    & trivy fs `
        --scanners vuln `
        --format table `
        --output $trivyText `
        .
} else {
    "Trivy is not installed. Install it and rerun this script: winget install AquaSecurity.Trivy" | Out-File -FilePath $trivyText -Encoding utf8
    "{}" | Out-File -FilePath $trivyJson -Encoding utf8
}

& $python scripts\sca_summary.py

Write-Host ""
Write-Host "SCA reports saved to $OutputDir"
Write-Host "pip-audit JSON: $pipAuditJson"
Write-Host "pip-audit TXT: $pipAuditText"
Write-Host "Trivy JSON: $trivyJson"
Write-Host "Trivy TXT: $trivyText"
Write-Host "Summary: $(Join-Path $OutputDir 'summary.md')"
