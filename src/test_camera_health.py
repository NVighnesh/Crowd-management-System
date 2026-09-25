import time

from src.video.camera_worker import CameraWorker


class FakeSource:

    def __init__(self):
        self.frame_available = True

    def read(self):

        if self.frame_available:
            return True, "fake_frame"

        return False, None


class FakePipeline:

    def __init__(self):
        self.source = FakeSource()

    def process_frame(self, frame):
        return None


def main():

    pipeline = FakePipeline()

    worker = CameraWorker(
        pipeline=pipeline,
        inference_fps=5,
        camera_stale_timeout_seconds=5,
    )

    # --------------------------------------------------
    # Simulate a recent frame
    # --------------------------------------------------

    worker.running = True
    worker.last_frame_time = time.time()

    worker.update_health_status()

    status = worker.get_status()

    print(
        "Recent frame:"
    )

    print(
        f"Camera status: "
        f"{status['status']}"
    )

    if status["status"] != "ONLINE":

        raise AssertionError(
            "Camera with a recent frame "
            "should be ONLINE."
        )

    # --------------------------------------------------
    # Simulate an old frame
    # --------------------------------------------------

    worker.last_frame_time = (
        time.time() - 10
    )

    worker.update_health_status()

    status = worker.get_status()

    print(
        "\nOld frame:"
    )

    print(
        f"Camera status: "
        f"{status['status']}"
    )

    if status["status"] != "STALE":

        raise AssertionError(
            "Camera with an old frame "
            "should be STALE."
        )

    # --------------------------------------------------
    # Simulate camera failure
    # --------------------------------------------------

    worker.running = True

    worker._capture_loop_test_mode = True

    pipeline.source.frame_available = False

    success, frame = pipeline.source.read()

    if success:

        raise AssertionError(
            "Fake camera should have "
            "failed to provide a frame."
        )

    worker.running = False
    worker.status = "OFFLINE"
    worker.last_error = (
        "Unable to read frame from source"
    )

    status = worker.get_status()

    print(
        "\nFailed camera:"
    )

    print(
        f"Camera status: "
        f"{status['status']}"
    )

    print(
        f"Last error: "
        f"{status['last_error']}"
    )

    if status["status"] != "OFFLINE":

        raise AssertionError(
            "Failed camera should "
            "be OFFLINE."
        )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print(
        "\nCamera health test successful."
    )


if __name__ == "__main__":
    main()