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

    print(
        f"Enabled cameras: {len(cameras)}"
    )

    if not cameras:
        print("No enabled cameras.")
        return

    manager = MultiCameraManager(
        cameras=cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        processing_config=config["processing"],
    )

    manager.setup()

    print(
        f"Active cameras: "
        f"{manager.get_camera_ids()}"
    )

    try:

        # Allow workers to capture frames
        time.sleep(2)

        # Process one result from every camera
        for camera_id in manager.get_camera_ids():

            while True:

                result = manager.process_frame(
                    camera_id
                )

                if result is not None:
                    break

                time.sleep(0.01)

        print("\nLatest results from ResultStore:")
        print("-" * 60)

        for camera_id in manager.get_camera_ids():

            result = manager.get_latest_result(
                camera_id
            )

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

        print("-" * 60)

        print("\nAll stored results:")

        all_results = (
            manager.get_all_latest_results()
        )

        for camera_id, result in all_results.items():

            print(
                f"{camera_id}: "
                f"{result.total_people} people"
            )

        print(
            "\nResultStore integration test complete."
        )

    finally:

        manager.release()

        print(
            "All camera workers stopped."
        )


if __name__ == "__main__":
    main()