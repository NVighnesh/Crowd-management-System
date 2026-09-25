import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import src.api as api
from src.config.settings import load_config
from src.video.multi_camera_manager import MultiCameraManager


class FakePipeline:
    def __init__(self, camera_config, **kwargs):
        self.camera_config = camera_config
        self.released = False

    def setup(self):
        return None

    def release(self):
        self.released = True


class FakeWorker:
    def __init__(self, pipeline, **kwargs):
        self.pipeline = pipeline
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class FakeRepository:
    def __init__(self, camera):
        self.camera = camera

    def get(self, camera_id):
        if self.camera and self.camera["camera_id"] == camera_id:
            return dict(self.camera)
        return None


class FakeApiManager:
    def __init__(self, camera):
        self.camera_repository = FakeRepository(camera)
        self.calls = []

    def enable_camera(self, camera_id):
        self.calls.append(("enable", camera_id))

    def disable_camera(self, camera_id):
        self.calls.append(("disable", camera_id))

    def restart_camera(self, camera_id):
        self.calls.append(("restart", camera_id))

    def update_camera(self, camera):
        self.calls.append(("update", camera))


class FakeApiCameraManager:
    def get_camera(self, camera_id):
        return {
            "id": camera_id,
            "enabled": True,
        }


class Phase6CameraLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source_one = Path(self.temp_dir.name) / "one.mp4"
        self.source_two = Path(self.temp_dir.name) / "two.mp4"
        self.source_one.write_bytes(b"test")
        self.source_two.write_bytes(b"test")
        self.camera_id = "PHASE6_TEST_CAMERA"

        self.manager = MultiCameraManager(
            cameras=[],
            inference_config=self.config["inference"],
            tracking_config=self.config["tracking"],
            counting_config=self.config["counting"],
            processing_config=self.config["processing"],
        )
        self.manager.camera_repository.delete(self.camera_id)

    def tearDown(self):
        self.manager.delete_camera(self.camera_id) if self.manager.get_camera(self.camera_id) else None
        self.temp_dir.cleanup()

    def camera(self, **overrides):
        camera = {
            "id": self.camera_id,
            "name": "Original",
            "source_type": "file",
            "source": str(self.source_one),
            "loop": True,
            "enabled": False,
        }
        camera.update(overrides)
        return camera

    @patch("src.video.multi_camera_manager.CameraWorker", FakeWorker)
    @patch("src.video.multi_camera_manager.CameraPipeline", FakePipeline)
    def test_complete_lifecycle_and_rename_preserves_source(self):
        self.manager.add_camera(self.camera())
        self.assertEqual(self.manager.camera_repository.get(self.camera_id)["enabled"], 0)
        self.assertNotIn(self.camera_id, self.manager.workers)

        self.manager.update_camera({"id": self.camera_id, "name": "Renamed"})
        self.assertEqual(self.manager.get_camera(self.camera_id)["source"], str(self.source_one))
        self.assertNotIn(self.camera_id, self.manager.workers)

        self.manager.enable_camera(self.camera_id)
        self.assertIn(self.camera_id, self.manager.workers)
        old_worker = self.manager.workers[self.camera_id]

        self.manager.update_camera({
            **self.camera(),
            "name": "Updated",
            "source": str(self.source_two),
            "enabled": True,
        })
        self.assertIsNot(self.manager.workers[self.camera_id], old_worker)
        self.assertEqual(self.manager.get_camera(self.camera_id)["source"], str(self.source_two))

        self.manager.restart_camera(self.camera_id)
        self.assertEqual(len(self.manager.workers), 1)
        self.manager.disable_camera(self.camera_id)
        self.assertNotIn(self.camera_id, self.manager.workers)
        self.assertIsNotNone(self.manager.camera_repository.get(self.camera_id))
        self.manager.delete_camera(self.camera_id)
        self.assertIsNone(self.manager.camera_repository.get(self.camera_id))

    def test_invalid_source_and_duplicate_id_are_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.add_camera(self.camera(source="missing.mp4"))

        self.manager.add_camera(self.camera())
        with self.assertRaises(ValueError):
            self.manager.add_camera(self.camera())

    @patch("src.video.multi_camera_manager.CameraWorker", FakeWorker)
    @patch("src.video.multi_camera_manager.CameraPipeline", FakePipeline)
    def test_delete_running_camera_stops_worker_and_releases_pipeline(self):
        self.manager.add_camera(self.camera(enabled=True))
        worker = self.manager.workers[self.camera_id]
        pipeline = self.manager.pipelines[self.camera_id]

        self.manager.delete_camera(self.camera_id)

        self.assertTrue(worker.stopped)
        self.assertTrue(pipeline.released)
        self.assertNotIn(self.camera_id, self.manager.workers)
        self.assertNotIn(self.camera_id, self.manager.pipelines)
        self.assertIsNone(self.manager.camera_repository.get(self.camera_id))

    def test_api_enable_disable_restart_endpoints(self):
        camera = {
            "camera_id": self.camera_id,
            "camera_name": "API camera",
            "source_type": "file",
            "source": "videos/crowd.mp4",
            "loop": 1,
            "enabled": 0,
        }
        fake_manager = FakeApiManager(camera)

        @asynccontextmanager
        async def no_lifespan(_app):
            yield

        with patch.object(api.app.router, "lifespan_context", no_lifespan):
            with patch.object(api, "multi_camera_manager", fake_manager):
                with patch.object(api, "camera_manager", FakeApiCameraManager()):
                    with TestClient(api.app) as client:
                        self.assertEqual(
                            client.post(f"/cameras/{self.camera_id}/enable").status_code,
                            200,
                        )
                        self.assertEqual(
                            client.post(f"/cameras/{self.camera_id}/disable").status_code,
                            200,
                        )
                        self.assertEqual(
                            client.post(f"/cameras/{self.camera_id}/restart").status_code,
                            200,
                        )

        self.assertEqual(
            fake_manager.calls,
            [
                ("enable", self.camera_id),
                ("disable", self.camera_id),
                ("restart", self.camera_id),
            ],
        )

    def test_api_multipart_video_replacement_uses_upload_storage(self):
        source = Path("videos/crowd.mp4")
        self.assertTrue(source.is_file())
        upload_dir = Path("data") / "phase6_test_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        existing = {
            "camera_id": self.camera_id,
            "camera_name": "API camera",
            "source_type": "file",
            "source": "videos/crowd.mp4",
            "loop": 1,
            "enabled": 0,
        }
        fake_manager = FakeApiManager(existing)

        @asynccontextmanager
        async def no_lifespan(_app):
            yield

        try:
            with patch.object(api.app.router, "lifespan_context", no_lifespan):
                with patch.object(api, "multi_camera_manager", fake_manager):
                    with patch.object(api, "VIDEO_UPLOAD_DIR", api.PROJECT_ROOT / upload_dir):
                        with TestClient(api.app) as client:
                            response = client.put(
                                f"/cameras/{self.camera_id}",
                                data={
                                    "camera_name": "Replaced",
                                    "source_type": "file",
                                    "enabled": "false",
                                    "loop": "true",
                                },
                                files={
                                    "video_file": (
                                        source.name,
                                        source.read_bytes(),
                                        "video/mp4",
                                    )
                                },
                            )

            self.assertEqual(response.status_code, 200)
            update = fake_manager.calls[-1][1]
            stored_path = api.PROJECT_ROOT / update["source"]
            self.assertTrue(stored_path.is_file())
            self.assertEqual(stored_path.read_bytes(), source.read_bytes())
        finally:
            for path in upload_dir.glob("*"):
                path.unlink()
            upload_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
