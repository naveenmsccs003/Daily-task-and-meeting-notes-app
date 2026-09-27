from models import User


def _login(client, username, password="password123"):
    client.get("/logout")
    return client.post("/login", data={"username": username, "password": password})


def test_non_admin_cannot_access_users_page(auth_client):
    # the default test user created in conftest has role 'user'
    response = auth_client.get("/users")
    assert response.status_code == 403


def test_admin_can_view_users_list(app, client):
    with app.app_context():
        User.create(username="boss", password="password123", full_name="Boss", role="admin")
    _login(client, "boss")
    response = client.get("/users")
    assert response.status_code == 200
    assert b"boss" in response.data


def test_admin_can_create_user(app, client):
    with app.app_context():
        User.create(username="boss2", password="password123", role="admin")
    _login(client, "boss2")

    response = client.post(
        "/users/create",
        data={
            "username": "newhire",
            "password": "password123",
            "full_name": "New Hire",
            "email": "",
            "role": "user",
        },
        follow_redirects=True,
    )
    assert b"created successfully" in response.data

    with app.app_context():
        created = User.get_by_username("newhire")
        assert created is not None
        assert created.role == "user"
        assert created.is_active


def test_create_user_duplicate_username_fails(app, client):
    with app.app_context():
        User.create(username="boss3", password="password123", role="admin")
        User.create(username="taken", password="password123", role="user")
    _login(client, "boss3")

    response = client.post(
        "/users/create",
        data={"username": "taken", "password": "password123", "role": "user"},
        follow_redirects=True,
    )
    assert b"already taken" in response.data


def test_create_user_missing_password_fails(app, client):
    with app.app_context():
        User.create(username="boss4", password="password123", role="admin")
    _login(client, "boss4")

    response = client.post(
        "/users/create",
        data={"username": "someone", "password": "", "role": "user"},
        follow_redirects=True,
    )
    assert b"Password is required" in response.data


def test_admin_cannot_deactivate_own_account(app, client):
    with app.app_context():
        User.create(username="boss5", password="password123", role="admin")
    _login(client, "boss5")

    with app.app_context():
        me = User.get_by_username("boss5")

    response = client.post(f"/users/{me.id}/toggle-active", follow_redirects=True)
    assert b"cannot deactivate your own account" in response.data

    with app.app_context():
        still_active = User.get_by_username("boss5")
        assert still_active.is_active


def test_admin_cannot_change_own_role_via_edit(app, client):
    with app.app_context():
        User.create(username="onlyadmin", password="password123", role="admin")
    _login(client, "onlyadmin")

    with app.app_context():
        me = User.get_by_username("onlyadmin")

    client.post(
        f"/users/{me.id}/edit",
        data={"full_name": "Renamed", "email": "", "role": "user"},
        follow_redirects=True,
    )

    with app.app_context():
        unchanged = User.get_by_username("onlyadmin")
        # role is forced to stay 'admin' regardless of what the form posted,
        # but other fields (full_name) still update normally.
        assert unchanged.role == "admin"
        assert unchanged.full_name == "Renamed"


def test_admin_can_deactivate_another_admin_when_not_the_last_one(app, client):
    with app.app_context():
        User.create(username="admin_a", password="password123", role="admin")
        User.create(username="admin_b", password="password123", role="admin")
    _login(client, "admin_a")

    with app.app_context():
        target = User.get_by_username("admin_b")

    response = client.post(f"/users/{target.id}/toggle-active", follow_redirects=True)
    assert b"deactivated" in response.data

    with app.app_context():
        deactivated = User.get_by_username("admin_b")
        assert not deactivated.is_active


def test_deactivated_user_cannot_login(app, client):
    with app.app_context():
        User.create(username="boss6", password="password123", role="admin")
        User.create(username="tobedeactivated", password="password123", role="user")
    _login(client, "boss6")

    with app.app_context():
        target = User.get_by_username("tobedeactivated")
    client.post(f"/users/{target.id}/toggle-active")

    response = _login(client, "tobedeactivated")
    response = client.get("/dashboard", follow_redirects=True)
    assert b"Please log in" in response.data or response.request.path == "/login"
