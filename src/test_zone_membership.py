import cv2

from src.config.settings import load_config, resolve_path
from src.video.file_source import FileVideoSource
from src.video.camera_manager import CameraManager
from src.zones.zone_manager import ZoneManager
from src.zones.zone_counter import ZoneCounter
from src.inference.factory import InferenceFactory


def main():

    config = load_config()

    camera_manager = CameraManager(config["cameras"])
    camera = camera_manager.get_enabled_cameras()[0]

    print(f"Testing camera: {camera['id']}")

    source = FileVideoSource(
        path=str(resolve_path(camera["source"])),
        loop=False,
    )

    source.open()

    if not source.is_opened():
        raise RuntimeError("Could not open video source.")

    success, frame = source.read()

    if not success:
        raise RuntimeError("Could not read frame.")

    height, width = frame.shape[:2]

    print(f"Frame size: {width} x {height}")

    zone_manager = ZoneManager(
        config_path=camera["zones_config"],
        expected_camera_id=camera["id"],
    )

    zone_manager.load()

    zone_manager.validate_against_frame(
        frame_width=width,
        frame_height=height,
    )

    inference_engine = InferenceFactory.create_engine(
        inference_config=config["inference"],
        tracking_config={
            **config["tracking"],
            "enabled": False,
        },
    )

    detections = inference_engine.infer(frame)

    print(f"\nDetected people: {len(detections)}")

    for index, detection in enumerate(detections, start=1):

        x1, y1, x2, y2 = detection.bbox

        center_x = int((x1 + x2) / 2)
        bottom_y = int(y2)

        print(
            f"Person {index}: "
            f"bbox=({x1}, {y1}, {x2}, {y2}) "
            f"bottom_center=({center_x}, {bottom_y})"
        )

    counter = ZoneCounter()

    zone_results = counter.count(
        detections=detections,
        zones=zone_manager.get_zones(),
    )

    print("\nZone membership results:")

    for zone_id, result in zone_results.items():

        print(
            f"{zone_id}: "
            f"{result['count']} people"
        )

    source.release()

    print("\nZone membership test successful.")


if __name__ == "__main__":
    main()