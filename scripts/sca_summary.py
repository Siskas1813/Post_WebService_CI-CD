import json
from collections import Counter
from pathlib import Path


ROOT = Path("reports/sca")
PIP_AUDIT_JSON = ROOT / "pip-audit.json"
TRIVY_JSON = ROOT / "trivy.json"
SUMMARY_MD = ROOT / "summary.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def pip_audit_rows(data: dict) -> list[dict]:
    rows = []
    for dep in data.get("dependencies", []):
        name = dep.get("name", "")
        version = dep.get("version", "")
        for vuln in dep.get("vulns", []):
            aliases = ", ".join(vuln.get("aliases", []))
            fix_versions = ", ".join(vuln.get("fix_versions", []))
            rows.append(
                {
                    "tool": "pip-audit",
                    "dependency": f"{name} {version}".strip(),
                    "id": vuln.get("id", ""),
                    "severity": aliases or "-",
                    "fix": fix_versions or "-",
                    "description": vuln.get("description", "").replace("\n", " "),
                }
            )
    return rows


def trivy_rows(data: dict) -> list[dict]:
    rows = []
    for result in data.get("Results", []):
        target = result.get("Target", "")
        for vuln in result.get("Vulnerabilities", []) or []:
            rows.append(
                {
                    "tool": "Trivy",
                    "dependency": f"{vuln.get('PkgName', '')} {vuln.get('InstalledVersion', '')}".strip(),
                    "id": vuln.get("VulnerabilityID", ""),
                    "severity": vuln.get("Severity", "-"),
                    "fix": vuln.get("FixedVersion", "-") or "-",
                    "description": f"{target}: {vuln.get('Title', '')}".replace("\n", " "),
                }
            )
    return rows


def markdown_table(rows: list[dict], limit: int = 30) -> str:
    lines = [
        "| Tool | Dependency | ID | Severity / Alias | Fix version | Description |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows[:limit]:
        description = row["description"].replace("|", "\\|")
        lines.append(
            f"| {row['tool']} | `{row['dependency']}` | `{row['id']}` | {row['severity']} | `{row['fix']}` | {description} |"
        )
    return "\n".join(lines)


def main() -> None:
    pip_rows = pip_audit_rows(load_json(PIP_AUDIT_JSON))
    trivy_rows_list = trivy_rows(load_json(TRIVY_JSON))
    all_rows = pip_rows + trivy_rows_list

    by_tool = Counter(row["tool"] for row in all_rows)
    by_severity = Counter(row["severity"] for row in all_rows)

    lines = [
        "# SCA Summary",
        "",
        "## Totals",
        "",
        f"- pip-audit findings: {by_tool.get('pip-audit', 0)}",
        f"- Trivy findings: {by_tool.get('Trivy', 0)}",
        f"- Total findings: {len(all_rows)}",
        "",
        "## By Severity / Alias",
        "",
        "| Severity / Alias | Count |",
        "| --- | --- |",
    ]

    if by_severity:
        for name, count in sorted(by_severity.items()):
            lines.append(f"| {name} | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Findings",
            "",
            markdown_table(all_rows) if all_rows else "No vulnerable dependencies were reported.",
            "",
        ]
    )

    ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to {SUMMARY_MD}")


if __name__ == "__main__":
    main()
