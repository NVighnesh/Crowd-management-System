from src.config.settings import load_config, resolve_path
from src.video.file_source import FileVideoSource
from src.tracking.ultralytics_tracker import UltralyticsPersonTracker
from src.zones.zone_manager import ZoneManager
from src.zones.zone_counter import ZoneCounter


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
    # Zone manager
    # -------------------------

    zone_manager = ZoneManager(
        str(resolve_path(camera["zones_config"]))
    )

    zone_manager.load()

    zones = zone_manager.get_zones()

    print(f"Loaded zones: {len(zones)}")
    print()

    # -------------------------
    # Zone counter
    # -------------------------

    zone_counter = ZoneCounter()

    # -------------------------
    # Read first frame
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

    print(f"Detections: {len(detections)}")
    print()

    # -------------------------
    # Zone counting
    # -------------------------

    results = zone_counter.count(
        detections,
        zones
    )

    print("Zone counting test successful.")
    print()

    for zone_id, result in results.items():
        print(
            f"{zone_id} | "
            f"{result['name']} | "
            f"count={result['count']} | "
            f"threshold={result['threshold']}"
        )

    # -------------------------
    # Cleanup
    # -------------------------

    tracker.reset()
    source.release()


if __name__ == "__main__":
    main()