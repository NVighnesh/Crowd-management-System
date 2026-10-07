import pytest

from src.config.settings import get_runtime_mode
from src.video.api_only_manager import ApiOnlyCameraManager


def test_runtime_mode_defaults_to_api_only(monkeypatch):
    monkeypatch.delenv("CROWD_RUNTIME_MODE", raising=False)
    assert get_runtime_mode() == "API_ONLY"


def test_runtime_mode_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("CROWD_RUNTIME_MODE", "WORKER")
    with pytest.raises(ValueError, match="CROWD_RUNTIME_MODE"):
        get_runtime_mode()


def test_api_only_manager_does_not_create_workers():
    class CameraManager:
        cameras = []

        def replace_cameras(self, cameras):
            self.cameras = cameras

    class DatabaseService:
        database = object()
        camera_repository = object()
        crowd_repository = object()
        zone_repository = object()
        alert_repository = object()

    manager = ApiOnlyCameraManager(
        camera_manager=CameraManager(),
        database_service=DatabaseService(),
    )

    assert manager.runtime_mode == "API_ONLY"
    assert manager.workers == {}
    assert manager.pipelines == {}
    manager.setup()
