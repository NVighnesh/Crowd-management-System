import cv2

from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.video.file_source import FileVideoSource
from src.zones.zone_manager import ZoneManager


def main():

    config = load_config()
    ConfigValidator.validate(config)

    camera_manager = CameraManager(config["cameras"])
    cameras = camera_manager.get_enabled_cameras()

    for camera in cameras:

        print(f"\nChecking camera: {camera['id']}")

        source = FileVideoSource(
            path=str(camera["source"]),
            loop=False,
        )

        source.open()

        if not source.is_opened():
            print("Could not open video source.")
            continue

        success, frame = source.read()

        if not success:
            print("Could not read first frame.")
            source.release()
            continue

        height, width = frame.shape[:2]

        print(f"Actual frame size: {width} x {height}")

        zone_manager = ZoneManager(
            config_path=camera["zones_config"],
            expected_camera_id=camera["id"],
        )

        zone_manager.load()

        try:

            zone_manager.validate_against_frame(
                frame_width=width,
                frame_height=height,
            )

            print("All zone coordinates are inside the frame.")

        except ValueError as error:

            print(f"ZONE VALIDATION FAILED: {error}")

        source.release()


if __name__ == "__main__":
    main()