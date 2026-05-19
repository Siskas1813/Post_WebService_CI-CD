from http.cookies import SimpleCookie

from webmail.db import get_conn


def login(client, username="employee", password="employee123"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": "/dashboard"},
        follow_redirects=False,
    )


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert "/?next=/dashboard" in response.headers["Location"]


def test_admin_users_forbidden_for_regular_user(client):
    login(client, "employee", "employee123")

    response = client.get("/admin/users", follow_redirects=False)

    assert response.status_code == 403


def test_admin_sql_forbidden_for_regular_user(client):
    login(client, "employee", "employee123")

    response = client.get("/admin/sql")

    assert response.status_code == 403


def test_admin_user_can_access_admin_pages(client):
    login(client, "admin", "admin123")

    response = client.get("/admin/users")

    assert response.status_code == 200


def test_logout_terminates_session(client):
    login(client, "employee", "employee123")
    before_logout = client.get("/dashboard")
    assert before_logout.status_code == 200

    client.get("/logout")
    after_logout = client.get("/dashboard", follow_redirects=False)

    assert after_logout.status_code == 302
    assert "/?next=/dashboard" in after_logout.headers["Location"]


def test_session_cookie_has_secure_baseline_flags(client):
    response = login(client, "employee", "employee123")
    cookie_header = response.headers.get("Set-Cookie", "")
    cookie = SimpleCookie(cookie_header)

    assert "session" in cookie
    session_cookie = cookie["session"]
    assert session_cookie["httponly"]
    assert session_cookie["samesite"] == "Lax"


def test_idor_regular_user_cannot_open_manager_message(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute(
        """
        INSERT INTO mails(sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
        VALUES ('ceo@corp.local', 'manager', '', 'Manager only message', 'private body', 'inbox', datetime('now'), 'high', 'confidential', 'Audit', 0, 0, 'thread-idor')
        RETURNING id
        """
    ).fetchone()
    conn.commit()
    conn.close()

    login(client, "employee", "employee123")
    response = client.get(f"/mail/{row['id']}")

    assert response.status_code == 404
    assert b"Manager only message" not in response.data


def test_api_mail_detail_requires_login(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute("SELECT id FROM mails LIMIT 1").fetchone()
    conn.close()

    response = client.get(f"/api/v1/mail/{row['id']}")

    assert response.status_code == 401


def test_sql_injection_does_not_bypass_login(client):
    response = client.post(
        "/login",
        data={"username": "employee' --", "password": "wrong", "next": "/dashboard"},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert "Location" not in response.headers
