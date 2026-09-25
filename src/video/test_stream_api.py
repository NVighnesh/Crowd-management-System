import subprocess
import sys
import time

import httpx


HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"


def wait_for_server(
    timeout=30,
):

    start_time = time.time()

    while time.time() - start_time < timeout:

        try:

            response = httpx.get(
                f"{BASE_URL}/health",
                timeout=2,
            )

            if response.status_code == 200:
                return True

        except Exception:
            pass

        time.sleep(0.5)

    return False


def wait_for_frame(
    camera_id,
    timeout=30,
):

    start_time = time.time()

    while time.time() - start_time < timeout:

        try:

            response = httpx.get(
                f"{BASE_URL}/cameras/{camera_id}/frame",
                timeout=3,
            )

            if response.status_code == 200:
                return True

        except Exception:
            pass

        time.sleep(0.5)

    return False


def main():

    print("Testing live stream API...")

    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api:app",
            "--host",
            HOST,
            "--port",
            str(PORT),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:

        # --------------------------------------------------
        # Wait for API server
        # --------------------------------------------------

        print()
        print(
            "Waiting for API server..."
        )

        if not wait_for_server():

            raise AssertionError(
                "API server did not start "
                "within the timeout."
            )

        print(
            "API server is running."
        )

        # --------------------------------------------------
        # Get cameras
        # --------------------------------------------------

        print()
        print(
            "Getting cameras..."
        )

        response = httpx.get(
            f"{BASE_URL}/cameras",
            timeout=5,
        )

        if response.status_code != 200:

            raise AssertionError(
                "Camera endpoint failed."
            )

        cameras = response.json()["cameras"]

        if not cameras:

            raise AssertionError(
                "No cameras available."
            )

        camera_ids = [
            camera["camera_id"]
            for camera in cameras
        ]

        print(
            f"Available cameras: "
            f"{camera_ids}"
        )

        # --------------------------------------------------
        # Wait for annotated frame
        # --------------------------------------------------

        camera_id = camera_ids[0]

        print()
        print(
            f"Waiting for annotated frame "
            f"from {camera_id}..."
        )

        if not wait_for_frame(
            camera_id
        ):

            raise AssertionError(
                "Annotated frame did not "
                "become available."
            )

        print(
            "Annotated frame available."
        )

        # --------------------------------------------------
        # Connect to live stream
        # --------------------------------------------------

        print()
        print(
            f"Connecting to stream: "
            f"/cameras/{camera_id}/stream"
        )

        with httpx.stream(
            "GET",
            f"{BASE_URL}/cameras/{camera_id}/stream",
            timeout=None,
        ) as response:

            print(
                f"  Status code: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                raise AssertionError(
                    "Stream endpoint failed."
                )

            content_type = response.headers.get(
                "content-type",
                "",
            )

            print(
                f"  Content-Type: "
                f"{content_type}"
            )

            if (
                "multipart/x-mixed-replace"
                not in content_type
            ):

                raise AssertionError(
                    "Incorrect stream "
                    "Content-Type."
                )

            if "boundary=frame" not in content_type:

                raise AssertionError(
                    "MJPEG boundary is missing."
                )

            print(
                "  Stream headers: PASS"
            )

            # --------------------------------------------------
            # Read the real HTTP stream
            # --------------------------------------------------

            data = b""

            start_time = time.time()

            for chunk in response.iter_bytes(
                chunk_size=8192
            ):

                data += chunk

                if (
                    b"\xff\xd8" in data
                    and b"\xff\xd9" in data
                ):

                    break

                if (
                    time.time() - start_time
                    > 10
                ):

                    raise AssertionError(
                        "No complete JPEG frame "
                        "received within timeout."
                    )

            print(
                f"  Stream data received: "
                f"{len(data)} bytes"
            )

            # --------------------------------------------------
            # Validate MJPEG frame
            # --------------------------------------------------

            if b"--frame\r\n" not in data:

                raise AssertionError(
                    "MJPEG frame boundary "
                    "was not received."
                )

            if (
                b"Content-Type: image/jpeg"
                not in data
            ):

                raise AssertionError(
                    "JPEG content type "
                    "was not received."
                )

            if b"\xff\xd8" not in data:

                raise AssertionError(
                    "JPEG start marker "
                    "was not received."
                )

            if b"\xff\xd9" not in data:

                raise AssertionError(
                    "JPEG end marker "
                    "was not received."
                )

            print(
                "  MJPEG frame received: PASS"
            )

        # --------------------------------------------------
        # Invalid camera
        # --------------------------------------------------

        print()
        print(
            "Testing invalid camera stream..."
        )

        response = httpx.get(
            f"{BASE_URL}/cameras/"
            "INVALID_CAMERA/stream",
            timeout=5,
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

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        print()
        print(
            "Live stream API test successful."
        )

    finally:

        print()
        print(
            "Stopping API server..."
        )

        server_process.terminate()

        try:

            server_process.wait(
                timeout=10
            )

        except subprocess.TimeoutExpired:

            server_process.kill()
            server_process.wait()

        print(
            "API server stopped."
        )


if __name__ == "__main__":

    main()