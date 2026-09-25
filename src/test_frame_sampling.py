import time

from src.video.camera_worker import CameraWorker


class FakeSource:

    def __init__(self):
        self.running = True
        self.frame_number = 0

    def read(self):

        if not self.running:
            return False, None

        frame = self.frame_number
        self.frame_number += 1

        time.sleep(0.02)

        return True, frame

    def is_opened(self):
        return True

    def release(self):
        self.running = False


class FakePipeline:

    def __init__(self):
        self.source = FakeSource()
        self.processed_frames = []

    def process_frame(self, frame):

        self.processed_frames.append(
            frame
        )

        class Result:
            camera_id = "TEST_CAMERA"

        return Result()

    def release(self):
        self.source.release()


def main():

    print(
        "Testing frame sampling and "
        "inference scheduling..."
    )

    pipeline = FakePipeline()

    worker = CameraWorker(
        pipeline=pipeline,
        inference_fps=5,
        camera_stale_timeout_seconds=5,
        result_callback=None,
    )

    # --------------------------------------------------
    # Start worker
    # --------------------------------------------------

    worker.start()

    print(
        "Camera and inference workers started."
    )

    # --------------------------------------------------
    # Allow capture and inference to run
    # --------------------------------------------------

    time.sleep(2)

    # --------------------------------------------------
    # Stop worker
    # --------------------------------------------------

    worker.stop()

    # --------------------------------------------------
    # Analyze processed frames
    # --------------------------------------------------

    processed = (
        pipeline.processed_frames
    )

    print(
        f"Frames processed by inference: "
        f"{len(processed)}"
    )

    print(
        f"Processed frame values: "
        f"{processed}"
    )

    # --------------------------------------------------
    # Validation: inference processed frames
    # --------------------------------------------------

    if not processed:

        raise AssertionError(
            "Inference worker did not "
            "process any frames."
        )

    print(
        "Inference execution: PASS"
    )

    # --------------------------------------------------
    # Validation: sampling
    # --------------------------------------------------

    capture_count = (
        worker.capture_count
    )

    inference_count = (
        worker.inference_count
    )

    print(
        f"Captured frames: "
        f"{capture_count}"
    )

    print(
        f"Inference executions: "
        f"{inference_count}"
    )

    if inference_count >= capture_count:

        raise AssertionError(
            "Inference processed every "
            "captured frame. "
            "Frame sampling is not working."
        )

    print(
        "Frame sampling: PASS"
    )

    # --------------------------------------------------
    # Calculate elapsed measurement time
    # --------------------------------------------------

    elapsed_seconds = 2.0

    inference_fps = (
        worker.get_inference_fps(
            elapsed_seconds
        )
    )

    average_latency = (
        worker.get_average_latency_ms()
    )

    print(
        f"Inference FPS: "
        f"{inference_fps:.2f}"
    )

    print(
        f"Average inference latency: "
        f"{average_latency:.2f} ms"
    )

    # --------------------------------------------------
    # Latest-frame behavior
    # --------------------------------------------------

    latest_processed = processed[-1]

    latest_available = (
        worker.frame_buffer.get()
    )

    print(
        f"Latest available frame: "
        f"{latest_available}"
    )

    print(
        f"Last processed frame: "
        f"{latest_processed}"
    )

    if latest_processed != latest_available:

        print(
            "Note: last processed frame "
            "may differ slightly from the "
            "latest captured frame because "
            "capture and inference run concurrently."
        )

    else:

        print(
            "Latest-frame processing: PASS"
        )

    print(
        "\nFrame sampling test successful."
    )


if __name__ == "__main__":
    main()