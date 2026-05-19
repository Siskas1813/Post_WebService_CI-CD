import json
from collections import Counter
from pathlib import Path


ROOT = Path("reports/sast")
SEMGREP_JSON = ROOT / "semgrep.json"
BANDIT_JSON = ROOT / "bandit.json"
SUMMARY_MD = ROOT / "summary.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def semgrep_rows(data: dict) -> list[dict]:
    rows = []
    for item in data.get("results", []):
        extra = item.get("extra", {})
        start = item.get("start", {})
        rows.append(
            {
                "tool": "Semgrep",
                "rule": item.get("check_id", ""),
                "severity": extra.get("severity", ""),
                "path": item.get("path", ""),
                "line": start.get("line", ""),
                "message": extra.get("message", "").replace("\n", " "),
            }
        )
    return rows


def bandit_rows(data: dict) -> list[dict]:
    rows = []
    for item in data.get("results", []):
        rows.append(
            {
                "tool": "Bandit",
                "rule": item.get("test_id", ""),
                "severity": item.get("issue_severity", ""),
                "path": item.get("filename", ""),
                "line": item.get("line_number", ""),
                "message": item.get("issue_text", "").replace("\n", " "),
            }
        )
    return rows


def markdown_table(rows: list[dict], limit: int = 25) -> str:
    lines = [
        "| Tool | Rule | Severity | Location | Message |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows[:limit]:
        location = f"{row['path']}:{row['line']}"
        message = row["message"].replace("|", "\\|")
        lines.append(f"| {row['tool']} | `{row['rule']}` | {row['severity']} | `{location}` | {message} |")
    return "\n".join(lines)


def main() -> None:
    semgrep = semgrep_rows(load_json(SEMGREP_JSON))
    bandit = bandit_rows(load_json(BANDIT_JSON))
    all_rows = semgrep + bandit

    severity = Counter(row["severity"] or "UNKNOWN" for row in all_rows)
    by_tool = Counter(row["tool"] for row in all_rows)

    lines = [
        "# SAST Summary",
        "",
        "## Totals",
        "",
        f"- Semgrep findings: {by_tool.get('Semgrep', 0)}",
        f"- Bandit findings: {by_tool.get('Bandit', 0)}",
        f"- Total findings: {len(all_rows)}",
        "",
        "## By Severity",
        "",
        "| Severity | Count |",
        "| --- | --- |",
    ]

    for name, count in sorted(severity.items()):
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "## First Findings",
            "",
            markdown_table(all_rows),
            "",
        ]
    )

    ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to {SUMMARY_MD}")


if __name__ == "__main__":
    main()
