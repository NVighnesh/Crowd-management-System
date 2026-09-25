import cv2
import json
import os
import numpy as np


VIDEO_PATH = "videos/crowd.mp4"
ZONE_FILE = "configs/zones.json"

points = []
zones = []


def mouse_callback(event, x, y, flags, param):

    if event == cv2.EVENT_LBUTTONDOWN:

        points.append([x, y])

        print(
            f"Point added: ({x}, {y})"
        )


def main():

    global points, zones

    video = cv2.VideoCapture(VIDEO_PATH)

    if not video.isOpened():
        raise RuntimeError(
            f"Could not open video: {VIDEO_PATH}"
        )

    success, frame = video.read()

    video.release()

    if not success:
        raise RuntimeError(
            "Could not read video frame."
        )

    height, width = frame.shape[:2]

    print(
        f"\nVideo resolution: "
        f"{width} x {height}"
    )

    os.makedirs(
        "configs",
        exist_ok=True
    )

    window_name = "Crowd Management - Zone Setup"

    # Use original frame size
    cv2.namedWindow(
        window_name,
        cv2.WINDOW_AUTOSIZE
    )

    cv2.setMouseCallback(
        window_name,
        mouse_callback
    )

    print("\n==============================")
    print("       CROWD ZONE SETUP")
    print("==============================")
    print()
    print("LEFT CLICK -> Add point")
    print("S -> Save current zone")
    print("R -> Reset current zone")
    print("Q -> Finish")
    print()
    print(
        "Important: Draw directly on the "
        f"{width} x {height} image."
    )
    print("==============================\n")

    while True:

        display = frame.copy()

        # Draw saved zones
        for zone in zones:

            polygon = np.array(
                zone["polygon"],
                dtype=np.int32
            )

            cv2.polylines(
                display,
                [polygon],
                True,
                (255, 0, 0),
                2
            )

            x, y = zone["polygon"][0]

            cv2.putText(
                display,
                zone["zone_id"],
                (x, max(y - 5, 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                2
            )

        # Draw current zone
        if len(points) > 0:

            for point in points:

                cv2.circle(
                    display,
                    tuple(point),
                    4,
                    (0, 255, 0),
                    -1
                )

        if len(points) >= 2:

            polygon = np.array(
                points,
                dtype=np.int32
            )

            cv2.polylines(
                display,
                [polygon],
                False,
                (0, 255, 255),
                2
            )

        if len(points) >= 3:

            polygon = np.array(
                points,
                dtype=np.int32
            )

            cv2.polylines(
                display,
                [polygon],
                True,
                (0, 255, 255),
                2
            )

        cv2.imshow(
            window_name,
            display
        )

        key = cv2.waitKey(20) & 0xFF

        # SAVE
        if key == ord("s"):

            if len(points) < 3:

                print(
                    "\nNeed at least "
                    "3 points."
                )

                continue

            print("\n--- New Zone ---")

            name = input(
                "Enter zone name: "
            ).strip()

            if not name:

                name = (
                    f"Zone {len(zones) + 1}"
                )

            while True:

                try:

                    threshold = int(
                        input(
                            "Enter crowd threshold: "
                        )
                    )

                    if threshold < 0:

                        print(
                            "Threshold cannot "
                            "be negative."
                        )

                        continue

                    break

                except ValueError:

                    print(
                        "Enter a valid number."
                    )

            zone_number = (
                len(zones) + 1
            )

            zone = {

                "zone_id":
                    f"ZONE_{zone_number:03d}",

                "camera_id":
                    "CAM_001",

                "name":
                    name,

                "threshold":
                    threshold,

                "threshold_type":
                    "count",

                "polygon":
                    points.copy()
            }

            zones.append(zone)

            print(
                f"\nSaved "
                f"{zone['zone_id']}: "
                f"{zone['name']}"
            )

            print(
                f"Threshold: "
                f"{zone['threshold']}"
            )

            print(
                f"Polygon: "
                f"{zone['polygon']}"
            )

            points.clear()

            data = {
                "camera_id": "CAM_001",
                "zones": zones
            }

            with open(
                ZONE_FILE,
                "w"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=4
                )

            print(
                f"Total zones: "
                f"{len(zones)}"
            )

        # RESET
        elif key == ord("r"):

            points.clear()

            print(
                "\nCurrent zone reset."
            )

        # QUIT
        elif key == ord("q"):

            break

    cv2.destroyAllWindows()

    data = {
        "camera_id": "CAM_001",
        "zones": zones
    }

    with open(
        ZONE_FILE,
        "w"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )

    print("\n==============================")
    print("Zone setup complete.")
    print(
        f"Total zones: {len(zones)}"
    )
    print(
        f"Saved to: {ZONE_FILE}"
    )
    print("==============================")


if __name__ == "__main__":
    main()