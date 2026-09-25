from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager


def main():
    config = load_config()

    # -------------------------
    # Camera configuration
    # -------------------------

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = camera_manager.get_enabled_cameras()

    print(f"Enabled cameras: {len(cameras)}")

    if not cameras:
        print("No enabled cameras.")
        return

    # -------------------------
    # Multi-camera manager
    # -------------------------

    manager = MultiCameraManager(
        cameras=cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=config["processing"],
    )

    manager.setup()

    print(
        f"Active pipelines: "
        f"{manager.get_camera_ids()}"
    )

    # -------------------------
    # Process one frame
    # -------------------------

    for camera_id in manager.get_camera_ids():

        result = manager.process_frame(
            camera_id
        )

        if result is None:
            print(
                f"{camera_id}: "
                f"no frame available"
            )
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

    manager.release()

    print("Multi-camera test complete.")


if __name__ == "__main__":
    main()