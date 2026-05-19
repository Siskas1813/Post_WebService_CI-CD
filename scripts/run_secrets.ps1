param(
    [string]$OutputDir = "reports\secrets"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$localPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path $localPython) {
    $python = $localPython
} else {
    $python = "python"
}

$detectSecretsJson = Join-Path $OutputDir "detect-secrets.json"
$detectSecretsBaseline = Join-Path $OutputDir "detect-secrets.baseline"
$gitleaksJson = Join-Path $OutputDir "gitleaks.json"
$gitleaksSarif = Join-Path $OutputDir "gitleaks.sarif"
$gitleaksText = Join-Path $OutputDir "gitleaks.txt"

$excludeRegex = "(\.venv|reports|uploads|__pycache__|corp_mail\.db|diplom.*\.zip)"

Write-Host "Running detect-secrets..."
& $python -m detect_secrets scan `
    --all-files `
    --exclude-files $excludeRegex `
    app.py webmail templates static requirements.txt requirements-dev.txt README.md .semgrep.yml bandit.yml .gitleaks.toml scripts docs `
    | Out-File -FilePath $detectSecretsJson -Encoding utf8

Copy-Item -LiteralPath $detectSecretsJson -Destination $detectSecretsBaseline -Force

$gitleaksCommand = Get-Command gitleaks -ErrorAction SilentlyContinue
if ($gitleaksCommand) {
    Write-Host "Running Gitleaks..."

    & gitleaks detect `
        --source . `
        --config .gitleaks.toml `
        --no-git `
        --report-format json `
        --report-path $gitleaksJson `
        --redact=80
    $gitleaksJsonExit = $LASTEXITCODE

    & gitleaks detect `
        --source . `
        --config .gitleaks.toml `
        --no-git `
        --report-format sarif `
        --report-path $gitleaksSarif `
        --redact=80
    $gitleaksSarifExit = $LASTEXITCODE

    "Gitleaks JSON exit code: $gitleaksJsonExit`nGitleaks SARIF exit code: $gitleaksSarifExit" | Out-File -FilePath $gitleaksText -Encoding utf8
} else {
    "Gitleaks is not installed. Install it and rerun this script: winget install Gitleaks.Gitleaks" | Out-File -FilePath $gitleaksText -Encoding utf8
    "[]" | Out-File -FilePath $gitleaksJson -Encoding utf8
    '{"version":"2.1.0","runs":[]}' | Out-File -FilePath $gitleaksSarif -Encoding utf8
}

& $python scripts\secrets_summary.py

Write-Host ""
Write-Host "Secrets reports saved to $OutputDir"
Write-Host "detect-secrets JSON: $detectSecretsJson"
Write-Host "detect-secrets baseline: $detectSecretsBaseline"
Write-Host "Gitleaks JSON: $gitleaksJson"
Write-Host "Gitleaks SARIF: $gitleaksSarif"
Write-Host "Summary: $(Join-Path $OutputDir 'summary.md')"
