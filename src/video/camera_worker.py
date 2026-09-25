import threading
import time

from src.video.frame_buffer import LatestFrameBuffer


class CameraWorker:

    def __init__(
        self,
        pipeline,
        inference_fps=5,
        camera_stale_timeout_seconds=5,
        result_callback=None,
        frame_failure_threshold=3,
    ):

        self.pipeline = pipeline

        self.inference_fps = inference_fps
        self.camera_stale_timeout_seconds = (
            camera_stale_timeout_seconds
        )

        self.result_callback = result_callback
        self.frame_failure_threshold = max(
            1,
            int(frame_failure_threshold),
        )

        # --------------------------------------------------
        # Worker state
        # --------------------------------------------------

        self.running = False
        self.started_at = None

        self.capture_thread = None
        self.inference_thread = None

        self.next_inference_time = None
        self._last_inferred_frame_sequence = 0

        # --------------------------------------------------
        # Camera state
        # --------------------------------------------------

        self.status = "STARTING"
        self.processing_status = "STARTING"

        self.last_error = None

        self.last_frame_time = None
        self.last_inference_time = None
        self.consecutive_frame_failures = 0

        # --------------------------------------------------
        # Metrics
        # --------------------------------------------------

        self.total_frames_captured = 0
        self.total_inferences = 0

        self.total_capture_time = 0.0
        self.total_inference_time = 0.0

        # Existing compatibility counters
        self.capture_count = 0
        self.inference_count = 0

        # --------------------------------------------------
        # Latest frame buffer
        # --------------------------------------------------

        self.frame_buffer = LatestFrameBuffer()

        # --------------------------------------------------
        # Thread safety
        # --------------------------------------------------

        self._state_lock = threading.Lock()

    # --------------------------------------------------
    # Start
    # --------------------------------------------------

    def start(self):

        if self.running:
            return

        self.running = True
        self.started_at = time.time()

        self.status = "STARTING"
        self.processing_status = "STARTING"

        self.last_error = None

        self.capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
        )

        self.inference_thread = threading.Thread(
            target=self._inference_loop,
            daemon=True,
        )

        self.capture_thread.start()
        self.inference_thread.start()

    # --------------------------------------------------
    # Capture loop
    # --------------------------------------------------

    def _capture_loop(self):

        while self.running:

            start_time = time.time()

            try:
                success, frame = self.pipeline.source.read()
            except Exception as exc:
                success, frame = False, None
                read_error = str(exc)
            else:
                read_error = None

            elapsed = time.time() - start_time

            with self._state_lock:

                self.total_capture_time += elapsed

                if success and frame is not None:

                    self.total_frames_captured += 1
                    self.capture_count += 1

                    self.last_frame_time = time.time()
                    self.consecutive_frame_failures = 0

                    self.status = "ONLINE"

                else:
                    self.consecutive_frame_failures += 1
                    self.status = "DEGRADED"
                    self.processing_status = "DEGRADED"
                    self.last_error = (
                        read_error
                        or "Unable to read frame from source"
                    )
                    if (
                        self.consecutive_frame_failures
                        >= self.frame_failure_threshold
                    ):
                        self.status = "OFFLINE"
                        self.processing_status = "OFFLINE"
                        self.running = False
                        break

            if not success or frame is None:
                time.sleep(0.05)
                continue

            # --------------------------------------------------
            # Store latest frame
            # --------------------------------------------------

            if success and frame is not None:

                self.frame_buffer.update(frame)

    # --------------------------------------------------
    # Inference loop
    # --------------------------------------------------

    def _inference_loop(self):

        interval = 1.0 / self.inference_fps

        self.next_inference_time = time.time()

        while self.running:

            now = time.time()

            if now < self.next_inference_time:

                time.sleep(
                    min(
                        0.01,
                        self.next_inference_time - now,
                    )
                )

                continue

            self.next_inference_time = (
                now + interval
            )

            self._run_inference()

    # --------------------------------------------------
    # Run inference
    # --------------------------------------------------

    def _run_inference(self):

        frame, sequence = (
            self.frame_buffer.get_with_sequence()
        )

        if frame is None:
            return

        if sequence <= self._last_inferred_frame_sequence:
            return

        start_time = time.time()

        try:

            result = self.pipeline.process_frame(
                frame
            )

            elapsed = time.time() - start_time

            with self._state_lock:

                self._last_inferred_frame_sequence = sequence
                self.total_inferences += 1
                self.inference_count += 1

                self.total_inference_time += elapsed

                self.last_inference_time = time.time()

                self.processing_status = "HEALTHY"

                self.last_error = None

            if (
                result is not None
                and self.result_callback is not None
            ):

                self.result_callback(result)

        except Exception as exc:

            with self._state_lock:

                self.processing_status = "ERROR"

                self.last_error = str(exc)

    # --------------------------------------------------
    # Manual inference
    # --------------------------------------------------

    def process_latest_frame(self):

        frame = self.get_latest_frame()

        if frame is None:
            return None

        start_time = time.time()

        try:

            result = self.pipeline.process_frame(
                frame
            )

            elapsed = time.time() - start_time

            with self._state_lock:

                self.total_inferences += 1
                self.inference_count += 1

                self.total_inference_time += elapsed

                self.last_inference_time = time.time()

                self.processing_status = "HEALTHY"

                self.last_error = None

            if (
                result is not None
                and self.result_callback is not None
            ):

                self.result_callback(result)

            return result

        except Exception as exc:

            with self._state_lock:

                self.processing_status = "ERROR"

                self.last_error = str(exc)

            raise

    # --------------------------------------------------
    # Latest raw frame
    # --------------------------------------------------

    def get_latest_frame(self):

        return self.frame_buffer.get()

    # --------------------------------------------------
    # Latest annotated frame
    # --------------------------------------------------

    def get_latest_annotated_frame(self):

        return self.pipeline.get_latest_annotated_frame()

    # --------------------------------------------------
    # Camera health
    # --------------------------------------------------

    def update_health_status(self):

        now = time.time()

        with self._state_lock:

            # --------------------------------------------------
            # Camera status
            # --------------------------------------------------
            #
            # OFFLINE has highest priority because it represents
            # an actual source failure.
            # --------------------------------------------------

            if self.status == "OFFLINE":

                self.status = "OFFLINE"

            elif self.last_frame_time is None:

                if self.running:
                    self.status = "STARTING"

            else:

                frame_age = (
                    now - self.last_frame_time
                )

                if frame_age > (
                    self.camera_stale_timeout_seconds
                ):

                    self.status = "STALE"

                elif self.running:

                    self.status = "ONLINE"

            # --------------------------------------------------
            # Processing status
            # --------------------------------------------------

            if self.processing_status == "OFFLINE":

                self.processing_status = "OFFLINE"

            elif self.last_inference_time is None:

                if self.running:
                    self.processing_status = "STARTING"

            else:

                expected_interval = (
                    1.0 / self.inference_fps
                )

                healthy_limit = (
                    expected_interval * 3
                )

                inference_age = (
                    now - self.last_inference_time
                )

                if inference_age <= healthy_limit:

                    self.processing_status = "HEALTHY"

                elif self.running:

                    self.processing_status = "DEGRADED"

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def get_status(self):

        self.update_health_status()

        with self._state_lock:
            elapsed = (
                time.time() - self.started_at
                if self.started_at is not None
                else 0
            )
            capture_fps = (
                self.total_frames_captured / elapsed
                if elapsed > 0
                else 0.0
            )
            inference_fps = (
                self.total_inferences / elapsed
                if elapsed > 0
                else 0.0
            )

            return {
                "status": self.status,
                "processing_status": (
                    self.processing_status
                ),
                "last_error": self.last_error,
                "last_frame_time": (
                    self.last_frame_time
                ),
                "last_inference_time": (
                    self.last_inference_time
                ),
                "running": self.running,
                "worker_state": (
                    "RUNNING" if self.running else "STOPPED"
                ),
                "capture_fps": capture_fps,
                "inference_fps": inference_fps,
                "average_inference_latency_ms": (
                    self.get_average_latency_ms()
                ),
                "frames_captured": self.total_frames_captured,
                "inferences": self.total_inferences,
                "pipeline_initialized": (
                    self.pipeline is not None
                    and self.pipeline.source is not None
                ),
                "source_open": self._source_is_open(),
                "consecutive_frame_failures": (
                    self.consecutive_frame_failures
                ),
                "source_last_error": getattr(
                    self.pipeline.source,
                    "last_error",
                    None,
                ) if self.pipeline is not None else None,
                "source_last_successful_frame_time": getattr(
                    self.pipeline.source,
                    "last_successful_frame_time",
                    None,
                ) if self.pipeline is not None else None,
                "source_read_failures": getattr(
                    self.pipeline.source,
                    "read_failures",
                    0,
                ) if self.pipeline is not None else 0,
            }

    def _source_is_open(self):
        if self.pipeline is None or self.pipeline.source is None:
            return False
        is_opened = getattr(
            self.pipeline.source,
            "is_opened",
            None,
        )
        return bool(is_opened()) if callable(is_opened) else True

    # --------------------------------------------------
    # Metrics
    # --------------------------------------------------

    def get_capture_fps(
        self,
        elapsed_seconds,
    ):

        if elapsed_seconds <= 0:
            return 0.0

        return (
            self.total_frames_captured
            / elapsed_seconds
        )

    def get_inference_fps(
        self,
        elapsed_seconds,
    ):

        if elapsed_seconds <= 0:
            return 0.0

        return (
            self.total_inferences
            / elapsed_seconds
        )

    def get_average_latency_ms(self):

        if self.total_inferences == 0:
            return 0.0

        return (
            self.total_inference_time
            / self.total_inferences
            * 1000
        )

    # --------------------------------------------------
    # Reset metrics
    # --------------------------------------------------

    def reset_metrics(self):

        with self._state_lock:

            self.total_frames_captured = 0
            self.total_inferences = 0

            self.total_capture_time = 0.0
            self.total_inference_time = 0.0

            self.capture_count = 0
            self.inference_count = 0

            self.last_inference_time = None

    # --------------------------------------------------
    # Stop
    # --------------------------------------------------

    def stop(self):

        self.running = False

        current_thread = threading.current_thread()

        if (
            self.capture_thread is not None
            and self.capture_thread is not current_thread
        ):

            self.capture_thread.join(timeout=2)

        if (
            self.inference_thread is not None
            and self.inference_thread is not current_thread
        ):

            self.inference_thread.join(timeout=2)

        self.capture_thread = None
        self.inference_thread = None
