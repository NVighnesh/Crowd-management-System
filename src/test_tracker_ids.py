from src.config.settings import load_config, resolve_path
from src.config.validator import ConfigValidator
from src.tracking.ultralytics_tracker import (
    UltralyticsPersonTracker,
)
from src.video.file_source import FileVideoSource


def main():

    print("Testing actual YOLO tracker...")

    # --------------------------------------------------
    # Load configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    inference_config = config["inference"]
    tracking_config = config["tracking"]

    # --------------------------------------------------
    # Create video source
    # --------------------------------------------------

    camera = next(
        camera
        for camera in config["cameras"]
        if camera.get("enabled", True)
    )

    source = FileVideoSource(
        path=str(
            resolve_path(
                camera["source"]
            )
        ),
        loop=False,
    )

    source.open()

    if not source.is_opened():

        raise RuntimeError(
            f"Could not open video source: "
            f"{camera['source']}"
        )

    # --------------------------------------------------
    # Create actual tracker
    # --------------------------------------------------

    tracker = UltralyticsPersonTracker(
        model_path=str(
            resolve_path(
                inference_config["model"]
            )
        ),
        confidence=inference_config[
            "confidence"
        ],
        image_size=inference_config[
            "image_size"
        ],
        device=inference_config[
            "device"
        ],
        tracker=tracking_config[
            "tracker"
        ],
    )

    # --------------------------------------------------
    # Read first frame
    # --------------------------------------------------

    success, frame = source.read()

    if not success:

        source.release()

        raise RuntimeError(
            "Could not read a frame from "
            "the video source."
        )

    print(
        f"Testing camera: {camera['id']}"
    )

    print(
        f"Video source: {camera['source']}"
    )

    # --------------------------------------------------
    # Run tracker
    # --------------------------------------------------

    detections = tracker.infer(frame)

    # --------------------------------------------------
    # Analyze track IDs
    # --------------------------------------------------

    total_detections = len(
        detections
    )

    detections_with_ids = sum(
        1
        for detection in detections
        if detection.track_id is not None
    )

    detections_without_ids = (
        total_detections
        - detections_with_ids
    )

    print(
        f"Total person detections: "
        f"{total_detections}"
    )

    print(
        f"Detections with track IDs: "
        f"{detections_with_ids}"
    )

    print(
        f"Detections without track IDs: "
        f"{detections_without_ids}"
    )

    # --------------------------------------------------
    # Print individual detections
    # --------------------------------------------------

    for detection in detections:

        print(
            f"  bbox={detection.bbox}, "
            f"confidence="
            f"{detection.confidence:.2f}, "
            f"track_id="
            f"{detection.track_id}"
        )

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    if total_detections == 0:

        print(
            "\nNo people detected in the "
            "first frame."
        )

    elif detections_with_ids == 0:

        raise AssertionError(
            "Tracker returned detections, "
            "but none have a track ID."
        )

    else:

        print(
            "\nTracker ID validation: PASS"
        )

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    tracker.reset()
    source.release()

    print(
        "Tracker ID test successful."
    )


if __name__ == "__main__":
    main()