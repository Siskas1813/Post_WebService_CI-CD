import io

from webmail.db import get_conn


def login(client, username="employee", password="employee123"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": "/dashboard"},
        follow_redirects=False,
    )


def test_dashboard_without_session_redirects_to_login(client):
    response = client.get("/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/?next=/dashboard")


def test_regular_user_cannot_open_admin_area(client):
    login(client, "employee", "employee123")

    response = client.get("/admin/users", follow_redirects=False)

    assert response.status_code == 403


def test_sql_injection_in_login_is_rejected(client):
    response = client.post(
        "/login",
        data={"username": "employee' --", "password": "wrong", "next": "/dashboard"},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert "Location" not in response.headers


def test_pkl_upload_is_forbidden(client):
    login(client, "employee", "employee123")

    response = client.post(
        "/attachments",
        data={
            "mail_id": "1",
            "attachment": (io.BytesIO(b"not-a-safe-format"), "payload.pkl", "application/octet-stream"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_download_path_traversal_is_forbidden(client):
    response = client.get("/download", query_string={"path": "../Diplom/app.py"})

    assert response.status_code in (400, 403, 404)
    assert b"app.run" not in response.data


def test_api_without_authorization_returns_401(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute("SELECT id FROM mails LIMIT 1").fetchone()
    conn.close()

    response = client.get(f"/api/v1/mail/{row['id']}")

    assert response.status_code == 401


def test_api_other_users_mail_returns_403_or_404(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute(
        """
        INSERT INTO mails(sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
        VALUES ('ceo@corp.local', 'manager', '', 'Manager regression mail', 'private regression body', 'inbox', datetime('now'), 'high', 'restricted', 'API', 0, 0, 'thread-regression-api')
        RETURNING id
        """
    ).fetchone()
    conn.commit()
    conn.close()

    login(client, "employee", "employee123")
    response = client.get(f"/api/v1/mail/{row['id']}")

    assert response.status_code in (403, 404)
