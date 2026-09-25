from src.config.settings import load_config
from src.video.file_source import FileVideoSource
from src.tracking.ultralytics_tracker import UltralyticsPersonTracker
from src.crowd.whole_frame_counter import WholeFrameCounter


def main():

    config = load_config()

    # -------------------------
    # Video source
    # -------------------------

    source = FileVideoSource(
        config["camera"]["source"]
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
        model_path=inference_config["model"],
        confidence=inference_config["confidence"],
        image_size=inference_config["image_size"],
        device=inference_config["device"],
        tracker=tracking_config["tracker"],
    )

    # -------------------------
    # Whole-frame counter
    # -------------------------

    counter = WholeFrameCounter()

    print("Live whole-frame counting started.")
    print("Processing 30 frames...\n")

    # -------------------------
    # Process frames
    # -------------------------

    for frame_number in range(30):

        success, frame = source.read()

        if not success:
            break

        detections = tracker.update(frame)

        total_people = counter.count(detections)

        track_ids = [
            detection.track_id
            for detection in detections
            if detection.track_id is not None
        ]

        print(
            f"Frame {frame_number + 1}: "
            f"total_people={total_people}, "
            f"active_tracks={len(track_ids)}"
        )

    # -------------------------
    # Cleanup
    # -------------------------

    tracker.reset()
    source.release()

    print("\nLive counting test complete.")


if __name__ == "__main__":
    main()