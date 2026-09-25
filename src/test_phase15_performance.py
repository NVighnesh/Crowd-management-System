import threading
import time

import numpy as np

from src.config.validator import ConfigValidator
from src.video.camera_worker import CameraWorker
from src.video.frame_buffer import LatestFrameBuffer


class FakeSource:
    def __init__(self):
        self.number = 0
        self.opened = True

    def read(self):
        self.number += 1
        return True, np.full((4, 4, 3), self.number, dtype=np.uint8)

    def is_opened(self):
        return self.opened

    def release(self):
        self.opened = False


class FakePipeline:
    def __init__(self, delay=0):
        self.source = FakeSource()
        self.delay = delay
        self.frames = []

    def process_frame(self, frame):
        if self.delay:
            time.sleep(self.delay)
        self.frames.append(frame.copy())
        return type("Result", (), {"camera_id": "CAM"})()

    def release(self):
        self.source.release()


def test_latest_frame_buffer_is_bounded_and_sequence_aware():
    buffer = LatestFrameBuffer()
    buffer.update("first")
    buffer.update("latest")

    frame, sequence = buffer.get_with_sequence()

    assert frame == "latest"
    assert sequence == 2


def test_worker_does_not_infer_same_frame_twice():
    pipeline = FakePipeline()
    worker = CameraWorker(pipeline, inference_fps=100)
    worker.running = True
    worker.frame_buffer.update(np.zeros((4, 4, 3), dtype=np.uint8))

    worker._run_inference()
    worker._run_inference()

    assert len(pipeline.frames) == 1
    assert worker.total_inferences == 1


def test_worker_samples_latest_frames_and_reports_metrics():
    pipeline = FakePipeline()
    worker = CameraWorker(pipeline, inference_fps=20)
    worker.start()
    time.sleep(0.15)
    worker.stop()

    assert worker.capture_count > worker.inference_count
    assert worker.get_status()["inference_fps"] >= 0
    assert len(pipeline.frames) == worker.inference_count
    assert pipeline.frames[-1].max() <= pipeline.source.number


def test_slow_camera_does_not_block_another_worker():
    fast_pipeline = FakePipeline()
    slow_pipeline = FakePipeline(delay=0.15)
    fast_worker = CameraWorker(fast_pipeline, inference_fps=20)
    slow_worker = CameraWorker(slow_pipeline, inference_fps=20)

    fast_worker.start()
    slow_worker.start()
    time.sleep(0.35)
    fast_worker.stop()
    slow_worker.stop()

    assert fast_worker.total_inferences > 0
    assert fast_worker.total_frames_captured > 0


def test_processing_configuration_accepts_performance_settings():
    ConfigValidator._validate_processing(
        {
            "inference_fps": 5,
            "stream_fps": 12,
            "jpeg_quality": 75,
            "max_result_age_seconds": 5,
            "camera_stale_timeout_seconds": 10,
        }
    )
