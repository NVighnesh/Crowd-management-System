import time

from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.file_source import FileVideoSource
from src.detection.ultralytics_detector import (
    UltralyticsPersonDetector,
)


def main():

    config = load_config()

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = camera_manager.get_enabled_cameras()

    if not cameras:

        print("No enabled cameras.")
        return

    camera = cameras[0]

    print(
        f"Testing detection-only performance: "
        f"{camera['id']}"
    )

    # --------------------------------------------------
    # Create video source
    # --------------------------------------------------

    source = FileVideoSource(
        path=camera["source"],
        loop=True,
    )

    source.open()

    if not source.is_opened():

        print(
            f"Could not open source: "
            f"{camera['source']}"
        )

        return

    # --------------------------------------------------
    # Create detector
    # --------------------------------------------------

    detector = UltralyticsPersonDetector(
        model_path=config["inference"]["model"],
        confidence=config["inference"]["confidence"],
        image_size=config["inference"]["image_size"],
        device=config["inference"]["device"],
    )

    print(
        f"Model: "
        f"{config['inference']['model']}"
    )

    print(
        f"Image size: "
        f"{config['inference']['image_size']}"
    )

    print(
        "Warming up for 5 seconds..."
    )

    warmup_start = time.time()

    while time.time() - warmup_start < 5:

        success, frame = source.read()

        if not success:
            continue

        detector.infer(frame)

    print(
        "Warm-up complete."
    )

    # --------------------------------------------------
    # Performance measurement
    # --------------------------------------------------

    inference_count = 0
    total_inference_time = 0.0

    print(
        "Measuring detection-only performance "
        "for 10 seconds...\n"
    )

    start_time = time.time()

    try:

        while time.time() - start_time < 10:

            success, frame = source.read()

            if not success:
                continue

            inference_start = time.perf_counter()

            detections = detector.infer(frame)

            inference_time = (
                time.perf_counter()
                - inference_start
            )

            inference_count += 1
            total_inference_time += inference_time

    finally:

        elapsed = time.time() - start_time

        if elapsed > 0:

            inference_fps = (
                inference_count / elapsed
            )

        else:

            inference_fps = 0.0

        if inference_count > 0:

            average_latency = (
                total_inference_time
                / inference_count
                * 1000
            )

        else:

            average_latency = 0.0

        print(
            "Detection-only performance:"
        )

        print(
            f"Inference count: "
            f"{inference_count}"
        )

        print(
            f"Inference FPS: "
            f"{inference_fps:.2f}"
        )

        print(
            f"Average latency: "
            f"{average_latency:.2f} ms"
        )

        print()

        # Show the final detection count
        if 'detections' in locals():

            print(
                f"People detected in final frame: "
                f"{len(detections)}"
            )

        source.release()

        print(
            "\nTest complete."
        )


if __name__ == "__main__":
    main()