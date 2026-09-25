from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.zones.zone_manager import ZoneManager


def main():

    # --------------------------------------------------
    # Load and validate application configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    # --------------------------------------------------
    # Get enabled cameras
    # --------------------------------------------------

    camera_manager = CameraManager(
        config["cameras"]
    )

    cameras = (
        camera_manager.get_enabled_cameras()
    )

    if not cameras:

        print("No enabled cameras.")
        return

    # --------------------------------------------------
    # Test zone manager for every enabled camera
    # --------------------------------------------------

    for camera in cameras:

        camera_id = camera["id"]

        print(
            f"\nTesting ZoneManager for "
            f"{camera_id}"
        )

        zone_manager = ZoneManager(
            config_path=camera["zones_config"],
            expected_camera_id=camera_id,
        )

        # --------------------------------------------------
        # Load zone configuration
        # --------------------------------------------------

        zone_manager.load()

        # --------------------------------------------------
        # Verify camera ID
        # --------------------------------------------------

        loaded_camera_id = (
            zone_manager.get_camera_id()
        )

        if loaded_camera_id != camera_id:

            raise AssertionError(
                f"Expected camera ID "
                f"{camera_id}, but got "
                f"{loaded_camera_id}"
            )

        # --------------------------------------------------
        # Get all zones
        # --------------------------------------------------

        zones = zone_manager.get_zones()

        if not zones:

            raise AssertionError(
                f"No zones loaded for "
                f"{camera_id}"
            )

        print(
            f"Loaded camera ID: "
            f"{loaded_camera_id}"
        )

        print(
            f"Number of zones: "
            f"{len(zones)}"
        )

        for zone in zones:

            print(
                f"  {zone['zone_id']}: "
                f"{zone['name']} "
                f"(threshold="
                f"{zone['threshold']})"
            )

        # --------------------------------------------------
        # Test get_zone()
        # --------------------------------------------------

        first_zone = zones[0]

        zone_id = first_zone[
            "zone_id"
        ]

        retrieved_zone = (
            zone_manager.get_zone(
                zone_id
            )
        )

        if retrieved_zone is None:

            raise AssertionError(
                f"Could not retrieve "
                f"zone {zone_id}"
            )

        if (
            retrieved_zone["zone_id"]
            != zone_id
        ):

            raise AssertionError(
                f"Retrieved incorrect "
                f"zone: {retrieved_zone}"
            )

        # --------------------------------------------------
        # Test missing zone
        # --------------------------------------------------

        missing_zone = (
            zone_manager.get_zone(
                "ZONE_DOES_NOT_EXIST"
            )
        )

        if missing_zone is not None:

            raise AssertionError(
                "Non-existent zone should "
                "return None."
            )

        print(
            "Zone retrieval checks passed."
        )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print(
        "\nZone manager test successful."
    )


if __name__ == "__main__":
    main()