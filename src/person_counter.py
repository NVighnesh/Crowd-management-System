from ultralytics import YOLO
import cv2


MODEL_PATH = "yolo26n.pt"
VIDEO_PATH = "videos/crowd.mp4"
OUTPUT_PATH = "outputs/crowd_counted.mp4"

CONFIDENCE = 0.35


def main():
    model = YOLO(MODEL_PATH)

    video = cv2.VideoCapture(VIDEO_PATH)

    if not video.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    fps = video.get(cv2.CAP_PROP_FPS)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

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

        results = model(
            frame,
            classes=[0],
            conf=CONFIDENCE,
            verbose=False
        )

        person_count = 0

        for result in results:
            boxes = result.boxes

            if boxes is not None:
                person_count = len(boxes)

                for box in boxes:
                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0].tolist()
                    )

                    confidence = float(box.conf[0])

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Person {confidence:.2f}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )

        cv2.putText(
            frame,
            f"Person Count: {person_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        writer.write(frame)

        print(
            f"Frame {frame_number}: "
            f"{person_count} persons"
        )

    video.release()
    writer.release()

    print("\nProcessing complete.")
    print(f"Output saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()