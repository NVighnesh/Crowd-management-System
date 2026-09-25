import time

from src.video.camera_worker import CameraWorker


class StableTestSource:

    def __init__(self):
        self.opened = False
        self.read_count = 0

    def open(self):
        self.opened = True

    def read(self):

        if not self.opened:
            return False, None

        self.read_count += 1

        return True, self.read_count

    def is_opened(self):
        return self.opened

    def release(self):
        self.opened = False


class FailingTestSource:

    def __init__(self):
        self.opened = False
        self.read_count = 0

    def open(self):
        self.opened = True

    def read(self):

        if not self.opened:
            return False, None

        self.read_count += 1

        return False, None

    def is_opened(self):
        return self.opened

    def release(self):
        self.opened = False


class TestPipeline:

    def __init__(self, source):
        self.source = source
        self.processed_frames = []

    def process_frame(self, frame):

        self.processed_frames.append(frame)

        class Result:
            camera_id = "TEST_CAMERA"

        return Result()

    def release(self):
        self.source.release()


def wait_for_status(
    worker,
    expected_status,
    timeout=2.0,
):

    start = time.time()

    while time.time() - start < timeout:

        status = worker.get_status()

        if status["status"] == expected_status:
            return True

        time.sleep(0.02)

    return False


def test_camera_starts_online():

    source = StableTestSource()

    pipeline = TestPipeline(
        source
    )

    worker = CameraWorker(
        pipeline=pipeline,
        inference_fps=5,
        camera_stale_timeout_seconds=5,
        result_callback=None,
    )

    # The source is already available.
    source.open()

    worker.start()

    online = wait_for_status(
        worker,
        "ONLINE",
    )

    status = worker.get_status()

    print(
        "\nInitial camera status:"
    )

    print(
        f"  Camera: "
        f"{status['status']}"
    )

    print(
        f"  Processing: "
        f"{status['processing_status']}"
    )

    if not online:

        worker.stop()

        raise AssertionError(
            "Camera did not reach ONLINE state."
        )

    print(
        "Initial ONLINE state: PASS"
    )

    worker.stop()


def test_camera_failure():

    source = FailingTestSource()

    pipeline = TestPipeline(
        source
    )

    source.open()

    worker = CameraWorker(
        pipeline=pipeline,
        inference_fps=5,
        camera_stale_timeout_seconds=5,
        result_callback=None,
    )

    worker.start()

    offline = wait_for_status(
        worker,
        "OFFLINE",
    )

    status = worker.get_status()

    print(
        "\nAfter simulated camera failure:"
    )

    print(
        f"  Camera: "
        f"{status['status']}"
    )

    print(
        f"  Processing: "
        f"{status['processing_status']}"
    )

    print(
        f"  Error: "
        f"{status['last_error']}"
    )

    if not offline:

        worker.stop()

        raise AssertionError(
            "Camera did not enter OFFLINE state."
        )

    if status["last_error"] is None:

        worker.stop()

        raise AssertionError(
            "Camera failure should "
            "produce an error message."
        )

    print(
        "Camera failure detection: PASS"
    )

    worker.stop()


def test_camera_reconnect():

    source = StableTestSource()

    pipeline = TestPipeline(
        source
    )

    source.open()

    worker = CameraWorker(
        pipeline=pipeline,
        inference_fps=5,
        camera_stale_timeout_seconds=5,
        result_callback=None,
    )

    worker.start()

    online = wait_for_status(
        worker,
        "ONLINE",
    )

    if not online:

        worker.stop()

        raise AssertionError(
            "Reconnected camera did not "
            "reach ONLINE state."
        )

    status = worker.get_status()

    print(
        "\nAfter camera reconnect:"
    )

    print(
        f"  Camera: "
        f"{status['status']}"
    )

    print(
        f"  Processing: "
        f"{status['processing_status']}"
    )

    if status["status"] != "ONLINE":

        worker.stop()

        raise AssertionError(
            "Reconnected camera should "
            "be ONLINE."
        )

    print(
        "Camera reconnect: PASS"
    )

    if not pipeline.processed_frames:

        worker.stop()

        raise AssertionError(
            "Inference should resume "
            "after reconnect."
        )

    print(
        "Inference after reconnect: PASS"
    )

    worker.stop()


def main():

    print(
        "Testing camera failure "
        "and reconnect..."
    )

    test_camera_starts_online()

    test_camera_failure()

    test_camera_reconnect()

    print(
        "\nCamera failure and reconnect "
        "test successful."
    )


if __name__ == "__main__":
    main()