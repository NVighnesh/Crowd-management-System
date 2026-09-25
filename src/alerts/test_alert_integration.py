import time

from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager


def main():

    print("Testing multi-camera alert integration...")

    # --------------------------------------------------
    # Load and validate configuration
    # --------------------------------------------------

    config = load_config()

    ConfigValidator.validate(config)

    camera_manager = CameraManager(
        config["cameras"]
    )

    enabled_cameras = (
        camera_manager.get_enabled_cameras()
    )

    print()
    print(
        f"Enabled cameras: "
        f"{len(enabled_cameras)}"
    )

    # --------------------------------------------------
    # Create multi-camera manager
    # --------------------------------------------------

    manager = MultiCameraManager(
        cameras=enabled_cameras,
        inference_config=config["inference"],
        tracking_config=config["tracking"],
        counting_config=config["counting"],
        processing_config=config["processing"],
    )

    try:

        # --------------------------------------------------
        # Start cameras
        # --------------------------------------------------

        manager.setup()

        print(
            "All camera workers started."
        )

        # --------------------------------------------------
        # Wait for first results
        # --------------------------------------------------

        print()
        print(
            "Waiting for first AI results..."
        )

        timeout = 30
        start_time = time.time()

        while time.time() - start_time < timeout:

            results = (
                manager.get_all_latest_results()
            )

            ready = len(results)

            print(
                f"\r  Results ready: "
                f"{ready}/"
                f"{len(enabled_cameras)}",
                end="",
                flush=True,
            )

            if ready == len(enabled_cameras):

                break

            time.sleep(0.5)

        print()

        if len(results) != len(enabled_cameras):

            raise AssertionError(
                "Not all cameras produced "
                "an AI result within the timeout."
            )

        print(
            "All cameras produced their first "
            "AI result."
        )

        # --------------------------------------------------
        # Display results
        # --------------------------------------------------

        print()
        print(
            "Latest crowd results:"
        )

        for camera_id, result in results.items():

            print()
            print(
                f"{camera_id}:"
            )

            print(
                f"  Total people: "
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
        # Check AlertManager integration
        # --------------------------------------------------

        alert_count = (
            manager.get_alert_count()
        )

        print()
        print(
            f"Alerts currently stored: "
            f"{alert_count}"
        )

        print()
        print(
            "AlertManager integration: PASS"
        )

        # --------------------------------------------------
        # Check alert access methods
        # --------------------------------------------------

        all_alerts = (
            manager.get_all_alerts()
        )

        latest_alert = (
            manager.get_latest_alert()
        )

        print()
        print(
            f"All alerts returned: "
            f"{len(all_alerts)}"
        )

        if alert_count > 0:

            if latest_alert is None:

                raise AssertionError(
                    "Latest alert should not "
                    "be None when alerts exist."
                )

            print(
                "Latest alert:"
            )

            print(
                f"  Camera: "
                f"{latest_alert.camera_id}"
            )

            print(
                f"  Zone: "
                f"{latest_alert.zone_id}"
            )

            print(
                f"  Type: "
                f"{latest_alert.alert_type}"
            )

        # --------------------------------------------------
        # Verify camera-specific alert access
        # --------------------------------------------------

        for camera in enabled_cameras:

            camera_id = camera["id"]

            camera_alerts = (
                manager.get_camera_alerts(
                    camera_id
                )
            )

            print(
                f"{camera_id} alerts: "
                f"{len(camera_alerts)}"
            )

            for alert in camera_alerts:

                if alert.camera_id != camera_id:

                    raise AssertionError(
                        "Camera alert filtering "
                        "returned an alert belonging "
                        "to another camera."
                    )

        print()
        print(
            "Camera alert filtering: PASS"
        )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print()
        print(
            "Multi-camera alert integration "
            "test successful."
        )

    finally:

        # --------------------------------------------------
        # Always release resources
        # --------------------------------------------------

        manager.release()

        print()
        print(
            "All camera workers stopped."
        )


if __name__ == "__main__":

    main()