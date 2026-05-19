from http.cookies import SimpleCookie
from pathlib import Path


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=()",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cache-Control": "no-store",
}


def login(client, username="employee", password="employee123"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": "/dashboard"},
        follow_redirects=False,
    )


def assert_security_headers(response):
    for name, expected_fragment in SECURITY_HEADERS.items():
        assert name in response.headers
        assert expected_fragment in response.headers[name]


def test_main_pages_set_required_security_headers(client):
    response = client.get("/")

    assert response.status_code == 200
    assert_security_headers(response)


def test_authenticated_pages_set_required_security_headers(client):
    login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert_security_headers(response)


def test_api_responses_set_required_security_headers(client):
    response = client.get("/api/v1/config")

    assert response.status_code == 401
    assert_security_headers(response)


def test_session_cookie_has_httponly_and_samesite_flags(client):
    response = login(client)
    cookie_header = response.headers.get("Set-Cookie", "")
    cookie = SimpleCookie(cookie_header)

    assert "session" in cookie
    session_cookie = cookie["session"]
    assert session_cookie["httponly"]
    assert session_cookie["samesite"] == "Lax"


def test_api_cors_does_not_allow_any_origin_and_headers(client):
    response = client.options("/api/v1/users/employee", headers={"Origin": "https://evil.example"})

    assert response.status_code == 204
    assert response.headers.get("Access-Control-Allow-Origin") != "*"
    assert response.headers.get("Access-Control-Allow-Headers") != "*"


def test_application_entrypoint_runs_with_debug_mode_disabled():
    source = Path("app.py").read_text(encoding="utf-8")

    assert "debug=False" in source
    assert "debug=True" not in source


def test_sql_console_does_not_return_internal_error_details_to_user(client):
    login(client, "admin", "admin123")

    response = client.post("/admin/sql", data={"query": "SELECT * FROM table_that_does_not_exist"})

    assert response.status_code == 200
    assert b"Only the approved diagnostic query is allowed." in response.data
    assert b"no such table" not in response.data.lower()
