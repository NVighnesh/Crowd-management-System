import cv2
import numpy as np


class FrameAnnotator:

    def __init__(self):

        self.font = cv2.FONT_HERSHEY_SIMPLEX

    # --------------------------------------------------
    # Status color
    # --------------------------------------------------

    def _get_status_color(self, status):

        if status == "GREEN":
            return (0, 180, 0)

        if status == "YELLOW":
            return (0, 200, 200)

        if status == "RED":
            return (0, 0, 220)

        return (255, 255, 255)

    # --------------------------------------------------
    # Draw zone
    # --------------------------------------------------

    def _draw_zone(
        self,
        frame,
        zone,
        zone_result,
    ):

        polygon = np.array(
            zone["polygon"],
            dtype=np.int32,
        )

        status = zone_result.status

        color = self._get_status_color(
            status
        )

        # --------------------------------------------------
        # Zone polygon
        # --------------------------------------------------

        cv2.polylines(
            frame,
            [polygon],
            isClosed=True,
            color=color,
            thickness=3,
        )

        # --------------------------------------------------
        # Find label position
        # --------------------------------------------------

        x, y = polygon[0]

        # Keep zone labels away from the top
        # summary area.
        label_y = max(
            int(y),
            75,
        )

        label_x = max(
            int(x),
            5,
        )

        # --------------------------------------------------
        # Zone label
        # --------------------------------------------------

        label = (
            f"{zone_result.name}: "
            f"{zone_result.count}/"
            f"{zone_result.threshold} "
            f"{zone_result.status}"
        )

        (
            text_width,
            text_height,
        ), baseline = cv2.getTextSize(
            label,
            self.font,
            0.7,
            2,
        )

        # --------------------------------------------------
        # Keep label inside frame
        # --------------------------------------------------

        frame_height, frame_width = (
            frame.shape[:2]
        )

        if (
            label_x + text_width + 8
            > frame_width
        ):

            label_x = (
                frame_width
                - text_width
                - 10
            )

        if (
            label_y + 5
            > frame_height
        ):

            label_y = (
                frame_height
                - text_height
                - baseline
                - 10
            )

        # --------------------------------------------------
        # Label background
        # --------------------------------------------------

        cv2.rectangle(
            frame,
            (
                label_x,
                label_y
                - text_height
                - baseline
                - 8,
            ),
            (
                label_x
                + text_width
                + 8,
                label_y,
            ),
            color,
            -1,
        )

        # --------------------------------------------------
        # Label text
        # --------------------------------------------------

        cv2.putText(
            frame,
            label,
            (
                label_x + 4,
                label_y - 6,
            ),
            self.font,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    # --------------------------------------------------
    # Draw detection
    # --------------------------------------------------

    def _draw_detection(
        self,
        frame,
        detection,
    ):

        x1, y1, x2, y2 = (
            detection.bbox
        )

        # --------------------------------------------------
        # Bounding box
        # --------------------------------------------------

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2,
        )

        # --------------------------------------------------
        # Detection label
        # --------------------------------------------------

        if detection.track_id is not None:

            label = (
                f"Person ID:"
                f"{detection.track_id} "
                f"{detection.confidence:.2f}"
            )

        else:

            label = (
                f"Person "
                f"{detection.confidence:.2f}"
            )

        label_y = max(
            20,
            y1 - 8,
        )

        cv2.putText(
            frame,
            label,
            (
                x1,
                label_y,
            ),
            self.font,
            0.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    # --------------------------------------------------
    # Draw total people summary
    # --------------------------------------------------

    def _draw_summary(
        self,
        frame,
        total_people,
    ):

        if total_people is None:

            text = "Total People: N/A"

        else:

            text = (
                f"Total People: "
                f"{total_people}"
            )

        (
            text_width,
            text_height,
        ), baseline = cv2.getTextSize(
            text,
            self.font,
            0.9,
            2,
        )

        # --------------------------------------------------
        # Summary background
        # --------------------------------------------------

        cv2.rectangle(
            frame,
            (10, 10),
            (
                25 + text_width,
                25 + text_height,
            ),
            (40, 40, 40),
            -1,
        )

        # --------------------------------------------------
        # Summary text
        # --------------------------------------------------

        cv2.putText(
            frame,
            text,
            (
                18,
                18 + text_height,
            ),
            self.font,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    # --------------------------------------------------
    # Annotate complete frame
    # --------------------------------------------------

    def annotate(
        self,
        frame,
        detections,
        zones,
        result,
    ):

        if frame is None:

            raise ValueError(
                "Frame cannot be None."
            )

        # --------------------------------------------------
        # Never modify original frame
        # --------------------------------------------------

        annotated = frame.copy()

        # --------------------------------------------------
        # Draw people
        # --------------------------------------------------

        for detection in detections:

            self._draw_detection(
                annotated,
                detection,
            )

        # --------------------------------------------------
        # Map zone results
        # --------------------------------------------------

        zone_results_by_id = {
            zone_result.zone_id:
                zone_result
            for zone_result in result.zones
        }

        # --------------------------------------------------
        # Draw zones
        # --------------------------------------------------

        for zone in zones:

            zone_result = (
                zone_results_by_id.get(
                    zone["zone_id"]
                )
            )

            if zone_result is None:
                continue

            self._draw_zone(
                annotated,
                zone,
                zone_result,
            )

        # --------------------------------------------------
        # Draw whole-frame summary LAST
        # --------------------------------------------------

        self._draw_summary(
            annotated,
            result.total_people,
        )

        return annotated