param(
    [string]$Target = "http://host.docker.internal:5000",
    [string]$OutputDir = "reports\dast",
    [string]$Username = $env:ZAP_AUTH_USERNAME,
    [string]$Password = $env:ZAP_AUTH_PASSWORD
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Username)) {
    $Username = "employee"
}
if ([string]::IsNullOrWhiteSpace($Password)) {
    throw "Set ZAP_AUTH_PASSWORD or pass -Password before running the authenticated scan."
}
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

$planPath = Join-Path $OutputDir "zap-auth-plan.yaml"
$targetEscaped = $Target.TrimEnd("/")

@"
env:
  contexts:
    - name: "corp-mail-authenticated"
      urls:
        - "$targetEscaped"
      includePaths:
        - "$targetEscaped.*"
      excludePaths:
        - "$targetEscaped/logout.*"
      authentication:
        method: "form"
        parameters:
          loginPageUrl: "$targetEscaped/"
          loginRequestUrl: "$targetEscaped/login"
          loginRequestBody: "username={%username%}&password={%password%}&next=/dashboard"
        verification:
          method: "response"
          loggedInRegex: "dashboard|Corp Mail Enterprise"
          loggedOutRegex: "Corp Mail Login|authentication required"
      users:
        - name: "$Username"
          credentials:
            username: "$Username"
            password: "$Password"

jobs:
  - type: "passiveScan-config"
    parameters:
      maxAlertsPerRule: 20
      scanOnlyInScope: true

  - type: "spider"
    parameters:
      context: "corp-mail-authenticated"
      user: "$Username"
      url: "$targetEscaped"
      maxDuration: 5

  - type: "passiveScan-wait"
    parameters:
      maxDuration: 5

  - type: "activeScan"
    parameters:
      context: "corp-mail-authenticated"
      user: "$Username"
      policy: "Default Policy"
      maxRuleDurationInMins: 3
      maxScanDurationInMins: 15

  - type: "report"
    parameters:
      template: "traditional-html"
      reportDir: "/zap/wrk"
      reportFile: "zap-auth.html"
      reportTitle: "Corp Mail Authenticated ZAP Scan"

  - type: "report"
    parameters:
      template: "traditional-json"
      reportDir: "/zap/wrk"
      reportFile: "zap-auth.json"
      reportTitle: "Corp Mail Authenticated ZAP Scan"

  - type: "report"
    parameters:
      template: "traditional-md"
      reportDir: "/zap/wrk"
      reportFile: "zap-auth.md"
      reportTitle: "Corp Mail Authenticated ZAP Scan"
"@ | Out-File -FilePath $planPath -Encoding utf8

Write-Host "Running OWASP ZAP Authenticated Scan against $Target"

$ErrorActionPreference = "Continue"
docker run --rm `
    -v "${resolvedOutput}:/zap/wrk" `
    ghcr.io/zaproxy/zaproxy:stable `
    zap.sh `
    -cmd `
    -autorun /zap/wrk/zap-auth-plan.yaml
$zapExit = $LASTEXITCODE
$ErrorActionPreference = $oldErrorActionPreference

if ($zapExit -ne 0) {
    throw "OWASP ZAP Authenticated Scan failed with exit code $zapExit"
}

if (Test-Path ".\.venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe scripts\dast_summary.py
}

Write-Host "Authenticated scan reports saved to $OutputDir"
