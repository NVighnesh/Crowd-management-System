import logging
import threading
import time
from urllib.parse import urlparse
from datetime import datetime, timezone

from src.database.database import Database
from src.database.camera_repository import CameraRepository
from src.database.crowd_repository import CrowdRepository
from src.database.zone_repository import ZoneRepository
from src.database.alert_repository import AlertRepository

from src.video.camera_pipeline import CameraPipeline
from src.video.camera_worker import CameraWorker

from src.crowd.result_store import ResultStore
from src.alerts.alert_manager import AlertManager
from src.alerts.alert import Alert
from src.config.settings import resolve_path
from src.storage.supabase_storage import SupabaseStorage


class MultiCameraManager:

    def __init__(
        self,
        cameras,
        inference_config,
        tracking_config,
        counting_config,
        processing_config,
        camera_manager=None,
        storage_service=None,
    ):
        self.cameras = list(cameras)

        self.inference_config = inference_config
        self.tracking_config = tracking_config
        self.counting_config = counting_config
        self.processing_config = processing_config

        self.camera_manager = camera_manager
        self.storage_service = storage_service or SupabaseStorage()

        self.pipelines = {}
        self.workers = {}

        self.result_store = ResultStore()
        self.alert_manager = AlertManager()

        self.database = Database()
        self.database.initialize()

        self.camera_repository = CameraRepository(
            self.database
        )

        self.crowd_repository = CrowdRepository(
            self.database
        )

        self.zone_repository = ZoneRepository(
            self.database
        )

        self.alert_repository = AlertRepository(
            self.database
        )

        self.alert_manager.load_alerts(
            self._load_persisted_alerts()
        )

        self._manager_lock = threading.RLock()
        self._recovery_stop = threading.Event()
        self._recovery_thread = None
        self._recovery_state = {}
        self._recovery_max_attempts = max(0, int(
            self.processing_config.get("recovery_max_attempts", 3)
        ))
        self._recovery_retry_delay = max(0.1, float(
            self.processing_config.get("recovery_retry_delay_seconds", 1.0)
        ))
        self._recovery_backoff_multiplier = max(1.0, float(
            self.processing_config.get("recovery_backoff_multiplier", 2.0)
        ))
        self._recovery_poll_interval = max(0.05, float(
            self.processing_config.get("recovery_poll_interval_seconds", 0.5)
        ))
        self._stale_recovery_threshold = max(1, int(
            self.processing_config.get("stale_recovery_threshold", 2)
        ))
        self._logger = logging.getLogger(__name__)

    def _load_persisted_alerts(self):
        alerts = []
        for row in self.alert_repository.get_all():
            alert_timestamp = row["alert_timestamp"]
            timestamp = (
                alert_timestamp
                if isinstance(alert_timestamp, datetime)
                else datetime.fromisoformat(str(alert_timestamp))
            )
            alerts.append(
                Alert(
                    alert_id=row["id"],
                    camera_id=row["camera_id"],
                    zone_id=row["zone_id"],
                    zone_name=row["zone_name"],
                    previous_status=row["previous_status"],
                    current_status=row["current_status"],
                    count=row["count"],
                    threshold=row["threshold"],
                    timestamp=timestamp,
                    alert_type=row["alert_type"],
                    active=bool(row.get("active", 0)),
                    resolved=bool(row.get("resolved", 0)),
                )
            )
        return list(reversed(alerts))

    # --------------------------------------------------
    # CAMERA MANAGER SYNCHRONIZATION
    # --------------------------------------------------

    def _sync_camera_manager(self):

        if self.camera_manager is not None:

            self.camera_manager.replace_cameras(
                self.cameras
            )

    # --------------------------------------------------
    # SETUP
    # --------------------------------------------------

    def setup(self):

        for camera in self.cameras:

            if not camera.get("enabled", True):
                continue

            try:
                self._start_camera(camera)
            except Exception as exc:
                self._record_recovery_failure(camera["id"], exc)
                self._logger.error(
                    "Camera %s startup failure: %s",
                    camera["id"],
                    exc,
                )

        self._sync_camera_manager()
        self._start_recovery_monitor()

    # --------------------------------------------------
    # START CAMERA
    # --------------------------------------------------

    def _start_camera(self, camera):

        camera = self._normalize_camera(camera)
        camera_id = camera["id"]

        with self._manager_lock:

            if camera_id in self.workers:
                return

            zones_config = (
                self.zone_repository
                .get_by_camera(camera_id)
            )

            pipeline = CameraPipeline(
                camera_config=camera,
                inference_config=(
                    self.inference_config
                ),
                tracking_config=(
                    self.tracking_config
                ),
                counting_config=(
                    self.counting_config
                ),
                zones_config=zones_config,
                processing_config=self.processing_config,
                storage_service=self.storage_service,
            )

            try:
                pipeline.setup()

                worker = CameraWorker(
                    pipeline=pipeline,
                    inference_fps=(
                        self.processing_config[
                            "inference_fps"
                        ]
                    ),
                    camera_stale_timeout_seconds=(
                        self.processing_config[
                            "camera_stale_timeout_seconds"
                        ]
                    ),
                    result_callback=(
                        self._process_result
                    ),
                    frame_failure_threshold=self.processing_config.get(
                        "frame_failure_threshold",
                        3,
                    ),
                )

                self.pipelines[camera_id] = pipeline
                self.workers[camera_id] = worker
                worker.start()
                self._recovery_state.pop(camera_id, None)
            except Exception:
                self.pipelines.pop(camera_id, None)
                self.workers.pop(camera_id, None)
                pipeline.release()
                raise

    def _start_recovery_monitor(self):
        if self._recovery_thread is not None and self._recovery_thread.is_alive():
            return
        self._recovery_stop.clear()
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            name="camera-recovery",
            daemon=True,
        )
        self._recovery_thread.start()

    def _record_recovery_failure(self, camera_id, error):
        state = self._recovery_state.setdefault(
            camera_id,
            {"attempts": 0, "next_retry_at": 0.0, "stale_polls": 0},
        )
        state["last_error"] = str(error)
        state["next_retry_at"] = time.time()

    def _recovery_loop(self):
        while not self._recovery_stop.wait(self._recovery_poll_interval):
            for camera in list(self.cameras):
                if camera.get("enabled", True):
                    self._recover_camera_if_needed(camera)

    def _recover_camera_if_needed(self, camera):
        camera_id = camera["id"]
        with self._manager_lock:
            worker = self.workers.get(camera_id)
            if worker is not None:
                status = worker.get_status()
                if status["status"] == "STALE":
                    state = self._recovery_state.setdefault(
                        camera_id,
                        {"attempts": 0, "next_retry_at": 0.0, "stale_polls": 0},
                    )
                    state["stale_polls"] += 1
                    if state["stale_polls"] < self._stale_recovery_threshold:
                        return
                elif worker.running:
                    self._recovery_state.pop(camera_id, None)
                    return

            state = self._recovery_state.setdefault(
                camera_id,
                {"attempts": 0, "next_retry_at": 0.0, "stale_polls": 0},
            )
            if state["attempts"] >= self._recovery_max_attempts:
                return
            if time.time() < state["next_retry_at"]:
                return

            attempt = state["attempts"] + 1
            state["attempts"] = attempt
            error = (
                worker.last_error
                if worker is not None
                else state.get("last_error", "camera startup failed")
            )
            self._logger.warning(
                "Camera %s recovery attempt %s/%s after failure: %s",
                camera_id,
                attempt,
                self._recovery_max_attempts,
                error,
            )
            self.stop_camera(camera_id)
            try:
                self._start_camera(camera)
            except Exception as exc:
                state["last_error"] = str(exc)
                state["next_retry_at"] = (
                    time.time()
                    + self._recovery_retry_delay
                    * self._recovery_backoff_multiplier ** (attempt - 1)
                )
                self._logger.error(
                    "Camera %s recovery attempt failed: %s",
                    camera_id,
                    exc,
                )
            else:
                self._logger.info("Camera %s recovery succeeded", camera_id)

    @staticmethod
    def _normalize_camera(camera):
        if not isinstance(camera, dict):
            raise ValueError("Camera configuration must be an object.")

        camera_id = str(camera.get("id", "")).strip()
        if not camera_id:
            raise ValueError("Camera ID cannot be empty.")

        source_type = str(camera.get("source_type", "")).strip().lower()
        if source_type not in {"file", "rtsp", "drone"}:
            raise ValueError(
                "source_type must be 'file', 'rtsp' or 'drone'."
            )

        source = str(camera.get("source", "")).strip()
        if not source:
            raise ValueError("Camera source cannot be empty.")

        if source_type == "file" and self.storage_service.is_storage_source(source):
            if not self.storage_service.configured:
                raise ValueError("Supabase Storage is not configured for camera source.")
        elif source_type == "file" and not resolve_path(source).is_file():
            raise ValueError(f"Camera source file not found: {source}")

        if source_type == "rtsp":
            parsed = urlparse(source)
            if parsed.scheme.lower() not in {"rtsp", "rtsps"}:
                raise ValueError(
                    "RTSP source must use the rtsp:// or rtsps:// scheme."
                )
            if not parsed.hostname:
                raise ValueError("RTSP source must include a host.")

        if source_type == "drone":
            parsed = urlparse(source)
            if parsed.scheme.lower() in {"rtsp", "rtsps"}:
                if not parsed.hostname:
                    raise ValueError(
                        "Drone RTSP source must include a host."
                    )
            elif self.storage_service.is_storage_source(source):
                if not self.storage_service.configured:
                    raise ValueError("Supabase Storage is not configured for camera source.")
            elif not resolve_path(source).is_file():
                raise ValueError(
                    f"Drone camera source file not found: {source}"
                )

        return {
            "id": camera_id,
            "name": str(camera.get("name", camera_id)).strip() or camera_id,
            "source_type": source_type,
            "source": source,
            "loop": bool(camera.get("loop", False)),
            "enabled": bool(camera.get("enabled", True)),
            "owner_id": str(camera.get("owner_id", "system")),
        }

    def _persist_camera(self, camera):
        self.camera_repository.save(
            camera_id=camera["id"],
            camera_name=camera["name"],
            source_type=camera["source_type"],
            source=camera["source"],
            enabled=camera["enabled"],
            loop=camera["loop"],
            owner_id=camera.get("owner_id", "system"),
        )

    # --------------------------------------------------
    # LIVE ZONE SYNCHRONIZATION
    # --------------------------------------------------

    def refresh_camera_zones(self, camera_id):

        with self._manager_lock:

            pipeline = self.pipelines.get(
                camera_id
            )

            if pipeline is None:
                raise ValueError(
                    f"Camera '{camera_id}' is not running."
                )

            zones_config = (
                self.zone_repository
                .get_by_camera(camera_id)
            )

            pipeline.update_zones(
                zones_config
            )

            return zones_config

    # --------------------------------------------------
    # ADD CAMERA
    # --------------------------------------------------

    def add_camera(self, camera):

        camera = self._normalize_camera(camera)
        camera_id = camera["id"]

        with self._manager_lock:

            if self.get_camera(camera_id) is not None or self.camera_repository.get(camera_id):

                raise ValueError(
                    f"Camera '{camera_id}' already exists."
                )

            try:
                self._persist_camera(camera)
                self.cameras.append(camera)

                if camera["enabled"]:
                    self._start_camera(camera)

                self._sync_camera_manager()

            except Exception:
                self.stop_camera(camera_id)
                self.camera_repository.delete(camera_id)
                self.cameras = [
                    existing
                    for existing in self.cameras
                    if existing["id"] != camera_id
                ]

                self._sync_camera_manager()

                raise

    # --------------------------------------------------
    # UPDATE CAMERA
    # --------------------------------------------------

    def update_camera(self, camera):

        with self._manager_lock:
            camera_id = str(camera.get("id", "")).strip()
            existing = self.camera_repository.get(camera_id)

            if existing is None:
                raise ValueError(
                    f"Camera '{camera_id}' does not exist."
                )

            previous = self._normalize_camera({
                "id": existing["camera_id"],
                "name": existing.get("camera_name"),
                "source_type": existing["source_type"],
                "source": existing["source"],
                "loop": bool(existing.get("loop", 1)),
                "enabled": bool(existing.get("enabled", 1)),
                "owner_id": existing.get("owner_id", "system"),
            })
            updated = self._normalize_camera({
                "id": camera_id,
                "name": camera.get("name", previous["name"]),
                "source_type": camera.get("source_type", previous["source_type"]),
                "source": camera.get("source", previous["source"]),
                "loop": camera.get("loop", previous["loop"]),
                "enabled": camera.get("enabled", previous["enabled"]),
                "owner_id": previous["owner_id"],
            })

            runtime = self.get_camera(camera_id)
            was_running = camera_id in self.workers
            requires_restart = (
                not runtime
                or any(
                    updated[field] != previous[field]
                    for field in ("source_type", "source", "loop", "enabled")
                )
            )

            try:
                self._persist_camera(updated)
                if runtime is not None:
                    runtime.update(updated)
                else:
                    self.cameras.append(updated)

                if requires_restart:
                    self.stop_camera(camera_id)
                    if updated["enabled"]:
                        self._start_camera(updated)

                self._sync_camera_manager()
            except Exception:
                self.stop_camera(camera_id)
                self._persist_camera(previous)
                if runtime is not None:
                    runtime.clear()
                    runtime.update(previous)
                else:
                    self.cameras = [
                        item for item in self.cameras if item["id"] != camera_id
                    ]
                if was_running and previous["enabled"]:
                    self._start_camera(previous)
                self._sync_camera_manager()
                raise

    def enable_camera(self, camera_id):
        with self._manager_lock:
            camera = self.get_camera(camera_id)
            if camera is None:
                raise ValueError(f"Camera '{camera_id}' does not exist.")
            camera["enabled"] = True
            self._persist_camera(camera)
            if camera_id not in self.workers:
                self._start_camera(camera)
            self._sync_camera_manager()

    def disable_camera(self, camera_id):
        with self._manager_lock:
            camera = self.get_camera(camera_id)
            if camera is None:
                raise ValueError(f"Camera '{camera_id}' does not exist.")
            self.stop_camera(camera_id)
            camera["enabled"] = False
            self._persist_camera(camera)
            self._sync_camera_manager()

    def restart_camera(self, camera_id):
        with self._manager_lock:
            camera = self.get_camera(camera_id)
            if camera is None:
                raise ValueError(f"Camera '{camera_id}' does not exist.")
            camera["enabled"] = True
            self._persist_camera(camera)
            self.stop_camera(camera_id)
            self._start_camera(camera)
            self._sync_camera_manager()

    # --------------------------------------------------
    # DELETE CAMERA
    # --------------------------------------------------

    def delete_camera(self, camera_id):

        with self._manager_lock:
            if self.get_camera(camera_id) is None and not self.camera_repository.get(camera_id):
                raise ValueError(f"Camera '{camera_id}' does not exist.")

            self.stop_camera(camera_id)

            # Camera-owned history and alert rows must be removed in the
            # same transaction as the camera. Discover direct foreign keys
            # from the live schema so this remains correct when deployments
            # contain additional camera-owned tables.
            with self.database.transaction() as connection:
                constraints = connection.execute(
                    """
                    SELECT DISTINCT
                        child.relname AS table_name,
                        child_column.attname AS column_name
                    FROM pg_constraint constraint_row
                    JOIN pg_class child
                      ON child.oid = constraint_row.conrelid
                    JOIN pg_class parent
                      ON parent.oid = constraint_row.confrelid
                    JOIN pg_namespace child_schema
                      ON child_schema.oid = child.relnamespace
                    JOIN pg_attribute child_column
                      ON child_column.attrelid = child.oid
                     AND child_column.attnum = constraint_row.conkey[1]
                    WHERE constraint_row.contype = 'f'
                      AND parent.relname = 'cameras'
                      AND child_schema.nspname = 'public'
                      AND child_column.attname = 'camera_id'
                    ORDER BY child.relname
                    """
                ).fetchall()

                for constraint in constraints:
                    table_name = constraint["table_name"]
                    column_name = constraint["column_name"]
                    if table_name == "cameras":
                        continue
                    connection.execute(
                        f'DELETE FROM "{table_name}" WHERE "{column_name}" = %s',
                        (camera_id,),
                    )

                connection.execute(
                    'DELETE FROM cameras WHERE camera_id = %s',
                    (camera_id,),
                )

            self.cameras = [
                camera
                for camera in self.cameras
                if camera["id"] != camera_id
            ]

            self.result_store.remove(
                camera_id
            )

            self._sync_camera_manager()

    # --------------------------------------------------
    # STOP CAMERA
    # --------------------------------------------------

    def stop_camera(self, camera_id):

        worker = self.workers.pop(
            camera_id,
            None,
        )

        if worker is not None:

            worker.stop()

        pipeline = self.pipelines.pop(
            camera_id,
            None,
        )

        if pipeline is not None:

            pipeline.release()

        self.result_store.remove(
            camera_id
        )

    # --------------------------------------------------
    # GET CAMERAS
    # --------------------------------------------------

    def get_camera(self, camera_id):

        return next(
            (
                camera
                for camera in self.cameras
                if camera["id"] == camera_id
            ),
            None,
        )

    def get_cameras(self):

        return list(
            self.cameras
        )

    # --------------------------------------------------
    # RESULT PROCESSING
    # --------------------------------------------------

    def _process_result(self, result):

        camera_id = result.camera_id

        self.result_store.update(
            camera_id,
            result,
        )

        result_entry = (
            self.result_store
            .get_with_timestamp(camera_id)
        )

        result_timestamp = result_entry[
            "timestamp"
        ]

        self.crowd_repository.save_result(
            camera_id=camera_id,
            total_people=result.total_people,
            result_timestamp=datetime.fromtimestamp(
                result_timestamp,
                tz=timezone.utc,
            ).isoformat(),
        )

        for zone in result.zones:
            self.zone_repository.save_result(
                camera_id=camera_id,
                zone_id=zone.zone_id,
                zone_name=zone.name,
                count=zone.count,
                threshold=zone.threshold,
                status=zone.status,
                result_timestamp=datetime.fromtimestamp(
                    result_timestamp,
                    tz=timezone.utc,
                ).isoformat(),
            )

        alerts = (
            self.alert_manager
            .process_result(result)
        )

        for alert in alerts:

            self.alert_repository.resolve_active(
                camera_id=alert.camera_id,
                zone_id=alert.zone_id,
                resolved_timestamp=alert.timestamp.isoformat(),
            )

            alert.alert_id = self.alert_repository.save(
                camera_id=alert.camera_id,
                zone_id=alert.zone_id,
                zone_name=alert.zone_name,
                previous_status=alert.previous_status,
                current_status=alert.current_status,
                count=alert.count,
                threshold=alert.threshold,
                alert_type=alert.alert_type,
                alert_timestamp=alert.timestamp.isoformat(),
                active=alert.active,
                resolved=alert.resolved,
            )

    # --------------------------------------------------
    # RESULT ACCESS
    # --------------------------------------------------

    def get_latest_result(
        self,
        camera_id,
    ):

        return self.result_store.get(
            camera_id
        )

    def get_latest_result_with_timestamp(
        self,
        camera_id,
    ):

        return (
            self.result_store
            .get_with_timestamp(
                camera_id
            )
        )

    def get_latest_results(self):

        return (
            self.result_store
            .get_all()
        )

    # --------------------------------------------------
    # ALERT ACCESS
    # --------------------------------------------------

    def get_all_alerts(self):

        return (
            self.alert_manager
            .get_all_alerts()
        )

    def get_latest_alert(self):

        return (
            self.alert_manager
            .get_latest_alert()
        )

    def get_camera_alerts(
        self,
        camera_id,
    ):

        return (
            self.alert_manager
            .get_camera_alerts(
                camera_id
            )
        )

    def get_zone_alerts(
        self,
        camera_id,
        zone_id,
    ):

        return (
            self.alert_manager
            .get_zone_alerts(
                camera_id=camera_id,
                zone_id=zone_id,
            )
        )

    # --------------------------------------------------
    # RELEASE
    # --------------------------------------------------

    def release(self):

        with self._manager_lock:
            self._recovery_stop.set()
            if (
                self._recovery_thread is not None
                and self._recovery_thread is not threading.current_thread()
            ):
                self._recovery_thread.join(timeout=2)
            self._recovery_thread = None

            for camera_id in list(
                self.workers.keys()
            ):

                self.stop_camera(
                    camera_id
                )

            self.pipelines.clear()

            self.workers.clear()

            self.result_store.clear()

            self.alert_manager.reset()
