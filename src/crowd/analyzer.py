from datetime import datetime, timezone

from src.crowd.result import (
    CrowdAnalysisResult,
    ZoneResult,
)
from src.crowd.whole_frame_counter import (
    WholeFrameCounter,
)
from src.crowd.threshold import ThresholdEngine
from src.zones.zone_counter import ZoneCounter


class CrowdAnalyzer:

    def __init__(
        self,
        whole_frame_enabled=True,
        whole_frame_mode="detection",
        zones_enabled=True,
        zone_point_mode="bottom_center",
    ):
        # --------------------------------------------------
        # Counting configuration
        # --------------------------------------------------

        self.whole_frame_enabled = (
            whole_frame_enabled
        )

        self.zones_enabled = zones_enabled

        # --------------------------------------------------
        # Counters
        # --------------------------------------------------

        self.whole_frame_counter = (
            WholeFrameCounter(
                mode=whole_frame_mode
            )
        )

        self.zone_counter = ZoneCounter(
            point_mode=zone_point_mode
        )

        # --------------------------------------------------
        # Threshold engine
        # --------------------------------------------------

        self.threshold_engine = (
            ThresholdEngine()
        )

    def analyze(
        self,
        camera_id,
        detections,
        zones,
    ):

        # --------------------------------------------------
        # Whole-frame counting
        # --------------------------------------------------

        if self.whole_frame_enabled:

            total_people = (
                self.whole_frame_counter.count(
                    detections
                )
            )

        else:

            total_people = None

        # --------------------------------------------------
        # Zone counting
        # --------------------------------------------------

        zone_results = []

        if self.zones_enabled:

            zone_counts = (
                self.zone_counter.count(
                    detections,
                    zones,
                )
            )

            for zone in zones:

                zone_id = zone["zone_id"]

                result = zone_counts[
                    zone_id
                ]

                status = (
                    self.threshold_engine.evaluate(
                        result["count"],
                        result["threshold"],
                    )
                )

                zone_results.append(
                    ZoneResult(
                        zone_id=zone_id,
                        name=result["name"],
                        count=result["count"],
                        threshold=result["threshold"],
                        status=status,
                    )
                )

        # --------------------------------------------------
        # Final result
        # --------------------------------------------------

        return CrowdAnalysisResult(
            camera_id=camera_id,
            total_people=total_people,
            zones=zone_results,
            timestamp=datetime.now(
                timezone.utc
            ),
        )