import cv2
import numpy as np


class ZoneCounter:

    def __init__(self, point_mode="bottom_center"):
        supported_modes = {
            "bottom_center",
            "center",
        }

        if point_mode not in supported_modes:
            raise ValueError(
                f"Unsupported zone point mode: {point_mode}. "
                f"Supported modes: {sorted(supported_modes)}"
            )

        self.point_mode = point_mode

    def _get_reference_point(self, bbox):

        x1, y1, x2, y2 = bbox

        if self.point_mode == "bottom_center":

            x = int((x1 + x2) / 2)
            y = int(y2)

            return x, y

        if self.point_mode == "center":

            x = int((x1 + x2) / 2)
            y = int((y1 + y2) / 2)

            return x, y

        raise ValueError(
            f"Unsupported zone point mode: {self.point_mode}"
        )

    def count(self, detections, zones):

        results = {}

        for zone in zones:

            polygon = np.array(
                zone["polygon"],
                dtype=np.int32,
            )

            count = 0

            for detection in detections:

                point = self._get_reference_point(
                    detection.bbox
                )

                inside = cv2.pointPolygonTest(
                    polygon,
                    point,
                    False,
                )

                if inside >= 0:
                    count += 1

            results[zone["zone_id"]] = {
                "name": zone["name"],
                "count": count,
                "threshold": zone["threshold"],
                "threshold_type": zone["threshold_type"],
            }

        return results