#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports/secrets
rm -f reports/secrets/detect-secrets.json reports/secrets/detect-secrets.baseline reports/secrets/gitleaks.json reports/secrets/gitleaks.sarif reports/secrets/gitleaks.txt reports/secrets/summary.md

EXCLUDE_REGEX='(\.venv|reports|uploads|__pycache__|corp_mail\.db|diplom.*\.zip)'

echo "Running detect-secrets..."
python -m detect_secrets scan \
  --all-files \
  --exclude-files "$EXCLUDE_REGEX" \
  app.py webmail templates static requirements.txt requirements-dev.txt README.md .semgrep.yml bandit.yml .gitleaks.toml scripts docs \
  > reports/secrets/detect-secrets.json

cp reports/secrets/detect-secrets.json reports/secrets/detect-secrets.baseline

echo "Running Gitleaks..."
set +e
gitleaks detect \
  --source . \
  --config .gitleaks.toml \
  --no-git \
  --report-format json \
  --report-path reports/secrets/gitleaks.json \
  --redact=80
GITLEAKS_JSON_EXIT=$?

gitleaks detect \
  --source . \
  --config .gitleaks.toml \
  --no-git \
  --report-format sarif \
  --report-path reports/secrets/gitleaks.sarif \
  --redact=80
GITLEAKS_SARIF_EXIT=$?
set -e

if [[ ! -f reports/secrets/gitleaks.json ]]; then
  echo "[]" > reports/secrets/gitleaks.json
fi
if [[ ! -f reports/secrets/gitleaks.sarif ]]; then
  echo '{"version":"2.1.0","runs":[]}' > reports/secrets/gitleaks.sarif
fi

{
  echo "Gitleaks JSON exit code: $GITLEAKS_JSON_EXIT"
  echo "Gitleaks SARIF exit code: $GITLEAKS_SARIF_EXIT"
} > reports/secrets/gitleaks.txt

python scripts/secrets_summary.py
