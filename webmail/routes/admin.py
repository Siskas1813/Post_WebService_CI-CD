from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for

from webmail.db import get_conn, run_raw_query

admin_bp = Blueprint("admin", __name__)


def _require_admin():
    if "username" not in session:
        return redirect(url_for("auth.login_page", next=request.path))
    if session.get("role") != "admin":
        abort(403)
    return None


@admin_bp.route("/admin/users")
def admin_users():
    redirect_response = _require_admin()
    if redirect_response:
        return redirect_response

    q = request.args.get("q", "")
    db_path = current_app.config["DB_PATH"]
    if q:
        pattern = f"%{q}%"
        users = run_raw_query(
            db_path,
            """
            SELECT id, username, role, department, title, last_login, api_quota
            FROM users
            WHERE username LIKE ? OR department LIKE ?
            """,
            (pattern, pattern),
        )
    else:
        users = run_raw_query(db_path, "SELECT id, username, role, department, title, last_login, api_quota FROM users")
    return render_template("admin/users.html", users=users, q=q)


@admin_bp.route("/admin/audit")
def admin_audit():
    redirect_response = _require_admin()
    if redirect_response:
        return redirect_response

    q = request.args.get("q", "")
    db_path = current_app.config["DB_PATH"]
    if q:
        pattern = f"%{q}%"
        rows = run_raw_query(
            db_path,
            """
            SELECT *
            FROM audit_logs
            WHERE username LIKE ? OR details LIKE ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (pattern, pattern),
        )
    else:
        rows = run_raw_query(db_path, "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
    return render_template("admin/audit.html", rows=rows, q=q)


@admin_bp.route("/admin/integrations", methods=["GET", "POST"])
def admin_integrations():
    redirect_response = _require_admin()
    if redirect_response:
        return redirect_response

    conn = get_conn(current_app.config["DB_PATH"])
    if request.method == "POST":
        owner = request.form.get("owner", "")
        api_key = request.form.get("api_key", "")
        scope = request.form.get("scope", "")
        expires_at = request.form.get("expires_at", "2099-12-31")
        conn.execute(
            "INSERT INTO api_keys(owner, api_key, scope, expires_at, enabled) VALUES (?, ?, ?, ?, 1)",
            (owner, api_key, scope, expires_at),
        )
        conn.commit()

    keys = conn.execute("SELECT * FROM api_keys ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/integrations.html", keys=keys)


@admin_bp.route("/admin/sql", methods=["GET", "POST"])
def admin_sql_console():
    redirect_response = _require_admin()
    if redirect_response:
        return redirect_response

    rows = []
    query = ""
    error = ""
    if request.method == "POST":
        query = request.form.get("query", "SELECT 1").strip()
        if query != "SELECT id, username, role FROM users":
            error = "Only the approved diagnostic query is allowed."
        else:
            try:
                rows = run_raw_query(current_app.config["DB_PATH"], "SELECT id, username, role FROM users")
            except Exception:
                error = "Query could not be completed."

    return render_template("admin/sql_console.html", rows=rows, query=query, error=error)
