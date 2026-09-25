import cv2

from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.inference.factory import InferenceFactory
from src.zones.zone_manager import ZoneManager
from src.crowd.analyzer import CrowdAnalyzer
from src.visualization.frame_annotator import FrameAnnotator


def main():

    print(
        "Testing frame annotation layer..."
    )

    # --------------------------------------------------
    # Load configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    camera = config["cameras"][0]

    print(
        f"Testing camera: "
        f"{camera['id']}"
    )

    # --------------------------------------------------
    # Open video
    # --------------------------------------------------

    video_path = camera["source"]

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():

        raise RuntimeError(
            f"Could not open video: "
            f"{video_path}"
        )

    success, frame = cap.read()

    cap.release()

    if not success:

        raise RuntimeError(
            "Could not read video frame."
        )

    print(
        f"Frame shape: "
        f"{frame.shape}"
    )

    # --------------------------------------------------
    # Create inference engine
    # --------------------------------------------------

    inference_engine = (
        InferenceFactory.create_engine(
            inference_config=config["inference"],
            tracking_config=config["tracking"],
        )
    )

    print(
        "Running AI inference..."
    )

    detections = (
        inference_engine.infer(frame)
    )

    print(
        f"People detected: "
        f"{len(detections)}"
    )

    # --------------------------------------------------
    # Load zones
    # --------------------------------------------------

    zone_manager = ZoneManager(
        camera["zones_config"],
        expected_camera_id=camera["id"],
    )

    zone_manager.load()

    zones = zone_manager.get_zones()

    print(
        f"Zones loaded: "
        f"{len(zones)}"
    )

    # --------------------------------------------------
    # Analyze crowd
    # --------------------------------------------------

    counting_config = config["counting"]

    analyzer = CrowdAnalyzer(
        whole_frame_enabled=(
            counting_config[
                "whole_frame"
            ]["enabled"]
        ),
        whole_frame_mode=(
            counting_config[
                "whole_frame"
            ]["mode"]
        ),
        zones_enabled=(
            counting_config[
                "zones"
            ]["enabled"]
        ),
        zone_point_mode=(
            counting_config[
                "zones"
            ]["point"]
        ),
    )

    result = analyzer.analyze(
        camera_id=camera["id"],
        detections=detections,
        zones=zones,
    )

    print(
        f"Total people: "
        f"{result.total_people}"
    )

    for zone in result.zones:

        print(
            f"  {zone.zone_id}: "
            f"{zone.count}/"
            f"{zone.threshold} "
            f"{zone.status}"
        )

    # --------------------------------------------------
    # Annotate frame
    # --------------------------------------------------

    annotator = FrameAnnotator()

    annotated_frame = (
        annotator.annotate(
            frame=frame,
            detections=detections,
            zones=zones,
            result=result,
        )
    )

    print(
        f"Annotated frame shape: "
        f"{annotated_frame.shape}"
    )

    # --------------------------------------------------
    # Validate output
    # --------------------------------------------------

    if annotated_frame is None:

        raise AssertionError(
            "Annotated frame is None."
        )

    if annotated_frame.shape != frame.shape:

        raise AssertionError(
            "Annotated frame dimensions "
            "do not match original frame."
        )

    # --------------------------------------------------
    # Save test output
    # --------------------------------------------------

    output_path = (
        "outputs/test_annotated_frame.jpg"
    )

    success = cv2.imwrite(
        output_path,
        annotated_frame,
    )

    if not success:

        raise RuntimeError(
            "Failed to save annotated frame."
        )

    print(
        f"Annotated frame saved to: "
        f"{output_path}"
    )

    print(
        "\nFrame annotation test successful."
    )


if __name__ == "__main__":
    main()