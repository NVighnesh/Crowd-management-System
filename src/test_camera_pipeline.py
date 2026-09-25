from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.camera_pipeline import CameraPipeline


def main():

    config = load_config()

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = camera_manager.get_enabled_cameras()

    if not cameras:
        print("No enabled cameras found.")
        return

    camera = cameras[0]

    pipeline = CameraPipeline(
        camera_config=camera,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        zones_config=config["counting"]["zones"]["config"],
    )

    pipeline.setup()

    print(f"Processing camera: {camera['id']}")

    for frame_number in range(10):

        result = pipeline.process_frame()

        if result is None:
            print("End of video.")
            break

        print(
            f"Frame {frame_number + 1}: "
            f"total={result.total_people}"
        )

        for zone in result.zones:

            print(
                f"  {zone.zone_id}: "
                f"{zone.count}/{zone.threshold} "
                f"{zone.status}"
            )

    pipeline.release()

    print("Camera pipeline test complete.")


if __name__ == "__main__":
    main()