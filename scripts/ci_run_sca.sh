#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports/sca
rm -f reports/sca/pip-audit.json reports/sca/pip-audit.txt reports/sca/trivy.json reports/sca/trivy.txt reports/sca/summary.md

echo "Running pip-audit..."
python -m pip_audit \
  -r requirements.txt \
  --no-deps \
  --disable-pip \
  -f json \
  -o reports/sca/pip-audit.json || true

python -m pip_audit \
  -r requirements.txt \
  --no-deps \
  --disable-pip \
  -f columns \
  -o reports/sca/pip-audit.txt || true

if [[ ! -s reports/sca/pip-audit.txt ]]; then
  echo "No known vulnerabilities found" > reports/sca/pip-audit.txt
fi

echo "Running Trivy..."
trivy fs \
  --scanners vuln \
  --format json \
  --output reports/sca/trivy.json \
  .

trivy fs \
  --scanners vuln \
  --format table \
  --output reports/sca/trivy.txt \
  .

python scripts/sca_summary.py
