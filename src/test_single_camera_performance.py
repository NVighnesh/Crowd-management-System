import time

from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager


def main():

    config = load_config()

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = camera_manager.get_enabled_cameras()

    if not cameras:

        print("No enabled cameras.")
        return

    # Test only the first camera
    camera = cameras[0]

    print(
        f"Testing single camera: "
        f"{camera['id']}"
    )

    manager = MultiCameraManager(
        cameras=[camera],
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        processing_config=config["processing"],
    )

    manager.setup()

    worker = manager.workers[camera["id"]]

    print(
        f"Configured inference FPS: "
        f"{config['processing']['inference_fps']}"
    )

    print(
        "Warming up for 5 seconds..."
    )

    time.sleep(5)

    # Reset metrics after warm-up
    worker.capture_count = 0
    worker.capture_start_time = time.time()

    worker.inference_count = 0
    worker.total_inference_time = 0.0

    print(
        "Warm-up complete."
    )

    print(
        "Measuring for 10 seconds...\n"
    )

    start_time = time.time()

    try:

        time.sleep(10)

    finally:

        elapsed = time.time() - start_time

        capture_fps = worker.get_capture_fps(
            elapsed
        )

        inference_fps = worker.get_inference_fps(
            elapsed
        )

        latency = worker.get_average_latency_ms()

        result = manager.get_latest_result(
            camera["id"]
        )

        print(
            "Performance:"
        )

        print(
            f"Capture FPS: "
            f"{capture_fps:.2f}"
        )

        print(
            f"Inference FPS: "
            f"{inference_fps:.2f}"
        )

        print(
            f"Average latency: "
            f"{latency:.2f} ms"
        )

        print()

        if result is not None:

            print(
                "Latest result:"
            )

            print(
                f"Total people: "
                f"{result.total_people}"
            )

            for zone in result.zones:

                print(
                    f"{zone.zone_id}: "
                    f"{zone.count}/"
                    f"{zone.threshold} "
                    f"{zone.status}"
                )

        else:

            print(
                "No crowd result available."
            )

        manager.release()

        print(
            "\nTest complete."
        )


if __name__ == "__main__":
    main()