param(
    [string]$Target = "http://host.docker.internal:5000",
    [string]$OutputDir = "reports\dast"
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$resolvedOutput = Resolve-Path $OutputDir

$oldErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker info > $null 2>&1
$dockerInfoExit = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference
if ($dockerInfoExit -ne 0) {
    throw "Docker daemon is not available. Start Docker Desktop and rerun this script."
}

Write-Host "Running OWASP ZAP Full Scan against $Target"

$ErrorActionPreference = "Continue"
docker run --rm `
    -v "${resolvedOutput}:/zap/wrk" `
    ghcr.io/zaproxy/zaproxy:stable `
    zap-full-scan.py `
    -t $Target `
    -r zap-full.html `
    -J zap-full.json `
    -w zap-full.md `
    -I
$zapExit = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference

if ($zapExit -ne 0) {
    throw "OWASP ZAP Full Scan failed with exit code $zapExit"
}

if (Test-Path ".\.venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe scripts\dast_summary.py
}

Write-Host "Full scan reports saved to $OutputDir"
