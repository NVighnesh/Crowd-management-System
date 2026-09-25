from pathlib import Path
from urllib.parse import urlparse

from src.config.settings import resolve_path


class ConfigValidator:

    @staticmethod
    def validate(config):
        if not isinstance(config, dict):
            raise ValueError(
                "Configuration must be a dictionary."
            )

        # --------------------------------------------------
        # Required top-level sections
        # --------------------------------------------------

        required_sections = [
            "system",
            "cameras",
            "inference",
            "tracking",
            "counting",
            "processing",
        ]

        for section in required_sections:
            if section not in config:
                raise ValueError(
                    f"Missing configuration section: {section}"
                )

        ConfigValidator._validate_system(
            config["system"]
        )

        ConfigValidator._validate_cameras(
            config["cameras"]
        )

        ConfigValidator._validate_inference(
            config["inference"]
        )

        ConfigValidator._validate_tracking(
            config["tracking"]
        )

        ConfigValidator._validate_counting(
            config["counting"]
        )

        ConfigValidator._validate_processing(
            config["processing"]
        )
        ConfigValidator._validate_security(
            config.get("security", {})
        )

        return True

    # ======================================================
    # SYSTEM
    # ======================================================

    @staticmethod
    def _validate_system(system):

        if not isinstance(system, dict):
            raise ValueError(
                "system configuration must be a dictionary."
            )

        if not system.get("name"):
            raise ValueError(
                "system.name is required."
            )

        if not system.get("version"):
            raise ValueError(
                "system.version is required."
            )

    # ======================================================
    # CAMERAS
    # ======================================================

    @staticmethod
    def _validate_cameras(cameras):

        if not isinstance(cameras, list):
            raise ValueError(
                "cameras configuration must be a list."
            )

        if not cameras:
            raise ValueError(
                "At least one camera must be configured."
            )

        camera_ids = set()

        for camera in cameras:

            if not isinstance(camera, dict):
                raise ValueError(
                    "Each camera configuration must be a dictionary."
                )

            # ----------------------------------------------
            # Camera ID
            # ----------------------------------------------

            camera_id = camera.get("id")

            if not camera_id:
                raise ValueError(
                    "Each camera must have an id."
                )

            if camera_id in camera_ids:
                raise ValueError(
                    f"Duplicate camera ID detected: {camera_id}"
                )

            camera_ids.add(camera_id)

            # ----------------------------------------------
            # Source
            # ----------------------------------------------

            source_type = camera.get("source_type")

            if source_type not in {
                "file",
                "rtsp",
                "drone",
            }:
                raise ValueError(
                    f"Unsupported source type for "
                    f"{camera_id}: {source_type}"
                )

            source = camera.get("source")

            if not source:
                raise ValueError(
                    f"Camera {camera_id} must have a source."
                )

            if source_type == "rtsp":
                parsed_source = urlparse(str(source))
                if (
                    parsed_source.scheme.lower()
                    not in {"rtsp", "rtsps"}
                    or not parsed_source.hostname
                ):
                    raise ValueError(
                        f"Camera {camera_id} must have a valid RTSP URL."
                    )

            if source_type == "drone":
                parsed_source = urlparse(str(source))
                if parsed_source.scheme.lower() in {"rtsp", "rtsps"}:
                    if not parsed_source.hostname:
                        raise ValueError(
                            f"Camera {camera_id} must have a valid "
                            "drone RTSP URL."
                        )
                elif not resolve_path(source).is_file():
                    raise ValueError(
                        f"Drone camera source file not found "
                        f"for {camera_id}: {source}"
                    )

            # ----------------------------------------------
            # Zone configuration
            # ----------------------------------------------

            zones_config = camera.get(
                "zones_config"
            )

            if not zones_config and source_type != "drone":
                raise ValueError(
                    f"Camera {camera_id} must have "
                    f"a zones_config."
                )

            if zones_config:
                zone_path = resolve_path(
                    zones_config
                )

                if not zone_path.is_file():
                    raise ValueError(
                        f"Zone configuration file not found "
                        f"for {camera_id}: {zones_config}"
                    )

            # ----------------------------------------------
            # Enabled
            # ----------------------------------------------

            enabled = camera.get(
                "enabled",
                True,
            )

            if not isinstance(enabled, bool):
                raise ValueError(
                    f"Camera {camera_id}.enabled "
                    f"must be true or false."
                )

            # ----------------------------------------------
            # File loop option
            # ----------------------------------------------

            if source_type == "file":

                loop = camera.get(
                    "loop",
                    False,
                )

                if not isinstance(loop, bool):
                    raise ValueError(
                        f"Camera {camera_id}.loop "
                        f"must be true or false."
                    )

    # ======================================================
    # INFERENCE
    # ======================================================

    @staticmethod
    def _validate_inference(inference):

        if not isinstance(inference, dict):
            raise ValueError(
                "inference configuration must be a dictionary."
            )

        # ----------------------------------------------
        # Model
        # ----------------------------------------------

        model = inference.get("model")

        if not model:
            raise ValueError(
                "inference.model is required."
            )

        model_path = resolve_path(model)

        if not model_path.is_file():
            raise ValueError(
                f"Inference model not found: {model}"
            )

        # ----------------------------------------------
        # Backend
        # ----------------------------------------------

        backend = inference.get(
            "backend",
            "ultralytics",
        )

        if not isinstance(backend, str):
            raise ValueError(
                "inference.backend must be a string."
            )

        # ----------------------------------------------
        # Device
        # ----------------------------------------------

        device = inference.get(
            "device",
            "auto",
        )

        if not isinstance(device, str):
            raise ValueError(
                "inference.device must be a string."
            )

        # ----------------------------------------------
        # Task
        # ----------------------------------------------

        task = inference.get(
            "task",
            "detect",
        )

        if task != "detect":
            raise ValueError(
                f"Unsupported inference task: {task}"
            )

        # ----------------------------------------------
        # Image size
        # ----------------------------------------------

        image_size = inference.get(
            "image_size"
        )

        if not isinstance(
            image_size,
            int,
        ):
            raise ValueError(
                "inference.image_size must be an integer."
            )

        if image_size <= 0:
            raise ValueError(
                "inference.image_size must be greater than zero."
            )

        # ----------------------------------------------
        # Confidence
        # ----------------------------------------------

        confidence = inference.get(
            "confidence"
        )

        if not isinstance(
            confidence,
            (int, float),
        ):
            raise ValueError(
                "inference.confidence must be a number."
            )

        if not 0 < confidence <= 1:
            raise ValueError(
                "inference.confidence must be "
                "greater than 0 and at most 1."
            )

    # ======================================================
    # TRACKING
    # ======================================================

    @staticmethod
    def _validate_tracking(tracking):

        if not isinstance(tracking, dict):
            raise ValueError(
                "tracking configuration must be a dictionary."
            )

        enabled = tracking.get(
            "enabled",
            False,
        )

        if not isinstance(enabled, bool):
            raise ValueError(
                "tracking.enabled must be true or false."
            )

        if enabled:

            tracker = tracking.get(
                "tracker"
            )

            if not tracker:
                raise ValueError(
                    "tracking.tracker is required "
                    "when tracking is enabled."
                )

            if not isinstance(
                tracker,
                str,
            ):
                raise ValueError(
                    "tracking.tracker must be a string."
                )

    # ======================================================
    # COUNTING
    # ======================================================

    @staticmethod
    def _validate_counting(counting):

        if not isinstance(counting, dict):
            raise ValueError(
                "counting configuration must be a dictionary."
            )

        # ----------------------------------------------
        # Whole-frame counting
        # ----------------------------------------------

        whole_frame = counting.get(
            "whole_frame"
        )

        if not isinstance(
            whole_frame,
            dict,
        ):
            raise ValueError(
                "counting.whole_frame must be a dictionary."
            )

        whole_frame_enabled = whole_frame.get(
            "enabled"
        )

        if not isinstance(
            whole_frame_enabled,
            bool,
        ):
            raise ValueError(
                "counting.whole_frame.enabled "
                "must be true or false."
            )

        whole_frame_mode = whole_frame.get(
            "mode"
        )

        if not isinstance(
            whole_frame_mode,
            str,
        ):
            raise ValueError(
                "counting.whole_frame.mode "
                "must be a string."
            )

        if whole_frame_mode not in {
            "detection",
            "tracked_active",
        }:
            raise ValueError(
                "Unsupported whole-frame counting mode: "
                f"{whole_frame_mode}. "
                "Supported modes: "
                "detection, tracked_active"
            )

        # ----------------------------------------------
        # Zone counting
        # ----------------------------------------------

        zones = counting.get(
            "zones"
        )

        if not isinstance(
            zones,
            dict,
        ):
            raise ValueError(
                "counting.zones must be a dictionary."
            )

        zones_enabled = zones.get(
            "enabled"
        )

        if not isinstance(
            zones_enabled,
            bool,
        ):
            raise ValueError(
                "counting.zones.enabled "
                "must be true or false."
            )

        point_mode = zones.get(
            "point",
            "bottom_center",
        )

        if point_mode not in {
            "bottom_center",
            "center",
        }:
            raise ValueError(
                "Unsupported counting.zones.point: "
                f"{point_mode}. "
                "Supported modes: "
                "bottom_center, center"
            )

    # ======================================================
    # SECURITY
    # ======================================================

    @staticmethod
    def _validate_security(security):
        if not isinstance(security, dict):
            raise ValueError("security configuration must be a dictionary.")
        enabled = security.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("security.enabled must be true or false.")
        expiry = security.get("token_expiry_minutes", 60)
        if not isinstance(expiry, int) or expiry < 1:
            raise ValueError(
                "security.token_expiry_minutes must be a positive integer."
            )
        stream_expiry = security.get("stream_token_expiry_seconds", 300)
        if not isinstance(stream_expiry, int) or stream_expiry < 30:
            raise ValueError(
                "security.stream_token_expiry_seconds must be at least 30."
            )
        rate_limit = security.get("login_rate_limit", {})
        if not isinstance(rate_limit, dict):
            raise ValueError("security.login_rate_limit must be a dictionary.")
        for key in ("max_failures", "window_seconds", "lockout_seconds"):
            value = rate_limit.get(key, 5 if key == "max_failures" else 300)
            if not isinstance(value, int) or value < 1:
                raise ValueError(
                    f"security.login_rate_limit.{key} must be positive."
                )

    # ======================================================
    # PROCESSING
    # ======================================================

    @staticmethod
    def _validate_processing(processing):

        if not isinstance(
            processing,
            dict,
        ):
            raise ValueError(
                "processing configuration "
                "must be a dictionary."
            )

        # ----------------------------------------------
        # Inference FPS
        # ----------------------------------------------

        inference_fps = processing.get(
            "inference_fps"
        )

        if not isinstance(
            inference_fps,
            (int, float),
        ):
            raise ValueError(
                "processing.inference_fps "
                "must be a number."
            )

        if inference_fps <= 0:
            raise ValueError(
                "processing.inference_fps "
                "must be greater than zero."
            )

        stream_fps = processing.get("stream_fps", 10)
        if not isinstance(stream_fps, (int, float)) or stream_fps <= 0:
            raise ValueError(
                "processing.stream_fps must be greater than zero."
            )

        jpeg_quality = processing.get("jpeg_quality", 80)
        if not isinstance(jpeg_quality, int) or not 1 <= jpeg_quality <= 100:
            raise ValueError(
                "processing.jpeg_quality must be an integer between 1 and 100."
            )

        # ----------------------------------------------
        # Maximum result age
        # ----------------------------------------------

        max_result_age = processing.get(
            "max_result_age_seconds"
        )

        if not isinstance(
            max_result_age,
            (int, float),
        ):
            raise ValueError(
                "processing.max_result_age_seconds "
                "must be a number."
            )

        if max_result_age <= 0:
            raise ValueError(
                "processing.max_result_age_seconds "
                "must be greater than zero."
            )

        # ----------------------------------------------
        # Camera stale timeout
        # ----------------------------------------------

        stale_timeout = processing.get(
            "camera_stale_timeout_seconds"
        )

        if not isinstance(
            stale_timeout,
            (int, float),
        ):
            raise ValueError(
                "processing.camera_stale_timeout_seconds "
                "must be a number."
            )

        if stale_timeout <= 0:
            raise ValueError(
                "processing.camera_stale_timeout_seconds "
                "must be greater than zero."
            )

        for key in (
            "recovery_max_attempts",
            "frame_failure_threshold",
            "stale_recovery_threshold",
        ):
            value = processing.get(key)
            if value is not None and (
                not isinstance(value, int) or value < 1
            ):
                raise ValueError(
                    f"processing.{key} must be a positive integer."
                )

        for key in (
            "recovery_retry_delay_seconds",
            "recovery_backoff_multiplier",
            "recovery_poll_interval_seconds",
        ):
            value = processing.get(key)
            if value is not None and (
                not isinstance(value, (int, float)) or value <= 0
            ):
                raise ValueError(
                    f"processing.{key} must be greater than zero."
                )

        for key in (
            "rtsp_open_timeout_ms",
            "rtsp_read_timeout_ms",
        ):
            value = processing.get(key)
            if value is not None and (
                not isinstance(value, int) or value <= 0
            ):
                raise ValueError(
                    f"processing.{key} must be a positive integer."
                )

        backend = processing.get("rtsp_backend", "any")
        if backend not in {"any", "ffmpeg", "gstreamer"}:
            raise ValueError(
                "processing.rtsp_backend must be any, ffmpeg, or gstreamer."
            )
