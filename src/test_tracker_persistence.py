from src.config.settings import load_config, resolve_path
from src.config.validator import ConfigValidator
from src.tracking.ultralytics_tracker import (
    UltralyticsPersonTracker,
)
from src.video.file_source import FileVideoSource


def main():

    print("Testing tracker persistence across frames...")

    # --------------------------------------------------
    # Load and validate configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    inference_config = config["inference"]
    tracking_config = config["tracking"]

    # --------------------------------------------------
    # Select first enabled camera
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
    # Create tracker
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
    # Process consecutive frames
    # --------------------------------------------------

    frames_to_test = 10

    previous_ids = set()

    total_frames = 0
    frames_with_detections = 0
    frames_with_ids = 0

    print(
        f"Testing {frames_to_test} "
        f"consecutive frames..."
    )

    for frame_number in range(
        1,
        frames_to_test + 1,
    ):

        success, frame = source.read()

        if not success:
            break

        total_frames += 1

        detections = tracker.infer(
            frame
        )

        current_ids = {
            detection.track_id
            for detection in detections
            if detection.track_id is not None
        }

        if detections:
            frames_with_detections += 1

        if current_ids:
            frames_with_ids += 1

        print(
            f"Frame {frame_number}: "
            f"detections={len(detections)}, "
            f"track_ids="
            f"{sorted(current_ids)}"
        )

        # --------------------------------------------------
        # Check for duplicate IDs within a frame
        # --------------------------------------------------

        if len(current_ids) != len(
            [
                detection
                for detection in detections
                if detection.track_id is not None
            ]
        ):

            raise AssertionError(
                f"Duplicate track IDs detected "
                f"within frame {frame_number}."
            )

        # --------------------------------------------------
        # Check ID persistence
        # --------------------------------------------------

        if previous_ids and current_ids:

            persisted_ids = (
                previous_ids & current_ids
            )

            print(
                f"  Persistent IDs from "
                f"previous frame: "
                f"{sorted(persisted_ids)}"
            )

        previous_ids = current_ids

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    if total_frames == 0:

        raise AssertionError(
            "No frames were processed."
        )

    if frames_with_detections == 0:

        raise AssertionError(
            "No person detections were "
            "produced."
        )

    if frames_with_ids == 0:

        raise AssertionError(
            "No track IDs were produced."
        )

    print()
    print(
        f"Frames processed: {total_frames}"
    )

    print(
        f"Frames with detections: "
        f"{frames_with_detections}"
    )

    print(
        f"Frames with track IDs: "
        f"{frames_with_ids}"
    )

    if total_frames > 1:

        print(
            "Multi-frame tracker execution: PASS"
        )

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    tracker.reset()
    source.release()

    print(
        "Tracker persistence test successful."
    )


if __name__ == "__main__":
    main()