import time

from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager


def main():

    # Load application configuration
    config = load_config()

    # Get enabled cameras
    camera_manager = CameraManager(config["cameras"])
    cameras = camera_manager.get_enabled_cameras()

    print(f"Enabled cameras: {len(cameras)}")

    if not cameras:
        print("No enabled cameras.")
        return

    # Create multi-camera manager
    manager = MultiCameraManager(
        cameras=cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
    )

    # Setup all camera pipelines
    manager.setup()

    print(f"Active pipelines: {manager.get_camera_ids()}")
    print("Starting continuous processing...")
    print("Press Ctrl+C to stop.\n")

    try:

        while True:

            start_time = time.time()

            # Process every active camera
            for camera_id in manager.get_camera_ids():

                result = manager.process_frame(camera_id)

                if result is None:
                    print(f"{camera_id}: no frame available")
                    continue

                print(
                    f"{camera_id}: "
                    f"total_people={result.total_people}"
                )

                for zone in result.zones:

                    print(
                        f"  {zone.zone_id}: "
                        f"{zone.count}/{zone.threshold} "
                        f"{zone.status}"
                    )

            elapsed = time.time() - start_time

            print(
                f"Processing cycle time: "
                f"{elapsed:.2f}s"
            )

            print("-" * 60)

    except KeyboardInterrupt:

        print("\nStopping continuous processing...")

    finally:

        manager.release()

        print("All cameras released.")
        print("Continuous processing stopped.")


if __name__ == "__main__":
    main()