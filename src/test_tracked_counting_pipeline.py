from src.config.settings import (
    load_config,
    resolve_path,
)
from src.config.validator import ConfigValidator

from src.video.file_source import FileVideoSource

from src.tracking.ultralytics_tracker import (
    UltralyticsPersonTracker,
)

from src.zones.zone_manager import ZoneManager

from src.crowd.analyzer import CrowdAnalyzer


def main():

    print(
        "Testing complete tracked "
        "counting pipeline..."
    )

    # --------------------------------------------------
    # Load and validate configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    inference_config = config["inference"]
    tracking_config = config["tracking"]
    counting_config = config["counting"]

    # --------------------------------------------------
    # Select first enabled camera
    # --------------------------------------------------

    camera = next(
        camera
        for camera in config["cameras"]
        if camera.get("enabled", True)
    )

    camera_id = camera["id"]

    print(
        f"Testing camera: {camera_id}"
    )

    print(
        f"Video source: "
        f"{camera['source']}"
    )

    # --------------------------------------------------
    # Create video source
    # --------------------------------------------------

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
    # Create zone manager
    # --------------------------------------------------

    zone_manager = ZoneManager(
        config_path=camera[
            "zones_config"
        ],
        expected_camera_id=camera_id,
    )

    zone_manager.load()

    # --------------------------------------------------
    # Read first frame for zone validation
    # --------------------------------------------------

    success, frame = source.read()

    if not success:

        source.release()

        raise RuntimeError(
            "Could not read first frame."
        )

    height, width = frame.shape[:2]

    zone_manager.validate_against_frame(
        frame_width=width,
        frame_height=height,
    )

    # --------------------------------------------------
    # Create analyzer using actual config
    # --------------------------------------------------

    whole_frame_config = (
        counting_config["whole_frame"]
    )

    zones_config = (
        counting_config["zones"]
    )

    analyzer = CrowdAnalyzer(
        whole_frame_enabled=(
            whole_frame_config["enabled"]
        ),
        whole_frame_mode=(
            whole_frame_config["mode"]
        ),
        zones_enabled=(
            zones_config["enabled"]
        ),
        zone_point_mode=(
            zones_config["point"]
        ),
    )

    # --------------------------------------------------
    # Process first frame + remaining frames
    # --------------------------------------------------

    frames_to_test = 10

    frames_processed = 0

    previous_track_ids = set()

    print(
        f"\nProcessing {frames_to_test} "
        f"consecutive frames..."
    )

    for frame_number in range(
        1,
        frames_to_test + 1,
    ):

        # First frame was already read.
        if frame_number > 1:

            success, frame = source.read()

            if not success:
                break

        frames_processed += 1

        # --------------------------------------------------
        # AI inference + tracking
        # --------------------------------------------------

        detections = tracker.infer(
            frame
        )

        # --------------------------------------------------
        # Track IDs
        # --------------------------------------------------

        current_track_ids = {
            detection.track_id
            for detection in detections
            if detection.track_id is not None
        }

        # --------------------------------------------------
        # Count raw detections
        # --------------------------------------------------

        raw_detection_count = len(
            detections
        )

        # --------------------------------------------------
        # Run complete analyzer
        # --------------------------------------------------

        result = analyzer.analyze(
            camera_id=camera_id,
            detections=detections,
            zones=zone_manager.get_zones(),
        )

        # --------------------------------------------------
        # Validate tracked count
        # --------------------------------------------------

        expected_tracked_count = len(
            current_track_ids
        )

        if (
            result.total_people
            != expected_tracked_count
        ):

            raise AssertionError(
                f"Frame {frame_number}: "
                f"tracked count mismatch. "
                f"Expected "
                f"{expected_tracked_count}, "
                f"got "
                f"{result.total_people}."
            )

        # --------------------------------------------------
        # Display result
        # --------------------------------------------------

        print(
            f"\nFrame {frame_number}:"
        )

        print(
            f"  Raw detections: "
            f"{raw_detection_count}"
        )

        print(
            f"  Active tracked people: "
            f"{result.total_people}"
        )

        print(
            f"  Track IDs: "
            f"{sorted(current_track_ids)}"
        )

        # --------------------------------------------------
        # Persistent IDs
        # --------------------------------------------------

        if previous_track_ids:

            persistent_ids = (
                previous_track_ids
                & current_track_ids
            )

            print(
                f"  Persistent IDs: "
                f"{sorted(persistent_ids)}"
            )

        # --------------------------------------------------
        # Zone results
        # --------------------------------------------------

        for zone in result.zones:

            print(
                f"  {zone.name}: "
                f"{zone.count}/"
                f"{zone.threshold} "
                f"{zone.status}"
            )

        previous_track_ids = (
            current_track_ids
        )

    # --------------------------------------------------
    # Final validation
    # --------------------------------------------------

    if frames_processed == 0:

        raise AssertionError(
            "No frames were processed."
        )

    print()
    print(
        f"Frames processed: "
        f"{frames_processed}"
    )

    print(
        "Tracked counting validation: PASS"
    )

    print(
        "Zone counting validation: PASS"
    )

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    tracker.reset()

    source.release()

    print(
        "\nComplete tracked counting "
        "pipeline test successful."
    )


if __name__ == "__main__":
    main()