from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

import src.api as api
from src.crowd.result import CrowdAnalysisResult, ZoneResult
from src.detection.detection_types import Detection
from src.video.camera_pipeline import CameraPipeline
from src.video.frame_streamer import FrameStreamer


class FakeSource:
    def __init__(self, *args, **kwargs):
        self.opened = True

    def open(self):
        self.opened = True

    def read(self):
        return True, np.zeros((120, 160, 3), dtype=np.uint8)

    def is_opened(self):
        return self.opened

    def release(self):
        self.opened = False


class FakeEngine:
    def __init__(self):
        self.calls = 0

    def infer(self, frame):
        self.calls += 1
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
                bbox=(100, 70, 130, 110),
                track_id=2,
            ),
        ]


class FakeAnnotator:
    def annotate(self, frame, detections, zones, result):
        return frame.copy()


def make_result(zones=None, total_people=2):
    return CrowdAnalysisResult(
        camera_id="CAM_VIS",
        total_people=total_people,
        zones=list(zones or []),
    )


def test_frame_annotator_draws_summary_detections_and_zone_metadata():
    from src.visualization.frame_annotator import FrameAnnotator

    frame = np.zeros((180, 240, 3), dtype=np.uint8)
    detections = [
        Detection(
            class_id=0,
            confidence=0.9,
            bbox=(20, 20, 60, 80),
            track_id=4,
        )
    ]
    zones = [
        {
            "zone_id": "ZONE_001",
            "name": "Gate",
            "polygon": [[5, 90], [110, 90], [110, 170], [5, 170]],
        }
    ]
    result = make_result(
        [
            ZoneResult(
                zone_id="ZONE_001",
                name="Gate",
                count=2,
                threshold=1,
                status="RED",
            )
        ]
    )

    annotated = FrameAnnotator().annotate(
        frame,
        detections,
        zones,
        result,
    )

    assert annotated.shape == frame.shape
    assert np.any(annotated != frame)
    assert np.array_equal(frame, np.zeros_like(frame))


def test_zero_zone_annotation_still_draws_whole_frame_count():
    from src.visualization.frame_annotator import FrameAnnotator

    frame = np.zeros((100, 140, 3), dtype=np.uint8)
    annotated = FrameAnnotator().annotate(
        frame,
        [],
        [],
        make_result(total_people=7),
    )

    assert annotated.shape == frame.shape
    assert np.any(annotated != frame)


def test_pipeline_reuses_one_inference_result_for_annotation(tmp_path):
    engine = FakeEngine()
    camera = {
        "id": "CAM_VIS",
        "source_type": "file",
        "source": str(tmp_path / "aerial.mp4"),
        "loop": True,
    }
    (tmp_path / "aerial.mp4").write_bytes(b"video")

    with patch(
        "src.video.camera_pipeline.FileVideoSource",
        FakeSource,
    ), patch(
        "src.video.camera_pipeline.InferenceFactory.create_engine",
        return_value=engine,
    ), patch(
        "src.video.camera_pipeline.FrameAnnotator",
        FakeAnnotator,
    ):
        pipeline = CameraPipeline(
            camera,
            inference_config={},
            tracking_config={},
            zones_config=[],
        )
        pipeline.setup()
        result = pipeline.process_frame(
            np.zeros((120, 160, 3), dtype=np.uint8)
        )

        assert engine.calls == 1
        assert pipeline.get_latest_annotated_frame() is not None
        assert result.total_people == 2
        pipeline.release()


def test_frame_streamer_reuses_worker_annotated_frame():
    frame = np.zeros((20, 20, 3), dtype=np.uint8)

    class Worker:
        def get_latest_annotated_frame(self):
            return frame

    chunk = next(
        FrameStreamer(
            Worker(),
            stream_fps=1000,
        ).generate()
    )

    assert chunk.startswith(b"--frame\r\n")
    assert b"Content-Type: image/jpeg" in chunk
    assert b"\xff\xd8" in chunk
    assert b"\xff\xd9" in chunk


def test_stream_endpoint_returns_503_when_frame_is_unavailable(monkeypatch):
    class Worker:
        def get_status(self):
            return {
                "status": "STARTING",
                "processing_status": "STARTING",
            }

        def get_latest_annotated_frame(self):
            return None

    manager = type("Manager", (), {"workers": {"CAM_VIS": Worker()}})()

    monkeypatch.setenv("CROWD_SECURITY_ENABLED", "false")
    with TestClient(api.app) as client:
        original_manager = api.multi_camera_manager
        monkeypatch.setattr(api, "multi_camera_manager", manager)
        response = client.get("/cameras/CAM_VIS/stream")
        monkeypatch.setattr(api, "multi_camera_manager", original_manager)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Annotated frame is not available yet."
    )


def test_stream_endpoint_returns_404_for_unknown_camera(monkeypatch):
    manager = type("Manager", (), {"workers": {}})()

    monkeypatch.setenv("CROWD_SECURITY_ENABLED", "false")
    with TestClient(api.app) as client:
        original_manager = api.multi_camera_manager
        monkeypatch.setattr(api, "multi_camera_manager", manager)
        response = client.get("/cameras/MISSING/stream")
        monkeypatch.setattr(api, "multi_camera_manager", original_manager)

    assert response.status_code == 404
