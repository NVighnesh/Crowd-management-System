import cv2
import time

from src.video.source import VideoSource


class RTSPVideoSource(VideoSource):

    _BACKENDS = {
        "ffmpeg": cv2.CAP_FFMPEG,
        "gstreamer": cv2.CAP_GSTREAMER,
        "any": cv2.CAP_ANY,
    }

    def __init__(
        self,
        url: str,
        open_timeout_ms=10000,
        read_timeout_ms=10000,
        backend="any",
    ):
        self.url = url
        self.open_timeout_ms = int(open_timeout_ms)
        self.read_timeout_ms = int(read_timeout_ms)
        self.backend = str(backend or "any").lower()
        self.cap = None
        self.last_error = None
        self.last_successful_frame_time = None
        self.read_failures = 0

    def open(self):
        self.release()
        backend = self._BACKENDS.get(self.backend, cv2.CAP_ANY)
        self.cap = cv2.VideoCapture()
        try:
            if self.open_timeout_ms > 0:
                self._set_property(
                    "CAP_PROP_OPEN_TIMEOUT_MSEC",
                    self.open_timeout_ms,
                )
            if self.read_timeout_ms > 0:
                self._set_property(
                    "CAP_PROP_READ_TIMEOUT_MSEC",
                    self.read_timeout_ms,
                )
            opened = self.cap.open(self.url, backend)
        except Exception as exc:
            self.last_error = str(exc)
            self.release()
            raise RuntimeError(
                f"Unable to open RTSP stream: {self.url}"
            ) from exc
        if not opened or not self.is_opened():
            self.last_error = (
                f"Unable to open RTSP stream: {self.url}"
            )
            self.release()
            raise RuntimeError(self.last_error)
        self.last_error = None
        self.read_failures = 0

    def _set_property(self, name, value):
        property_id = getattr(cv2, name, None)
        if property_id is not None:
            self.cap.set(property_id, value)

    def read(self):
        if self.cap is None:
            return False, None

        try:
            success, frame = self.cap.read()
        except Exception as exc:
            self.last_error = str(exc)
            self.read_failures += 1
            return False, None
        if success and frame is not None:
            self.last_successful_frame_time = time.time()
            self.read_failures = 0
            self.last_error = None
        else:
            self.read_failures += 1
            self.last_error = "Unable to read frame from RTSP stream"
        return success, frame

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None