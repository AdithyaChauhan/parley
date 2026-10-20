ANA = {"name": "Ana Silva", "email": "ana@example.com", "password": "secret123"}


def _sign_up(client) -> str:
    """Sign Ana up and return her access token."""
    response = client.post("/api/auth/signup", json=ANA)
    assert response.status_code == 201
    return response.json()["access_token"]


def test_signup_gives_201_and_same_email_again_gives_409(client):
    response = client.post("/api/auth/signup", json=ANA)

    assert response.status_code == 201
    assert response.json()["access_token"]
    assert client.cookies.get("refresh_token")

    assert client.post("/api/auth/signup", json=ANA).status_code == 409


def test_login_with_right_password_works(client):
    _sign_up(client)

    response = client.post("/api/auth/login", json={"email": ANA["email"], "password": ANA["password"]})

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_wrong_password_and_unknown_email_both_give_401(client):
    _sign_up(client)

    wrong_password = client.post(
        "/api/auth/login", json={"email": ANA["email"], "password": "wrong-password"}
    )
    unknown_email = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": ANA["password"]}
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # The same reply both times, so it doesn't reveal which emails have accounts.
    assert wrong_password.json() == unknown_email.json()


def test_me_works_with_token_and_gives_401_without(client):
    token = _sign_up(client)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == ANA["email"]
    assert "password_hash" not in response.json()
    assert client.get("/api/auth/me").status_code == 401


def test_refresh_works_with_cookie(client):
    _sign_up(client)
    old_cookie = client.cookies.get("refresh_token")

    response = client.post("/api/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]
    # Rotation: the old refresh token was swapped for a new one.
    assert client.cookies.get("refresh_token") != old_cookie


def test_refresh_after_logout_gives_401(client):
    _sign_up(client)
    cookie = client.cookies.get("refresh_token")

    assert client.post("/api/auth/logout").status_code == 204

    # Log-out also deletes the cookie from this test browser. Put it back by
    # hand, so the 401 proves the session was closed, not just that the cookie is gone.
    client.cookies.set("refresh_token", cookie)
    assert client.post("/api/auth/refresh").status_code == 401
