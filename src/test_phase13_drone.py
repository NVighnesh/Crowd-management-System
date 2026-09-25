from unittest.mock import patch

import pytest

from src.config.validator import ConfigValidator
from src.crowd.analyzer import CrowdAnalyzer
from src.detection.detection_types import Detection
from src.video.camera_pipeline import CameraPipeline
from src.video.multi_camera_manager import MultiCameraManager


class FakeSource:
    def __init__(self, *args, **kwargs):
        self.opened = False
        self.frames = [("frame",)]
        self.released = False

    def open(self):
        self.opened = True

    def read(self):
        return True, "frame"

    def is_opened(self):
        return self.opened and not self.released

    def release(self):
        self.released = True
        self.opened = False


class FakeEngine:
    def infer(self, frame):
        return [
            Detection(
                class_id=0,
                confidence=0.95,
                bbox=(10, 10, 30, 40),
                track_id=1,
            ),
            Detection(
                class_id=0,
                confidence=0.90,
                bbox=(100, 100, 130, 150),
                track_id=2,
            ),
        ]


class FakeAnnotator:
    def annotate(self, frame, detections, zones, result):
        return frame


def drone_camera(source, **overrides):
    camera = {
        "id": "DRONE_001",
        "name": "Aerial camera",
        "source_type": "drone",
        "source": source,
        "loop": True,
        "enabled": True,
    }
    camera.update(overrides)
    return camera


def test_drone_source_normalization_supports_file_and_rtsp(tmp_path):
    video = tmp_path / "aerial.mp4"
    video.write_bytes(b"video")

    file_camera = MultiCameraManager._normalize_camera(
        drone_camera(str(video))
    )
    rtsp_camera = MultiCameraManager._normalize_camera(
        drone_camera("rtsps://drone.example/live")
    )

    assert file_camera["source_type"] == "drone"
    assert rtsp_camera["source_type"] == "drone"


def test_drone_source_rejects_invalid_network_or_file_source(tmp_path):
    with pytest.raises(ValueError, match="source file not found"):
        MultiCameraManager._normalize_camera(
            drone_camera(str(tmp_path / "missing.mp4"))
        )

    with pytest.raises(ValueError, match="host"):
        MultiCameraManager._normalize_camera(
            drone_camera("rtsp://")
        )


def test_drone_file_pipeline_counts_whole_frame_without_zones(tmp_path):
    video = tmp_path / "aerial.mp4"
    video.write_bytes(b"video")

    with patch(
        "src.video.camera_pipeline.FileVideoSource",
        FakeSource,
    ), patch(
        "src.video.camera_pipeline.InferenceFactory.create_engine",
        return_value=FakeEngine(),
    ), patch(
        "src.video.camera_pipeline.FrameAnnotator",
        FakeAnnotator,
    ):
        pipeline = CameraPipeline(
            camera_config=drone_camera(str(video)),
            inference_config={},
            tracking_config={},
            zones_config=[],
        )
        pipeline.setup()
        result = pipeline.process_frame()
        pipeline.release()

    assert result.total_people == 2
    assert result.zones == []


def test_drone_rtsp_pipeline_uses_existing_rtsp_source():
    with patch(
        "src.video.camera_pipeline.RTSPVideoSource",
        FakeSource,
    ) as source_class, patch(
        "src.video.camera_pipeline.InferenceFactory.create_engine",
        return_value=FakeEngine(),
    ), patch(
        "src.video.camera_pipeline.FrameAnnotator",
        FakeAnnotator,
    ):
        pipeline = CameraPipeline(
            camera_config=drone_camera(
                "rtsp://drone.example/live"
            ),
            inference_config={},
            tracking_config={},
            zones_config=[],
        )
        pipeline.setup()
        result = pipeline.process_frame()
        pipeline.release()

    assert result.total_people == 2
    assert result.zones == []


def test_drone_whole_frame_count_includes_people_outside_zones():
    detections = FakeEngine().infer("frame")
    zones = [
        {
            "zone_id": "ZONE_001",
            "name": "Landing area",
            "threshold": 10,
            "threshold_type": "count",
            "polygon": [[0, 0], [60, 0], [60, 60], [0, 60]],
        }
    ]

    result = CrowdAnalyzer().analyze(
        "DRONE_001",
        detections,
        zones,
    )

    assert result.total_people == 2
    assert result.zones[0].count == 1


def test_config_validator_allows_drone_without_zone_file(tmp_path):
    video = tmp_path / "aerial.mp4"
    model = tmp_path / "model.pt"
    video.write_bytes(b"video")
    model.write_bytes(b"model")

    config = {
        "system": {"name": "test", "version": "1"},
        "cameras": [
            {
                "id": "DRONE_001",
                "source_type": "drone",
                "source": str(video),
                "enabled": False,
            }
        ],
        "inference": {
            "model": str(model),
            "image_size": 640,
            "confidence": 0.35,
        },
        "tracking": {"enabled": False},
        "counting": {
            "whole_frame": {"enabled": True, "mode": "detection"},
            "zones": {"enabled": True, "point": "bottom_center"},
        },
        "processing": {
            "inference_fps": 5,
            "max_result_age_seconds": 5,
            "camera_stale_timeout_seconds": 10,
        },
    }

    assert ConfigValidator.validate(config) is True
