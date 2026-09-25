import json
import uuid

import pytest
from fastapi.testclient import TestClient

from src.security.auth import hash_password


def _login(client, username, password):
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_registration_always_creates_operator(monkeypatch):
    monkeypatch.setenv("CROWD_SECURITY_ENABLED", "true")
    monkeypatch.setenv("CROWD_AUTH_SECRET", "a" * 32)
    monkeypatch.setenv("CROWD_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CROWD_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("CROWD_USERS_JSON", "[]")
    from src import api

    username = f"owner-phase-{uuid.uuid4().hex[:8]}"
    with TestClient(api.app) as client:
        response = client.post(
            "/auth/register",
            json={"username": username, "password": "owner-password"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "OPERATOR"
        assert _login(client, username, "owner-password")


def test_operator_cannot_read_another_operators_camera(monkeypatch):
    monkeypatch.setenv("CROWD_SECURITY_ENABLED", "true")
    monkeypatch.setenv("CROWD_AUTH_SECRET", "b" * 32)
    monkeypatch.setenv("CROWD_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CROWD_ADMIN_PASSWORD", "admin-password")
    owner_b_name = f"owner-b-{uuid.uuid4().hex[:8]}"
    camera_id = f"OWNER_A_CAMERA_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv(
        "CROWD_USERS_JSON",
        json.dumps([
            {
                "username": "owner-a",
                "role": "OPERATOR",
                "password_hash": hash_password("owner-a-password"),
            },
            {
                "username": owner_b_name,
                "role": "OPERATOR",
                "password_hash": hash_password("owner-b-password"),
            },
        ]),
    )
    from src import api

    with TestClient(api.app) as client:
        admin = _login(client, "admin", "admin-password")
        created = client.post(
            "/cameras",
            headers=admin,
            json={
                "camera_id": camera_id,
                "camera_name": "Owner A",
                "source_type": "file",
                "source": "videos/crowd.mp4",
                "loop": True,
                "enabled": False,
            },
        )
        assert created.status_code == 200
        owner_b = _login(client, owner_b_name, "owner-b-password")
        assert client.get(
            f"/database/cameras/{camera_id}",
            headers=owner_b,
        ).status_code == 404
        assert client.delete(
            f"/cameras/{camera_id}",
            headers=admin,
        ).status_code == 200


def test_cross_operator_resource_matrix_and_admin_context(monkeypatch):
    monkeypatch.setenv("CROWD_SECURITY_ENABLED", "true")
    monkeypatch.setenv("CROWD_AUTH_SECRET", "c" * 32)
    monkeypatch.setenv("CROWD_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CROWD_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv(
        "CROWD_USERS_JSON",
        json.dumps([
            {"username": "operator-a", "role": "OPERATOR", "password_hash": hash_password("a-password")},
            {"username": "operator-b", "role": "OPERATOR", "password_hash": hash_password("b-password")},
        ]),
    )
    from src import api

    camera_id = f"AUTH_MATRIX_{uuid.uuid4().hex[:10]}"
    zone_id = f"ZONE_{uuid.uuid4().hex[:8]}"
    with TestClient(api.app) as client:
        admin = _login(client, "admin", "admin-password")
        selected_admin = {**admin, "X-Operator-Username": "operator-a"}
        created = client.post(
            "/cameras",
            headers=selected_admin,
            json={
                "camera_id": camera_id,
                "camera_name": "Operator A camera",
                "source_type": "file",
                "source": "videos/crowd.mp4",
                "loop": True,
                "enabled": False,
            },
        )
        assert created.status_code == 200
        assert client.post(
            f"/cameras/{camera_id}/zones",
            headers=selected_admin,
            json={
                "zone_id": zone_id,
                "zone_name": "A zone",
                "polygon": [[0, 0], [10, 0], [10, 10]],
                "threshold": 2,
            },
        ).status_code == 200

        operator_b = _login(client, "operator-b", "b-password")
        spoofed_b = {**operator_b, "X-Operator-Username": "operator-a"}
        protected_paths = [
            f"/database/cameras/{camera_id}",
            f"/database/cameras/{camera_id}/crowd",
            f"/database/cameras/{camera_id}/history",
            f"/database/cameras/{camera_id}/analytics",
            f"/database/cameras/{camera_id}/zones/{zone_id}",
            f"/database/cameras/{camera_id}/alerts",
            f"/cameras/{camera_id}/zones",
            f"/cameras/{camera_id}/status",
            f"/cameras/{camera_id}/overview",
            f"/cameras/{camera_id}/frame",
            f"/cameras/{camera_id}/stream",
        ]
        for path in protected_paths:
            response = client.get(path, headers=spoofed_b)
            assert response.status_code in {403, 404, 503}
            assert "Operator A camera" not in response.text

        cameras_response = client.get("/cameras", headers=spoofed_b)
        assert cameras_response.status_code in {403, 200}
        if cameras_response.status_code == 200:
            assert cameras_response.json()["cameras"] == []
        database_cameras_response = client.get("/database/cameras", headers=spoofed_b)
        assert database_cameras_response.status_code in {403, 200}
        if database_cameras_response.status_code == 200:
            assert database_cameras_response.json()["cameras"] == []
        overview_response = client.get("/system/overview", headers=spoofed_b)
        assert overview_response.status_code in {403, 200}
        if overview_response.status_code == 200:
            assert overview_response.json()["cameras"] == []

        admin_view = client.get(f"/database/cameras/{camera_id}", headers=selected_admin)
        assert admin_view.status_code == 200
        assert admin_view.json()["camera"]["owner_id"] == "operator-a"


def test_operator_lifecycle_and_final_admin_protection():
    from src.security.auth import AuthService, InactiveAccountError, hash_password

    service = AuthService(
        {
            "enabled": True,
            "secret": "d" * 32,
            "admin_username": "admin",
            "admin_password": "admin-password",
        }
    )
    service.users["operator-a"] = (hash_password("password"), "OPERATOR")
    service.active_users["operator-a"] = True
    assert service.authenticate("operator-a", "password").role == "OPERATOR"
    assert service.authenticate("operator-a", "wrong-password") is None

    token = service.issue_token(service.authenticate("operator-a", "password"))
    service.set_user_active("operator-a", False)
    with pytest.raises(InactiveAccountError):
        service.authenticate("operator-a", "password")
    with pytest.raises(ValueError):
        service.verify_token(token)

    service.set_user_active("operator-a", True)
    service.promote_user("operator-a")
    service.users["admin-2"] = (hash_password("admin-2-password"), "ADMIN")
    service.active_users["admin-2"] = True
    service.demote_user("operator-a")
    assert service.users["operator-a"][1] == "OPERATOR"
    service.demote_user("admin")
    with pytest.raises(ValueError):
        service.set_user_active("admin-2", False)
    with pytest.raises(ValueError):
        service.delete_user("admin-2")
