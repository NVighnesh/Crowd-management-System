import json

from src.database.database import postgres_timestamp

class ZoneRepository:

    def __init__(self, database):
        self.database = database

    # ==================================================
    # Zone configuration
    # ==================================================

    def get_by_camera(self, camera_id: str):
        rows = self.database.fetch_all(
            """
            SELECT
                zone_id,
                camera_id,
                zone_name,
                polygon,
                threshold,
                point,
                enabled,
                created_at,
                updated_at
            FROM zones
            WHERE camera_id = %s
            ORDER BY created_at ASC, zone_id ASC
            """,
            (camera_id,),
        )

        return [
            self._deserialize_zone(row)
            for row in rows
        ]

    def get(
        self,
        camera_id: str,
        zone_id: str,
    ):
        row = self.database.fetch_one(
            """
            SELECT
                zone_id,
                camera_id,
                zone_name,
                polygon,
                threshold,
                point,
                enabled,
                created_at,
                updated_at
            FROM zones
            WHERE camera_id = %s
              AND zone_id = %s
            LIMIT 1
            """,
            (
                camera_id,
                zone_id,
            ),
        )

        if row is None:
            return None

        return self._deserialize_zone(row)

    def save(
        self,
        zone_id: str,
        camera_id: str,
        zone_name: str,
        polygon,
        threshold: int,
        point: str = "bottom_center",
        enabled: bool = True,
    ):
        self.database.execute(
            """
            INSERT INTO zones (
                zone_id,
                camera_id,
                zone_name,
                polygon,
                threshold,
                point,
                enabled
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(camera_id, zone_id)
            DO UPDATE SET
                zone_name = excluded.zone_name,
                polygon = excluded.polygon,
                threshold = excluded.threshold,
                point = excluded.point,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                zone_id,
                camera_id,
                zone_name,
                json.dumps(polygon),
                threshold,
                point,
                1 if enabled else 0,
            ),
        )

    def update(
        self,
        camera_id: str,
        zone_id: str,
        zone_name: str,
        polygon,
        threshold: int,
        point: str = "bottom_center",
        enabled: bool = True,
    ):
        self.database.execute(
            """
            UPDATE zones
            SET
                zone_name = %s,
                polygon = %s,
                threshold = %s,
                point = %s,
                enabled = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE camera_id = %s
              AND zone_id = %s
            """,
            (
                zone_name,
                json.dumps(polygon),
                threshold,
                point,
                1 if enabled else 0,
                camera_id,
                zone_id,
            ),
        )

    def delete(
        self,
        camera_id: str,
        zone_id: str,
    ):
        self.database.execute(
            """
            DELETE FROM zones
            WHERE camera_id = %s
              AND zone_id = %s
            """,
            (
                camera_id,
                zone_id,
            ),
        )

    def delete_by_camera(self, camera_id: str):
        self.database.execute(
            """
            DELETE FROM zones
            WHERE camera_id = %s
            """,
            (camera_id,),
        )

    # ==================================================
    # Zone result history
    # ==================================================

    def save_result(
        self,
        camera_id: str,
        zone_id: str,
        zone_name: str,
        count: int,
        threshold: int,
        status: str,
        result_timestamp: str,
    ):
        self.database.execute(
            """
            INSERT INTO zone_results (
                camera_id,
                zone_id,
                zone_name,
                count,
                threshold,
                status,
                result_timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                camera_id,
                zone_id,
                zone_name,
                count,
                threshold,
                status,
                postgres_timestamp(result_timestamp),
            ),
        )

    def get_latest(
        self,
        camera_id: str,
        zone_id: str,
    ):
        return self.database.fetch_one(
            """
            SELECT
                id,
                camera_id,
                zone_id,
                zone_name,
                count,
                threshold,
                status,
                result_timestamp
            FROM zone_results
            WHERE camera_id = %s
              AND zone_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                camera_id,
                zone_id,
            ),
        )

    def get_recent(
        self,
        camera_id: str,
        zone_id: str,
        limit: int = 100,
    ):
        return self.database.fetch_all(
            """
            SELECT
                id,
                camera_id,
                zone_id,
                zone_name,
                count,
                threshold,
                status,
                result_timestamp
            FROM zone_results
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

    def get_history(
        self,
        camera_id: str,
        zone_id: str | None = None,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
        limit: int = 1000,
    ):
        clauses = ["camera_id = %s"]
        parameters = [camera_id]

        if zone_id is not None:
            clauses.append("zone_id = %s")
            parameters.append(zone_id)

        if start_timestamp is not None:
            clauses.append("result_timestamp >= %s")
            parameters.append(postgres_timestamp(start_timestamp))

        if end_timestamp is not None:
            clauses.append("result_timestamp <= %s")
            parameters.append(postgres_timestamp(end_timestamp))

        parameters.append(limit)

        return self.database.fetch_all(
            f"""
            SELECT
                id,
                camera_id,
                zone_id,
                zone_name,
                count,
                threshold,
                status,
                result_timestamp
            FROM zone_results
            WHERE {" AND ".join(clauses)}
            ORDER BY result_timestamp ASC, id ASC
            LIMIT %s
            """,
            tuple(parameters),
        )

    def get_recent_by_camera(
        self,
        camera_id: str,
        limit_per_zone: int = 20,
    ):
        return self.database.fetch_all(
            """
            SELECT
                ranked.id,
                ranked.camera_id,
                ranked.zone_id,
                ranked.zone_name,
                ranked.count,
                ranked.threshold,
                ranked.status,
                ranked.result_timestamp
            FROM (
                SELECT
                    id,
                    camera_id,
                    zone_id,
                    zone_name,
                    count,
                    threshold,
                    status,
                    result_timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY zone_id
                        ORDER BY result_timestamp DESC, id DESC
                    ) AS row_number
                FROM zone_results
                WHERE camera_id = %s
            ) AS ranked
            WHERE ranked.row_number <= %s
            ORDER BY ranked.zone_id, ranked.result_timestamp ASC, ranked.id ASC
            """,
            (camera_id, limit_per_zone),
        )

    def get_analytics(
        self,
        camera_id: str,
        zone_id: str | None = None,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
    ):
        clauses = ["camera_id = %s"]
        parameters = [camera_id]

        if zone_id is not None:
            clauses.append("zone_id = %s")
            parameters.append(zone_id)

        if start_timestamp is not None:
            clauses.append("result_timestamp >= %s")
            parameters.append(postgres_timestamp(start_timestamp))

        if end_timestamp is not None:
            clauses.append("result_timestamp <= %s")
            parameters.append(postgres_timestamp(end_timestamp))

        where = " AND ".join(clauses)
        summary = self.database.fetch_one(
            f"""
            SELECT
                COUNT(*) AS total_observations,
                MIN(count) AS minimum_count,
                MAX(count) AS maximum_count,
                AVG(count) AS average_count
            FROM zone_results
            WHERE {where}
            """,
            tuple(parameters),
        )
        peak = self.database.fetch_one(
            f"""
            SELECT count AS peak_count, result_timestamp AS peak_timestamp
            FROM zone_results
            WHERE {where}
            ORDER BY count DESC, result_timestamp ASC, id ASC
            LIMIT 1
            """,
            tuple(parameters),
        )
        statuses = self.database.fetch_all(
            f"""
            SELECT status, COUNT(*) AS occurrences
            FROM zone_results
            WHERE {where}
            GROUP BY status
            ORDER BY status ASC
            """,
            tuple(parameters),
        )
        return {
            **dict(summary),
            **(dict(peak) if peak else {}),
            "status_occurrences": {
                row["status"]: row["occurrences"]
                for row in statuses
            },
        }

    @staticmethod
    def _deserialize_zone(row):
        zone = dict(row)

        polygon = zone.get("polygon")

        if isinstance(polygon, str):
            try:
                polygon = json.loads(polygon)
            except json.JSONDecodeError:
                polygon = []

        zone["polygon"] = polygon or []
        zone["enabled"] = bool(zone.get("enabled", 0))

        return zone
