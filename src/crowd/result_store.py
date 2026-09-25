import threading
import time


class ResultStore:

    def __init__(self):

        self._results = {}
        self._lock = threading.Lock()

    def update(self, camera_id, result):

        with self._lock:

            self._results[camera_id] = {
                "result": result,
                "timestamp": time.time(),
            }

    def get(self, camera_id):

        with self._lock:

            entry = self._results.get(camera_id)

            if entry is None:
                return None

            return entry["result"]

    def get_with_timestamp(self, camera_id):

        with self._lock:

            return self._results.get(camera_id)

    def get_all(self):

        with self._lock:

            return {
                camera_id: entry["result"]
                for camera_id, entry in self._results.items()
            }

    def get_all_with_timestamp(self):

        with self._lock:

            return self._results.copy()

    def remove(self, camera_id):

        with self._lock:

            self._results.pop(camera_id, None)

    def clear(self):

        with self._lock:

            self._results.clear()