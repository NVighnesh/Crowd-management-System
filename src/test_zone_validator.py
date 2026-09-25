from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.zones.zone_validator import ZoneValidator


def main():

    config = load_config()

    ConfigValidator.validate(config)

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = (
        camera_manager.get_enabled_cameras()
    )

    for camera in cameras:

        ZoneValidator.validate_file(
            config_path=camera["zones_config"],
            expected_camera_id=camera["id"],
        )

        print(
            f"{camera['id']}: "
            "zone configuration valid."
        )

    print(
        "Zone validation successful."
    )


if __name__ == "__main__":
    main()