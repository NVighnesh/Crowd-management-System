import time


class SystemHealthService:

    def __init__(
        self,
        camera_manager,
        multi_camera_manager,
        database,
        started_at=None,
    ):
        self.camera_manager = camera_manager
        self.multi_camera_manager = multi_camera_manager
        self.database = database
        self.started_at = started_at or time.time()

    def get_camera_health(self, camera_id):
        camera = self.camera_manager.get_camera(camera_id)
        if camera is None:
            return None

        worker = self.multi_camera_manager.workers.get(camera_id)
        if worker is None:
            recovery = getattr(
                self.multi_camera_manager,
                "_recovery_state",
                {},
            ).get(camera_id, {})
            failed = bool(recovery.get("last_error"))
            return {
                "camera_id": camera_id,
                "camera_name": camera.get("name", camera_id),
                "owner_id": camera.get("owner_id", "system"),
                "enabled": bool(camera.get("enabled", True)),
                "status": (
                    "DISABLED"
                    if not camera.get("enabled", True)
                    else "OFFLINE"
                    if failed
                    else "STOPPED"
                ),
                "processing_status": "DISABLED"
                if not camera.get("enabled", True)
                else "ERROR"
                if failed
                else "STOPPED",
                "worker_state": "STOPPED",
                "pipeline_initialized": False,
                "source_open": False,
                "last_frame_time": None,
                "last_inference_time": None,
                "inference_fps": 0.0,
                "average_inference_latency_ms": 0.0,
                "last_error": recovery.get("last_error"),
                "recovery_attempts": recovery.get("attempts", 0),
                "recovery_exhausted": (
                    failed
                    and recovery.get("attempts", 0)
                    >= getattr(
                        self.multi_camera_manager,
                        "_recovery_max_attempts",
                        0,
                    )
                ),
            }

        recovery = getattr(
            self.multi_camera_manager,
            "_recovery_state",
            {},
        ).get(camera_id, {})
        return {
            "camera_id": camera_id,
            "camera_name": camera.get("name", camera_id),
            "owner_id": camera.get("owner_id", "system"),
            "enabled": bool(camera.get("enabled", True)),
            **worker.get_status(),
            "recovery_attempts": recovery.get("attempts", 0),
            "recovery_exhausted": (
                recovery.get("attempts", 0)
                >= getattr(
                    self.multi_camera_manager,
                    "_recovery_max_attempts",
                    0,
                )
                and bool(recovery.get("last_error"))
            ),
        }

    def get_health(self):
        cameras = [
            self.get_camera_health(camera["id"])
            for camera in self.camera_manager.get_all_cameras()
        ]
        enabled = [camera for camera in cameras if camera["enabled"]]
        healthy = [
            camera for camera in enabled
            if camera["status"] == "ONLINE"
            and camera["processing_status"] == "HEALTHY"
        ]
        connection = None
        try:
            connection = self.database.get_connection()
            connection.execute("SELECT 1").fetchone()
            database_status = "UP"
        except Exception as error:
            database_status = "DOWN"
            database_error = str(error)
        else:
            database_error = None
        finally:
            if connection is not None:
                connection.close()
        return {
            "status": "UP" if database_status == "UP" else "DEGRADED",
            "service": "crowd-management",
            "uptime_seconds": time.time() - self.started_at,
            "database": {
                "status": database_status,
                "error": database_error,
            },
            "cameras": cameras,
            "summary": {
                "configured": len(cameras),
                "enabled": len(enabled),
                "healthy": len(healthy),
                "unhealthy": len(enabled) - len(healthy),
            },
        }
