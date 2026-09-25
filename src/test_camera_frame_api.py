import io
import time

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from src.api import app


def main():

    print("Testing camera frame API...")

    with TestClient(app) as client:

        # --------------------------------------------------
        # Wait for camera workers to start
        # --------------------------------------------------

        print()
        print("Waiting for camera frames...")

        deadline = time.time() + 30

        while time.time() < deadline:

            response = client.get("/cameras")

            if response.status_code != 200:
                time.sleep(0.5)
                continue

            data = response.json()

            cameras = data.get("cameras", [])

            if not cameras:
                time.sleep(0.5)
                continue

            all_online = all(
                camera["status"] == "ONLINE"
                for camera in cameras
            )

            if all_online:
                break

            time.sleep(0.5)

        else:

            raise AssertionError(
                "Cameras did not become ONLINE."
            )

        print("  Camera frames are available.")

        # --------------------------------------------------
        # Wait for annotated frames
        # --------------------------------------------------

        print()
        print(
            "Waiting for first AI-annotated frames..."
        )

        deadline = time.time() + 60

        while time.time() < deadline:

            ready = 0

            for camera in cameras:

                camera_id = camera["camera_id"]

                response = client.get(
                    f"/cameras/{camera_id}/frame"
                )

                if response.status_code == 200:

                    ready += 1

            print(
                f"  Annotated frames ready: "
                f"{ready}/{len(cameras)}"
            )

            if ready == len(cameras):
                break

            time.sleep(1)

        else:

            raise AssertionError(
                "Not all cameras produced "
                "an annotated frame within "
                "the timeout."
            )

        print(
            "  All cameras produced "
            "their first annotated frame."
        )

        # --------------------------------------------------
        # Test each camera
        # --------------------------------------------------

        for camera in cameras:

            camera_id = camera["camera_id"]

            print()
            print(
                f"Testing frame endpoint: "
                f"{camera_id}"
            )

            response = client.get(
                f"/cameras/{camera_id}/frame"
            )

            print(
                f"  Status code: "
                f"{response.status_code}"
            )

            if response.status_code != 200:

                raise AssertionError(
                    f"{camera_id} frame endpoint "
                    f"failed: "
                    f"{response.status_code}"
                )

            content_type = (
                response.headers.get(
                    "content-type",
                    "",
                )
            )

            print(
                f"  Content-Type: "
                f"{content_type}"
            )

            if content_type != "image/jpeg":

                raise AssertionError(
                    f"{camera_id} returned "
                    f"unexpected content type: "
                    f"{content_type}"
                )

            image_size = len(response.content)

            print(
                f"  Image size: "
                f"{image_size} bytes"
            )

            if image_size <= 0:

                raise AssertionError(
                    f"{camera_id} returned "
                    f"empty image."
                )

            # --------------------------------------------------
            # Validate JPEG
            # --------------------------------------------------

            try:

                image = Image.open(
                    io.BytesIO(
                        response.content
                    )
                )

                image.verify()

            except Exception as exc:

                raise AssertionError(
                    f"{camera_id} returned "
                    f"invalid JPEG: {exc}"
                )

            print(
                "  JPEG frame validation: PASS"
            )

            # --------------------------------------------------
            # Decode JPEG with OpenCV
            # --------------------------------------------------

            encoded = np.frombuffer(
                response.content,
                dtype=np.uint8,
            )

            decoded_frame = cv2.imdecode(
                encoded,
                cv2.IMREAD_COLOR,
            )

            if decoded_frame is None:

                raise AssertionError(
                    f"{camera_id} JPEG could not "
                    "be decoded by OpenCV."
                )

            print(
                f"  Decoded frame shape: "
                f"{decoded_frame.shape}"
            )

            # --------------------------------------------------
            # Save one API frame for visual inspection
            # --------------------------------------------------

            if camera_id == cameras[0]["camera_id"]:

                output_path = (
                    "outputs/api_annotated_frame.jpg"
                )

                success = cv2.imwrite(
                    output_path,
                    decoded_frame,
                )

                if not success:

                    raise AssertionError(
                        "Failed to save API "
                        "annotated frame."
                    )

                print(
                    f"  Annotated frame saved to: "
                    f"{output_path}"
                )

        # --------------------------------------------------
        # Invalid camera
        # --------------------------------------------------

        print()
        print("Testing invalid camera...")

        response = client.get(
            "/cameras/INVALID_CAMERA/frame"
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

        print()
        print(
            "Camera annotated frame API "
            "test successful."
        )


if __name__ == "__main__":
    main()