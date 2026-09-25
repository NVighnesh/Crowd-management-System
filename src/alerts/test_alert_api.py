import time

from fastapi.testclient import TestClient

from src.api import app


def wait_for_results(
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

            if response.status_code == 200:

                data = response.json()

                if data.get("fresh") is True:
                    ready += 1

        if ready == len(camera_ids):
            return True

        time.sleep(0.5)

    return False


def main():

    print("Testing Alert API...")

    with TestClient(app) as client:

        # --------------------------------------------------
        # Health
        # --------------------------------------------------

        print()
        print("Testing API startup...")

        response = client.get(
            "/health"
        )

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

        print()
        print("Getting cameras...")

        response = client.get(
            "/cameras"
        )

        if response.status_code != 200:
            raise AssertionError(
                "Camera endpoint failed."
            )

        cameras_data = response.json()

        camera_ids = [
            camera["camera_id"]
            for camera in cameras_data["cameras"]
        ]

        print(
            f"  Cameras available: "
            f"{camera_ids}"
        )

        if not camera_ids:
            raise AssertionError(
                "No cameras available."
            )

        print(
            "  Camera endpoint: PASS"
        )

        # --------------------------------------------------
        # Wait for AI results
        # --------------------------------------------------

        print()
        print(
            "Waiting for fresh AI results..."
        )

        results_ready = wait_for_results(
            client=client,
            camera_ids=camera_ids,
        )

        if not results_ready:
            raise AssertionError(
                "Not all cameras produced "
                "fresh results."
            )

        print(
            "  Fresh AI results available."
        )

        # --------------------------------------------------
        # GET /alerts
        # --------------------------------------------------

        print()
        print(
            "Testing GET /alerts..."
        )

        response = client.get(
            "/alerts"
        )

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            raise AssertionError(
                "/alerts endpoint failed."
            )

        data = response.json()

        print(
            f"  Alert count: "
            f"{data['count']}"
        )

        if "alerts" not in data:
            raise AssertionError(
                "Response does not contain "
                "'alerts'."
            )

        if not isinstance(
            data["alerts"],
            list,
        ):
            raise AssertionError(
                "'alerts' must be a list."
            )

        print(
            "  GET /alerts: PASS"
        )

        # --------------------------------------------------
        # GET /cameras/{camera_id}/alerts
        # --------------------------------------------------

        for camera_id in camera_ids:

            print()
            print(
                f"Testing camera alerts: "
                f"{camera_id}"
            )

            response = client.get(
                f"/cameras/{camera_id}/alerts"
            )

            print(
                f"  Status code: "
                f"{response.status_code}"
            )

            if response.status_code != 200:
                raise AssertionError(
                    "Camera alerts endpoint failed."
                )

            data = response.json()

            if data["camera_id"] != camera_id:
                raise AssertionError(
                    "Incorrect camera ID."
                )

            if "alerts" not in data:
                raise AssertionError(
                    "Camera response does not "
                    "contain alerts."
                )

            print(
                f"  Alerts: "
                f"{data['count']}"
            )

            print(
                "  Camera alerts endpoint: PASS"
            )

        # --------------------------------------------------
        # GET zone alerts
        # --------------------------------------------------

        test_camera_id = camera_ids[0]

        print()
        print(
            f"Testing zone alerts: "
            f"{test_camera_id}/ZONE_001"
        )

        response = client.get(
            f"/cameras/"
            f"{test_camera_id}/"
            f"zones/"
            f"ZONE_001/"
            f"alerts"
        )

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            raise AssertionError(
                "Zone alerts endpoint failed."
            )

        data = response.json()

        if data["camera_id"] != test_camera_id:
            raise AssertionError(
                "Incorrect camera ID."
            )

        if data["zone_id"] != "ZONE_001":
            raise AssertionError(
                "Incorrect zone ID."
            )

        if "alerts" not in data:
            raise AssertionError(
                "Zone response does not "
                "contain alerts."
            )

        print(
            f"  Alerts: "
            f"{data['count']}"
        )

        print(
            "  Zone alerts endpoint: PASS"
        )

        # --------------------------------------------------
        # Test latest alert endpoint
        # --------------------------------------------------

        print()
        print(
            "Testing GET /alerts/latest..."
        )

        response = client.get(
            "/alerts/latest"
        )

        if response.status_code == 200:

            latest = response.json()

            required_fields = {
                "camera_id",
                "zone_id",
                "zone_name",
                "previous_status",
                "current_status",
                "count",
                "threshold",
                "timestamp",
                "alert_type",
            }

            missing = (
                required_fields
                - set(latest.keys())
            )

            if missing:
                raise AssertionError(
                    f"Latest alert is missing "
                    f"fields: {missing}"
                )

            print(
                "  Alert exists."
            )

            print(
                f"  Camera: "
                f"{latest['camera_id']}"
            )

            print(
                f"  Zone: "
                f"{latest['zone_id']}"
            )

            print(
                f"  Type: "
                f"{latest['alert_type']}"
            )

            print(
                "  Latest alert serialization: PASS"
            )

        elif response.status_code == 404:

            print(
                "  No alert has been generated "
                "yet."
            )

            print(
                "  Empty latest-alert handling: PASS"
            )

        else:

            raise AssertionError(
                "Unexpected status code from "
                "/alerts/latest."
            )

        # --------------------------------------------------
        # Invalid camera
        # --------------------------------------------------

        print()
        print(
            "Testing invalid camera..."
        )

        response = client.get(
            "/cameras/INVALID_CAMERA/alerts"
        )

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if response.status_code != 404:
            raise AssertionError(
                "Invalid camera should return 404."
            )

        print(
            "  Invalid camera handling: PASS"
        )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print()
        print(
            "Alert API test successful."
        )


if __name__ == "__main__":

    main()