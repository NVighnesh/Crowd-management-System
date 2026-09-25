import threading


class LatestFrameBuffer:

    def __init__(self):

        self._frame = None
        self._sequence = 0
        self._lock = threading.Lock()

    def update(self, frame):

        with self._lock:
            self._frame = frame
            self._sequence += 1

    def get(self):

        with self._lock:
            return self._frame

    def get_with_sequence(self):

        with self._lock:
            return self._frame, self._sequence