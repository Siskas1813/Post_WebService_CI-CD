import json
from collections import Counter
from pathlib import Path


ROOT = Path("reports/secrets")
DETECT_SECRETS_JSON = ROOT / "detect-secrets.json"
GITLEAKS_JSON = ROOT / "gitleaks.json"
SUMMARY_MD = ROOT / "summary.md"


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return fallback


def detect_secrets_rows(data: dict) -> list[dict]:
    rows = []
    results = data.get("results", {})
    for file_path, findings in results.items():
        for item in findings:
            rows.append(
                {
                    "tool": "detect-secrets",
                    "rule": item.get("type", ""),
                    "path": file_path,
                    "line": item.get("line_number", ""),
                    "fingerprint": item.get("hashed_secret", "")[:12],
                    "description": item.get("type", ""),
                }
            )
    return rows


def gitleaks_rows(data) -> list[dict]:
    rows = []
    if not isinstance(data, list):
        return rows
    for item in data:
        rows.append(
            {
                "tool": "Gitleaks",
                "rule": item.get("RuleID", ""),
                "path": item.get("File", ""),
                "line": item.get("StartLine", ""),
                "fingerprint": item.get("Fingerprint", "")[:20],
                "description": item.get("Description", ""),
            }
        )
    return rows


def markdown_table(rows: list[dict], limit: int = 40) -> str:
    lines = [
        "| Tool | Rule | Location | Fingerprint | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows[:limit]:
        location = f"{row['path']}:{row['line']}"
        description = row["description"].replace("|", "\\|")
        lines.append(
            f"| {row['tool']} | `{row['rule']}` | `{location}` | `{row['fingerprint']}` | {description} |"
        )
    return "\n".join(lines)


def main() -> None:
    detect_rows = detect_secrets_rows(load_json(DETECT_SECRETS_JSON, {}))
    gitleaks_rows_list = gitleaks_rows(load_json(GITLEAKS_JSON, []))
    all_rows = detect_rows + gitleaks_rows_list

    by_tool = Counter(row["tool"] for row in all_rows)
    by_rule = Counter(row["rule"] or "unknown" for row in all_rows)

    lines = [
        "# Secrets Scanning Summary",
        "",
        "## Totals",
        "",
        f"- detect-secrets findings: {by_tool.get('detect-secrets', 0)}",
        f"- Gitleaks findings: {by_tool.get('Gitleaks', 0)}",
        f"- Total findings: {len(all_rows)}",
        "",
        "## By Rule",
        "",
        "| Rule | Count |",
        "| --- | --- |",
    ]

    if by_rule:
        for name, count in sorted(by_rule.items()):
            lines.append(f"| `{name}` | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Findings",
            "",
            markdown_table(all_rows) if all_rows else "No potential secrets were reported.",
            "",
        ]
    )

    ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to {SUMMARY_MD}")


if __name__ == "__main__":
    main()
