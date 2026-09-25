from ultralytics import YOLO
import cv2
import os


MODEL_PATH = "yolo26n.pt"
VIDEO_PATH = "videos/crowd.mp4"
OUTPUT_PATH = "outputs/crowd_tracked.mp4"

CONFIDENCE = 0.35
TRACKER = "bytetrack.yaml"


def main():
    model = YOLO(MODEL_PATH)

    video = cv2.VideoCapture(VIDEO_PATH)

    if not video.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs("outputs", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

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

        person_count = 0

        for result in results:

            boxes = result.boxes

            if boxes is None:
                continue

            person_count = len(boxes)

            if boxes.id is None:
                continue

            track_ids = boxes.id.int().cpu().tolist()

            for box, track_id in zip(boxes, track_ids):

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist()
                )

                confidence = float(box.conf[0])

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 0, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"ID: {track_id} Person {confidence:.2f}",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    2
                )

        cv2.putText(
            frame,
            f"Active Persons: {person_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        writer.write(frame)

        print(
            f"Frame {frame_number}: "
            f"{person_count} active persons"
        )

    video.release()
    writer.release()

    print("\nTracking complete.")
    print(f"Output saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()