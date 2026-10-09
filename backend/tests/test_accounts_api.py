import pytest
from django.contrib.auth.models import User
from django.test import Client

PASSWORD = "correct-horse-battery"


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user("learner", email="Learner@Example.com", password=PASSWORD)


def _client() -> Client:
    return Client(enforce_csrf_checks=True)


def _with_csrf(client: Client) -> str:
    client.get("/api/auth/csrf")
    return client.cookies["csrftoken"].value


def _login(client: Client, token: str, **overrides: object) -> object:
    body = {"email": "learner@example.com", "password": PASSWORD, **overrides}
    return client.post(
        "/api/auth/login", body, content_type="application/json", headers={"X-CSRFToken": token}
    )


def test_profile_created_with_user(user: User) -> None:
    assert user.profile.time_zone == "UTC"  # type: ignore[attr-defined]


def test_login_requires_csrf(user: User) -> None:
    response = _client().post(
        "/api/auth/login",
        {"email": "learner@example.com", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_login_me_logout_flow(user: User) -> None:
    client = _client()
    token = _with_csrf(client)
    assert client.get("/api/auth/me").status_code == 401

    response = _login(client, token)
    assert response.status_code == 200  # type: ignore[attr-defined]
    assert response.json()["email"] == "Learner@example.com"  # type: ignore[attr-defined]

    token = client.cookies["csrftoken"].value
    assert client.get("/api/auth/me").status_code == 200
    out = client.post("/api/auth/logout", headers={"X-CSRFToken": token})
    assert out.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_logout_requires_csrf(user: User) -> None:
    client = _client()
    token = _with_csrf(client)
    _login(client, token)
    assert client.post("/api/auth/logout").status_code == 403


def test_bad_credentials_look_identical(user: User) -> None:
    client = _client()
    token = _with_csrf(client)
    wrong_pw = _login(client, token, password="nope")
    unknown = _login(client, token, email="nobody@example.com")
    assert wrong_pw.status_code == unknown.status_code == 401  # type: ignore[attr-defined]
    assert wrong_pw.json() == unknown.json()  # type: ignore[attr-defined]


def test_time_zone_captured_on_first_login_only(user: User) -> None:
    client = _client()
    token = _with_csrf(client)
    _login(client, token, time_zone="Europe/Sofia")
    user.profile.refresh_from_db()  # type: ignore[attr-defined]
    assert user.profile.time_zone == "Europe/Sofia"  # type: ignore[attr-defined]

    token = client.cookies["csrftoken"].value
    client.post("/api/auth/logout", headers={"X-CSRFToken": token})
    token = _with_csrf(client)
    _login(client, token, time_zone="Asia/Tokyo")
    user.profile.refresh_from_db()  # type: ignore[attr-defined]
    assert user.profile.time_zone == "Europe/Sofia"  # type: ignore[attr-defined]


def test_invalid_time_zone_ignored(user: User) -> None:
    client = _client()
    token = _with_csrf(client)
    _login(client, token, time_zone="Not/AZone")
    user.profile.refresh_from_db()  # type: ignore[attr-defined]
    assert user.profile.time_zone == "UTC"  # type: ignore[attr-defined]


def test_login_accepts_vite_dev_origin(user: User) -> None:
    client = _client()
    token = _with_csrf(client)
    response = client.post(
        "/api/auth/login",
        {"email": "learner@example.com", "password": PASSWORD},
        content_type="application/json",
        headers={"X-CSRFToken": token, "Origin": "http://127.0.0.1:5173"},
    )
    assert response.status_code == 200
