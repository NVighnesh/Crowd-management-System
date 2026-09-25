from src.config.settings import resolve_path

from src.video.file_source import FileVideoSource
from src.video.rtsp_source import RTSPVideoSource

from src.inference.factory import InferenceFactory

from src.zones.zone_manager import ZoneManager

from src.crowd.analyzer import CrowdAnalyzer

from src.visualization.frame_annotator import FrameAnnotator


class CameraPipeline:

    def __init__(
        self,
        camera_config,
        inference_config,
        tracking_config,
        counting_config=None,
        zones_config=None,
        processing_config=None,
    ):
        self.camera_config = camera_config
        self.inference_config = inference_config
        self.tracking_config = tracking_config
        self.counting_config = counting_config
        self.processing_config = processing_config or {}

        self.zones_config = (
            zones_config
            if zones_config is not None
            else []
        )

        self.source = None
        self.engine = None
        self.zone_manager = None
        self.analyzer = None
        self.annotator = None

        self.last_frame = None
        self.last_annotated_frame = None

    def setup(self):

        source_type = self.camera_config["source_type"]
        source = self.camera_config["source"]

        loop = self.camera_config.get(
            "loop",
            False,
        )

        # --------------------------------------------------
        # Video Source
        # --------------------------------------------------

        if source_type == "file":

            source_path = str(
                resolve_path(source)
            )

            self.source = FileVideoSource(
                source_path,
                loop=loop,
            )

        elif source_type == "rtsp":

            self.source = RTSPVideoSource(
                source,
                open_timeout_ms=self.processing_config.get(
                    "rtsp_open_timeout_ms",
                    10000,
                ),
                read_timeout_ms=self.processing_config.get(
                    "rtsp_read_timeout_ms",
                    10000,
                ),
                backend=self.processing_config.get(
                    "rtsp_backend",
                    "any",
                ),
            )

        elif source_type == "drone":

            source_scheme = str(
                source
            ).split(":", 1)[0].lower()

            if source_scheme in {"rtsp", "rtsps"}:
                self.source = RTSPVideoSource(
                    source,
                    open_timeout_ms=self.processing_config.get(
                        "rtsp_open_timeout_ms",
                        10000,
                    ),
                    read_timeout_ms=self.processing_config.get(
                        "rtsp_read_timeout_ms",
                        10000,
                    ),
                    backend=self.processing_config.get(
                        "rtsp_backend",
                        "any",
                    ),
                )
            else:
                self.source = FileVideoSource(
                    str(resolve_path(source)),
                    loop=loop,
                )

        else:

            raise ValueError(
                f"Unsupported camera source type: "
                f"{source_type}"
            )

        try:
            self.source.open()
            if not self.source.is_opened():
                raise ValueError(
                    f"Unable to open camera source: {source}"
                )
        except Exception:
            self.release()
            raise

        # --------------------------------------------------
        # Inference Engine
        # --------------------------------------------------

        self.engine = InferenceFactory.create_engine(
            inference_config=self.inference_config,
            tracking_config=self.tracking_config,
        )

        # --------------------------------------------------
        # Zone Manager
        # --------------------------------------------------

        self.zone_manager = ZoneManager(
            self.zones_config,
            expected_camera_id=self.camera_config["id"],
        )

        self.zone_manager.load()

        # --------------------------------------------------
        # Crowd Analyzer
        # --------------------------------------------------

        self.analyzer = CrowdAnalyzer(
            whole_frame_enabled=True,
            whole_frame_mode="detection",
            zones_enabled=True,
            zone_point_mode="bottom_center",
        )

        # --------------------------------------------------
        # Frame Annotator
        # --------------------------------------------------

        self.annotator = FrameAnnotator()

        self.last_frame = None
        self.last_annotated_frame = None

    def update_zones(self, zones_config):

        self.zones_config = (
            zones_config
            if zones_config is not None
            else []
        )

        self.zone_manager = ZoneManager(
            self.zones_config,
            expected_camera_id=self.camera_config["id"],
        )

        self.zone_manager.load()

        self.analyzer = CrowdAnalyzer(
            whole_frame_enabled=True,
            whole_frame_mode="detection",
            zones_enabled=True,
            zone_point_mode="bottom_center",
        )

    def process_frame(self, frame=None):

        if self.source is None:
            raise RuntimeError(
                "CameraPipeline is not initialized. "
                "Call setup() before processing frames."
            )

        if self.engine is None:
            raise RuntimeError(
                "Inference engine is not initialized."
            )

        if self.zone_manager is None:
            raise RuntimeError(
                "ZoneManager is not initialized."
            )

        if self.analyzer is None:
            raise RuntimeError(
                "CrowdAnalyzer is not initialized."
            )

        # --------------------------------------------------
        # Get Frame
        # --------------------------------------------------

        if frame is None:
            frame = self.source.read()

        if frame is None:
            return None

        self.last_frame = frame

        # --------------------------------------------------
        # Inference
        # --------------------------------------------------

        detections = self.engine.infer(
            frame
        )

        # --------------------------------------------------
        # Zones
        # --------------------------------------------------

        zones = self.zone_manager.get_zones()

        # --------------------------------------------------
        # Crowd Analysis
        # --------------------------------------------------

        result = self.analyzer.analyze(
            self.camera_config["id"],
            detections,
            zones,
        )

        # --------------------------------------------------
        # Frame Annotation
        # --------------------------------------------------

        self.last_annotated_frame = (
            self.annotator.annotate(
                frame,
                detections,
                zones,
                result,
            )
        )

        return result

    def get_latest_annotated_frame(self):
        return self.last_annotated_frame

    def get_latest_frame(self):
        return self.last_frame

    def release(self):

        if self.source is not None:

            self.source.release()

            self.source = None

        self.engine = None
        self.zone_manager = None
        self.analyzer = None
        self.annotator = None

        self.last_frame = None
        self.last_annotated_frame = None