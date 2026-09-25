class WholeFrameCounter:

    def __init__(self, mode="detection"):

        supported_modes = {
            "detection",
            "tracked_active",
        }

        if mode not in supported_modes:
            raise ValueError(
                f"Unsupported whole-frame counting mode: "
                f"{mode}. "
                f"Supported modes: "
                f"{sorted(supported_modes)}"
            )

        self.mode = mode

    def count(self, detections) -> int:

        if self.mode == "detection":

            return len(detections)

        if self.mode == "tracked_active":

            return sum(
                1
                for detection in detections
                if detection.track_id is not None
            )

        raise ValueError(
            f"Unsupported whole-frame counting mode: "
            f"{self.mode}"
        )