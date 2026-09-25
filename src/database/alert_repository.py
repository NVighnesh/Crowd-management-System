from src.database.database import Database, postgres_timestamp


class AlertRepository:

    def __init__(self, database: Database):
        self.database = database

    def save(
        self,
        camera_id: str,
        zone_id: str,
        zone_name: str,
        previous_status: str | None,
        current_status: str,
        count: int,
        threshold: int,
        alert_type: str,
        alert_timestamp,
        active: bool = True,
        resolved: bool = False,
        resolved_timestamp: str | None = None,
    ):
        insert_query = """
            INSERT INTO alerts (
                camera_id,
                zone_id,
                zone_name,
                previous_status,
                current_status,
                count,
                threshold,
                alert_type,
                alert_timestamp,
                active,
                resolved,
                resolved_timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        parameters = (
            camera_id,
            zone_id,
            zone_name,
            previous_status,
            current_status,
            count,
            threshold,
            alert_type,
            postgres_timestamp(alert_timestamp),
            active,
            resolved,
            postgres_timestamp(resolved_timestamp),
        )
        return self.database.execute_insert_returning_id(
            insert_query,
            parameters,
        )

    def resolve_active(
        self,
        camera_id: str,
        zone_id: str,
        resolved_timestamp: str,
    ):
        self.database.execute(
            """
            UPDATE alerts
            SET active = FALSE,
                resolved = TRUE,
                resolved_timestamp = %s
            WHERE camera_id = %s
              AND zone_id = %s
              AND active = TRUE
            """,
            (postgres_timestamp(resolved_timestamp), camera_id, zone_id),
        )

    def get_all(
        self,
        limit: int = 1000,
    ):
        return self.database.fetch_all(
            """
            SELECT
                id,
                id AS alert_id,
                camera_id,
                zone_id,
                zone_name,
                previous_status,
                current_status,
                count,
                threshold,
                alert_type,
                alert_timestamp,
                alert_timestamp AS timestamp,
                active,
                resolved,
                resolved_timestamp
            FROM alerts
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )

    def get_latest(self):
        return self.database.fetch_one(
            """
            SELECT
                id,
                id AS alert_id,
                camera_id,
                zone_id,
                zone_name,
                previous_status,
                current_status,
                count,
                threshold,
                alert_type,
                alert_timestamp,
                alert_timestamp AS timestamp,
                active,
                resolved,
                resolved_timestamp
            FROM alerts
            ORDER BY id DESC
            LIMIT 1
            """
        )

    def get_by_camera(
        self,
        camera_id: str,
        limit: int = 1000,
    ):
        return self.database.fetch_all(
            """
            SELECT
                id,
                id AS alert_id,
                camera_id,
                zone_id,
                zone_name,
                previous_status,
                current_status,
                count,
                threshold,
                alert_type,
                alert_timestamp,
                alert_timestamp AS timestamp,
                active,
                resolved,
                resolved_timestamp
            FROM alerts
            WHERE camera_id = %s
            ORDER BY alert_timestamp DESC, id DESC
            LIMIT %s
            """,
            (
                camera_id,
                limit,
            ),
        )


    def get_by_zone(
        self,
        camera_id: str,
        zone_id: str,
        limit: int = 1000,
    ):
        return self.database.fetch_all(
            """
            SELECT
                id,
                id AS alert_id,
                camera_id,
                zone_id,
                zone_name,
                previous_status,
                current_status,
                count,
                threshold,
                alert_type,
                alert_timestamp,
                alert_timestamp AS timestamp,
                active,
                resolved,
                resolved_timestamp
            FROM alerts
            WHERE camera_id = %s
              AND zone_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (
                camera_id,
                zone_id,
                limit,
            ),
        )

    def count(self):
        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM alerts
            """
        )

        return row["count"]

    def count_unresolved(self):
        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM alerts
            WHERE active = TRUE
              AND resolved = FALSE
            """
        )
        return row["count"]
