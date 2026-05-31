from pathlib import Path


REPORTS = Path("reports")
OUTPUT = REPORTS / "security-ci-summary.md"


def read(path: Path) -> str:
    if not path.exists():
        return "_Report was not generated._"
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()


def first_matching(path: Path, prefix: str) -> str:
    content = read(path)
    for line in content.splitlines():
        if line.startswith(prefix):
            return line.replace(prefix, "").strip()
    return "-"


def pytest_result() -> str:
    path = REPORTS / "pytest" / "security-tests.txt"
    if not path.exists():
        return "-"
    lines = read(path).splitlines()
    for line in reversed(lines):
        if " passed" in line or " failed" in line:
            return line.strip("= ")
    return "-"


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)

    sast = REPORTS / "sast" / "summary.md"
    sca = REPORTS / "sca" / "summary.md"
    secrets = REPORTS / "secrets" / "summary.md"
    dast = REPORTS / "dast" / "summary.md"

    lines = [
        "# Security CI/CD Summary",
        "",
        "## Gate Results",
        "",
        "| Control | Report | Key result |",
        "| --- | --- | --- |",
        f"| Pytest security tests | `reports/pytest/security-tests.txt` | {pytest_result()} |",
        f"| SAST: Semgrep + Bandit | `reports/sast/summary.md` | {first_matching(sast, '- Total findings:')} findings |",
        f"| SCA: pip-audit + Trivy | `reports/sca/summary.md` | {first_matching(sca, '- Total findings:')} findings |",
        f"| Secrets: detect-secrets + Gitleaks | `reports/secrets/summary.md` | {first_matching(secrets, '- Total findings:')} findings |",
        f"| DAST: OWASP ZAP | `reports/dast/summary.md` | {first_matching(dast, '- Total alerts:')} alerts total, gate blocks only Medium/High |",
        "",
        "## Included Reports",
        "",
        "- `reports/sast/semgrep.json`",
        "- `reports/sast/semgrep.sarif`",
        "- `reports/sast/bandit.json`",
        "- `reports/sca/pip-audit.json`",
        "- `reports/sca/trivy.json`",
        "- `reports/secrets/detect-secrets.json`",
        "- `reports/secrets/gitleaks.json`",
        "- `reports/dast/zap-baseline.html`",
        "- `reports/dast/zap-full.html`",
        "- `reports/dast/zap-auth.html`",
        "",
        "## Notes",
        "",
        "The CI/CD security gate fails on SAST, SCA and secrets findings. For DAST, the dashboard still shows the total ZAP alerts, but the gate fails only on Medium and High risk alerts; informational and low-risk observations remain in the artifact for manual review.",
        "",
    ]

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to {OUTPUT}")


if __name__ == "__main__":
    main()
