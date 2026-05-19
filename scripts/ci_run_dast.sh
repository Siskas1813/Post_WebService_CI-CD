#!/usr/bin/env bash
set -euo pipefail

TARGET="${DAST_TARGET:-http://host.docker.internal:5000}"
ZAP_IMAGE="${ZAP_IMAGE:-ghcr.io/zaproxy/zaproxy:stable}"
ZAP_AUTH_USERNAME="${ZAP_AUTH_USERNAME:-employee}"
ZAP_AUTH_PASSWORD="${ZAP_AUTH_PASSWORD:-employee123}"
APP_PORT="${APP_PORT:-5000}"

mkdir -p reports/dast uploads
rm -f reports/dast/zap-*.html reports/dast/zap-*.json reports/dast/zap-*.md reports/dast/zap-auth-plan.yaml reports/dast/summary.md reports/dast/flask.out.log reports/dast/flask.err.log

echo "Starting application for DAST..."
export CORP_MAIL_DISABLE_CSRF_FOR_DAST=1
python - <<'PY' > reports/dast/flask.out.log 2> reports/dast/flask.err.log &
from werkzeug.serving import WSGIRequestHandler
from webmail import create_app

WSGIRequestHandler.server_version = "CorpMail"
WSGIRequestHandler.sys_version = ""

app = create_app()
app.run(host="0.0.0.0", port=5000, debug=False)
PY
APP_PID=$!

cleanup() {
  kill "$APP_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for application..."
for _ in {1..45}; do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/" >/dev/null; then
    break
  fi
  sleep 2
done
curl -fsS "http://127.0.0.1:${APP_PORT}/" >/dev/null

ZAP_DOCKER_ARGS=(--rm --add-host=host.docker.internal:host-gateway -v "${PWD}/reports/dast:/zap/wrk" "$ZAP_IMAGE")

echo "Running OWASP ZAP Baseline Scan..."
set +e
docker run "${ZAP_DOCKER_ARGS[@]}" \
  zap-baseline.py \
  -t "$TARGET" \
  -r zap-baseline.html \
  -J zap-baseline.json \
  -w zap-baseline.md \
  -I
ZAP_BASELINE_EXIT=$?
set -e

echo "Running OWASP ZAP Full Scan..."
set +e
docker run "${ZAP_DOCKER_ARGS[@]}" \
  zap-full-scan.py \
  -t "$TARGET" \
  -r zap-full.html \
  -J zap-full.json \
  -w zap-full.md \
  -I
ZAP_FULL_EXIT=$?
set -e

cat > reports/dast/zap-auth-plan.yaml <<YAML
env:
  contexts:
    - name: "corp-mail-authenticated"
      urls:
        - "$TARGET"
      includePaths:
        - "$TARGET.*"
      excludePaths:
        - "$TARGET/logout.*"
      authentication:
        method: "form"
        parameters:
          loginPageUrl: "$TARGET/"
          loginRequestUrl: "$TARGET/login"
          loginRequestBody: "username={%username%}&password={%password%}&next=/dashboard"
        verification:
          method: "response"
          loggedInRegex: "dashboard|Corp Mail Enterprise"
          loggedOutRegex: "Corp Mail Login|authentication required"
      users:
        - name: "$ZAP_AUTH_USERNAME"
          credentials:
            username: "$ZAP_AUTH_USERNAME"
            password: "$ZAP_AUTH_PASSWORD"

jobs:
  - type: "passiveScan-config"
    parameters:
      maxAlertsPerRule: 20
      scanOnlyInScope: true

  - type: "spider"
    parameters:
      context: "corp-mail-authenticated"
      user: "$ZAP_AUTH_USERNAME"
      url: "$TARGET"
      maxDuration: 5

  - type: "passiveScan-wait"
    parameters:
      maxDuration: 5

  - type: "activeScan"
    parameters:
      context: "corp-mail-authenticated"
      user: "$ZAP_AUTH_USERNAME"
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
YAML

echo "Running OWASP ZAP Authenticated Scan..."
set +e
docker run "${ZAP_DOCKER_ARGS[@]}" \
  zap.sh \
  -cmd \
  -autorun /zap/wrk/zap-auth-plan.yaml
ZAP_AUTH_EXIT=$?
set -e

{
  echo "ZAP baseline exit code: $ZAP_BASELINE_EXIT"
  echo "ZAP full exit code: $ZAP_FULL_EXIT"
  echo "ZAP authenticated exit code: $ZAP_AUTH_EXIT"
} > reports/dast/zap-exit-codes.txt

python scripts/dast_summary.py

if ! compgen -G "reports/dast/zap-*.json" > /dev/null; then
  echo "No ZAP JSON reports were generated." >&2
  exit 1
fi
