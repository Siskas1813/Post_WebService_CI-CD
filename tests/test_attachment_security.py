import io
import os

from webmail.db import get_conn


def login(client, username="employee", password="employee123"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": "/dashboard"},
        follow_redirects=False,
    )


def upload_attachment(client, filename, payload=b"file-body", content_type="text/plain", mail_id="1"):
    return client.post(
        "/attachments",
        data={
            "mail_id": mail_id,
            "attachment": (io.BytesIO(payload), filename, content_type),
        },
        content_type="multipart/form-data",
    )


def latest_attachment(app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute("SELECT * FROM attachments ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row


def test_forbidden_extensions_are_rejected(client, app):
    login(client)

    samples = ["dropper.exe", "shell.php", "script.js", "object.pkl"]
    for filename in samples:
        response = upload_attachment(client, filename, b"payload", "application/octet-stream")
        assert response.status_code == 400

    conn = get_conn(app.config["DB_PATH"])
    count = conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0]
    conn.close()
    assert count == 0


def test_double_extension_upload_is_rejected(client):
    login(client)

    response = upload_attachment(client, "invoice.jpg.php", b"<?php echo 1; ?>", "application/octet-stream")

    assert response.status_code == 400


def test_upload_filename_is_sanitized_against_directory_traversal(client, app):
    login(client)
    outside_path = os.path.join(app.config["UPLOAD_TEST_ROOT"], "outside.txt")

    response = upload_attachment(client, "../outside.txt", b"safe content", "text/plain")

    assert response.status_code == 200
    assert not os.path.exists(outside_path)
    row = latest_attachment(app)
    assert row["filename"] == "outside.txt"
    assert os.path.exists(os.path.join(app.config["UPLOAD_DIR"], row["storage_path"]))


def test_identical_filename_uses_unique_storage_name(client, app):
    login(client)

    first = upload_attachment(client, "report.txt", b"original report", "text/plain")
    assert first.status_code == 200
    first_row = latest_attachment(app)

    second = upload_attachment(client, "report.txt", b"second report", "text/plain")
    assert second.status_code == 200
    second_row = latest_attachment(app)

    assert first_row["filename"] == second_row["filename"] == "report.txt"
    assert first_row["storage_path"] != second_row["storage_path"]


def test_large_file_upload_is_limited(client):
    login(client)
    payload = b"A" * (6 * 1024 * 1024)

    response = upload_attachment(client, "large.txt", payload, "text/plain")

    assert response.status_code == 413


def test_content_type_spoofing_is_rejected(client):
    login(client)
    html_payload = b"<html><script>alert('mail')</script></html>"

    response = upload_attachment(client, "notice.txt", html_payload, content_type="text/html")

    assert response.status_code == 400


def test_download_endpoint_rejects_path_traversal_without_login(client):
    response = client.get("/download", query_string={"path": "../app.py"})

    assert response.status_code in (400, 403, 404)


def test_user_cannot_download_another_users_attachment(client, app):
    conn = get_conn(app.config["DB_PATH"])
    row = conn.execute(
        """
        INSERT INTO mails(sender, recipient, cc, subject, body, status, created_at, priority, classification, label, is_read, starred, thread_id)
        VALUES ('ceo@corp.local', 'manager', '', 'Manager attachment mail', 'private', 'inbox', datetime('now'), 'high', 'restricted', 'API', 0, 0, 'thread-attachment')
        RETURNING id
        """
    ).fetchone()
    conn.commit()
    conn.close()

    login(client, "manager", "manager123")
    upload_response = upload_attachment(client, "manager-plan.txt", b"manager only data", "text/plain", mail_id=str(row["id"]))
    assert upload_response.status_code == 200
    attachment = latest_attachment(app)

    client.get("/logout")
    login(client, "employee", "employee123")
    response = client.get(f"/download/{attachment['id']}")

    assert response.status_code == 404
    assert response.data != b"manager only data"
