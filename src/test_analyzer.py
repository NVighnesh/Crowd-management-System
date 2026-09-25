from src.config.settings import load_config, resolve_path
from src.video.file_source import FileVideoSource
from src.tracking.ultralytics_tracker import UltralyticsPersonTracker
from src.zones.zone_manager import ZoneManager
from src.crowd.analyzer import CrowdAnalyzer


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
    # Video
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
    # Zones
    # -------------------------

    zone_manager = ZoneManager(
        str(resolve_path(camera["zones_config"]))
    )

    zone_manager.load()

    zones = zone_manager.get_zones()

    print(f"Loaded zones: {len(zones)}")

    # -------------------------
    # Analyzer
    # -------------------------

    analyzer = CrowdAnalyzer()

    # -------------------------
    # Read frame
    # -------------------------

    success, frame = source.read()

    if not success:
        print("Could not read frame.")
        source.release()
        return

    # -------------------------
    # Tracking
    # -------------------------

    detections = tracker.infer(frame)

    print(f"Tracked detections: {len(detections)}")

    # -------------------------
    # Analysis
    # -------------------------

    result = analyzer.analyze(
        camera_id=camera["id"],
        detections=detections,
        zones=zones,
    )

    # -------------------------
    # Display result
    # -------------------------

    print()
    print("===================================")
    print("CROWD ANALYSIS RESULT")
    print("===================================")

    print(f"Camera: {result.camera_id}")
    print(f"Whole-frame people: {result.total_people}")

    print()
    print("Zones:")

    for zone in result.zones:
        print(
            f"{zone.zone_id} | "
            f"{zone.name} | "
            f"count={zone.count} | "
            f"threshold={zone.threshold} | "
            f"status={zone.status}"
        )

    print("===================================")

    # -------------------------
    # Cleanup
    # -------------------------

    tracker.reset()
    source.release()


if __name__ == "__main__":
    main()