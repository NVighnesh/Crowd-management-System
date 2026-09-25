import time

from src.config.settings import load_config
from src.config.validator import ConfigValidator
from src.video.camera_manager import CameraManager
from src.video.multi_camera_manager import MultiCameraManager
from src.system.overview_service import SystemOverviewService


def main():

    print("Testing system overview service...")

    # --------------------------------------------------
    # Load configuration
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

    multi_camera_manager = MultiCameraManager(
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

        multi_camera_manager.setup()

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

        start_time = time.time()
        timeout = 30

        while (
            time.time() - start_time
            < timeout
        ):

            results = (
                multi_camera_manager
                .get_all_latest_results()
            )

            ready = len(results)

            print(
                f"\r  Results ready: "
                f"{ready}/"
                f"{len(enabled_cameras)}",
                end="",
                flush=True,
            )

            if ready == len(
                enabled_cameras
            ):

                break

            time.sleep(0.5)

        print()

        if len(results) != len(
            enabled_cameras
        ):

            raise AssertionError(
                "Not all cameras produced "
                "an AI result within the "
                "timeout."
            )

        print(
            "All cameras produced their "
            "first AI result."
        )

        # --------------------------------------------------
        # Create overview service
        # --------------------------------------------------

        service = SystemOverviewService(
            camera_manager=camera_manager,
            multi_camera_manager=(
                multi_camera_manager
            ),
        )

        # --------------------------------------------------
        # Get system overview
        # --------------------------------------------------

        overview = service.get_overview()

        print()
        print(
            "System overview:"
        )

        print(
            f"  Total cameras: "
            f"{overview.total_cameras}"
        )

        print(
            f"  Online cameras: "
            f"{overview.online_cameras}"
        )

        print(
            f"  Offline cameras: "
            f"{overview.offline_cameras}"
        )

        print(
            f"  Stale cameras: "
            f"{overview.stale_cameras}"
        )

        print(
            f"  Total people: "
            f"{overview.total_people}"
        )

        print(
            f"  Total alerts: "
            f"{overview.total_alerts}"
        )

        # --------------------------------------------------
        # Validate camera count
        # --------------------------------------------------

        if overview.total_cameras != len(
            enabled_cameras
        ):

            raise AssertionError(
                "Incorrect total camera count."
            )

        if (
            overview.online_cameras
            + overview.offline_cameras
            + overview.stale_cameras
            != overview.total_cameras
        ):

            raise AssertionError(
                "Camera status counts do "
                "not add up to total cameras."
            )

        print()
        print(
            "Camera status aggregation: PASS"
        )

        # --------------------------------------------------
        # Validate individual cameras
        # --------------------------------------------------

        if len(overview.cameras) != len(
            enabled_cameras
        ):

            raise AssertionError(
                "Overview does not contain "
                "all enabled cameras."
            )

        calculated_total_people = 0

        for camera in overview.cameras:

            camera_id = camera[
                "camera_id"
            ]

            print()
            print(
                f"{camera_id}:"
            )

            print(
                f"  Status: "
                f"{camera['status']}"
            )

            print(
                f"  Processing: "
                f"{camera['processing_status']}"
            )

            print(
                f"  Total people: "
                f"{camera['total_people']}"
            )

            print(
                f"  Fresh: "
                f"{camera['fresh']}"
            )

            print(
                f"  Zones: "
                f"{len(camera['zones'])}"
            )

            if camera["total_people"] is not None:

                calculated_total_people += (
                    camera["total_people"]
                )

            if camera["status"] != "ONLINE":

                raise AssertionError(
                    f"{camera_id} should be "
                    "ONLINE during this test."
                )

            if camera[
                "processing_status"
            ] != "HEALTHY":

                raise AssertionError(
                    f"{camera_id} processing "
                    "should be HEALTHY."
                )

            if not camera["fresh"]:

                raise AssertionError(
                    f"{camera_id} result "
                    "should be fresh."
                )

        # --------------------------------------------------
        # Validate total people
        # --------------------------------------------------

        print()
        print(
            f"Calculated total people: "
            f"{calculated_total_people}"
        )

        if (
            overview.total_people
            != calculated_total_people
        ):

            raise AssertionError(
                "System total people does "
                "not match the sum of camera "
                "totals."
            )

        print(
            "Total people aggregation: PASS"
        )

        # --------------------------------------------------
        # Validate alerts
        # --------------------------------------------------

        alerts = (
            multi_camera_manager
            .get_all_alerts()
        )

        if overview.total_alerts != len(
            alerts
        ):

            raise AssertionError(
                "System alert count does "
                "not match AlertManager."
            )

        print()
        print(
            "Alert aggregation: PASS"
        )

        # --------------------------------------------------
        # Validate zones
        # --------------------------------------------------

        for camera in overview.cameras:

            if len(camera["zones"]) == 0:

                raise AssertionError(
                    f"{camera['camera_id']} "
                    "should contain zone data."
                )

            for zone in camera["zones"]:

                required_fields = {
                    "zone_id",
                    "name",
                    "count",
                    "threshold",
                    "status",
                }

                if not required_fields.issubset(
                    zone.keys()
                ):

                    raise AssertionError(
                        "Zone data is missing "
                        "required fields."
                    )

        print(
            "Zone aggregation: PASS"
        )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print()
        print(
            "System overview service "
            "test successful."
        )

    finally:

        multi_camera_manager.release()

        print()
        print(
            "All camera workers stopped."
        )


if __name__ == "__main__":

    main()