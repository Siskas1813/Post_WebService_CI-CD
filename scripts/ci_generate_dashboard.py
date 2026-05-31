import html
import json
import re
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path


REPORTS = Path("reports")
OUT = REPORTS / "security-dashboard.html"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return fallback


def first_int(text: str, label: str) -> int:
    match = re.search(rf"{re.escape(label)}\s*(\d+)", text)
    return int(match.group(1)) if match else 0


def pytest_result() -> str:
    text = read_text(REPORTS / "pytest" / "security-tests.txt")
    for line in reversed(text.splitlines()):
        if " passed" in line or " failed" in line:
            return line.strip("= ")
    return "not generated"


def sast_metrics():
    semgrep = load_json(REPORTS / "sast" / "semgrep.json", {})
    bandit = load_json(REPORTS / "sast" / "bandit.json", {})
    semgrep_count = len(semgrep.get("results", []))
    bandit_count = len(bandit.get("results", []))
    severity = Counter()
    for item in semgrep.get("results", []):
        severity[item.get("extra", {}).get("severity", "UNKNOWN")] += 1
    for item in bandit.get("results", []):
        severity[item.get("issue_severity", "UNKNOWN")] += 1
    return semgrep_count, bandit_count, severity


def sca_metrics():
    pip_audit = load_json(REPORTS / "sca" / "pip-audit.json", {})
    trivy = load_json(REPORTS / "sca" / "trivy.json", {})
    pip_count = sum(len(dep.get("vulns", [])) for dep in pip_audit.get("dependencies", []))
    trivy_count = 0
    severity = Counter()
    for result in trivy.get("Results", []):
        for vuln in result.get("Vulnerabilities", []) or []:
            trivy_count += 1
            severity[vuln.get("Severity", "UNKNOWN")] += 1
    return pip_count, trivy_count, severity


def secrets_metrics():
    detect = load_json(REPORTS / "secrets" / "detect-secrets.json", {})
    gitleaks = load_json(REPORTS / "secrets" / "gitleaks.json", [])
    detect_count = sum(len(items) for items in detect.get("results", {}).values())
    gitleaks_count = len(gitleaks) if isinstance(gitleaks, list) else 0
    return detect_count, gitleaks_count


def dast_alerts():
    rows = []
    for path in sorted((REPORTS / "dast").glob("zap-*.json")):
        data = load_json(path, {})
        alerts = []
        if isinstance(data.get("site"), list):
            for site in data["site"]:
                alerts.extend(site.get("alerts", []))
        if isinstance(data.get("alerts"), list):
            alerts.extend(data["alerts"])
        for alert in alerts:
            risk = alert.get("riskdesc") or alert.get("risk") or "unknown"
            rows.append(
                {
                    "scan": path.stem,
                    "name": alert.get("name") or alert.get("alert") or "",
                    "risk": risk,
                    "confidence": str(alert.get("confidence") or ""),
                    "instances": len(alert.get("instances", [])) if isinstance(alert.get("instances"), list) else 0,
                }
            )
    return rows


def is_reported_dast_alert(row: dict) -> bool:
    name = (row.get("name") or "").strip()
    scan = (row.get("scan") or "").strip()

    false_positive_names = {
        "Format String Error",
    }
    if name in false_positive_names:
        return False

    duplicate_baseline_info = scan == "zap-baseline" and name == "Authentication Request Identified"
    if duplicate_baseline_info:
        return False

    return True


def risk_bucket(risk: str) -> str:
    risk = risk.lower()
    if "high" in risk and not risk.startswith("informational"):
        return "High"
    if "medium" in risk and not risk.startswith("informational"):
        return "Medium"
    if "low" in risk and not risk.startswith("informational"):
        return "Low"
    if "informational" in risk:
        return "Info"
    return "Unknown"


def status_class(blocking: int) -> str:
    return "ok" if blocking == 0 else "bad"


def badge(text: str, kind: str) -> str:
    return f'<span class="badge {kind}">{html.escape(text)}</span>'


def bar(label: str, value: int, total: int, kind: str) -> str:
    width = 0 if total == 0 else max(4, round(value / total * 100))
    return f"""
    <div class="bar-row">
      <div class="bar-label"><span>{html.escape(label)}</span><strong>{value}</strong></div>
      <div class="bar"><span class="{kind}" style="width:{width}%"></span></div>
    </div>
    """


def control_row(name: str, tools: str, result: str, blocking: int, report: str) -> str:
    status = "PASS" if blocking == 0 else "FAIL"
    kind = "ok" if blocking == 0 else "bad"
    return f"""
    <tr>
      <td><strong>{html.escape(name)}</strong><small>{html.escape(tools)}</small></td>
      <td>{html.escape(result)}</td>
      <td>{badge(status, kind)}</td>
      <td><code>{html.escape(report)}</code></td>
    </tr>
    """


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)

    semgrep_count, bandit_count, sast_severity = sast_metrics()
    pip_count, trivy_count, sca_severity = sca_metrics()
    detect_count, gitleaks_count = secrets_metrics()
    dast_rows = [row for row in dast_alerts() if is_reported_dast_alert(row)]
    dast_risk = Counter(risk_bucket(row["risk"]) for row in dast_rows)
    dast_blocking = dast_risk["High"] + dast_risk["Medium"]

    pytest_text = pytest_result()
    pytest_blocking = 0 if "passed" in pytest_text and "failed" not in pytest_text else 1
    sast_total = semgrep_count + bandit_count
    sca_total = pip_count + trivy_count
    secrets_total = detect_count + gitleaks_count
    total_blocking = pytest_blocking + sast_total + sca_total + secrets_total + dast_blocking
    gate = "PASS" if total_blocking == 0 else "FAIL"

    total_dast = len(dast_rows)
    dast_bars = "\n".join(
        [
            bar("High", dast_risk["High"], total_dast, "high"),
            bar("Medium", dast_risk["Medium"], total_dast, "medium"),
            bar("Low", dast_risk["Low"], total_dast, "low"),
            bar("Informational", dast_risk["Info"], total_dast, "info"),
        ]
    )

    controls = "\n".join(
        [
            control_row("Regression tests", "pytest", pytest_text, pytest_blocking, "reports/pytest/security-tests.txt"),
            control_row("SAST", "Semgrep + Bandit", f"{sast_total} findings", sast_total, "reports/sast/summary.md"),
            control_row("SCA", "pip-audit + Trivy", f"{sca_total} vulnerabilities", sca_total, "reports/sca/summary.md"),
            control_row("Secrets", "detect-secrets + Gitleaks", f"{secrets_total} findings", secrets_total, "reports/secrets/summary.md"),
            control_row("DAST", "OWASP ZAP", f"{total_dast} alerts total, {dast_blocking} blocking", dast_blocking, "reports/dast/summary.md"),
        ]
    )

    dast_table = "\n".join(
        f"""
        <tr>
          <td>{html.escape(row['scan'])}</td>
          <td>{html.escape(row['name'])}</td>
          <td>{badge(risk_bucket(row['risk']), risk_bucket(row['risk']).lower())}</td>
          <td>{html.escape(row['confidence'])}</td>
          <td>{row['instances']}</td>
        </tr>
        """
        for row in dast_rows[:30]
    ) or '<tr><td colspan="5">No ZAP alerts were reported.</td></tr>'

    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    document = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Security CI/CD Dashboard</title>
  <style>
    :root {{
      --bg: #eef2f6;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #64748b;
      --line: #d8e0eb;
      --soft: #f8fafc;
      --navy: #111a2e;
      --ok: #07835d;
      --bad: #b42318;
      --info: #2563eb;
      --low: #b7791f;
      --medium: #c2410c;
      --high: #be123c;
      --shadow: 0 16px 34px rgba(15, 23, 42, .09);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.45;
    }}
    header {{
      background:
        radial-gradient(circle at 86% 14%, rgba(20, 184, 166, .22), transparent 28%),
        linear-gradient(135deg, #111827 0%, #18243a 62%, #23344f 100%);
      color: white;
      padding: 34px 24px 38px;
    }}
    .masthead {{
      max-width: 1320px;
      margin: 0 auto;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 24px;
    }}
    header h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    header p {{ margin: 0; color: #d9e2f0; max-width: 760px; }}
    .gate-chip {{
      min-width: 190px;
      border: 1px solid rgba(255, 255, 255, .22);
      background: rgba(255, 255, 255, .09);
      padding: 14px 16px;
      border-radius: 8px;
      text-align: right;
    }}
    .gate-chip span {{ display: block; color: #cbd5e1; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0; }}
    .gate-chip strong {{ display: block; margin-top: 4px; font-size: 24px; color: #5ee0ad; }}
    .gate-chip.bad strong {{ color: #fca5a5; }}
    main {{ padding: 24px 24px 46px; max-width: 1320px; margin: 0 auto; }}
    .hero {{
      display: grid;
      grid-template-columns: 1.25fr repeat(4, 1fr);
      gap: 14px;
      margin-top: 0;
      align-items: stretch;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .card {{
      min-height: 132px;
      padding: 18px;
      border-top: 4px solid #cbd5e1;
    }}
    .card h2 {{ margin: 0 0 12px; font-size: 12px; color: var(--muted); font-weight: 800; text-transform: uppercase; letter-spacing: 0; }}
    .metric {{ font-size: 32px; line-height: 1; font-weight: 850; margin: 0; }}
    .sub {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}
    .gate {{ border-top-color: var(--ok); background: linear-gradient(180deg, #ffffff 0%, #f3fbf8 100%); }}
    .gate.bad {{ border-top-color: var(--bad); background: linear-gradient(180deg, #ffffff 0%, #fff7f7 100%); }}
    .gate .metric {{ color: var(--ok); }}
    .gate.bad .metric {{ color: var(--bad); }}
    .grid {{ display: grid; grid-template-columns: 1.15fr .85fr; gap: 18px; margin-top: 20px; }}
    .panel {{ padding: 20px 22px; }}
    .panel h2 {{ margin: 0 0 14px; font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0; }}
    tbody tr:hover {{ background: var(--soft); }}
    td small {{ display: block; color: var(--muted); margin-top: 3px; }}
    code {{ background: #eef3f8; padding: 4px 7px; border-radius: 5px; font-size: 12px; color: #1f3b57; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 9px;
      border-radius: 999px;
      color: white;
      font-size: 12px;
      font-weight: 800;
    }}
    .badge.ok {{ background: var(--ok); }}
    .badge.bad {{ background: var(--bad); }}
    .badge.high {{ background: var(--high); }}
    .badge.medium {{ background: var(--medium); }}
    .badge.low {{ background: var(--low); }}
    .badge.info, .badge.unknown {{ background: var(--info); }}
    .bar-row {{ margin-bottom: 14px; }}
    .bar-label {{ display: flex; justify-content: space-between; margin-bottom: 6px; color: var(--muted); font-size: 14px; }}
    .bar {{ height: 12px; background: #e8edf5; border-radius: 999px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; border-radius: 999px; }}
    .bar .high {{ background: var(--high); }}
    .bar .medium {{ background: var(--medium); }}
    .bar .low {{ background: var(--low); }}
    .bar .info {{ background: var(--info); }}
    .links {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
    .link-card {{ border: 1px solid var(--line); border-radius: 8px; padding: 13px; background: var(--soft); }}
    .link-card strong {{ display: block; margin-bottom: 6px; }}
    .link-card span {{ color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }}
    @media (max-width: 1080px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .masthead {{ align-items: flex-start; flex-direction: column; }}
      .gate-chip {{ text-align: left; width: 100%; }}
      .hero, .grid, .links {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 760px) {{
      header h1 {{ font-size: 24px; }}
      main {{ padding-top: 18px; }}
      .panel {{ overflow-x: auto; }}
      table {{ min-width: 680px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="masthead">
      <div>
        <h1>Security CI/CD Dashboard</h1>
        <p>Единый отчет автоматизированных контролей безопасности. Сформировано: {generated_at}</p>
      </div>
      <div class="gate-chip {status_class(total_blocking)}">
        <span>Security Gate</span>
        <strong>{gate}</strong>
      </div>
    </div>
  </header>
  <main>
    <section class="hero">
      <div class="card gate {status_class(total_blocking)}">
        <h2>Security Gate</h2>
        <p class="metric">{gate}</p>
        <p class="sub">{total_blocking} blocking finding(s)</p>
      </div>
      <div class="card"><h2>Pytest</h2><p class="metric">{html.escape(pytest_text.split()[0] if pytest_text else '-')}</p><p class="sub">{html.escape(pytest_text)}</p></div>
      <div class="card"><h2>SAST</h2><p class="metric">{sast_total}</p><p class="sub">Semgrep {semgrep_count}, Bandit {bandit_count}</p></div>
      <div class="card"><h2>SCA</h2><p class="metric">{sca_total}</p><p class="sub">pip-audit {pip_count}, Trivy {trivy_count}</p></div>
      <div class="card"><h2>DAST Alerts</h2><p class="metric">{total_dast}</p><p class="sub">{dast_blocking} blocking; {dast_risk['Low']} low; {dast_risk['Info']} informational</p></div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Контроли безопасности</h2>
        <table>
          <thead><tr><th>Контроль</th><th>Результат</th><th>Gate</th><th>Отчет</th></tr></thead>
          <tbody>{controls}</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>DAST Risk Breakdown</h2>
        {dast_bars}
      </div>
    </section>

    <section class="panel" style="margin-top:18px">
      <h2>OWASP ZAP Alerts</h2>
      <table>
        <thead><tr><th>Scan</th><th>Alert</th><th>Risk</th><th>Confidence</th><th>Instances</th></tr></thead>
        <tbody>{dast_table}</tbody>
      </table>
    </section>

    <section class="panel" style="margin-top:18px">
      <h2>Артефакты</h2>
      <div class="links">
        <div class="link-card"><strong>SAST</strong><span>reports/sast/summary.md, semgrep.sarif, bandit.json</span></div>
        <div class="link-card"><strong>SCA</strong><span>reports/sca/summary.md, pip-audit.json, trivy.json</span></div>
        <div class="link-card"><strong>Secrets</strong><span>reports/secrets/summary.md, detect-secrets.json, gitleaks.sarif</span></div>
        <div class="link-card"><strong>DAST</strong><span>reports/dast/zap-baseline.html, zap-full.html, zap-auth.html</span></div>
        <div class="link-card"><strong>Pytest</strong><span>reports/pytest/security-tests.txt</span></div>
        <div class="link-card"><strong>Summary</strong><span>reports/security-ci-summary.md</span></div>
      </div>
    </section>
  </main>
</body>
</html>
"""

    OUT.write_text(document, encoding="utf-8")
    print(f"Dashboard written to {OUT}")


if __name__ == "__main__":
    main()
