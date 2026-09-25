from ultralytics import YOLO

from src.inference.inference_engine import InferenceEngine
from src.detection.detection_types import Detection


class UltralyticsPersonDetector(InferenceEngine):

    def __init__(
        self,
        model_path,
        confidence=0.35,
        image_size=640,
        device="auto",
    ):

        self.model = YOLO(model_path)

        self.confidence = confidence
        self.image_size = image_size

        self.device = (
            None
            if device == "auto"
            else device
        )

    def infer(self, frame) -> list[Detection]:

        results = self.model.predict(
            source=frame,
            classes=[0],
            conf=self.confidence,
            imgsz=self.image_size,
            device=self.device,
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
                )
            )

        return detections