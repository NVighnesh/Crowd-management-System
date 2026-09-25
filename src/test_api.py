import time

from fastapi.testclient import TestClient

from src.api import app


EXPECTED_CAMERA_IDS = {
    "CAM_001",
    "CAM_002",
}

RESULT_WAIT_TIMEOUT_SECONDS = 30
RESULT_POLL_INTERVAL_SECONDS = 1


def wait_for_camera_inference(client, camera_ids):
    """
    Wait until every configured camera has completed
    at least one AI inference.
    """

    print(
        "\nWaiting for cameras to produce "
        "their first AI results..."
    )

    start_time = time.time()

    while True:

        ready_cameras = set()

        for camera_id in camera_ids:

            response = client.get(
                f"/cameras/{camera_id}/status"
            )

            if response.status_code != 200:
                raise AssertionError(
                    f"{camera_id} status request failed: "
                    f"{response.status_code}"
                )

            status = response.json()

            if status["last_inference_time"] is not None:
                ready_cameras.add(camera_id)

        elapsed = time.time() - start_time

        print(
            f"  Inference ready: "
            f"{len(ready_cameras)}/{len(camera_ids)} "
            f"({elapsed:.1f}s)"
        )

        if ready_cameras == set(camera_ids):
            print(
                "  All cameras produced "
                "their first AI result."
            )
            return

        if elapsed >= RESULT_WAIT_TIMEOUT_SECONDS:
            raise AssertionError(
                "Timed out waiting for first AI "
                "inference from all cameras."
            )

        time.sleep(RESULT_POLL_INTERVAL_SECONDS)


def main():

    print("Testing Crowd Management API...")

    # --------------------------------------------------
    # Start FastAPI application
    # --------------------------------------------------

    with TestClient(app) as client:

        # --------------------------------------------------
        # Test health endpoint
        # --------------------------------------------------

        print("\nTesting GET /health...")

        response = client.get("/health")

        if response.status_code != 200:
            raise AssertionError(
                f"/health failed: {response.status_code}"
            )

        health = response.json()

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        print(
            f"  Response: "
            f"{health}"
        )

        if health.get("status") != "UP":
            raise AssertionError(
                "API health status should be UP."
            )

        print(
            "  Health endpoint: PASS"
        )

        # --------------------------------------------------
        # Test camera list
        # --------------------------------------------------

        print("\nTesting GET /cameras...")

        response = client.get("/cameras")

        if response.status_code != 200:
            raise AssertionError(
                f"/cameras failed: {response.status_code}"
            )

        camera_response = response.json()

        print(
            f"  Status code: "
            f"{response.status_code}"
        )

        if not isinstance(
            camera_response,
            dict,
        ):
            raise AssertionError(
                "/cameras response should "
                "be a JSON object."
            )

        if "count" not in camera_response:
            raise AssertionError(
                "/cameras response is missing "
                "'count'."
            )

        if "cameras" not in camera_response:
            raise AssertionError(
                "/cameras response is missing "
                "'cameras'."
            )

        cameras = camera_response["cameras"]

        print(
            f"  Cameras returned: "
            f"{camera_response['count']}"
        )

        if camera_response["count"] != 2:
            raise AssertionError(
                f"Expected camera count 2, "
                f"got {camera_response['count']}."
            )

        if not isinstance(cameras, list):
            raise AssertionError(
                "'cameras' should be a list."
            )

        if len(cameras) != 2:
            raise AssertionError(
                f"Expected 2 cameras, "
                f"got {len(cameras)}."
            )

        camera_ids = {
            camera["camera_id"]
            for camera in cameras
        }

        if camera_ids != EXPECTED_CAMERA_IDS:
            raise AssertionError(
                f"Unexpected camera IDs: "
                f"{camera_ids}"
            )

        print(
            "  Camera list endpoint: PASS"
        )

        # --------------------------------------------------
        # Wait for first AI inference
        # --------------------------------------------------

        wait_for_camera_inference(
            client=client,
            camera_ids=EXPECTED_CAMERA_IDS,
        )

        # --------------------------------------------------
        # Test each camera
        # --------------------------------------------------

        for camera_id in sorted(
            EXPECTED_CAMERA_IDS
        ):

            print(
                f"\nTesting camera: "
                f"{camera_id}"
            )

            # ----------------------------------------------
            # Camera status
            # ----------------------------------------------

            response = client.get(
                f"/cameras/{camera_id}/status"
            )

            if response.status_code != 200:
                raise AssertionError(
                    f"{camera_id} status failed: "
                    f"{response.status_code}"
                )

            status = response.json()

            print(
                f"  Status response: "
                f"{status}"
            )

            if status["status"] != "ONLINE":
                raise AssertionError(
                    f"{camera_id} should be ONLINE, "
                    f"got {status['status']}"
                )

            if status["processing_status"] != "HEALTHY":
                raise AssertionError(
                    f"{camera_id} processing should "
                    f"be HEALTHY, "
                    f"got {status['processing_status']}"
                )

            print(
                "  Camera status: PASS"
            )

            # ----------------------------------------------
            # Camera result
            # ----------------------------------------------

            response = client.get(
                f"/cameras/{camera_id}/result"
            )

            if response.status_code != 200:
                raise AssertionError(
                    f"{camera_id} result failed: "
                    f"{response.status_code}"
                )

            result = response.json()

            print(
                "  Result response:"
            )

            print(
                f"    Camera: "
                f"{result['camera_id']}"
            )

            print(
                f"    Camera status: "
                f"{result['camera_status']}"
            )

            print(
                f"    Processing status: "
                f"{result['processing_status']}"
            )

            print(
                f"    Total people: "
                f"{result['total_people']}"
            )

            print(
                f"    Result age: "
                f"{result['age_seconds']:.2f}s"
            )

            print(
                f"    Fresh: "
                f"{result['fresh']}"
            )

            # ----------------------------------------------
            # Validate result structure
            # ----------------------------------------------

            if result["camera_id"] != camera_id:
                raise AssertionError(
                    f"Incorrect camera ID in result: "
                    f"{result['camera_id']}"
                )

            if result["camera_status"] != "ONLINE":
                raise AssertionError(
                    f"{camera_id} result should "
                    f"report ONLINE."
                )

            if result["processing_status"] != "HEALTHY":
                raise AssertionError(
                    f"{camera_id} result should "
                    f"report HEALTHY processing status."
                )

            if result["total_people"] is None:
                raise AssertionError(
                    f"{camera_id} should have "
                    f"a whole-frame count."
                )

            if not isinstance(
                result["total_people"],
                int,
            ):
                raise AssertionError(
                    f"{camera_id} total_people "
                    f"must be an integer."
                )

            if not result["zones"]:
                raise AssertionError(
                    f"{camera_id} should have "
                    f"zone results."
                )

            # ----------------------------------------------
            # Validate zone structure
            # ----------------------------------------------

            for zone in result["zones"]:

                required_fields = {
                    "zone_id",
                    "name",
                    "count",
                    "threshold",
                    "status",
                }

                missing_fields = (
                    required_fields
                    - set(zone.keys())
                )

                if missing_fields:
                    raise AssertionError(
                        f"{camera_id} zone "
                        f"is missing fields: "
                        f"{missing_fields}"
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
                    f"    {zone['zone_id']}: "
                    f"{zone['count']}/"
                    f"{zone['threshold']} "
                    f"{zone['status']}"
                )

            # ----------------------------------------------
            # Freshness
            # ----------------------------------------------

            if not result["fresh"]:
                raise AssertionError(
                    f"{camera_id} result "
                    f"should be fresh."
                )

            print(
                "  Result endpoint: PASS"
            )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print(
            "\nAPI integration test successful."
        )


if __name__ == "__main__":
    main()