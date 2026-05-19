import json
from collections import Counter
from pathlib import Path


ROOT = Path("reports/dast")
SUMMARY_MD = ROOT / "summary.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def zap_alerts(path: Path) -> list[dict]:
    data = load_json(path)
    alerts = []

    if isinstance(data.get("site"), list):
        for site in data["site"]:
            alerts.extend(site.get("alerts", []))

    if isinstance(data.get("alerts"), list):
        alerts.extend(data["alerts"])

    rows = []
    for item in alerts:
        rows.append(
            {
                "scan": path.stem,
                "name": item.get("name") or item.get("alert") or "",
                "risk": item.get("riskdesc") or item.get("risk") or "",
                "confidence": item.get("confidence") or "",
                "count": len(item.get("instances", [])) if isinstance(item.get("instances"), list) else "",
            }
        )
    return rows


def markdown_table(rows: list[dict], limit: int = 40) -> str:
    lines = [
        "| Scan | Alert | Risk | Confidence | Instances |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows[:limit]:
        name = row["name"].replace("|", "\\|")
        lines.append(f"| {row['scan']} | {name} | {row['risk']} | {row['confidence']} | {row['count']} |")
    return "\n".join(lines)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(ROOT.glob("zap-*.json")):
        rows.extend(zap_alerts(path))

    by_risk = Counter(row["risk"] or "unknown" for row in rows)
    by_scan = Counter(row["scan"] for row in rows)

    lines = ["# DAST Summary", "", "## Totals", ""]

    if by_scan:
        for scan, count in sorted(by_scan.items()):
            lines.append(f"- {scan}: {count}")
    else:
        lines.append("- No ZAP JSON reports were found.")

    lines.extend(
        [
            f"- Total alerts: {len(rows)}",
            "",
            "## By Risk",
            "",
            "| Risk | Count |",
            "| --- | --- |",
        ]
    )

    if by_risk:
        for risk, count in sorted(by_risk.items()):
            lines.append(f"| {risk} | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Alerts",
            "",
            markdown_table(rows) if rows else "No ZAP alerts were reported.",
            "",
        ]
    )

    diagnostics = ROOT / "zap-diagnostics.md"
    if diagnostics.exists():
        lines.extend(
            [
                "## ZAP Execution Diagnostics",
                "",
                diagnostics.read_text(encoding="utf-8", errors="replace").strip(),
                "",
            ]
        )

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to {SUMMARY_MD}")


if __name__ == "__main__":
    main()
