from fastapi.testclient import TestClient

from src import api
from src.config.settings import get_cors_origins


def test_cors_origins_are_configurable(monkeypatch):
    monkeypatch.setenv(
        "CROWD_CORS_ORIGINS",
        "https://dashboard.example, https://admin.example",
    )
    assert get_cors_origins() == [
        "https://dashboard.example",
        "https://admin.example",
    ]


def test_default_health_endpoint_is_available():
    with TestClient(api.app) as client:
        response = client.get("/health")
    assert response.status_code in {200, 503}
    assert response.headers["content-type"].startswith("application/json")
