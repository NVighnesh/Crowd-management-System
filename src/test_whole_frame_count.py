from src.config.settings import load_config
from src.video.file_source import FileVideoSource
from src.detection.ultralytics_detector import UltralyticsPersonDetector
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
    # Detector
    # -------------------------

    inference_config = config["inference"]

    detector = UltralyticsPersonDetector(
        model_path=inference_config["model"],
        confidence=inference_config["confidence"],
        image_size=inference_config["image_size"],
        device=inference_config["device"],
    )

    # -------------------------
    # Whole-frame counter
    # -------------------------

    counter = WholeFrameCounter()

    # -------------------------
    # Read frame
    # -------------------------

    success, frame = source.read()

    if not success:
        print("Could not read frame.")
        source.release()
        return

    # -------------------------
    # Detection
    # -------------------------

    detections = detector.infer(frame)

    # -------------------------
    # Count
    # -------------------------

    total_people = counter.count(detections)

    print("Whole-frame counting test successful.")
    print(f"Total people in frame: {total_people}")

    source.release()


if __name__ == "__main__":
    main()