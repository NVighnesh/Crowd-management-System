from ultralytics import YOLO

from src.detection.detection_types import Detection
from src.tracking.tracker import PersonTracker


class UltralyticsPersonTracker(PersonTracker):

    def __init__(
        self,
        model_path,
        confidence=0.35,
        image_size=640,
        device="auto",
        tracker="bytetrack.yaml",
    ):
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.image_size = image_size
        self.tracker = tracker
        self.device = None if device == "auto" else device

    def infer(self, frame) -> list[Detection]:

        results = self.model.track(
            source=frame,
            classes=[0],
            conf=self.confidence,
            imgsz=self.image_size,
            device=self.device,
            tracker=self.tracker,
            persist=True,
            verbose=False,
        )

        detections = []

        result = results[0]

        if result.boxes is None:
            return detections

        for box in result.boxes:

            x1, y1, x2, y2 = (
                box.xyxy[0].tolist()
            )

            confidence = float(
                box.conf[0]
            )

            class_id = int(
                box.cls[0]
            )

            track_id = None

            if box.id is not None:
                track_id = int(
                    box.id[0]
                )

            detections.append(
                Detection(
                    class_id=class_id,
                    confidence=confidence,
                    bbox=(
                        int(x1),
                        int(y1),
                        int(x2),
                        int(y2),
                    ),
                    track_id=track_id,
                )
            )

        return detections

    def reset(self):
        self.model = YOLO(
            self.model.ckpt_path
        )