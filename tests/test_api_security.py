import base64

from webmail.db import get_conn


def login(client, username="employee", password="employee123"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": "/dashboard"},
        follow_redirects=False,
    )


def test_api_config_requires_admin_authentication(client):
    response = client.get("/api/v1/config")
    assert response.status_code == 401

    login(client, "employee", "employee123")
    regular = client.get("/api/v1/config")
    assert regular.status_code == 403

    client.get("/logout")
    login(client, "admin", "admin123")
    admin = client.get("/api/v1/config")
    assert admin.status_code == 200
    assert "smtp_password" not in admin.json
    assert "jwt_key" not in admin.json


def test_api_mail_detail_requires_authentication(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute("SELECT id FROM mails LIMIT 1").fetchone()
    conn.close()

    response = client.get(f"/api/v1/mail/{row['id']}")

    assert response.status_code == 401


def test_api_idor_blocks_access_to_another_users_mail(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute(
        """
        INSERT INTO mails(sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
        VALUES ('ceo@corp.local', 'manager', '', 'Private API mail', 'manager-only-api-body', 'inbox', datetime('now'), 'high', 'restricted', 'API', 0, 0, 'thread-api-idor')
        RETURNING id
        """
    ).fetchone()
    conn.commit()
    conn.close()

    login(client, "employee", "employee123")
    response = client.get(f"/api/v1/mail/{row['id']}")

    assert response.status_code == 404


def test_api_search_sql_injection_does_not_return_other_recipients(client):
    login(client, "employee", "employee123")

    response = client.get("/api/v1/mail/search?recipient=employee%27%20OR%20%271%27%3D%271&q=x")

    assert response.status_code == 200
    recipients = {row["recipient"] for row in response.json}
    assert "manager" not in recipients


def test_api_user_response_does_not_expose_password(client):
    login(client, "employee", "employee123")

    response = client.get("/api/v1/users/employee")

    assert response.status_code == 200
    assert "password" not in response.json


def test_api_mass_assignment_cannot_change_user_role(client):
    login(client, "employee", "employee123")

    response = client.put("/api/v1/users/employee", json={"role": "admin", "api_quota": 99999})

    assert response.status_code == 200
    assert response.json["role"] == "user"
    assert response.json["api_quota"] != 99999


def test_api_token_is_random_session_token_not_unsigned_base64_secret(client):
    login(client, "employee", "employee123")

    response = client.get("/api/v1/token?user=employee")

    assert response.status_code == 200
    token = response.json["token"]
    assert response.json["type"] == "session"
    try:
        decoded = base64.b64decode(token).decode()
    except Exception:
        decoded = ""
    assert "employee:" not in decoded


def test_api_cors_is_not_wildcard(client):
    response = client.options("/api/v1/users/employee", headers={"Origin": "https://evil.example"})

    assert response.status_code == 204
    assert response.headers.get("Access-Control-Allow-Origin") != "*"


def test_api_logs_require_admin_authentication(client):
    response = client.get("/api/v1/logs?q=compose")
    assert response.status_code == 401

    login(client, "employee", "employee123")
    regular = client.get("/api/v1/logs?q=compose")
    assert regular.status_code == 403
