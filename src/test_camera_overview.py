import time

from fastapi.testclient import TestClient

from src.api import app


def main():

    print("Testing camera overview API...")

    with TestClient(app) as client:

        # --------------------------------------------------
        # Wait for API cameras
        # --------------------------------------------------

        print()
        print("Waiting for cameras...")

        deadline = time.time() + 30

        while time.time() < deadline:

            response = client.get("/cameras")

            if response.status_code != 200:
                time.sleep(0.5)
                continue

            data = response.json()

            cameras = data.get(
                "cameras",
                [],
            )

            if cameras:

                all_online = all(
                    camera.get("camera_status") == "ONLINE"
                    or camera.get("status") == "ONLINE"
                    for camera in cameras
                )

                if all_online:
                    break

            time.sleep(0.5)

        else:

            raise AssertionError(
                "Cameras did not become ONLINE."
            )

        print(
            f"  Cameras online: "
            f"{len(cameras)}"
        )

        # --------------------------------------------------
        # Wait for AI results
        # --------------------------------------------------

        print()
        print(
            "Waiting for first AI results..."
        )

        deadline = time.time() + 60

        while time.time() < deadline:

            ready = 0

            for camera in cameras:

                camera_id = camera[
                    "camera_id"
                ]

                response = client.get(
                    f"/cameras/{camera_id}/result"
                )

                if response.status_code == 200:

                    result = response.json()

                    if result.get(
                        "fresh",
                        False,
                    ):

                        ready += 1

            print(
                f"  Fresh results: "
                f"{ready}/{len(cameras)}"
            )

            if ready == len(cameras):
                break

            time.sleep(1)

        else:

            raise AssertionError(
                "Not all cameras produced "
                "fresh AI results."
            )

        print(
            "  All cameras produced "
            "fresh AI results."
        )

        # --------------------------------------------------
        # Test overview endpoint
        # --------------------------------------------------

        for camera in cameras:

            camera_id = camera[
                "camera_id"
            ]

            print()
            print(
                f"Testing overview: "
                f"{camera_id}"
            )

            response = client.get(
                f"/cameras/{camera_id}/overview"
            )

            print(
                f"  Status code: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                raise AssertionError(
                    f"{camera_id} overview "
                    f"endpoint failed: "
                    f"{response.status_code}"
                )

            data = response.json()

            # --------------------------------------------------
            # Basic fields
            # --------------------------------------------------

            required_fields = [
                "camera_id",
                "camera_status",
                "processing_status",
                "last_error",
                "last_frame_time",
                "last_inference_time",
                "result_timestamp",
                "age_seconds",
                "fresh",
                "total_people",
                "frame_available",
                "frame_endpoint",
                "zones",
            ]

            for field in required_fields:

                if field not in data:

                    raise AssertionError(
                        f"{camera_id} overview "
                        f"missing field: "
                        f"{field}"
                    )

            print(
                f"  Camera status: "
                f"{data['camera_status']}"
            )

            print(
                f"  Processing status: "
                f"{data['processing_status']}"
            )

            print(
                f"  Total people: "
                f"{data['total_people']}"
            )

            print(
                f"  Fresh: "
                f"{data['fresh']}"
            )

            print(
                f"  Frame available: "
                f"{data['frame_available']}"
            )

            print(
                f"  Frame endpoint: "
                f"{data['frame_endpoint']}"
            )

            # --------------------------------------------------
            # Validate values
            # --------------------------------------------------

            if data["camera_id"] != camera_id:

                raise AssertionError(
                    "Camera ID mismatch."
                )

            if data["camera_status"] != "ONLINE":

                raise AssertionError(
                    f"{camera_id} is not ONLINE."
                )

            if data[
                "processing_status"
            ] != "HEALTHY":

                raise AssertionError(
                    f"{camera_id} processing "
                    "is not HEALTHY."
                )

            if data["fresh"] is not True:

                raise AssertionError(
                    f"{camera_id} result "
                    "is not fresh."
                )

            if data[
                "frame_available"
            ] is not True:

                raise AssertionError(
                    f"{camera_id} annotated "
                    "frame is unavailable."
                )

            if not isinstance(
                data["zones"],
                list,
            ):

                raise AssertionError(
                    "Zones must be a list."
                )

            # --------------------------------------------------
            # Validate zones
            # --------------------------------------------------

            for zone in data["zones"]:

                zone_fields = [
                    "zone_id",
                    "name",
                    "count",
                    "threshold",
                    "status",
                ]

                for field in zone_fields:

                    if field not in zone:

                        raise AssertionError(
                            f"Zone missing "
                            f"field: {field}"
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

                print(
                    f"  {zone['zone_id']}: "
                    f"{zone['count']}/"
                    f"{zone['threshold']} "
                    f"{zone['status']}"
                )

            print(
                "  Overview endpoint: PASS"
            )

        # --------------------------------------------------
        # Invalid camera
        # --------------------------------------------------

        print()
        print("Testing invalid camera...")

        response = client.get(
            "/cameras/INVALID_CAMERA/overview"
        )

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if response.status_code != 404:

            raise AssertionError(
                "Invalid camera should "
                "return 404."
            )

        print(
            "  Invalid camera handling: PASS"
        )

        print()
        print(
            "Camera overview API "
            "test successful."
        )


if __name__ == "__main__":
    main()