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
