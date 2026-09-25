import time

from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager


def main():

    print("Testing latest camera frame availability...")

    # --------------------------------------------------
    # Load and validate configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    # --------------------------------------------------
    # Create camera manager
    # --------------------------------------------------

    camera_manager = CameraManager(
        config["cameras"]
    )

    enabled_cameras = (
        camera_manager.get_enabled_cameras()
    )

    print(
        f"Enabled cameras: "
        f"{len(enabled_cameras)}"
    )

    # --------------------------------------------------
    # Create multi-camera manager
    # --------------------------------------------------

    manager = MultiCameraManager(
        cameras=enabled_cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=config["processing"],
    )

    try:

        # --------------------------------------------------
        # Start cameras
        # --------------------------------------------------

        manager.setup()

        print(
            "Camera workers started."
        )

        # --------------------------------------------------
        # Wait for camera frames
        # --------------------------------------------------

        print(
            "\nWaiting for camera frames..."
        )

        time.sleep(2)

        # --------------------------------------------------
        # Check each worker
        # --------------------------------------------------

        for camera_id in (
            manager.get_camera_ids()
        ):

            worker = manager.workers[camera_id]

            print(
                f"\nTesting camera: "
                f"{camera_id}"
            )

            # --------------------------------------------------
            # Check latest frame
            # --------------------------------------------------

            frame = worker.get_latest_frame()

            if frame is None:

                raise AssertionError(
                    f"{camera_id} does not have "
                    f"a latest frame."
                )

            print(
                f"  Frame shape: "
                f"{frame.shape}"
            )

            print(
                f"  Frame type: "
                f"{type(frame).__name__}"
            )

            # --------------------------------------------------
            # Validate OpenCV frame
            # --------------------------------------------------

            if len(frame.shape) != 3:

                raise AssertionError(
                    f"{camera_id} frame should "
                    f"have 3 dimensions."
                )

            height, width, channels = (
                frame.shape
            )

            if width <= 0 or height <= 0:

                raise AssertionError(
                    f"{camera_id} frame dimensions "
                    f"are invalid."
                )

            if channels != 3:

                raise AssertionError(
                    f"{camera_id} frame should "
                    f"have 3 color channels."
                )

            print(
                "  Latest frame availability: PASS"
            )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print(
            "\nLatest camera frame test successful."
        )

    finally:

        # --------------------------------------------------
        # Stop cameras
        # --------------------------------------------------

        manager.release()

        print(
            "Camera workers stopped."
        )


if __name__ == "__main__":
    main()