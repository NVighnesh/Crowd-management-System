from src.config.settings import load_config
from src.video.camera_manager import CameraManager


def main():

    config = load_config()

    manager = CameraManager(
        config["cameras"]
    )

    print(
        "All cameras:",
        manager.get_camera_ids(),
    )

    print(
        "Enabled cameras:",
        manager.get_enabled_camera_ids(),
    )

    print(
        "CAM_001 exists:",
        manager.has_camera("CAM_001"),
    )

    camera = manager.get_camera(
        "CAM_001"
    )

    print(
        "CAM_001 source:",
        camera["source"],
    )

    print(
        "Camera manager test successful."
    )


if __name__ == "__main__":
    main()