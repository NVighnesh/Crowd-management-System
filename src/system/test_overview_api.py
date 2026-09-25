import time

from fastapi.testclient import TestClient

from src.api import app


def wait_for_fresh_results(
    client,
    camera_ids,
    timeout=30,
):

    start_time = time.time()

    while time.time() - start_time < timeout:

        ready = 0

        for camera_id in camera_ids:

            response = client.get(
                f"/cameras/{camera_id}/result"
            )

            if response.status_code != 200:
                continue

            data = response.json()

            if data.get("fresh") is True:
                ready += 1

        if ready == len(camera_ids):
            return True

        time.sleep(0.5)

    return False


def main():

    print("Testing system overview API...")

    with TestClient(app) as client:

        # --------------------------------------------------
        # Health
        # --------------------------------------------------

        print()
        print("Testing API startup...")

        response = client.get("/health")

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            raise AssertionError(
                "Health endpoint failed."
            )

        print(
            "  API startup: PASS"
        )

        # --------------------------------------------------
        # Get cameras
        # --------------------------------------------------

        response = client.get("/cameras")

        if response.status_code != 200:
            raise AssertionError(
                "Camera endpoint failed."
            )

        cameras_data = response.json()

        camera_ids = [
            camera["camera_id"]
            for camera in cameras_data["cameras"]
        ]

        print()
        print(
            f"Configured cameras: "
            f"{camera_ids}"
        )

        if not camera_ids:
            raise AssertionError(
                "No cameras are available."
            )

        # --------------------------------------------------
        # Wait for AI results
        # --------------------------------------------------

        print()
        print(
            "Waiting for fresh AI results..."
        )

        if not wait_for_fresh_results(
            client=client,
            camera_ids=camera_ids,
        ):

            raise AssertionError(
                "Not all cameras produced "
                "fresh AI results."
            )

        print(
            "  Fresh results available."
        )

        # --------------------------------------------------
        # GET /system/overview
        # --------------------------------------------------

        print()
        print(
            "Testing GET /system/overview..."
        )

        response = client.get(
            "/system/overview"
        )

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            raise AssertionError(
                "System overview endpoint failed."
            )

        overview = response.json()

        # --------------------------------------------------
        # Required top-level fields
        # --------------------------------------------------

        required_fields = {
            "total_cameras",
            "online_cameras",
            "offline_cameras",
            "stale_cameras",
            "total_people",
            "total_alerts",
            "cameras",
            "alerts",
        }

        missing_fields = (
            required_fields
            - set(overview.keys())
        )

        if missing_fields:

            raise AssertionError(
                f"System overview is missing "
                f"fields: {missing_fields}"
            )

        print(
            "  Required fields: PASS"
        )

        # --------------------------------------------------
        # Camera count validation
        # --------------------------------------------------

        print()
        print(
            "System overview:"
        )

        print(
            f"  Total cameras: "
            f"{overview['total_cameras']}"
        )

        print(
            f"  Online cameras: "
            f"{overview['online_cameras']}"
        )

        print(
            f"  Offline cameras: "
            f"{overview['offline_cameras']}"
        )

        print(
            f"  Stale cameras: "
            f"{overview['stale_cameras']}"
        )

        print(
            f"  Total people: "
            f"{overview['total_people']}"
        )

        print(
            f"  Total alerts: "
            f"{overview['total_alerts']}"
        )

        if overview["total_cameras"] != len(
            camera_ids
        ):

            raise AssertionError(
                "Incorrect total camera count."
            )

        if len(overview["cameras"]) != len(
            camera_ids
        ):

            raise AssertionError(
                "Overview does not contain "
                "all cameras."
            )

        if (
            overview["online_cameras"]
            + overview["offline_cameras"]
            + overview["stale_cameras"]
            != overview["total_cameras"]
        ):

            raise AssertionError(
                "Camera status counts do "
                "not add up."
            )

        print()
        print(
            "Camera aggregation: PASS"
        )

        # --------------------------------------------------
        # Validate individual camera data
        # --------------------------------------------------

        calculated_total_people = 0

        for camera in overview["cameras"]:

            camera_id = camera["camera_id"]

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

            if camera["camera_id"] not in camera_ids:

                raise AssertionError(
                    f"Unexpected camera: "
                    f"{camera_id}"
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

            if camera["total_people"] is None:

                raise AssertionError(
                    f"{camera_id} should have "
                    "a people count."
                )

            calculated_total_people += (
                camera["total_people"]
            )

            # ----------------------------------------------
            # Validate zone structure
            # ----------------------------------------------

            for zone in camera["zones"]:

                required_zone_fields = {
                    "zone_id",
                    "name",
                    "count",
                    "threshold",
                    "status",
                }

                missing_zone_fields = (
                    required_zone_fields
                    - set(zone.keys())
                )

                if missing_zone_fields:

                    raise AssertionError(
                        f"{camera_id} zone is "
                        f"missing fields: "
                        f"{missing_zone_fields}"
                    )

                if zone["status"] not in {
                    "GREEN",
                    "YELLOW",
                    "RED",
                }:

                    raise AssertionError(
                        f"Invalid zone status: "
                        f"{zone['status']}"
                    )

            if len(camera["zones"]) == 0:

                raise AssertionError(
                    f"{camera_id} has no zones."
                )

        print()
        print(
            "Individual camera data: PASS"
        )

        # --------------------------------------------------
        # Validate total people
        # --------------------------------------------------

        print(
            f"  Calculated people total: "
            f"{calculated_total_people}"
        )

        if (
            overview["total_people"]
            != calculated_total_people
        ):

            raise AssertionError(
                "System total people does "
                "not match camera totals."
            )

        print(
            "Total people aggregation: PASS"
        )

        # --------------------------------------------------
        # Validate alerts
        # --------------------------------------------------

        if not isinstance(
            overview["alerts"],
            list,
        ):

            raise AssertionError(
                "System alerts must be a list."
            )

        if overview["total_alerts"] != len(
            overview["alerts"]
        ):

            raise AssertionError(
                "Total alert count does "
                "not match alerts list."
            )

        print()
        print(
            f"Alerts returned: "
            f"{len(overview['alerts'])}"
        )

        print(
            "Alert aggregation: PASS"
        )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print()
        print(
            "System overview API "
            "test successful."
        )


if __name__ == "__main__":

    main()