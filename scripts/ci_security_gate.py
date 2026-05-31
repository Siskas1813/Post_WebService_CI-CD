import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return fallback


def count_sast() -> int:
    semgrep = load_json(Path("reports/sast/semgrep.json"), {})
    bandit = load_json(Path("reports/sast/bandit.json"), {})
    return len(semgrep.get("results", [])) + len(bandit.get("results", []))


def count_sca() -> int:
    pip_audit = load_json(Path("reports/sca/pip-audit.json"), {})
    trivy = load_json(Path("reports/sca/trivy.json"), {})

    pip_count = sum(len(dep.get("vulns", [])) for dep in pip_audit.get("dependencies", []))
    trivy_count = 0
    for result in trivy.get("Results", []):
        trivy_count += len(result.get("Vulnerabilities", []) or [])
    return pip_count + trivy_count


def count_secrets() -> int:
    detect = load_json(Path("reports/secrets/detect-secrets.json"), {})
    gitleaks = load_json(Path("reports/secrets/gitleaks.json"), [])

    detect_count = sum(len(items) for items in detect.get("results", {}).values())
    gitleaks_count = len(gitleaks) if isinstance(gitleaks, list) else 0
    return detect_count + gitleaks_count


def count_dast_blocking() -> int:
    blocking = 0
    for path in Path("reports/dast").glob("zap-*.json"):
        data = load_json(path, {})
        sites = data.get("site", [])
        alerts = data.get("alerts", [])
        for site in sites if isinstance(sites, list) else []:
            alerts.extend(site.get("alerts", []))
        for alert in alerts:
            risk = (alert.get("riskdesc") or alert.get("risk") or "").split("(", 1)[0].strip().lower()
            if risk in {"medium", "high"}:
                blocking += 1
    return blocking


CHECKS = {
    "sast": count_sast,
    "sca": count_sca,
    "secrets": count_secrets,
    "dast": count_dast_blocking,
}

REPORT_ONLY_CHECKS = {"dast"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail CI when security reports contain blocking findings.")
    parser.add_argument("checks", nargs="+", choices=sorted(CHECKS))
    args = parser.parse_args()

    failed = False
    for check in args.checks:
        count = CHECKS[check]()
        print(f"{check}: {count} blocking finding(s)")
        if count and check in REPORT_ONLY_CHECKS:
            print(f"{check}: report-only control, findings are kept in artifacts and dashboard")
        elif count:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
