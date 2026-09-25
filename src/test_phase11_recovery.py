import time
from pathlib import Path
from unittest.mock import patch

from src.config.settings import load_config
from src.video.camera_worker import CameraWorker
from src.video.multi_camera_manager import MultiCameraManager


class RecoveryPipeline:
    attempts = 0

    def __init__(self, camera_config, **kwargs):
        self.camera_config = camera_config
        self.released = False

    def setup(self):
        RecoveryPipeline.attempts += 1
        if RecoveryPipeline.attempts == 1:
            raise RuntimeError("source open failed")

    def release(self):
        self.released = True


class RecoveryWorker:
    def __init__(self, pipeline, **kwargs):
        self.pipeline = pipeline
        self.running = False
        self.last_error = None

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def get_status(self):
        return {
            "status": "ONLINE" if self.running else "OFFLINE",
            "last_error": self.last_error,
        }


class ExhaustedPipeline(RecoveryPipeline):
    def setup(self):
        raise RuntimeError("source remains unavailable")


class FlakySource:
    def __init__(self):
        self.reads = 0
        self.opened = True

    def read(self):
        self.reads += 1
        if self.reads <= 3:
            return False, None
        return True, self.reads

    def is_opened(self):
        return self.opened

    def release(self):
        self.opened = False


class FlakyPipeline:
    def __init__(self):
        self.source = FlakySource()
        self.frames = []

    def process_frame(self, frame):
        self.frames.append(frame)
        return None


class StaleWorker(RecoveryWorker):
    def get_status(self):
        return {
            "status": "STALE",
            "last_error": "no frames",
        }


def make_manager(tmp_path, source_name="camera.mp4"):
    config = load_config()
    processing = {
        **config["processing"],
        "recovery_max_attempts": 2,
        "recovery_retry_delay_seconds": 0.01,
        "recovery_backoff_multiplier": 1,
        "recovery_poll_interval_seconds": 0.01,
    }
    source = Path(tmp_path) / source_name
    source.write_bytes(b"source")
    manager = MultiCameraManager(
        cameras=[{
            "id": "RECOVERY_CAM",
            "name": "Recovery",
            "source_type": "file",
            "source": str(source),
            "enabled": True,
        }],
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=processing,
    )
    return manager


def test_source_open_failure_recovers_without_duplicate_worker(tmp_path):
    manager = make_manager(tmp_path)
    try:
        RecoveryPipeline.attempts = 0
        with patch(
            "src.video.multi_camera_manager.CameraPipeline",
            RecoveryPipeline,
        ), patch(
            "src.video.multi_camera_manager.CameraWorker",
            RecoveryWorker,
        ):
            manager.setup()
            deadline = time.time() + 1
            while time.time() < deadline and "RECOVERY_CAM" not in manager.workers:
                time.sleep(0.01)

            assert "RECOVERY_CAM" in manager.workers
            assert len(manager.workers) == 1
            assert len(manager.pipelines) == 1
            assert manager.get_camera("RECOVERY_CAM")["enabled"] is True
            assert manager._recovery_state == {}
    finally:
        manager.release()


def test_recovery_exhaustion_keeps_camera_isolated_and_unhealthy(tmp_path):
    manager = make_manager(tmp_path)
    try:
        with patch(
            "src.video.multi_camera_manager.CameraPipeline",
            ExhaustedPipeline,
        ):
            manager.setup()
            deadline = time.time() + 1
            while time.time() < deadline:
                state = manager._recovery_state.get("RECOVERY_CAM", {})
                if state.get("attempts") >= 2:
                    break
                time.sleep(0.01)

            state = manager._recovery_state["RECOVERY_CAM"]
            assert state["attempts"] == 2
            assert "RECOVERY_CAM" not in manager.workers
            assert manager.get_camera("RECOVERY_CAM")["enabled"] is True
    finally:
        manager.release()


def test_repeated_read_failures_mark_worker_offline():
    worker = CameraWorker(
        FlakyPipeline(),
        inference_fps=20,
        frame_failure_threshold=3,
    )
    worker.start()
    deadline = time.time() + 1
    while time.time() < deadline:
        if worker.get_status()["status"] == "OFFLINE":
            break
        time.sleep(0.01)

    status = worker.get_status()
    worker.stop()
    assert status["status"] == "OFFLINE"
    assert status["consecutive_frame_failures"] >= 3


def test_failed_camera_recovery_does_not_stop_other_camera(tmp_path):
    manager = make_manager(tmp_path)
    other_source = Path(tmp_path) / "other.mp4"
    other_source.write_bytes(b"other")
    manager.cameras.append({
        "id": "HEALTHY_CAM",
        "name": "Healthy",
        "source_type": "file",
        "source": str(other_source),
        "enabled": True,
    })
    manager._record_recovery_failure(
        "RECOVERY_CAM",
        RuntimeError("failed"),
    )
    healthy_worker = RecoveryWorker(None)
    healthy_worker.start()
    manager.workers["HEALTHY_CAM"] = healthy_worker
    try:
        manager._recovery_max_attempts = 0
        manager._recover_camera_if_needed(manager.get_camera("RECOVERY_CAM"))
        assert manager.workers["HEALTHY_CAM"] is healthy_worker
        assert healthy_worker.running is True
    finally:
        manager.release()


def test_stalled_camera_is_restarted_after_stable_stale_state(tmp_path):
    manager = make_manager(tmp_path)
    stale_worker = StaleWorker(None)
    stale_worker.start()
    manager.workers["RECOVERY_CAM"] = stale_worker
    manager._stale_recovery_threshold = 2
    restarted = []

    def restart(camera):
        restarted.append(camera["id"])
        manager.workers[camera["id"]] = RecoveryWorker(None)
        manager.workers[camera["id"]].start()

    manager._start_camera = restart
    try:
        camera = manager.get_camera("RECOVERY_CAM")
        manager._recover_camera_if_needed(camera)
        assert restarted == []
        manager._recover_camera_if_needed(camera)
        assert restarted == ["RECOVERY_CAM"]
        assert len(manager.workers) == 1
    finally:
        manager.release()
