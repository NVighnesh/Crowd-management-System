import time
import statistics

from src.config.settings import load_config
from src.video.camera_manager import CameraManager
from src.video.file_source import FileVideoSource
from src.detection.ultralytics_detector import (
    UltralyticsPersonDetector,
)
from src.zones.zone_manager import ZoneManager
from src.zones.zone_counter import ZoneCounter


def main():

    config = load_config()

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = camera_manager.get_enabled_cameras()

    if not cameras:
        print("No enabled cameras.")
        return

    camera = cameras[0]

    print(
        f"Testing detection-only counting: "
        f"{camera['id']}"
    )

    # --------------------------------------------------
    # Video source
    # --------------------------------------------------

    source = FileVideoSource(
        path=camera["source"],
        loop=True,
    )

    source.open()

    if not source.is_opened():

        print(
            f"Could not open source: "
            f"{camera['source']}"
        )

        return

    # --------------------------------------------------
    # Detector
    # --------------------------------------------------

    detector = UltralyticsPersonDetector(
        model_path=config["inference"]["model"],
        confidence=config["inference"]["confidence"],
        image_size=config["inference"]["image_size"],
        device=config["inference"]["device"],
    )

    # --------------------------------------------------
    # Zones
    # --------------------------------------------------

    zone_manager = ZoneManager(
        camera["zones_config"],
        expected_camera_id=camera["id"],
    )

    zone_manager.load()

    zones = zone_manager.get_zones()

    zone_counter = ZoneCounter()

    print(
        f"Model: "
        f"{config['inference']['model']}"
    )

    print(
        f"Image size: "
        f"{config['inference']['image_size']}"
    )

    print(
        f"Zones: {len(zones)}"
    )

    # --------------------------------------------------
    # Warm-up
    # --------------------------------------------------

    print(
        "Warming up for 5 seconds..."
    )

    warmup_start = time.time()

    while time.time() - warmup_start < 5:

        success, frame = source.read()

        if not success:
            continue

        detector.infer(frame)

    print(
        "Warm-up complete."
    )

    # --------------------------------------------------
    # Measurement
    # --------------------------------------------------

    total_counts = []
    zone_counts = {
        zone["zone_id"]: []
        for zone in zones
    }

    inference_times = []

    print(
        "Measuring detection-only counting "
        "for 10 seconds...\n"
    )

    start_time = time.time()

    frame_number = 0

    try:

        while time.time() - start_time < 10:

            success, frame = source.read()

            if not success:
                continue

            inference_start = time.perf_counter()

            detections = detector.infer(frame)

            inference_time = (
                time.perf_counter()
                - inference_start
            )

            inference_times.append(
                inference_time
            )

            frame_number += 1

            # Whole-frame count
            total_people = len(detections)

            total_counts.append(
                total_people
            )

            # Zone counts
            results = zone_counter.count(
                detections,
                zones,
            )

            for zone in zones:

                zone_id = zone["zone_id"]

                zone_counts[zone_id].append(
                    results[zone_id]["count"]
                )

    finally:

        elapsed = time.time() - start_time

        print(
            "Detection-only counting results:"
        )

        print(
            "-" * 60
        )

        print(
            f"Frames processed: "
            f"{frame_number}"
        )

        print(
            f"Measurement time: "
            f"{elapsed:.2f} seconds"
        )

        if elapsed > 0:

            print(
                f"Effective inference FPS: "
                f"{frame_number / elapsed:.2f}"
            )

        if inference_times:

            average_latency = (
                statistics.mean(inference_times)
                * 1000
            )

            print(
                f"Average inference latency: "
                f"{average_latency:.2f} ms"
            )

        # --------------------------------------------------
        # Whole-frame statistics
        # --------------------------------------------------

        if total_counts:

            print()
            print(
                "Whole-frame count:"
            )

            print(
                f"  Minimum: "
                f"{min(total_counts)}"
            )

            print(
                f"  Maximum: "
                f"{max(total_counts)}"
            )

            print(
                f"  Average: "
                f"{statistics.mean(total_counts):.2f}"
            )

            print(
                f"  First: "
                f"{total_counts[0]}"
            )

            print(
                f"  Last: "
                f"{total_counts[-1]}"
            )

        # --------------------------------------------------
        # Zone statistics
        # --------------------------------------------------

        print()

        print(
            "Zone count stability:"
        )

        for zone in zones:

            zone_id = zone["zone_id"]

            counts = zone_counts[zone_id]

            if not counts:
                continue

            print(
                f"  {zone_id}:"
            )

            print(
                f"    Minimum: "
                f"{min(counts)}"
            )

            print(
                f"    Maximum: "
                f"{max(counts)}"
            )

            print(
                f"    Average: "
                f"{statistics.mean(counts):.2f}"
            )

        print(
            "-" * 60
        )

        source.release()

        print(
            "Test complete."
        )


if __name__ == "__main__":
    main()