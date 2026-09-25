from unittest.mock import patch

import pytest

from src.video.multi_camera_manager import MultiCameraManager
from src.video.rtsp_source import RTSPVideoSource


class FakeCapture:
    def __init__(self, opened=True, reads=None):
        self.opened = opened
        self.reads = list(reads or [])
        self.released = False
        self.settings = []

    def set(self, property_id, value):
        self.settings.append((property_id, value))
        return True

    def open(self, url, backend):
        return self.opened

    def isOpened(self):
        return self.opened and not self.released

    def read(self):
        if self.reads:
            return self.reads.pop(0)
        return False, None

    def release(self):
        self.released = True
        self.opened = False


def test_rtsp_source_applies_timeouts_and_reads_frames():
    capture = FakeCapture(reads=[(True, "frame")])
    with patch(
        "src.video.rtsp_source.cv2.VideoCapture",
        return_value=capture,
    ):
        source = RTSPVideoSource(
            "rtsp://camera.example/live",
            open_timeout_ms=1200,
            read_timeout_ms=2300,
            backend="any",
        )
        source.open()
        success, frame = source.read()

    assert success is True
    assert frame == "frame"
    assert source.last_successful_frame_time is not None
    assert source.read_failures == 0
    assert len(capture.settings) == 2


def test_rtsp_open_failure_releases_capture():
    capture = FakeCapture(opened=False)
    with patch(
        "src.video.rtsp_source.cv2.VideoCapture",
        return_value=capture,
    ):
        source = RTSPVideoSource("rtsp://camera.example/live")
        with pytest.raises(RuntimeError, match="Unable to open RTSP"):
            source.open()

    assert capture.released is True
    assert source.cap is None
    assert source.last_error


def test_rtsp_read_failure_is_reported_and_released_safely():
    capture = FakeCapture(reads=[(False, None)])
    with patch(
        "src.video.rtsp_source.cv2.VideoCapture",
        return_value=capture,
    ):
        source = RTSPVideoSource("rtsp://camera.example/live")
        source.open()
        success, frame = source.read()
        source.release()

    assert success is False
    assert frame is None
    assert source.read_failures == 1
    assert source.last_error == "Unable to read frame from RTSP stream"
    assert capture.released is True


def test_rtsp_configuration_validation():
    with pytest.raises(ValueError, match="scheme"):
        MultiCameraManager._normalize_camera({
            "id": "RTSP_1",
            "source_type": "rtsp",
            "source": "http://camera.example/live",
        })

    with pytest.raises(ValueError, match="host"):
        MultiCameraManager._normalize_camera({
            "id": "RTSP_1",
            "source_type": "rtsp",
            "source": "rtsp://",
        })

    camera = MultiCameraManager._normalize_camera({
        "id": "RTSP_1",
        "name": "Network camera",
        "source_type": "rtsp",
        "source": "rtsps://camera.example/live",
    })
    assert camera["source_type"] == "rtsp"
    assert camera["source"].startswith("rtsps://")


def test_file_camera_normalization_remains_unchanged(tmp_path):
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")
    camera = MultiCameraManager._normalize_camera({
        "id": "FILE_1",
        "source_type": "file",
        "source": str(source),
        "loop": True,
    })
    assert camera["source_type"] == "file"
    assert camera["loop"] is True
