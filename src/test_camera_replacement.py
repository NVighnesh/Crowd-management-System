import threading

import pytest

import src.api as api
from src.alerts.alert_manager import AlertManager
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


class FakeTransaction:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        self.database.started += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.database.rolled_back += 1
        else:
            self.database.committed += 1
        return False

    def execute(self, query, parameters):
        self.database.statements.append((query, parameters))


class FakeDatabase:
    def __init__(self):
        self.started = 0
        self.committed = 0
        self.rolled_back = 0
        self.statements = []

    def transaction(self):
        return FakeTransaction(self)


class FakeResultStore:
    def __init__(self):
        self.removed = []

    def remove(self, camera_id):
        self.removed.append(camera_id)

    def get_with_timestamp(self, camera_id):
        return None

    def restore(self, camera_id, entry):
        return None

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


class FailingStorage:
    def upload_file(self, **kwargs):
        from src.storage.supabase_storage import SupabaseStorageError

        raise SupabaseStorageError("storage unavailable")


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


@pytest.mark.anyio
async def test_failed_upload_returns_error_before_camera_update(monkeypatch):
    monkeypatch.setattr(api, "storage_service", FailingStorage())

    with pytest.raises(api.HTTPException) as error:
        await api._save_uploaded_camera_video(
            "CAM_FAILURE",
            FakeUpload(),
        )

    assert error.value.status_code == 503


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
    manager.database = FakeDatabase()
    manager.alert_manager = AlertManager()
    manager.result_store = FakeResultStore()
    manager._start_camera = lambda camera, zones_config=None: None

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

    assert manager.database.statements[3][1][2] == (
        f"supabase://camera-videos/{camera_id}/camera_1.mp4"
    )
    assert manager.database.committed == 1
    assert manager.database.rolled_back == 0
    assert [query.split()[1:4] for query, _ in manager.database.statements[:3]] == [
        ["FROM", "alerts", "WHERE"],
        ["FROM", "zone_results", "WHERE"],
        ["FROM", "zones", "WHERE"],
    ]
    assert all(
        parameters == (camera_id,)
        for _, parameters in manager.database.statements[:3]
    )


def test_metadata_only_update_preserves_existing_zones_and_alerts():
    camera_id = "CAM_METADATA"
    repository = FakeCameraRepository(
        {
            "camera_id": camera_id,
            "camera_name": "Existing",
            "source_type": "file",
            "source": "legacy/missing.mp4",
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
    manager.result_store = FakeResultStore()
    manager.alert_manager = type(
        "AlertManager",
        (),
        {"reset_camera": lambda *_: (_ for _ in ()).throw(
            AssertionError("metadata update reset alerts")
        )},
    )()
    manager.camera_manager = None
    manager._manager_lock = threading.RLock()
    manager._persist_camera = lambda camera: repository.save(
        camera_id=camera["id"],
        camera_name=camera["name"],
        source_type=camera["source_type"],
        source=camera["source"],
        loop=camera["loop"],
        enabled=camera["enabled"],
        owner_id=camera["owner_id"],
    )
    manager._sync_camera_manager = lambda: None

    manager.update_camera(
        {
            "id": camera_id,
            "name": "Renamed",
            "source_type": "file",
            "source": "legacy/missing.mp4",
            "loop": True,
            "enabled": False,
        }
    )

    assert repository.saved["source"] == "legacy/missing.mp4"


def test_replacement_failure_rolls_back_database_and_restores_worker():
    camera_id = "CAM_FAILURE"
    repository = FakeCameraRepository(
        {
            "camera_id": camera_id,
            "camera_name": "Existing",
            "source_type": "file",
            "source": "legacy/missing.mp4",
            "loop": 1,
            "enabled": 1,
            "owner_id": "operator",
        }
    )
    manager = object.__new__(MultiCameraManager)
    manager.storage_service = FakeStorage()
    manager.camera_repository = repository
    manager.database = FakeDatabase()
    manager.cameras = [{"id": camera_id, "source": "legacy/missing.mp4"}]
    manager.workers = {camera_id: object()}
    manager.pipelines = {}
    manager.result_store = FakeResultStore()
    manager.alert_manager = AlertManager()
    manager.camera_manager = None
    manager._manager_lock = threading.RLock()
    manager._logger = __import__("logging").getLogger(__name__)
    manager.stop_camera = lambda current_id: manager.workers.pop(current_id, None)
    manager._start_camera = lambda camera, zones_config=None: (
        (_ for _ in ()).throw(RuntimeError("replacement startup failed"))
    )

    with pytest.raises(RuntimeError, match="replacement startup failed"):
        manager.update_camera(
            {
                "id": camera_id,
                "name": "Replacement",
                "source_type": "file",
                "source": "supabase://camera-videos/CAM_FAILURE/new.mp4",
                "loop": True,
                "enabled": True,
            }
        )

    assert manager.database.committed == 0
    assert manager.database.rolled_back == 1
    assert repository.camera["source"] == "legacy/missing.mp4"


def test_replacement_starts_with_no_zones_for_whole_frame_counting():
    camera_id = "CAM_WHOLE_FRAME"
    repository = FakeCameraRepository(
        {
            "camera_id": camera_id,
            "camera_name": "Existing",
            "source_type": "file",
            "source": "old.mp4",
            "loop": 1,
            "enabled": 1,
            "owner_id": "operator",
        }
    )
    manager = object.__new__(MultiCameraManager)
    manager.storage_service = FakeStorage()
    manager.camera_repository = repository
    manager.database = FakeDatabase()
    manager.cameras = [{"id": camera_id, "source": "old.mp4"}]
    manager.workers = {}
    manager.pipelines = {}
    manager.result_store = FakeResultStore()
    manager.alert_manager = AlertManager()
    manager.camera_manager = None
    manager._manager_lock = threading.RLock()
    started = []
    manager._start_camera = lambda camera, zones_config=None: started.append(
        (camera, zones_config)
    )
    manager._sync_camera_manager = lambda: None

    manager.update_camera(
        {
            "id": camera_id,
            "name": "Replacement",
            "source_type": "file",
            "source": "supabase://camera-videos/CAM_WHOLE_FRAME/new.mp4",
            "loop": True,
            "enabled": True,
        }
    )

    assert started[0][1] == []
    assert manager.cameras[0]["source"].startswith("supabase://")
