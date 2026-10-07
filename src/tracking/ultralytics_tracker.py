import logging
import time

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
        self._logger = logging.getLogger(__name__)
        self._logged_first_inference = False

    def infer(self, frame) -> list[Detection]:

        started_at = time.time()
        if not self._logged_first_inference:
            self._logger.info(
                "[YOLO_START] tracker device=%s frame_shape=%s",
                self.device or "auto",
                getattr(frame, "shape", None),
            )
        self._logger.debug(
            "[YOLO_START] engine=tracker frame_shape=%s device=%s",
            getattr(frame, "shape", None),
            self.device or "auto",
        )
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
        if not self._logged_first_inference:
            self._logged_first_inference = True
            self._logger.info(
                "[YOLO_RETURN] tracker elapsed_ms=%.1f",
                (time.time() - started_at) * 1000,
            )
        self._logger.debug(
            "[YOLO_RETURN] engine=tracker elapsed_ms=%.1f",
            (time.time() - started_at) * 1000,
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