from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.camera_pipeline import CameraPipeline


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

    if not cameras:

        print("No enabled cameras.")
        return

    # --------------------------------------------------
    # Test first enabled camera
    # --------------------------------------------------

    camera = cameras[0]

    print(
        f"Testing camera: {camera['id']}"
    )

    # --------------------------------------------------
    # Create camera pipeline
    # --------------------------------------------------

    pipeline = CameraPipeline(
        camera_config=camera,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        zones_config=camera["zones_config"],
    )

    # --------------------------------------------------
    # Setup pipeline
    # --------------------------------------------------

    pipeline.setup()

    print(
        f"Video source: {camera['source']}"
    )

    # --------------------------------------------------
    # Read one frame
    # --------------------------------------------------

    success, frame = pipeline.source.read()

    if not success:

        print(
            "Could not read video frame."
        )

        pipeline.release()
        return

    # --------------------------------------------------
    # Process frame
    # --------------------------------------------------

    result = pipeline.process_frame(
        frame
    )

    if result is None:

        print(
            "No result produced."
        )

        pipeline.release()
        return

    # --------------------------------------------------
    # Display result
    # --------------------------------------------------

    print(
        f"People detected: "
        f"{result.total_people}"
    )

    for zone in result.zones:

        print(
            f"{zone.zone_id}: "
            f"{zone.count}/"
            f"{zone.threshold} "
            f"{zone.status}"
        )

    # --------------------------------------------------
    # Release resources
    # --------------------------------------------------

    pipeline.release()

    print(
        "Pipeline test successful."
    )


if __name__ == "__main__":
    main()