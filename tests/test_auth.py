def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_login_success(client):
    response = client.post(
        "/login",
        data={"username": "testuser", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_invalid_password(client):
    response = client.post(
        "/login",
        data={"username": "testuser", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_login_unknown_user(client):
    response = client.post(
        "/login",
        data={"username": "nobody", "password": "password123"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in" in response.data or response.request.path == "/login"


def test_logout(auth_client):
    response = auth_client.get("/logout", follow_redirects=True)
    assert b"logged out" in response.data.lower()


def test_app_name_on_login_and_dashboard(client):
    page = client.get("/login").data
    assert b"<title>Login - Moraccle Task &amp; Meeting Tracker</title>" in page
    assert b"Moraccle" in page

    client.post("/login", data={"username": "testuser", "password": "password123"})
    page = client.get("/dashboard").data
    assert b"Dashboard - Moraccle Task &amp; Meeting Tracker" in page
    assert b"sidebar-brand-name\">Moraccle" in page


def test_login_error_shown_inside_form(client):
    page = client.post("/login", data={"username": "x", "password": "y"}).data
    assert b'class="auth-alert auth-alert-danger"' in page
    # Only the in-form message is rendered, not the page-level flash bar too.
    assert b"flash-container" not in page


def test_login_page_has_theme_toggle(client):
    page = client.get("/login").data
    assert b'id="themeToggleBtn"' in page
    assert b"js/theme.js" in page
