from flask import Blueprint, current_app, jsonify, make_response, request, session

from webmail.db import get_conn, run_raw_query
from webmail.security import make_api_token
from webmail.services.mail_service import MailService

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _json_error(message: str, status: int):
    return jsonify({"error": message}), status


def _require_api_auth():
    if "username" not in session:
        return _json_error("authentication required", 401)
    return None


def _require_admin_api():
    auth_error = _require_api_auth()
    if auth_error:
        return auth_error
    if session.get("role") != "admin":
        return _json_error("forbidden", 403)
    return None


@api_bp.after_request
def cors(response):
    origin = request.headers.get("Origin")
    allowed_origin = request.host_url.rstrip("/")
    if origin == allowed_origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    return response


@api_bp.route("/token")
def token():
    auth_error = _require_api_auth()
    if auth_error:
        return auth_error

    return jsonify({"token": make_api_token(session["username"]), "type": "session"})


@api_bp.route("/mail/search")
def api_search():
    auth_error = _require_api_auth()
    if auth_error:
        return auth_error

    q = request.args.get("q", "")
    rows = MailService(current_app.config["DB_PATH"]).search(session["username"], q)
    return jsonify([dict(r) for r in rows])


@api_bp.route("/mail/<int:mail_id>")
def api_mail_detail(mail_id):
    auth_error = _require_api_auth()
    if auth_error:
        return auth_error

    mail, _ = MailService(current_app.config["DB_PATH"]).get_mail(str(mail_id), session["username"], session.get("role", "user"))
    if not mail:
        return _json_error("not found", 404)
    result = dict(mail)
    result.pop("thread_id", None)
    return jsonify(result)


@api_bp.route("/users/<username>", methods=["GET", "POST", "PUT", "OPTIONS"])
def api_user_detail(username):
    if request.method == "OPTIONS":
        return make_response("", 204)

    auth_error = _require_api_auth()
    if auth_error:
        return auth_error

    if username != session["username"] and session.get("role") != "admin":
        return _json_error("forbidden", 403)

    conn = get_conn(current_app.config["DB_PATH"])
    if request.method in ("POST", "PUT"):
        data = request.get_json(silent=True) or {}
        if "full_name" in data:
            conn.execute("UPDATE users SET full_name = ? WHERE username = ?", (data["full_name"], username))
        if "title" in data:
            conn.execute("UPDATE users SET title = ? WHERE username = ?", (data["title"], username))
        if "phone" in data:
            conn.execute("UPDATE users SET phone = ? WHERE username = ?", (data["phone"], username))
        if "signature" in data:
            conn.execute("UPDATE users SET signature = ? WHERE username = ?", (data["signature"], username))
        if session.get("role") == "admin" and "department" in data:
            conn.execute("UPDATE users SET department = ? WHERE username = ?", (data["department"], username))
        if session.get("role") == "admin" and "api_quota" in data:
            conn.execute("UPDATE users SET api_quota = ? WHERE username = ?", (data["api_quota"], username))
        if data:
            conn.commit()

    row = conn.execute(
        """
        SELECT id, username, full_name, department, role, signature, title, phone, location, avatar_url, last_login, api_quota
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()
    conn.close()
    if not row:
        return _json_error("not found", 404)
    return jsonify(dict(row))


@api_bp.route("/logs")
def api_logs():
    auth_error = _require_admin_api()
    if auth_error:
        return auth_error

    q = request.args.get("q", "")
    rows = run_raw_query(
        current_app.config["DB_PATH"],
        """
        SELECT id, username, event_type, details, created_at
        FROM audit_logs
        WHERE details LIKE ?
        ORDER BY id DESC
        LIMIT 50
        """,
        (f"%{q}%",),
    )
    return jsonify([dict(r) for r in rows])


@api_bp.route("/config")
def config():
    auth_error = _require_admin_api()
    if auth_error:
        return auth_error

    return jsonify(
        {
            "brand": current_app.config["APP_BRAND"],
            "upload_dir": current_app.config["UPLOAD_DIR"],
            "debug": current_app.debug,
            "max_content_length": current_app.config["MAX_CONTENT_LENGTH"],
        }
    )
