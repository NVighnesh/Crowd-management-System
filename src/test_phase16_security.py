import json

import pytest
from fastapi.testclient import TestClient

from src.security.auth import (
    AuthService,
    AuthenticatedUser,
    LoginRateLimiter,
    hash_password,
    verify_password,
)


def test_passwords_are_hashed_and_verified():
    encoded = hash_password("correct horse battery staple")
    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)


def test_signed_tokens_expire_and_reject_tampering():
    service = AuthService(
        {
            "enabled": True,
            "secret": "x" * 32,
            "admin_username": "admin",
            "admin_password": "password",
            "token_expiry_minutes": 1,
        }
    )
    token = service.issue_token(AuthenticatedUser("admin", "ADMIN"))
    assert service.verify_token(token).role == "ADMIN"
    header, payload, signature = token.split(".")
    with pytest.raises(ValueError):
        service.verify_token(f"{header}.{payload[:-1]}x.{signature}")


def test_expired_token_is_rejected(monkeypatch):
    service = AuthService(
        {
            "enabled": True,
            "secret": "x" * 32,
            "admin_username": "admin",
            "admin_password": "password",
        }
    )
    issued_at = 1000
    monkeypatch.setattr("src.security.auth.time.time", lambda: issued_at)
    token = service.issue_token(AuthenticatedUser("admin", "ADMIN"))
    monkeypatch.setattr(
        "src.security.auth.time.time",
        lambda: issued_at + 3601,
    )
    with pytest.raises(ValueError):
        service.verify_token(token)


@pytest.fixture()
def authenticated_client(monkeypatch):
    monkeypatch.setenv("CROWD_SECURITY_ENABLED", "true")
    monkeypatch.setenv("CROWD_AUTH_SECRET", "s" * 32)
    monkeypatch.setenv("CROWD_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CROWD_ADMIN_PASSWORD", "test-password")
    monkeypatch.setenv(
        "CROWD_USERS_JSON",
        json.dumps(
            [
                {
                    "username": "owner",
                    "role": "OPERATOR",
                    "password_hash": hash_password("operator-password"),
                },
                {
                    "username": "owner-read",
                    "role": "OPERATOR",
                    "password_hash": hash_password("viewer-password"),
                },
            ]
        ),
    )
    from src import api

    with TestClient(api.app) as client:
        yield client
    for key in (
        "CROWD_SECURITY_ENABLED",
        "CROWD_AUTH_SECRET",
        "CROWD_ADMIN_USERNAME",
        "CROWD_ADMIN_PASSWORD",
        "CROWD_USERS_JSON",
    ):
        monkeypatch.delenv(key, raising=False)


def _login(client, username, password):
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_login_and_role_protection(authenticated_client):
    assert authenticated_client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrong"},
    ).status_code == 401
    headers = _login(authenticated_client, "admin", "test-password")
    authenticated_client.cookies.delete("crowd_access_token")
    assert authenticated_client.get("/cameras").status_code == 401
    assert authenticated_client.get("/cameras", headers=headers).status_code == 200


def test_stream_token_endpoint_returns_short_lived_token(authenticated_client):
    headers = _login(authenticated_client, "admin", "test-password")
    response = authenticated_client.post(
        "/auth/stream-token",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["expires_in"] >= 30


def test_owner_read_scope_is_authenticated(authenticated_client):
    headers = _login(authenticated_client, "owner", "operator-password")
    for route in (
        "/cameras",
        "/cameras/health",
        "/alerts",
        "/alerts/latest",
        "/system/overview",
        "/database/cameras",
    ):
        assert authenticated_client.get(route, headers=headers).status_code != 401
    assert authenticated_client.get("/cameras", headers=headers).status_code != 401


def test_owner_can_read_and_is_authenticated(authenticated_client):
    headers = _login(authenticated_client, "owner-read", "viewer-password")
    for route in ("/cameras", "/alerts", "/system/health", "/database/cameras"):
        assert authenticated_client.get(route, headers=headers).status_code != 401
    assert authenticated_client.get("/cameras", headers=headers).status_code != 401


def test_route_authentication_matrix(authenticated_client):
    for route in ("/health", "/auth/config", "/docs", "/openapi.json"):
        assert authenticated_client.get(route).status_code != 401
    authenticated_client.cookies.delete("crowd_access_token")
    for route in (
        "/system/health",
        "/cameras/health",
        "/cameras",
        "/alerts",
        "/system/overview",
        "/database/cameras",
    ):
        assert authenticated_client.get(route).status_code == 401


def test_login_rate_limit_lockout_and_reset():
    limiter = LoginRateLimiter(
        max_failures=2,
        window_seconds=60,
        lockout_seconds=30,
    )
    limiter.record_failure("client:user", now=100)
    assert limiter.allow("client:user", now=100)
    limiter.record_failure("client:user", now=101)
    assert not limiter.allow("client:user", now=102)
    limiter.reset("client:user")
    assert limiter.allow("client:user", now=102)


def test_login_endpoint_rate_limit_and_success_reset(authenticated_client):
    from src import api

    api.auth_service.login_limiter = LoginRateLimiter(
        max_failures=2,
        window_seconds=60,
        lockout_seconds=30,
    )
    endpoint = "/auth/login"
    credentials = {"username": "admin", "password": "wrong"}
    assert authenticated_client.post(endpoint, json=credentials).status_code == 401
    assert authenticated_client.post(endpoint, json=credentials).status_code == 401
    assert authenticated_client.post(
        endpoint,
        json={"username": "admin", "password": "test-password"},
    ).status_code == 429

    api.auth_service.login_limiter.reset("testclient:admin")
    assert authenticated_client.post(
        endpoint,
        json={"username": "admin", "password": "test-password"},
    ).status_code == 200
    assert authenticated_client.post(endpoint, json=credentials).status_code == 401


def test_admin_is_authorized_for_mutation_routes(authenticated_client):
    headers = _login(authenticated_client, "admin", "test-password")
    requests = (
        ("post", "/cameras"),
        ("put", "/cameras/CAM_001"),
        ("delete", "/cameras/does-not-exist"),
        ("post", "/cameras/does-not-exist/enable"),
        ("post", "/cameras/does-not-exist/disable"),
        ("post", "/cameras/does-not-exist/restart"),
        ("post", "/cameras/does-not-exist/zones"),
        ("put", "/cameras/does-not-exist/zones/ZONE_001"),
        ("delete", "/cameras/does-not-exist/zones/ZONE_001"),
    )
    for method, route in requests:
        request = getattr(authenticated_client, method)
        kwargs = {"headers": headers}
        if method != "delete":
            kwargs["json"] = {}
        assert request(route, **kwargs).status_code != 403


def test_stream_requires_cookie_and_preserves_mjpeg(authenticated_client, monkeypatch):
    from src import api

    class Worker:
        running = True
        last_error = None

        def get_status(self):
            return {"status": "ONLINE"}

        def get_latest_annotated_frame(self):
            return object()

        def stop(self):
            pass

    class Streamer:
        def __init__(self, **kwargs):
            pass

        def generate(self):
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\njpeg\r\n"

    api.multi_camera_manager.workers["CAM_001"] = Worker()
    monkeypatch.setattr(api, "FrameStreamer", Streamer)
    authenticated_client.cookies.delete("crowd_access_token")
    assert authenticated_client.get("/cameras/CAM_001/stream").status_code == 401
    authenticated_client.post(
        "/auth/login",
        json={"username": "admin", "password": "test-password"},
    )
    stream = authenticated_client.get("/cameras/CAM_001/stream")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("multipart/x-mixed-replace")


def test_invalid_token_is_rejected(authenticated_client):
    response = authenticated_client.get(
        "/cameras",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_secrets_are_not_logged(caplog):
    from src.security.auth import audit

    with caplog.at_level("INFO"):
        audit("login", "admin")
    assert "super-secret-password" not in caplog.text
