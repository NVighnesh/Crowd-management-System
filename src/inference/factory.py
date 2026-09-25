from src.config.settings import resolve_path
from src.detection.ultralytics_detector import (
    UltralyticsPersonDetector,
)

from src.tracking.ultralytics_tracker import (
    UltralyticsPersonTracker,
)


class InferenceFactory:

    @staticmethod
    def create_engine(
        inference_config,
        tracking_config,
    ):

        backend = inference_config.get(
            "backend",
            "ultralytics",
        )

        tracking_enabled = tracking_config.get(
            "enabled",
            False,
        )

        if backend == "ultralytics":

            if tracking_enabled:

                return UltralyticsPersonTracker(
                    model_path=str(
                        resolve_path(
                            inference_config["model"]
                        )
                    ),
                    confidence=inference_config["confidence"],
                    image_size=inference_config["image_size"],
                    device=inference_config["device"],
                    tracker=tracking_config.get(
                        "tracker",
                        "bytetrack.yaml",
                    ),
                )

            return UltralyticsPersonDetector(
                model_path=str(
                    resolve_path(
                        inference_config["model"]
                    )
                ),
                confidence=inference_config["confidence"],
                image_size=inference_config["image_size"],
                device=inference_config["device"],
            )

        raise ValueError(
            f"Unsupported inference backend: "
            f"{backend}"
        )