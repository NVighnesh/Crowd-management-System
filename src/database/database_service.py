from src.database.database import Database
from src.database.camera_repository import CameraRepository
from src.database.crowd_repository import CrowdRepository
from src.database.zone_repository import ZoneRepository
from src.database.alert_repository import AlertRepository


class DatabaseService:

    def __init__(
        self,
        database: Database | None = None,
    ):
        self.database = (
            database
            if database is not None
            else Database()
        )

        self.database.initialize()

        self.camera_repository = (
            CameraRepository(
                self.database
            )
        )

        self.crowd_repository = (
            CrowdRepository(
                self.database
            )
        )

        self.zone_repository = (
            ZoneRepository(
                self.database
            )
        )

        self.alert_repository = (
            AlertRepository(
                self.database
            )
        )

    # --------------------------------------------------
    # Camera history
    # --------------------------------------------------

    def get_camera(
        self,
        camera_id: str,
    ):
        return self.camera_repository.get(
            camera_id
        )

    def get_cameras(self):
        return self.camera_repository.get_all()

    # --------------------------------------------------
    # Crowd history
    # --------------------------------------------------

    def get_latest_crowd(
        self,
        camera_id: str,
    ):
        return self.crowd_repository.get_latest(
            camera_id
        )

    def get_recent_crowd(
        self,
        camera_id: str,
        limit: int = 100,
    ):
        return self.crowd_repository.get_recent(
            camera_id=camera_id,
            limit=limit,
        )

    def get_crowd_history(
        self,
        camera_id,
        start_timestamp=None,
        end_timestamp=None,
        limit=1000,
    ):
        return self.crowd_repository.get_history(
            camera_id,
            start_timestamp,
            end_timestamp,
            limit,
        )

    def get_crowd_analytics(
        self,
        camera_id,
        start_timestamp=None,
        end_timestamp=None,
    ):
        return self.crowd_repository.get_analytics(
            camera_id,
            start_timestamp,
            end_timestamp,
        )

    # --------------------------------------------------
    # Zone history
    # --------------------------------------------------

    def get_latest_zone(
        self,
        camera_id: str,
        zone_id: str,
    ):
        return self.zone_repository.get_latest(
            camera_id=camera_id,
            zone_id=zone_id,
        )

    def get_recent_zone(
        self,
        camera_id: str,
        zone_id: str,
        limit: int = 100,
    ):
        return self.zone_repository.get_recent(
            camera_id=camera_id,
            zone_id=zone_id,
            limit=limit,
        )

    def get_zone_history(
        self,
        camera_id,
        zone_id=None,
        start_timestamp=None,
        end_timestamp=None,
        limit=1000,
    ):
        return self.zone_repository.get_history(
            camera_id,
            zone_id,
            start_timestamp,
            end_timestamp,
            limit,
        )

    def get_recent_zone_history(
        self,
        camera_id: str,
        limit_per_zone: int = 20,
    ):
        return self.zone_repository.get_recent_by_camera(
            camera_id,
            limit_per_zone,
        )

    def get_zone_analytics(
        self,
        camera_id,
        zone_id=None,
        start_timestamp=None,
        end_timestamp=None,
    ):
        return self.zone_repository.get_analytics(
            camera_id,
            zone_id,
            start_timestamp,
            end_timestamp,
        )

    # --------------------------------------------------
    # Alert history
    # --------------------------------------------------

    def get_alerts(
        self,
        limit: int = 1000,
    ):
        return self.alert_repository.get_all(
            limit=limit
        )

    def get_latest_alert(self):
        return self.alert_repository.get_latest()

    def get_camera_alerts(
        self,
        camera_id: str,
        limit: int = 1000,
    ):
        return self.alert_repository.get_by_camera(
            camera_id=camera_id,
            limit=limit,
        )

    def get_zone_alerts(
        self,
        camera_id: str,
        zone_id: str,
        limit: int = 1000,
    ):
        return self.alert_repository.get_by_zone(
            camera_id=camera_id,
            zone_id=zone_id,
            limit=limit,
        )

    def get_alert_count(self):
        return self.alert_repository.count()

    def get_unresolved_alert_count(self):
        return self.alert_repository.count_unresolved()