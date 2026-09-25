from src.config.settings import load_config, resolve_path
from src.video.file_source import FileVideoSource
from src.tracking.ultralytics_tracker import UltralyticsPersonTracker


def main():
    config = load_config()

    # -------------------------
    # Select first enabled camera
    # -------------------------

    cameras = [
        camera
        for camera in config["cameras"]
        if camera.get("enabled", True)
    ]

    if not cameras:
        print("No enabled cameras found.")
        return

    camera = cameras[0]

    print(f"Testing camera: {camera['id']}")

    # -------------------------
    # Video source
    # -------------------------

    source = FileVideoSource(
        str(resolve_path(camera["source"]))
    )

    source.open()

    if not source.is_opened():
        print("Could not open video.")
        return

    # -------------------------
    # Tracker
    # -------------------------

    inference_config = config["inference"]
    tracking_config = config["tracking"]

    tracker = UltralyticsPersonTracker(
        model_path=str(resolve_path(inference_config["model"])),
        confidence=inference_config["confidence"],
        image_size=inference_config["image_size"],
        device=inference_config["device"],
        tracker=tracking_config["tracker"],
    )

    # -------------------------
    # Read video frames
    # -------------------------

    print("Reading video frames...")
    print()

    for frame_number in range(10):
        success, frame = source.read()

        if not success:
            print("Could not read frame.")
            break

        detections = tracker.infer(frame)

        track_ids = [
            detection.track_id
            for detection in detections
            if detection.track_id is not None
        ]

        print(
            f"Frame {frame_number + 1}: "
            f"people={len(detections)}, "
            f"track_ids={track_ids}"
        )

    # -------------------------
    # Cleanup
    # -------------------------

    tracker.reset()
    source.release()

    print()
    print("Tracking test complete.")


if __name__ == "__main__":
    main()