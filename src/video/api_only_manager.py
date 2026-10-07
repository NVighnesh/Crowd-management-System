"""Database-backed camera facade used when inference runs in another process."""

from dataclasses import dataclass
from datetime import datetime
import threading

from src.alerts.alert import Alert
from src.database.database_service import DatabaseService


@dataclass
class StoredResult:
    camera_id: str
    total_people: int | None
    zones: list


class ApiOnlyCameraManager:
    """Preserve camera/history API contracts without starting OpenCV or YOLO."""

    runtime_mode = "API_ONLY"

    def __init__(self, camera_manager, database_service: DatabaseService):
        self.camera_manager = camera_manager
        self.database = database_service.database
        self.camera_repository = database_service.camera_repository
        self.crowd_repository = database_service.crowd_repository
        self.zone_repository = database_service.zone_repository
        self.alert_repository = database_service.alert_repository
        self.cameras = camera_manager.cameras
        self.workers = {}
        self.pipelines = {}
        self.processing_config = {}
        self._manager_lock = threading.RLock()

    def setup(self):
        return None

    def _camera_record(self, camera):
        return {
            "id": camera["id"],
            "name": camera.get("name", camera["id"]),
            "source_type": camera["source_type"],
            "source": camera["source"],
            "loop": bool(camera.get("loop", True)),
            "enabled": bool(camera.get("enabled", True)),
            "owner_id": camera.get("owner_id"),
        }

    def _sync(self):
        stored = self.camera_repository.get_all()
        cameras = [
            self._camera_record(
                {
                    "id": item["camera_id"],
                    "name": item.get("camera_name", item["camera_id"]),
                    "source_type": item["source_type"],
                    "source": item["source"],
                    "loop": item.get("loop", 1),
                    "enabled": item.get("enabled", 1),
                    "owner_id": item.get("owner_id"),
                }
            )
            for item in stored
        ]
        self.camera_manager.replace_cameras(cameras)
        self.cameras = self.camera_manager.cameras

    def get_camera(self, camera_id):
        return self.camera_manager.get_camera(camera_id)

    def add_camera(self, camera):
        with self._manager_lock:
            if self.camera_repository.get(camera["id"]) is not None:
                raise ValueError(f"Camera '{camera['id']}' already exists.")
            self.database.execute(
                """
                INSERT INTO cameras (
                    camera_id, camera_name, source_type, source,
                    loop, enabled, owner_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    camera["id"],
                    camera["name"],
                    camera["source_type"],
                    camera["source"],
                    camera["loop"],
                    camera["enabled"],
                    camera.get("owner_id"),
                ),
            )
            self._sync()

    def update_camera(self, camera):
        with self._manager_lock:
            existing = self.camera_repository.get(camera["id"])
            if existing is None:
                raise ValueError(f"Camera '{camera['id']}' does not exist.")

            source_replaced = (
                existing["source"] != camera["source"]
                or existing["source_type"] != camera["source_type"]
            )
            with self.database.transaction() as connection:
                if source_replaced:
                    connection.execute(
                        "DELETE FROM alerts WHERE camera_id = %s",
                        (camera["id"],),
                    )
                    connection.execute(
                        "DELETE FROM zone_results WHERE camera_id = %s",
                        (camera["id"],),
                    )
                    connection.execute(
                        "DELETE FROM zones WHERE camera_id = %s",
                        (camera["id"],),
                    )
                connection.execute(
                    """
                    UPDATE cameras
                    SET camera_name = %s, source_type = %s, source = %s,
                        loop = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE camera_id = %s
                    """,
                    (
                        camera["name"],
                        camera["source_type"],
                        camera["source"],
                        camera["loop"],
                        camera["enabled"],
                        camera["id"],
                    ),
                )
            self._sync()

    def enable_camera(self, camera_id):
        self._set_enabled(camera_id, True)

    def disable_camera(self, camera_id):
        self._set_enabled(camera_id, False)

    def restart_camera(self, camera_id):
        if self.camera_repository.get(camera_id) is None:
            raise ValueError(f"Camera '{camera_id}' does not exist.")

    def _set_enabled(self, camera_id, enabled):
        if self.camera_repository.get(camera_id) is None:
            raise ValueError(f"Camera '{camera_id}' does not exist.")
        self.database.execute(
            "UPDATE cameras SET enabled = %s, updated_at = CURRENT_TIMESTAMP "
            "WHERE camera_id = %s",
            (enabled, camera_id),
        )
        self._sync()

    def refresh_camera_zones(self, camera_id):
        raise ValueError(
            f"Camera '{camera_id}' is not running in API_ONLY mode."
        )

    def get_latest_result_with_timestamp(self, camera_id):
        row = self.crowd_repository.get_latest(camera_id)
        if row is None:
            return None
        timestamp = row["result_timestamp"]
        if not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(str(timestamp))
        return {
            "result": StoredResult(
                camera_id=camera_id,
                total_people=row["total_people"],
                zones=[],
            ),
            "timestamp": timestamp.timestamp(),
        }

    def get_latest_result(self, camera_id):
        entry = self.get_latest_result_with_timestamp(camera_id)
        return entry["result"] if entry else None

    def get_latest_results(self):
        return []

    def get_all_alerts(self):
        rows = self.alert_repository.get_all()
        return [
            Alert(
                alert_id=row["id"],
                camera_id=row["camera_id"],
                zone_id=row["zone_id"],
                zone_name=row["zone_name"],
                previous_status=row["previous_status"],
                current_status=row["current_status"],
                count=row["count"],
                threshold=row["threshold"],
                timestamp=(
                    row["alert_timestamp"]
                    if isinstance(row["alert_timestamp"], datetime)
                    else datetime.fromisoformat(str(row["alert_timestamp"]))
                ),
                alert_type=row["alert_type"],
                active=bool(row.get("active", 0)),
                resolved=bool(row.get("resolved", 0)),
            )
            for row in rows
        ]

    def get_latest_alert(self):
        alerts = self.get_all_alerts()
        return alerts[0] if alerts else None

    def get_camera_alerts(self, camera_id):
        return [item for item in self.get_all_alerts() if item.camera_id == camera_id]

    def get_zone_alerts(self, camera_id, zone_id):
        return [
            item
            for item in self.get_camera_alerts(camera_id)
            if item.zone_id == zone_id
        ]

    def release(self):
        return None
