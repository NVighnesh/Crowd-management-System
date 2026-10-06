import threading

import pytest

import src.api as api
from src.video.multi_camera_manager import MultiCameraManager


class FakeStorage:
    configured = True

    @staticmethod
    def is_storage_source(source):
        return str(source or "").startswith("supabase://")


class FakeCameraRepository:
    def __init__(self, camera):
        self.camera = dict(camera)
        self.saved = None

    def get(self, camera_id):
        if camera_id == self.camera["camera_id"]:
            return dict(self.camera)
        return None

    def save(self, **camera):
        self.saved = dict(camera)
        self.camera.update(
            {
                "camera_id": camera["camera_id"],
                "camera_name": camera["camera_name"],
                "source_type": camera["source_type"],
                "source": camera["source"],
                "loop": int(camera["loop"]),
                "enabled": int(camera["enabled"]),
                "owner_id": camera["owner_id"],
            }
        )


class FakeUpload:
    filename = "camera 1.mp4"
    content_type = "video/mp4"

    async def read(self):
        return b"replacement video"


class RecordingStorage:
    def __init__(self):
        self.calls = []

    def upload_file(self, **kwargs):
        self.calls.append(kwargs)
        return "supabase://camera-videos/CAM_TEST_20260925/camera_1.mp4"


@pytest.mark.anyio
async def test_uploaded_replacement_uses_supabase_storage(monkeypatch):
    storage = RecordingStorage()
    monkeypatch.setattr(api, "storage_service", storage)

    source = await api._save_uploaded_camera_video(
        "CAM_TEST_20260925",
        FakeUpload(),
    )

    assert source == (
        "supabase://camera-videos/CAM_TEST_20260925/camera_1.mp4"
    )
    assert storage.calls[0]["camera_id"] == "CAM_TEST_20260925"
    assert storage.calls[0]["filename"] == "camera 1.mp4"
    assert storage.calls[0]["content"] == b"replacement video"


def test_replacement_source_does_not_validate_legacy_local_source():
    camera_id = "CAM_TEST_20260925"
    repository = FakeCameraRepository(
        {
            "camera_id": camera_id,
            "camera_name": "Legacy camera",
            "source_type": "file",
            "source": rf"data\camera_uploads\{camera_id}_camera_1.mp4",
            "loop": 1,
            "enabled": 0,
            "owner_id": "operator",
        }
    )
    manager = object.__new__(MultiCameraManager)
    manager.storage_service = FakeStorage()
    manager.camera_repository = repository
    manager.cameras = []
    manager.workers = {}
    manager.pipelines = {}
    manager.result_store = type("ResultStore", (), {"remove": lambda *_: None})()
    manager.camera_manager = None
    manager._manager_lock = threading.RLock()

    manager.update_camera(
        {
            "id": camera_id,
            "name": "Replacement camera",
            "source_type": "file",
            "source": f"supabase://camera-videos/{camera_id}/camera_1.mp4",
            "loop": True,
            "enabled": False,
        }
    )

    assert repository.saved["source"] == (
        f"supabase://camera-videos/{camera_id}/camera_1.mp4"
    )
