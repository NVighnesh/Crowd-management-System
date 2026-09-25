from ultralytics import YOLO
import cv2
import json
import os
import numpy as np


MODEL_PATH = "yolo26n.pt"
VIDEO_PATH = "videos/crowd.mp4"
ZONE_FILE = "configs/zones.json"
OUTPUT_PATH = "outputs/zone_counted.mp4"

CONFIDENCE = 0.35
TRACKER = "bytetrack.yaml"


def load_zones():
    with open(ZONE_FILE, "r") as file:
        data = json.load(file)

    return data["zones"]


def get_status(count, threshold):
    if count < threshold:
        return "GREEN"
    elif count == threshold:
        return "YELLOW"
    else:
        return "RED"


def point_inside_polygon(point, polygon):
    polygon_array = np.array(
        polygon,
        dtype=np.int32
    )

    result = cv2.pointPolygonTest(
        polygon_array,
        point,
        False
    )

    return result >= 0


def main():

    print("Loading model...")

    model = YOLO(MODEL_PATH)

    zones = load_zones()

    print("\nLoaded zones:")

    for zone in zones:
        print(
            f"{zone['zone_id']} | "
            f"{zone['name']} | "
            f"Threshold: {zone['threshold']}"
        )

    video = cv2.VideoCapture(VIDEO_PATH)

    if not video.isOpened():
        raise RuntimeError(
            f"Could not open video: {VIDEO_PATH}"
        )

    fps = video.get(cv2.CAP_PROP_FPS)

    width = int(
        video.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        video.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    print(
        f"\nVideo resolution: "
        f"{width} x {height}"
    )

    os.makedirs("outputs", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    writer = cv2.VideoWriter(
        OUTPUT_PATH,
        fourcc,
        fps,
        (width, height)
    )

    frame_number = 0

    while True:

        success, frame = video.read()

        if not success:
            break

        frame_number += 1

        results = model.track(
            frame,
            persist=True,
            classes=[0],
            conf=CONFIDENCE,
            tracker=TRACKER,
            verbose=False
        )

        zone_counts = {
            zone["zone_id"]: 0
            for zone in zones
        }

        for result in results:

            boxes = result.boxes

            if boxes is None:
                continue

            if boxes.id is None:
                continue

            track_ids = (
                boxes.id
                .int()
                .cpu()
                .tolist()
            )

            for box, track_id in zip(
                boxes,
                track_ids
            ):

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist()
                )

                confidence = float(
                    box.conf[0]
                )

                # Bottom-center point
                center_x = int(
                    (x1 + x2) / 2
                )

                bottom_y = int(y2)

                person_point = (
                    center_x,
                    bottom_y
                )

                # Check every zone
                for zone in zones:

                    polygon = zone["polygon"]

                    inside = point_inside_polygon(
                        person_point,
                        polygon
                    )

                    if inside:
                        zone_counts[
                            zone["zone_id"]
                        ] += 1

                # Draw person bounding box
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 0, 0),
                    2
                )

                # Draw reference point
                cv2.circle(
                    frame,
                    person_point,
                    4,
                    (0, 255, 255),
                    -1
                )

                # Draw tracking ID
                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (
                        x1,
                        max(y1 - 10, 20)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2
                )

        # Draw zones and status
        dashboard_y = 30

        for zone in zones:

            zone_id = zone["zone_id"]
            name = zone["name"]
            threshold = zone["threshold"]

            count = zone_counts[zone_id]

            status = get_status(
                count,
                threshold
            )

            polygon = [
                tuple(point)
                for point in zone["polygon"]
            ]

            polygon_array = np.array(
                polygon,
                dtype=np.int32
            )

            if status == "GREEN":
                zone_color = (0, 255, 0)

            elif status == "YELLOW":
                zone_color = (0, 255, 255)

            else:
                zone_color = (0, 0, 255)

            # Draw polygon
            cv2.polylines(
                frame,
                [polygon_array],
                True,
                zone_color,
                3
            )

            # Zone label
            label_x = polygon[0][0]
            label_y = polygon[0][1]

            cv2.putText(
                frame,
                f"{zone_id}: {name}",
                (
                    label_x,
                    max(label_y - 10, 20)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                zone_color,
                2
            )

            # Dashboard
            dashboard_text = (
                f"{name}: "
                f"{count}/{threshold} "
                f"{status}"
            )

            cv2.putText(
                frame,
                dashboard_text,
                (
                    10,
                    dashboard_y
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                zone_color,
                2
            )

            dashboard_y += 30

        writer.write(frame)

        # Console output
        output = f"Frame {frame_number}: "

        for zone in zones:

            zone_id = zone["zone_id"]

            count = zone_counts[zone_id]

            threshold = zone["threshold"]

            status = get_status(
                count,
                threshold
            )

            output += (
                f"{zone_id}="
                f"{count}/{threshold}"
                f"({status}) "
            )

        print(output)

    video.release()
    writer.release()

    print("\n==============================")
    print("Zone counting complete.")
    print(
        f"Output saved to: "
        f"{OUTPUT_PATH}"
    )
    print("==============================")


if __name__ == "__main__":
    main()