#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports/sast
rm -f reports/sast/semgrep.json reports/sast/semgrep.sarif reports/sast/bandit.json reports/sast/bandit.txt reports/sast/summary.md

echo "Running Semgrep..."
semgrep \
  --config p/python \
  --config .semgrep.yml \
  --json \
  --output reports/sast/semgrep.json \
  app.py webmail templates || true

semgrep \
  --config p/python \
  --config .semgrep.yml \
  --sarif \
  --output reports/sast/semgrep.sarif \
  app.py webmail templates || true

if [[ ! -f reports/sast/semgrep.json ]]; then
  echo '{"results":[]}' > reports/sast/semgrep.json
fi
if [[ ! -f reports/sast/semgrep.sarif ]]; then
  echo '{"version":"2.1.0","runs":[]}' > reports/sast/semgrep.sarif
fi

echo "Running Bandit..."
python -m bandit \
  -c bandit.yml \
  -r app.py webmail \
  -f json \
  -o reports/sast/bandit.json || true

python -m bandit \
  -c bandit.yml \
  -r app.py webmail \
  -f txt \
  -o reports/sast/bandit.txt || true

python scripts/sast_summary.py
