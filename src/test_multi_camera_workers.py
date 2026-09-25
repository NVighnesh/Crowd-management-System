import time

from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager


def main():

    # --------------------------------------------------
    # Load configuration
    # --------------------------------------------------

    config = load_config()

    # --------------------------------------------------
    # Get enabled cameras
    # --------------------------------------------------

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = camera_manager.get_enabled_cameras()

    print(
        f"Enabled cameras: {len(cameras)}"
    )

    if not cameras:

        print("No enabled cameras.")
        return

    # --------------------------------------------------
    # Create multi-camera manager
    # --------------------------------------------------

    manager = MultiCameraManager(
        cameras=cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=config["processing"],
    )

    # --------------------------------------------------
    # Start camera workers
    # --------------------------------------------------

    manager.setup()

    print(
        f"Active workers: "
        f"{manager.get_camera_ids()}"
    )

    print(
        "Configured inference FPS: "
        f"{config['processing']['inference_fps']}"
    )

    print(
        "All camera workers started."
    )

    # --------------------------------------------------
    # Warm up AI models
    # --------------------------------------------------

    print(
        "Warming up AI models..."
    )

    time.sleep(5)

    print(
        "Warm-up complete."
    )

    # --------------------------------------------------
    # Reset performance metrics safely
    # --------------------------------------------------

    for camera_id in manager.get_camera_ids():

        worker = manager.workers[
            camera_id
        ]

        worker.reset_metrics()

    # --------------------------------------------------
    # Measure background inference
    # --------------------------------------------------

    print(
        "Measuring background inference "
        "performance for 10 seconds...\n"
    )

    start_time = time.time()

    try:

        time.sleep(10)

    finally:

        elapsed_seconds = (
            time.time() - start_time
        )

        # --------------------------------------------------
        # Performance metrics
        # --------------------------------------------------

        print(
            "\nInference metrics:"
        )

        for camera_id in manager.get_camera_ids():

            worker = manager.workers[
                camera_id
            ]

            capture_fps = (
                worker.get_capture_fps(
                    elapsed_seconds
                )
            )

            inference_fps = (
                worker.get_inference_fps(
                    elapsed_seconds
                )
            )

            average_latency = (
                worker.get_average_latency_ms()
            )

            print(
                f"{camera_id}: "
                f"capture_fps={capture_fps:.2f}, "
                f"inference_fps={inference_fps:.2f}, "
                f"avg_latency={average_latency:.2f} ms"
            )

        # --------------------------------------------------
        # Latest results
        # --------------------------------------------------

        print(
            "\nLatest results from ResultStore:"
        )

        print(
            "-" * 60
        )

        for camera_id in manager.get_camera_ids():

            result = manager.get_latest_result(
                camera_id
            )

            if result is None:

                print(
                    f"{camera_id}: "
                    "No result available"
                )

                continue

            print(
                f"{camera_id}: "
                f"total_people="
                f"{result.total_people}"
            )

            for zone in result.zones:

                print(
                    f"  {zone.zone_id}: "
                    f"{zone.count}/"
                    f"{zone.threshold} "
                    f"{zone.status}"
                )

        print(
            "-" * 60
        )

        # --------------------------------------------------
        # Release resources
        # --------------------------------------------------

        manager.release()

        print(
            "All camera workers stopped."
        )

        print(
            "Test complete."
        )


if __name__ == "__main__":
    main()